
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


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return  # To not perform the csrf check previously happening


def get_default_lb_service():
    lb_services = LbService.objects.all()
    if lb_services:
        return lb_services[0]
    return None


def update_pool_status(pool_id):
    pool_status = ""

    pool = Pool.objects.get(pool_id=pool_id)
    members = Member.objects.filter(memberpool=pool.id)
    if members.count() > 0:
        try:
            pool = Pool.objects.get(pool_id=pool_id)
        except Exception as err:
            logger.error("%s (pool_id=%s)" % ((str(err), request.data["pool_id"])))
            pool_status = "PENDING_CREATE"

        healths = Healthmonitor.objects.filter(id=pool.health_monitor_id)
        if healths.count() > 0:
            pool_status = "ACTIVE"
        else:
            logger.error("Healthmonitor information does not exist (pool_id=%s)" % pool_id)
            pool_status = "PENDING_CREATE"
    else:
        logger.error("Member information does not exist (pool_id=%s)" % pool.id)
        pool_status = "PENDING_CREATE"

    pool = Pool.objects.get(pool_id=pool_id)
    pool.status = pool_status
    pool.save()

    return pool.status


def update_loadbalancer_model(pool_id):
    lbs = Loadbalancer.objects.filter(ptr_pool_id=pool_id)
    for lb in lbs:
        lb.save(always_update_timestamp=True)

    if lbs.count() == 0:
        logger.info("pool_id(%s) does not exist in Loadbalancer table" % pool_id)


class PoolSerializer(PlusModelSerializer):
    id = ReadOnlyField()

    class Meta:
        model = Pool
        fields = ('id', 'ptr_health_monitor_id', 'name', 'health_monitor', 'lb_algorithm', 'protocol', 'description', 'admin_state_up')


