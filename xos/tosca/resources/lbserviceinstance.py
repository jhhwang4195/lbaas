
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


import uuid

from service import XOSService
from xosresource import XOSResource
from core.models import Service
from services.lbaas.models import Loadbalancer, Listener, Pool, Member, Healthmonitor


class LbaasLoadbalancer(XOSResource):
    provides = "tosca.nodes.Loadbalancer"
    xos_model = Loadbalancer
    copyin_props = ("loadbalancer_id", "ptr_listener_id", "ptr_pool_id", "description", "vip_subnet_id", "vip_address", "slice_name", "admin_state_up", "operating_status", "provisioning_status")

    def get_xos_args(self, throw_exception=True):
        args = super(LbaasLoadbalancer, self).get_xos_args()

        # LbTenant must always have a owner
        provider_name = self.get_requirement("tosca.relationships.TenantOfService", throw_exception=True)
        if provider_name:
            args["owner"] = self.get_xos_object(Service, throw_exception=True, name=provider_name)

        listener_name = self.get_requirement("tosca.relationships.ListenerOfLoadbalancer", throw_exception=False)
        if listener_name:
            args["listener"] = self.get_xos_object(Listener, throw_exception=True, name=listener_name)

        pool_name = self.get_requirement("tosca.relationships.PoolOfLoadbalancer", throw_exception=False)
        if pool_name:
            args["pool"] = self.get_xos_object(Pool, throw_exception=True, name=pool_name)

        if "loadbalancer_id" not in args:
            args["loadbalancer_id"] = str(uuid.uuid4())

        return args

    def get_existing_objs(self):
        args = self.get_xos_args(throw_exception=False)

        if "loadbalancer_id" in args:
            loadbalancer_obj = Loadbalancer.objects.filter(loadbalancer_id=args["loadbalancer_id"])
            if loadbalancer_obj:
                return loadbalancer_obj

        if "owner" in args:
            return Loadbalancer.objects.filter(name=args["name"], owner=args["owner"])
        return []

    def can_delete(self, obj):
        return super(LbaasLoadbalancer, self).can_delete(obj)


class LbaasListener(XOSResource):
    provides = "tosca.nodes.Listener"
    xos_model = Listener
    copyin_props = ("listener_id", "protocol", "protocol_port", "stat_port", "description", "admin_state_up", "connection_limit", )

    def get_xos_args(self, throw_exception=True):
        args = super(LbaasListener, self).get_xos_args()

        if "admin_state_up" not in args:
            args["admin_state_up"] = True
        if "listener_id" not in args:
            args["listener_id"] = str(uuid.uuid4())

        return args

    def get_existing_objs(self):
        args = self.get_xos_args(throw_exception=False)

        if "listener_id" in args:
            listener_obj = Listener.objects.filter(listener_id=args["listener_id"])
            if listener_obj:
                return listener_obj

        return Listener.objects.filter(name=args["name"])

    def can_delete(self, obj):
        return super(LbaasListener, self).can_delete(obj)


class LbaasPool(XOSResource):
    provides = "tosca.nodes.Pool"
    xos_model = Pool
    copyin_props = ("pool_id", "health_monitor_id", "ptr_health_monitor_id", "lb_algorithm", "description", "protocol", "admin_state_up", "status")

    def get_xos_args(self, throw_exception=True):
        args = super(LbaasPool, self).get_xos_args()

        if "admin_state_up" not in args:
            args["admin_state_up"] = True
        if "pool_id" not in args:
            args["pool_id"] = str(uuid.uuid4())

        # Member must always have a Pool
        monitor_name = self.get_requirement("tosca.relationships.HealthmonitorOfPool", throw_exception=True)
        if monitor_name:
            args["health_monitor"] = self.get_xos_object(Healthmonitor, throw_exception=True, name=monitor_name)

        return args

    def get_existing_objs(self):
        args = self.get_xos_args(throw_exception=False)

        if "pool_id" in args:
            pool_obj = Pool.objects.filter(pool_id=args["pool_id"])
            if pool_obj:
                return pool_obj

        return Pool.objects.filter(name=args["name"])

    def can_delete(self, obj):
        return super(LbaasPool, self).can_delete(obj)


class LbaasMember(XOSResource):
    provides = "tosca.nodes.Member"
    xos_model = Member
    copyin_props = ("member_id", "pool_id", "ptr_pool_id", "address", "protocol_port", "weight", "admin_state_up", "operating_status", "provisioning_status")

    def get_xos_args(self, throw_exception=True):
        args = super(LbaasMember, self).get_xos_args()

        if "admin_state_up" not in args:
            args["admin_state_up"] = True
        if "member_id" not in args:
            args["member_id"] = str(uuid.uuid4())

        # Member must always have a Pool
        pool_name = self.get_requirement("tosca.relationships.PoolOfMember", throw_exception=True)
        if pool_name:
            args["memberpool"] = self.get_xos_object(Pool, throw_exception=True, name=pool_name)

        return args

    def get_existing_objs(self):
        args = self.get_xos_args(throw_exception=False)

        if "member_id" in args:
            member_obj = Member.objects.filter(member_id=args["member_id"])
            if member_obj:
                return member_obj

        if "memberpool" in args:
            return Member.objects.filter(name=args["name"], memberpool=args["memberpool"])

        return []

    def can_delete(self, obj):
        return super(LbaasMember, self).can_delete(obj)


class LbaasHealthmonitor(XOSResource):
    provides = "tosca.nodes.Healthmonitor"
    xos_model = Healthmonitor
    copyin_props = ("health_monitor_id", "type", "delay", "max_retries", "timeout", "http_method", "url_path", "expected_codes", "admin_state_up")

    def get_xos_args(self, throw_exception=True):
        args = super(LbaasHealthmonitor, self).get_xos_args()

        if "health_monitor_id" not in args:
            args["health_monitor_id"] = str(uuid.uuid4())

        return args

    def can_delete(self, obj):
        return super(LbaasHealthmonitor, self).can_delete(obj)
