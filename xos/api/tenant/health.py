
# Copyright 2017-present Open Networking Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework import serializers
from rest_framework import generics
from rest_framework import status
from rest_framework.authentication import *
from core.models import *
from django.forms import widgets
from django.conf import settings
from xos.apibase import XOSListCreateAPIView, XOSRetrieveUpdateDestroyAPIView, XOSPermissionDenied
from api.xosapi_helpers import PlusModelSerializer, XOSViewSet, ReadOnlyField
from xos.logger import Logger, logging
from services.lbaas.models import LbService, Loadbalancer, Listener, Pool, Member, Healthmonitor
import json
import uuid
import traceback
import time
import threading

logger = Logger(level=logging.INFO)
settings.DEBUG = False


def get_default_lb_service():
    lb_services = LbService.objects.all()
    if lb_services:
        return lb_services[0]
    return None


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return  # To not perform the csrf check previously happening


def update_loadbalancer_model(health_monitor_id):
    health = Healthmonitor.objects.get(health_monitor_id=health_monitor_id)
    pools = Pool.objects.filter(health_monitor_id=health.id)

    for pool in pools:
        lbs = Loadbalancer.objects.filter(pool_id=pool.id)

        for lb in lbs:
            lb.save(always_update_timestamp=True)

        if lbs.count() == 0:
            logger.info("pool_id does not exist in Loadbalancer table (pool_id=%s)" % pool.id)

    if pools.count() == 0:
        logger.info("health_monitor_id does not exist in Pool table (health_monitor_id=%s)" % health.id)


class HealthSerializer(PlusModelSerializer):
    id = ReadOnlyField()

    class Meta:
        model = Healthmonitor
        fields = ('id', 'name', 'type', 'delay', 'max_retries', 'timeout', 'http_method', 'admin_state_up', 'url_path', 'expected_codes')