class PoolViewSet(XOSViewSet):
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)

    base_name = "pools"
    method_name = "pools"
    method_kind = "viewset"
    queryset = Pool.objects.all()
    serializer_class = PoolSerializer

    @classmethod
    def get_urlpatterns(self, api_path="^"):
        patterns = super(PoolViewSet, self).get_urlpatterns(api_path=api_path)

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

    def get_rsp_body(self, pool_id):
        update_pool_status(pool_id)

        pool = Pool.objects.get(pool_id=pool_id)

        root_obj = {}
        pool_obj = {}
        health_list = []
        member_list = []
        health_status_list = []
        root_obj['pool'] = pool_obj

        pool_obj['status'] = pool.status
        pool_obj['lb_algorithm'] = pool.lb_algorithm
        pool_obj['protocol'] = pool.protocol
        pool_obj['description'] = pool.description

        pool_obj['members'] = member_list
        members = Member.objects.filter(memberpool=pool.id)
        for member in members:
            member_list.append(member.member_id)

        pool_obj['pool_id'] = pool.pool_id
        pool_obj['name'] = pool.name
        pool_obj['admin_state_up'] = pool.admin_state_up

        pool_obj['health_monitors'] = health_list
        healths = Healthmonitor.objects.filter(id=pool.health_monitor_id)
        for health in healths:
            health_list.append(health.health_monitor_id)

        pool_obj['health_monitors_status'] = health_status_list
        healths = Healthmonitor.objects.filter(id=pool.health_monitor_id)
        for health in healths:
            health_status_obj = {}
            health_status_obj['monitor_id'] = health.health_monitor_id
            health_status_obj['status'] = "ACTIVE"
            health_status_obj['status_description'] = None
            health_status_list.append(health_status_obj)

        pool_obj['provider'] = "haproxy"

        return root_obj, pool_obj

    def update_pool_info(self, pool, request):
        required_flag = True
        if request.method == "POST":
            if 'lb_algorithm' not in request.data or request.data["lb_algorithm"] == "":
                required_flag = False
            if 'name' not in request.data or request.data["name"] == "":
                required_flag = False
            if 'protocol' not in request.data or request.data["protocol"] == "":
                required_flag = False

        if not required_flag:
            logger.error("Mandatory fields not exist!")
            return None

        try:
            if 'name' in request.data and request.data["name"]:
                pool.name = request.data["name"]
            if 'health_monitor_id' in request.data:
                pool.health_monitor_id = request.data["health_monitor_id"]
            if 'ptr_health_monitor_id' in request.data:
                pool.ptr_health_monitor_id = request.data["ptr_health_monitor_id"]
            if 'lb_algorithm' in request.data and request.data["lb_algorithm"]:
                pool.lb_algorithm = request.data["lb_algorithm"]
            if 'description' in request.data and request.data["description"]:
                pool.description = request.data["description"]
            if 'protocol' in request.data and request.data["protocol"]:
                pool.protocol = request.data["protocol"]
            if 'admin_state_up' in request.data and request.data["admin_state_up"]:
                pool.admin_state_up = request.data["admin_state_up"]
        except KeyError as err:
            logger.error("JSON Key error: %s" % str(err))
            return None

        if pool.ptr_health_monitor_id is None or pool.ptr_health_monitor_id == "":
            pool.health_monitor_id = None
        else:
            try:
                hm = Healthmonitor.objects.get(health_monitor_id=pool.ptr_health_monitor_id)
                pool.health_monitor_id = hm.id
            except KeyError as err:
                logger.info("health_monitor_id does not exist in Healthmonitor table (health_monitor_id=%s)" % pool.ptr_health_monitor_id)
                return None

        pool.save()
        return pool

    def check_pool_id(self, pool_id):
        try:
            pool = Pool.objects.get(pool_id=pool_id)
            return pool
        except Exception as err:
            logger.error("%s (pool_id=%s)" % ((str(err), pool_id)))
            return None

    # GET: /api/tenant/pools
    def list(self, request):
        self.print_message_log("REQ", request)
        queryset = self.filter_queryset(self.get_queryset())

        root_obj = {}
        pool_list = []
        root_obj['pools'] = pool_list

        for pool in queryset:
            temp_obj, pool_obj = self.get_rsp_body(pool.pool_id)
            pool_list.append(pool_obj)

        self.print_message_log("RSP", root_obj)
        return Response(root_obj)

    # POST: /api/tenant/pools
    def create(self, request):
        self.print_message_log("REQ", request)

        if 'ptr_health_monitor_id' in request.data and request.data["ptr_health_monitor_id"]:
            try:
                health = Healthmonitor.objects.get(health_monitor_id=request.data["ptr_health_monitor_id"])
            except Exception as err:
                logger.error("%s" % str(err))
                return Response("Error: health_monitor_id is not present in table lbaas_healthmonitor", status=status.HTTP_404_NOT_FOUND)

        pool = Pool()
        pool.pool_id = str(uuid.uuid4())

        pool = self.update_pool_info(pool, request)
        if pool is None:
            return Response("Error: Mandatory fields not exist!", status=status.HTTP_400_BAD_REQUEST)

        rsp_data, pool_obj = self.get_rsp_body(pool.pool_id)

        lb_thr = threading.Thread(target=update_loadbalancer_model, args=(pool.pool_id,))
        lb_thr.start()

        self.print_message_log("RSP", rsp_data)
        return Response(rsp_data, status=status.HTTP_201_CREATED)

    # GET: /api/tenant/pools/{pool_id}
    def retrieve(self, request, pk=None):
        self.print_message_log("REQ", request)

        if self.check_pool_id(pk) is None:
            return Response("Error: pool_id does not exist in Pooltable", status=status.HTTP_404_NOT_FOUND)

        rsp_data, pool_obj = self.get_rsp_body(pk)

        self.print_message_log("RSP", rsp_data)
        return Response(rsp_data)

    # PUT: /api/tenant/pools/{pool_id}
    def update(self, request, pk=None):
        self.print_message_log("REQ", request)

        pool = self.check_pool_id(pk)
        if pool is None:
            return Response("Error: pool_id does not exist in Pool table", status=status.HTTP_404_NOT_FOUND)

        pool = self.update_pool_info(pool, request)
        if pool is None:
            return Response("Error: Mandatory fields not exist!", status=status.HTTP_400_BAD_REQUEST)

        rsp_data, pool_obj = self.get_rsp_body(pk)

        lb_thr = threading.Thread(target=update_loadbalancer_model, args=(pk,))
        lb_thr.start()

        self.print_message_log("RSP", rsp_data)
        return Response(rsp_data, status=status.HTTP_202_ACCEPTED)

    # DELETE: /api/tenant/pools/{pool_id}
    def destroy(self, request, pk=None):
        self.print_message_log("REQ", request)

        pool = self.check_pool_id(pk)
        if pool is None:
            return Response("Error: pool_id does not exist in Pool table", status=status.HTTP_404_NOT_FOUND)

        try:
            lb = Loadbalancer.objects.get(pool_id=pool.id)
            return Response("Error: There is a loadbalancer that uses pool_id", status=status.HTTP_404_NOT_FOUND)
        except Exception as err:
            logger.error("%s" % str(err))

        members = Member.objects.filter(memberpool_id=pool.id)
        if members.count() > 0:
            return Response("Error: There is a member that uses pool_id", status=status.HTTP_404_NOT_FOUND)

        lb_thr = threading.Thread(target=update_loadbalancer_model, args=(pk,))
        lb_thr.start()
        Pool.objects.filter(pool_id=pk).delete()

        self.print_message_log("RSP", "")
        return Response(status=status.HTTP_204_NO_CONTENT)


