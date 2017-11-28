
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
import pool

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


def check_loadbalancer_model_info(lb_id):
    logger.info("###################################################")
    try:
        lb = Loadbalancer.objects.get(loadbalancer_id=lb_id)
    except Exception as err:
        logger.error("%s (loadbalancer_id=%s)" % (str(err), lb_id))
    if lb:
        logger.info("[Loadbalancer] loadbalancer_id=%s" % lb_id)
        listeners = Listener.objects.filter(id=lb.listener_id)
        for listener in listeners:
            logger.info("[Listener] listener_id=%s" % lb.listener_id)
            pools = Pool.objects.filter(id=lb.pool_id)
            for pool in pools:
                logger.info("[Pool] pool_id=%s" % lb.pool_id)
                members = Member.objects.filter(memberpool_id=pool.id)
                for member in members:
                    logger.info("[Member] pool_id=%s, member_id=%s" % (pool.id, member.member_id))
                    try:
                        health = Healthmonitor.objects.get(id=pool.health_monitor_id)
                        logger.info("[Healthmonitor] health_monitor_id=%s" % pool.health_monitor_id)
                    except Exception as err:
                        logger.error("%s (pool_id=%s)" % (str(err), pool.pool_id))
                        return "Error"
                if members.count() == 0:
                    logger.error("Member information does not exist (pool_id=%s)" % pool.pool_id)
                    return "Error"
            if pools.count() == 0:
                logger.error("Pool information does not exist (pool_id=%s)" % lb.pool_id)
                return "Error"
        if listeners.count() == 0:
            logger.error("Listener information does not exist (listener_id=%s)" % lb.listener_id)
            return "Error"
    return "Success"


def check_loadbalancer_model_all_info():
    logger.info("###################################################")

    logger.info("[Loadbalancer] check start")
    lbs = Loadbalancer.objects.all()
    for lb in lbs:
        listeners = Listener.objects.filter(id=lb.listener_id)
        if listeners.count() == 0:
            logger.error("Listener information does not exist (id=%s)" % lb.listener_id)
            return "Error"

        pools = Pool.objects.filter(id=lb.pool_id)
        if pools.count() == 0:
            logger.error("Pool information does not exist (id=%s)" % lb.pool_id)
            return "Error"

    logger.info("[Listener] check start")
    listeners = Listener.objects.all()
    for listener in listeners:
        lbs = Loadbalancer.objects.filter(listener=listener.id)
        if lbs.count() == 0:
            logger.error("Loadbalancer information does not exist (listener_id=%s)" % listener.id)
            return "Error"

    logger.info("[Pool] check start")
    pools = Pool.objects.all()
    for pool in pools:
        lbs = Loadbalancer.objects.filter(pool=pool.id)
        if lbs.count() == 0:
            logger.error("Loadbalancer information does not exist (pool_id=%s)" % pool.id)
            return "Error"

        members = Member.objects.filter(memberpool_id=pool.id)
        if members.count() == 0:
            logger.error("Member information does not exist (memberpool_id=%s)" % pool.id)
            return "Error"

        try:
            health = Healthmonitor.objects.get(id=pool.health_monitor_id)
        except Exception as err:
            logger.error("Health information does not exist (health_monitor_id=%s)" % pool.health_monitor_id)
            return "Error"

    logger.info("[Member] check start")
    members = Member.objects.all()
    for member in members:
        pools = Pool.objects.filter(id=member.memberpool_id)
        if pools.count() == 0:
            logger.error("Pool information does not exist (id=%s)" % member.memberpool_id)
            return "Error"

    logger.info("[Healthmonitor] check start")
    healths = Healthmonitor.objects.all()
    for health in healths:
        pools = Pool.objects.filter(health_monitor_id=health.id)
        if pools.count() == 0:
            logger.error("Pool information does not exist (health_monitor_id=%s)" % health.id)
            return "Error"

    return "Success"


class LoadbalancerSerializer(PlusModelSerializer):
        id = ReadOnlyField()
        owner = serializers.PrimaryKeyRelatedField(queryset=LbService.objects.all(), default=get_default_lb_service)
        vip_address = serializers.CharField(required=True)

        class Meta:
            model = Loadbalancer
            fields = ('id', 'owner', 'name', 'listener', 'ptr_listener_id', 'pool', 'ptr_pool_id', 'slice_name', 'vip_address', 'description', 'admin_state_up')