class HealthViewSet(XOSViewSet):
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)

    base_name = "healthmonitors"
    method_name = "healthmonitors"
    method_kind = "viewset"
    queryset = Healthmonitor.objects.all()
    serializer_class = HealthSerializer

    @classmethod
    def get_urlpatterns(self, api_path="^"):
        patterns = super(HealthViewSet, self).get_urlpatterns(api_path=api_path)

        return patterns

    def print_message_log(self, msg_type, http):
        if msg_type == "REQ":
            logger.info("###################################################")
            logger.info("[Server] <--- [Client]")
            logger.info("METHOD=%s" % http.method)
            logger.info("URI=%s" % http.path)
            logger.info("%s\n" % http.data)
        elif msg_type == "RSP":
            logger.info("[Server] ---> [Client]")
            logger.info("%s" % http)
            logger.info("Send http rsponse Success..\n")
        else:
            logger.error("Invalid msg_type(%s)" % msg_type)

    def get_rsp_body(self, health_monitor_id):
        health = Healthmonitor.objects.get(health_monitor_id=health_monitor_id)

        root_obj = {}
        health_obj = {}
        pool_list = []
        pool_obj = {}
        root_obj['health_monitor'] = health_obj

        health_obj['name'] = health.name
        health_obj['admin_state_up'] = health.admin_state_up
        health_obj['delay'] = health.delay
        health_obj['expected_codes'] = health.expected_codes
        health_obj['max_retries'] = health.max_retries
        health_obj['http_method'] = health.http_method
        health_obj['timeout'] = health.timeout

        health_obj['pools'] = pool_list
        try:
            pools = Pool.objects.filter(health_monitor_id=health.id)
            for pool in pools:
                pool_obj['status'] = pool.status
                pool_obj['pool_id'] = pool.pool_id
                pool_list.append(pool_obj)
        except Exception as err:
            logger.error("%s (health_monitor_id=%s)" % (str(err), health_monitor_id))

        health_obj['url_path'] = health.url_path
        health_obj['type'] = health.type
        health_obj['health_monitor_id'] = health.health_monitor_id

        return root_obj, health_obj

    def update_health_info(self, health, request):
        required_flag = True
        if request.method == "POST":
            if 'name' not in request.data or request.data["name"] == "":
                required_flag = False
            if 'delay' not in request.data or request.data["delay"] == "":
                required_flag = False
            if 'max_retries' not in request.data or request.data["max_retries"] == "":
                required_flag = False
            if 'timeout' not in request.data or request.data["timeout"] == "":
                required_flag = False
            if 'type' not in request.data or request.data["type"] == "":
                required_flag = False

        if not required_flag:
            logger.error("Mandatory fields not exist!")
            return None

        try:
            if 'name' in request.data and request.data["name"]:
                health.name = request.data["name"]
            if 'admin_state_up' in request.data and request.data["admin_state_up"]:
                health.admin_state_up = request.data["admin_state_up"]
            if 'delay' in request.data and request.data["delay"]:
                health.delay = request.data["delay"]
            if 'expected_codes' in request.data and request.data["expected_codes"]:
                health.expected_codes = request.data["expected_codes"]
            if 'http_method' in request.data and request.data["http_method"]:
                health.http_method = request.data["http_method"]
            if 'max_retries' in request.data and request.data["max_retries"]:
                health.max_retries = request.data["max_retries"]
            if 'timeout' in request.data and request.data["timeout"]:
                health.timeout = request.data["timeout"]
            if 'type' in request.data and request.data["type"]:
                health.type = request.data["type"]
            if 'url_path' in request.data and request.data["url_path"]:
                health.url_path = request.data["url_path"]
        except KeyError as err:
            logger.error("JSON Key error: %s" % str(err))
            return None

        health.save()
        return health

    def check_health_monitor_id(self, health_id):
        try:
            health = Healthmonitor.objects.get(health_monitor_id=health_id)
            return health
        except Exception as err:
            logger.error("%s (health_monitor_id=%s)" % ((str(err), health_id)))
            return None

    # GET: /api/tenant/healthmonitors
    def list(self, request):
        self.print_message_log("REQ", request)
        queryset = self.filter_queryset(self.get_queryset())

        root_obj = {}
        health_list = []
        root_obj['health_monitors'] = health_list

        for health in queryset:
            temp_obj, health_obj = self.get_rsp_body(health.health_monitor_id)
            health_list.append(health_obj)

        self.print_message_log("RSP", root_obj)
        return Response(root_obj)

    # POST: /api/tenant/healthmonitors
    def create(self, request):
        self.print_message_log("REQ", request)

        health = Healthmonitor()
        health.health_monitor_id = str(uuid.uuid4())

        health = self.update_health_info(health, request)
        if health is None:
            return Response("Error: Mandatory fields not exist!", status=status.HTTP_400_BAD_REQUEST)

        rsp_data, health_obj = self.get_rsp_body(health.health_monitor_id)

        lb_thr = threading.Thread(target=update_loadbalancer_model, args=(health.health_monitor_id,))
        lb_thr.start()

        self.print_message_log("RSP", rsp_data)
        return Response(rsp_data, status=status.HTTP_201_CREATED)

    # GET: /api/tenant/healthmonitors/{health_monitor_id}
    def retrieve(self, request, pk=None):
        self.print_message_log("REQ", request)

        if self.check_health_monitor_id(pk) is None:
            return Response("Error: health_monitor_id does not exist in Healthmonitor table", status=status.HTTP_404_NOT_FOUND)

        rsp_data, health_obj = self.get_rsp_body(pk)

        self.print_message_log("RSP", rsp_data)
        return Response(rsp_data)

    # PUT: /api/tenant/healthmonitors/{health_monitor_id}
    def update(self, request, pk=None):
        self.print_message_log("REQ", request)

        health = self.check_health_monitor_id(pk)
        if health is None:
            return Response("Error: health_monitor_id does not exist in Healthmonitor table", status=status.HTTP_404_NOT_FOUND)

        health = self.update_health_info(health, request)
        if health is None:
            return Response("Error: Mandatory fields not exist!", status=status.HTTP_400_BAD_REQUEST)

        rsp_data, health_obj = self.get_rsp_body(pk)

        lb_thr = threading.Thread(target=update_loadbalancer_model, args=(pk,))
        lb_thr.start()

        self.print_message_log("RSP", rsp_data)
        return Response(rsp_data, status=status.HTTP_202_ACCEPTED)

    # DELETE: /api/tenant/healthmonitors/{health_monitor_id}
    def destroy(self, request, pk=None):
        self.print_message_log("REQ", request)

        health = self.check_health_monitor_id(pk)
        if health is None:
            return Response("Error: health_monitor_id does not exist in Healthmonitor table", status=status.HTTP_404_NOT_FOUND)

        try:
            pool = Pool.objects.get(health_monitor_id=health.id)
            return Response("Error: There is a pool that uses healthmontor_id", status=status.HTTP_404_NOT_FOUND)
        except Exception as err:
            logger.error("%s" % str(err))

        lb_thr = threading.Thread(target=update_loadbalancer_model, args=(pk,))
        lb_thr.start()

        Healthmonitor.objects.filter(health_monitor_id=pk).delete()

        self.print_message_log("RSP", "")
        return Response(status=status.HTTP_204_NO_CONTENT)