class MemberSerializer(PlusModelSerializer):
    id = ReadOnlyField()

    class Meta:
        model = Member
        fields = ('id', 'memberpool', 'ptr_pool_id', 'address', 'protocol_port', 'weight', 'admin_state_up')


class MemberViewSet(XOSViewSet):
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)

    base_name = "pools"
    method_name = "pools/(?P<pool_id>[a-zA-Z0-9\-_]+)/members"
    method_kind = "viewset"
    queryset = Member.objects.all()
    serializer_class = MemberSerializer

    @classmethod
    def get_urlpatterns(self, api_path="^"):
        patterns = super(MemberViewSet, self).get_urlpatterns(api_path=api_path)

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

    def get_rsp_body(self, member_id):
        member = Member.objects.get(member_id=member_id)

        root_obj = {}
        member_obj = {}
        root_obj['member'] = member_obj

        member_obj['member_id'] = member.member_id
        member_obj['address'] = member.address
        member_obj['admin_state_up'] = member.admin_state_up
        member_obj['protocol_port'] = member.protocol_port
        member_obj['weight'] = member.weight

        return root_obj, member_obj

    def update_member_info(self, member, request):
        required_flag = True
        if request.method == "POST":
            if 'ptr_pool_id' not in request.data or request.data["ptr_pool_id"] == "":
                required_flag = False
            if 'address' not in request.data or request.data["address"] == "":
                required_flag = False
            if 'protocol_port' not in request.data or request.data["protocol_port"] == "":
                required_flag = False

        if not required_flag:
            logger.error("Mandatory fields do not exist!")
            return None

        try:
            if 'memberpool' in request.data and request.data["memberpool"]:
                member.memberpool_id = request.data["memberpool"]
            if 'ptr_pool_id' in request.data and request.data["ptr_pool_id"]:
                member.ptr_pool_id = request.data["ptr_pool_id"]
            if 'address' in request.data and request.data["address"]:
                member.address = request.data["address"]
            if 'protocol_port' in request.data and request.data["protocol_port"]:
                member.protocol_port = request.data["protocol_port"]
            if 'weight' in request.data and request.data["weight"]:
                member.weight = request.data["weight"]
            if 'admin_state_up' in request.data and request.data["admin_state_up"]:
                member.admin_state_up = request.data["admin_state_up"]
        except KeyError as err:
            logger.error("JSON Key error: %s" % str(err))
            return None

        try:
            pool = Pool.objects.get(pool_id=member.ptr_pool_id)
            member.memberpool_id = pool.id
        except KeyError as err:
            logger.info("pool_id does not exist in Pool table (pool_id=%s)" % member.ptr_pool_id)
            return None

        member.save()
        return member

    def check_pool_id(self, pool_id):
        try:
            pool = Pool.objects.get(pool_id=pool_id)
            return pool
        except Exception as err:
            logger.error("%s (pool_id=%s)" % ((str(err), pool_id)))
            return None

    def check_member_id(self, member_id):
        try:
            member = Member.objects.get(member_id=member_id)
            return member
        except Exception as err:
            logger.error("%s (member_id=%s)" % ((str(err), member_id)))
            return None

    # GET: /api/tenant/pools/{pool_id}/members
    def list(self, request, pool_id=None):
        self.print_message_log("REQ", request)
        pool = Pool.objects.get(pool_id=pool_id)
        queryset = Member.objects.filter(memberpool=pool.id)

        root_obj = {}
        member_list = []
        root_obj['members'] = member_list

        for member in queryset:
            temp_obj, member_obj = self.get_rsp_body(member.member_id)
            member_list.append(member_obj)

        self.print_message_log("RSP", root_obj)
        return Response(root_obj)

    # POST: /api/tenant/pools/{pool_id}/members
    def create(self, request, pool_id=None):
        self.print_message_log("REQ", request)

        # Check whether the pool_id exists in the Pool table
        try:
            pool = Pool.objects.get(pool_id=request.data["ptr_pool_id"])
        except Exception as err:
            logger.error("%s (ptr_pool_id=%s)" % ((str(err), request.data["ptr_pool_id"])))
            return Response("Error: pool_id is not present in table lbaas_pool", status=status.HTTP_404_NOT_FOUND)

        member = Member()
        member.member_id = str(uuid.uuid4())
        member.operating_status = "ONLINE"
        member.provisioning_status = "ACTIVE"

        member = self.update_member_info(member, request)
        if member is None:
            return Response("Error: Mandatory fields not exist!", status=status.HTTP_400_BAD_REQUEST)

        rsp_data, member_obj = self.get_rsp_body(member.member_id)

        update_pool_status(member.memberpool.pool_id)
        lb_thr = threading.Thread(target=update_loadbalancer_model, args=(pool_id,))
        lb_thr.start()

        self.print_message_log("RSP", rsp_data)
        return Response(rsp_data, status=status.HTTP_201_CREATED)

    # GET: /api/tenant/pools/{pool_id}/members/{member_id}
    def retrieve(self, request, pool_id=None, pk=None):
        self.print_message_log("REQ", request)

        if self.check_pool_id(pool_id) is None:
            return Response("Error: pool_id does not exist in Pool table", status=status.HTTP_404_NOT_FOUND)

        if self.check_member_id(pk) is None:
            return Response("Error: member_id does not exist in Member table", status=status.HTTP_404_NOT_FOUND)

        rsp_data, member_obj = self.get_rsp_body(pk)

        self.print_message_log("RSP", rsp_data)
        return Response(rsp_data)

    # PUT: /api/tenant/pools/{pool_id}/members/{member_id}
    def update(self, request, pool_id=None, pk=None):
        self.print_message_log("REQ", request)

        pool = self.check_pool_id(pool_id)
        if pool is None:
            return Response("Error: pool_id does not exist in Pool table", status=status.HTTP_404_NOT_FOUND)

        member = self.check_member_id(pk)
        if member is None:
            return Response("Error: member_id does not exist in Member table", status=status.HTTP_404_NOT_FOUND)

        member = self.update_member_info(member, request)
        if member is None:
            return Response("Error: Mandatory fields not exist!", status=status.HTTP_400_BAD_REQUEST)

        rsp_data, member_obj = self.get_rsp_body(pk)

        lb_thr = threading.Thread(target=update_loadbalancer_model, args=(pool_id,))
        lb_thr.start()

        self.print_message_log("RSP", rsp_data)
        return Response(rsp_data, status=status.HTTP_202_ACCEPTED)

    # DELETE: /api/tenant/pools/{pool_id}/members/{member_id}
    def destroy(self, request, pool_id=None, pk=None):
        self.print_message_log("REQ", request)

        if self.check_pool_id(pool_id) is None:
            return Response("Error: pool_id does not exist in Pool table", status=status.HTTP_404_NOT_FOUND)

        if self.check_member_id(pk) is None:
            return Response("Error: member_id does not exist in Member table", status=status.HTTP_404_NOT_FOUND)

        update_pool_status(pool_id)
        lb_thr = threading.Thread(target=update_loadbalancer_model, args=(pool_id,))
        lb_thr.start()

        Member.objects.filter(member_id=pk).delete()

        self.print_message_log("RSP", "")
        return Response(status=status.HTTP_204_NO_CONTENT)