class LoadbalancerViewSet(XOSViewSet):
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)

    base_name = "loadbalancers"
    method_name = "loadbalancers"
    method_kind = "viewset"
    queryset = Loadbalancer.objects.all()
    serializer_class = LoadbalancerSerializer

    @classmethod
    def get_urlpatterns(self, api_path="^"):
        patterns = super(LoadbalancerViewSet, self).get_urlpatterns(api_path=api_path)

        # lb to demonstrate adding a custom endpoint
        patterns.append(self.detail_url("statuses/$", {"get": "get_loadbalancer_statuses"}, "loadbalancer_statuses"))
        patterns.append(self.detail_url("check/$", {"get": "get_loadbalancer_check"}, "loadbalancer_check"))

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

    def get_rsp_body(self, lb_id):
        lb_info = Loadbalancer.objects.get(loadbalancer_id=lb_id)

        root_obj = {}
        lb_obj = {}
        listener_list = []
        pool_list = []
        root_obj['loadbalancer'] = lb_obj

        lb_obj['description'] = lb_info.description
        lb_obj['admin_state_up'] = lb_info.admin_state_up
        lb_obj['provisioning_status'] = lb_info.provisioning_status

        lb_obj['listeners'] = listener_list
        listeners = Listener.objects.filter(id=lb_info.listener_id)
        for listener in listeners:
            listener_obj = {}
            listener_obj['id'] = listener.listener_id
            listener_list.append(listener_obj)

        lb_obj['vip_address'] = lb_info.vip_address
        lb_obj['slice_name'] = lb_info.slice_name
        lb_obj['loadbalancer_id'] = lb_info.loadbalancer_id
        lb_obj['operating_status'] = lb_info.operating_status
        lb_obj['loadbalancer_name'] = lb_info.name

        lb_obj['pools'] = pool_list
        pools = Pool.objects.filter(id=lb_info.pool_id)
        for pool in pools:
            pool_obj = {}
            pool_obj['id'] = pool.pool_id
            pool_list.append(pool_obj)

        lb_obj['provider'] = "haproxy"

        return root_obj, lb_obj

    def update_loadbalancer_info(self, lb_info, request):
        required_flag = True
        if request.method == "POST":
            if 'name' not in request.data or request.data["name"] == "":
                required_flag = False
            if 'slice_name' not in request.data or request.data["slice_name"] == "":
                required_flag = False

        if not required_flag:
            logger.error("Mandatory fields not exist!")
            return None

        try:
            if 'name' in request.data and request.data["name"]:
                lb_info.name = request.data["name"]
            if 'listener' in request.data and request.data["listener"]:
                lb_info.listener_id = request.data["listener"]
            if 'pool' in request.data and request.data["pool"]:
                lb_info.pool_id = request.data["pool"]
            if 'slice_name' in request.data and request.data["slice_name"]:
                lb_info.slice_name = request.data["slice_name"]
            if 'vip_address' in request.data and request.data["vip_address"]:
                lb_info.vip_address = request.data["vip_address"]
            if 'description' in request.data and request.data["description"]:
                lb_info.description = request.data["description"]
            if 'admin_state_up' in request.data and request.data["admin_state_up"]:
                lb_info.admin_state_up = request.data["admin_state_up"]
            if 'listener_id' in request.data:
                lb_info.listener_id = request.data["listener_id"]
            if 'pool_id' in request.data:
                lb_info.pool_id = request.data["pool_id"]
            if 'ptr_listener_id' in request.data:
                lb_info.ptr_listener_id = request.data["ptr_listener_id"]
            if 'ptr_pool_id' in request.data:
                lb_info.ptr_pool_id = request.data["ptr_pool_id"]

        except KeyError as err:
            logger.error("JSON Key error: %s" % str(err))
            return None

        if lb_info.ptr_listener_id is None or lb_info.ptr_listener_id == "":
            lb_info.listener_id = None
        else:
            try:
                listener = Listener.objects.get(listener_id=lb_info.ptr_listener_id)
                lb_info.listener_id = listener.id
            except KeyError as err:
                logger.info("listener_id does not exist in Listener table (listener_id=%s)" % lb_info.ptr_listener_id)
                return None

        if lb_info.ptr_pool_id is None or lb_info.ptr_pool_id == "":
            lb_info.pool_id = None
        else:
            try:
                pool = Pool.objects.get(pool_id=lb_info.ptr_pool_id)
                lb_info.pool_id = pool.id
            except KeyError as err:
                logger.info("pool_id does not exist in Pool table (pool_id=%s)" % lb_info.ptr_pool_id)
                return None

        lb_info.save(always_update_timestamp=True)

        return lb_info

    def check_lb_id(self, lb_id):
        try:
            lb = Loadbalancer.objects.get(loadbalancer_id=lb_id)
            return lb
        except Exception as err:
            logger.error("%s (lb_id=%s)" % ((str(err), lb_id)))
            return None

    # GET: /api/tenant/loadbalancers
    def list(self, request):
        self.print_message_log("REQ", request)
        queryset = self.filter_queryset(self.get_queryset())

        root_obj = {}
        lb_obj_list = []
        root_obj['loadbalancers'] = lb_obj_list

        for lb in queryset:
            temp_obj, lb_obj = self.get_rsp_body(lb.loadbalancer_id)
            lb_obj_list.append(lb_obj)

        self.print_message_log("RSP", root_obj)
        return Response(root_obj)

    # POST: /api/tenant/loadbalancers
    def create(self, request):
        self.print_message_log("REQ", request)

        lb_info = Loadbalancer()
        lb_info.creator_id = 1

        if 'owner' in request.data and request.data["owner"]:
            lb_info.owner_id = request.data["owner"]
        else:
            try:
                service = Service.objects.get(name="lbaas")
                lb_info.owner_id = service.id
            except Exception as err:
                return Response("Error: name(lbaas) does not exist in core_service", status=status.HTTP_404_NOT_FOUND)

            # FIXME: Read from Config file
            # Because mount_data_sets information is not available with TOSCA
            slices = Slice.objects.filter(service_id=service.id)
            for slice in slices:
                if slice.mount_data_sets == "GenBank":
                    slice.mount_data_sets = "/usr/local/etc/haproxy/"
                    slice.save()

        if 'slice_name' in request.data and request.data["slice_name"]:
            tmp_slice_name = request.data["slice_name"]
            network_name = tmp_slice_name.split('_', 1)
            try:
                network = Network.objects.get(name=network_name[1])
                logger.info("network.id=%s" % network.id)
                lb_info.vip_subnet_id = network.id
            except Exception as err:
                err_str = "Error: network_name(%s) does not exist in Network table" % network_name[1]
                return Response(err_str, status=status.HTTP_404_NOT_FOUND)

        if 'listener_id' in request.data and request.data["listener_id"]:
            try:
                listener = Listener.objects.get(id=request.data["listener_id"])
            except Exception as err:
                logger.error("%s" % str(err))
                return Response("Error: listener_id does not exist in Listener table", status=status.HTTP_404_NOT_FOUND)

        if 'pool_id' in request.data and request.data["pool_id"]:
            try:
                pool = Pool.objects.get(id=request.data["pool_id"])
            except Exception as err:
                logger.error("%s" % str(err))
                return Response("Error: pool_id does not exist in Pool table", status=status.HTTP_404_NOT_FOUND)

        if 'ptr_listener_id' in request.data and request.data["ptr_listener_id"]:
            try:
                listener = Listener.objects.get(listener_id=request.data["ptr_listener_id"])
            except Exception as err:
                logger.error("%s" % str(err))
                return Response("Error: listener_id does not exist in Listener table", status=status.HTTP_404_NOT_FOUND)

        if 'ptr_pool_id' in request.data and request.data["ptr_pool_id"]:
            try:
                pool = Pool.objects.get(pool_id=request.data["ptr_pool_id"])
            except Exception as err:
                logger.error("%s" % str(err))
                return Response("Error: pool_id does not exist in Pool table", status=status.HTTP_404_NOT_FOUND)

        lb_info.loadbalancer_id = str(uuid.uuid4())
        lb_info.operating_status = "ONLINE"
        lb_info.provisioning_status = "PENDING_CREATE"

        lb_info = self.update_loadbalancer_info(lb_info, request)
        if lb_info is None:
            return Response("Error: Mandatory fields not exist!", status=status.HTTP_400_BAD_REQUEST)

        rsp_data, lb_obj = self.get_rsp_body(lb_info.loadbalancer_id)

        self.print_message_log("RSP", rsp_data)
        return Response(rsp_data, status=status.HTTP_201_CREATED)

    # GET: /api/tenant/loadbalancers/{loadbalancer_id}
    def retrieve(self, request, pk=None):
        self.print_message_log("REQ", request)

        if self.check_lb_id(pk) is None:
            return Response("Error: loadbalancer_id does not exist in Loadbalancer table", status=status.HTTP_404_NOT_FOUND)

        rsp_data, lb_obj = self.get_rsp_body(pk)

        self.print_message_log("RSP", rsp_data)
        return Response(rsp_data)

    # PUT: /api/tenant/loadbalancers/{loadbalancer_id}
    def update(self, request, pk=None):
        self.print_message_log("REQ", request)

        lb_info = self.check_lb_id(pk)
        if lb_info is None:
            return Response("Error: loadbalancer_id does not exist in Loadbalancer table", status=status.HTTP_404_NOT_FOUND)

        lb_info = self.update_loadbalancer_info(lb_info, request)
        if lb_info is None:
            return Response("Error: Mandatory fields not exist!", status=status.HTTP_400_BAD_REQUEST)

        rsp_data, lb_obj = self.get_rsp_body(pk)

        self.print_message_log("RSP", rsp_data)
        return Response(rsp_data, status=status.HTTP_202_ACCEPTED)

    # DELETE: /api/tenant/loadbalancers/{loadbalancer_id}
    def destroy(self, request, pk=None):
        self.print_message_log("REQ", request)

        lb_info = self.check_lb_id(pk)
        if lb_info is None:
            return Response("Error: loadbalancer_id does not exist in Loadbalancer table", status=status.HTTP_404_NOT_FOUND)

        ins = Instance.objects.get(id=lb_info.instance_id)
        ins.deleted = True
        ins.save()

        Loadbalancer.objects.filter(loadbalancer_id=pk).delete()
        Port.objects.filter(instance_id=lb_info.instance_id).delete()
        Tag.objects.filter(object_id=lb_info.instance_id).delete()

        self.print_message_log("RSP", "")
        return Response(status=status.HTTP_204_NO_CONTENT)

    # GET: /api/tenant/loadbalancers/{loadbalancer_id}/statuses
    def get_loadbalancer_statuses(self, request, pk=None):
        self.print_message_log("REQ", request)

        if self.check_lb_id(pk) is None:
            return Response("Error: loadbalancer_id does not exist in Loadbalancer table", status=status.HTTP_404_NOT_FOUND)

        root_obj = {}
        status_obj = {}
        lb_obj = {}
        listener_list = []

        root_obj['statuses'] = status_obj
        status_obj['loadblancer'] = lb_obj

        lb_info = Loadbalancer.objects.get(loadbalancer_id=pk)
        lb_obj['name'] = lb_info.name
        lb_obj['id'] = lb_info.loadbalancer_id
        lb_obj['operating_status'] = lb_info.operating_status
        lb_obj['provisioning_status'] = lb_info.provisioning_status

        lb_obj['listeners'] = listener_list
        listeners = Listener.objects.filter(id=lb_info.listener_id)
        if listeners.count() == 0:
            logger.error("listener_id does not exist in Listener table (listener_id=%s)" % lb_info.listener_id)

        for listener in listeners:
            listener_obj = {}
            pool_list = []
            listener_obj['name'] = listener.name
            listener_obj['id'] = listener.listener_id
            listener_obj['operating_status'] = "ONLINE"
            listener_obj['provisioning_status'] = "ACTIVE"
            listener_list.append(listener_obj)

            listener_obj['pools'] = pool_list
            pools = Pool.objects.filter(id=lb_info.pool_id)
            if pools.count() == 0:
                logger.error("pool_id does not exist in Pool table (pool_id=%s)" % lb_info.pool_id)

            for pool in pools:
                pool_obj = {}
                member_list = []
                pool_obj['name'] = pool.name
                pool_obj['id'] = pool.pool_id
                pool_obj['operating_status'] = "ONLINE"
                pool_obj['provisioning_status'] = pool.status
                pool_list.append(pool_obj)

                health_obj = {}
                pool_obj['health_monitor'] = health_obj
                try:
                    health = Healthmonitor.objects.get(id=pool.health_monitor_id)
                    health_obj['type'] = health.type
                    health_obj['id'] = health.health_monitor_id
                    health_obj['provisioning_status'] = "ACTIVE"
                except Exception as err:
                    logger.error("%s (health_monitor_id=%s)" % (str(err), pool.health_monitor_id))

                pool_obj['members'] = member_list
                members = Member.objects.filter(memberpool_id=pool.id)
                if members.count() == 0:
                    logger.error("memberpool_id does not exist in Member table (memberpool_id=%s)" % pool.id)

                for member in members:
                    member_obj = {}
                    member_obj['address'] = member.address
                    member_obj['protocol_port'] = member.protocol_port
                    member_obj['id'] = member.member_id
                    member_obj['operating_status'] = member.operating_status
                    member_obj['provisioning_status'] = member.provisioning_status
                    member_list.append(member_obj)

        self.print_message_log("RSP", root_obj)
        return Response(root_obj)

    # GET: /api/tenant/loadbalancers/{loadbalancer_id}/check
    def get_loadbalancer_check(self, request, pk=None):
        res_obj = {}
        result1 = check_loadbalancer_model_info(pk)
        result2 = check_loadbalancer_model_all_info()

        lb_id = "loadbalancer_id(%s)" % pk
        res_obj[lb_id] = result1
        res_obj['all_loadbalanacer'] = result2

        return Response(res_obj)
