
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


import os
import sys
import json
import collections
import time
import lbaas_log as slog

from datetime import datetime
from synchronizers.new_base.SyncInstanceUsingAnsible import SyncInstanceUsingAnsible
from synchronizers.new_base.modelaccessor import *

parentdir = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, parentdir)


class SyncLoadbalancer(SyncInstanceUsingAnsible):
    provides = [Loadbalancer]
    observes = Loadbalancer
    requested_interval = 0
    template_name = "loadbalancer_playbook.yaml"
    service_key_name = "/opt/xos/synchronizers/lbaas/lbaas_private_key"

    def __init__(self, *args, **kwargs):
        super(SyncLoadbalancer, self).__init__(*args, **kwargs)

    def convert_unicode_to_str(self, data):
        if isinstance(data, basestring):
            return str(data)
        elif isinstance(data, collections.Mapping):
            return dict(map(self.convert_unicode_to_str, data.iteritems()))
        elif isinstance(data, collections.Iterable):
            return type(data)(map(self.convert_unicode_to_str, data))
        else:
            return data

    def update_pool_status(self, pool_id):
        pool_status = ""

        pool = Pool.objects.get(id=pool_id)
        members = Member.objects.filter(memberpool_id=pool.id)
        if len(members) > 0:
            try:
                pool = Pool.objects.get(id=pool_id)
            except Exception as err:
                slog.error("%s (id=%s)" % ((str(err), pool_id)))
                pool_status = "ERROR"

            healths = Healthmonitor.objects.filter(id=pool.health_monitor_id)
            if len(healths) > 0:
                pool_status = "ACTIVE"
            else:
                slog.error("Healthmonitor information does not exist (id=%s)" % pool.health_monitor_id)
                pool_status = "ERROR"
        else:
            slog.error("Member information does not exist (memberpool_id=%s)" % pool.id)
            pool_status = "ERROR"

        try:
            pool = Pool.objects.get(id=pool_id)
            pool.status = pool_status
            pool.save()
        except Exception as err:
            slog.error("id does not exist in Pool table (id=%s)" % pool_id)

        return pool_status

    def update_loadbalancer_status(self, lb_id):
        lb = Loadbalancer.objects.get(loadbalancer_id=lb_id)
        if lb:
            listeners = Listener.objects.filter(id=lb.listener_id)
            for listener in listeners:
                pools = Pool.objects.filter(id=lb.pool_id)
                for pool in pools:
                    members = Member.objects.filter(memberpool_id=pool.id)
                    if len(members) > 0:
                        healths = Healthmonitor.objects.filter(id=pool.health_monitor_id)
                        if len(healths) > 0:
                            lb.provisioning_status = "ACTIVE"
                        else:
                            slog.error("Healthmonitor information does not exist (id=%s)" % pool.health_monitor_id)
                            lb.provisioning_status = "ERROR"
                    else:
                        slog.error("Member information does not exist (memberpool_id=%s)" % pool.id)
                        lb.provisioning_status = "ERROR"
                if len(pools) == 0:
                    slog.error("Pool information does not exist (loadbalancer_id=%s, id=%s)" % (lb_id, lb.pool_id))
                    lb.provisioning_status = "ERROR"
            if len(listeners) == 0:
                slog.error("Listener information does not exist (id=%s)" % lb.listener_id)
                lb.provisioning_status = "ERROR"
        else:
            slog.error("Loadbalancer information does not exist (loadbalancer_id=%s)" % lb_id)
            lb.provisioning_status = "ERROR"

        slog.info("lb.provisioning_status=%s" % lb.provisioning_status)
        lb.save()

        return lb.provisioning_status

    # Gets the attributes that are used by the Ansible template but are not
    # part of the set of default attributes.
    def get_extra_attributes(self, o):
        slog.info("===============================================================")
        slog.info("instance_name=%s, instance_id=%d, instance_uuid=%s"
                  % (o.instance.instance_name, o.instance_id, o.instance.instance_uuid))

        try:
            tags = Tag.objects.filter(object_id=o.instance.id)

            if not len(tags):
                userdata = {}
                userdata['create_date'] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time()))
                userdata['update_date'] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time()))
                userdata['command'] = "service haproxy status"
                userdata['expected_result'] = "haproxy is running."
                userdata['result'] = "Initialized"

                tag = Tag(service=o.instance.slice.service,
                          content_type=o.instance.self_content_type_id,
                          object_id=o.instance.id,
                          name="chk_container_status",
                          value=json.dumps(userdata))

                tag.save()
        except Exception as e:
            slog.error("Instance.objects.get() failed - %s" % str(e))

        lb_status = True
        if self.update_pool_status(o.pool_id) != "ACTIVE":
            slog.error("Pool status is not ACTIVE (pool_id=%s)" % o.pool_id)
            lb_status = False

        if self.update_loadbalancer_status(o.loadbalancer_id) != "ACTIVE":
            slog.error("Loadbalancer status is not ACTIVE (loadbalancer_id=%s)" % o.loadbalancer_id)
            lb_status = False

        if not lb_status:
            return None

        fields = {}
        fields['instance_id'] = o.instance.id
        fields['update_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        fields["baremetal_ssh"] = True

        loadbalancer = {}
        loadbalancer['loadbalancer_id'] = o.loadbalancer_id
        loadbalancer['lb_name'] = o.name
        loadbalancer['vip_address'] = o.vip_address
        fields['loadbalancer'] = json.dumps(loadbalancer, indent=4)

        slog.info(">>>>> Loadbalancer")
        slog.info("%s" % json.dumps(loadbalancer, indent=4))

        try:
            listener = {}
            obj = Listener.objects.get(id=o.listener_id)
            listener['listener_name'] = obj.name
            listener['listener_id'] = obj.listener_id
            listener['protocol'] = obj.protocol
            listener['protocol_port'] = obj.protocol_port
            listener['stat_port'] = obj.stat_port
            listener['connection_limit'] = obj.connection_limit
            fields['listener'] = json.dumps(listener, indent=4)

            slog.info(">>>>> Listener")
            slog.info("%s" % json.dumps(listener, indent=4))
        except Exception as e:
            slog.error("Listener.objects.get() failed - %s" % str(e))
            return None

        try:
            pool = {}
            obj = Pool.objects.get(id=o.pool_id)
            pool['pool_name'] = obj.name
            pool['pool_id'] = obj.pool_id
            pool['health_monitor_id'] = obj.health_monitor_id
            pool['lb_algorithm'] = obj.lb_algorithm
            pool['protocol'] = obj.protocol
            fields['pool'] = json.dumps(pool, indent=4)

            slog.info(">>>>> Pool")
            slog.info("%s" % json.dumps(pool, indent=4))
        except Exception as e:
            slog.error("Pool.objects.get() failed - %s" % str(e))
            return None

        try:
            root_obj = {}
            member_list = []
            root_obj['members'] = member_list

            objs = Member.objects.filter(memberpool_id=o.pool_id)
            for obj in objs:
                member_obj = {}
                member_obj['member_id'] = obj.member_id
                member_obj['address'] = obj.address
                member_obj['protocol_port'] = obj.protocol_port
                member_obj['weight'] = obj.weight
                member_list.append(member_obj)

            fields['members'] = json.dumps(root_obj, indent=4)

            slog.info(">>>>> Members")
            slog.info("%s" % json.dumps(root_obj, indent=4))
        except Exception as e:
            slog.error("Member.objects.get() failed - %s" % str(e))

        try:
            health_monitor = {}
            obj = Healthmonitor.objects.get(id=pool['health_monitor_id'])

            health_monitor['health_monitor_id'] = obj.health_monitor_id
            health_monitor['type'] = obj.type
            health_monitor['delay'] = obj.delay
            health_monitor['max_retries'] = obj.max_retries
            health_monitor['timeout'] = obj.timeout
            health_monitor['http_method'] = obj.http_method
            health_monitor['url_path'] = obj.url_path
            health_monitor['expected_codes'] = obj.expected_codes
            fields['health_monitor'] = json.dumps(health_monitor, indent=4)

            slog.info(">>>>> Healthmonitor")
            slog.info("%s" % json.dumps(health_monitor, indent=4))
        except Exception as e:
            slog.error("Healthmonitor.objects.get() failed - %s" % str(e))

        slog.info("===============================================================")
        slog.info(">>> curl command for haproxy test")
        slog.info("curl %s:%s" % (loadbalancer['vip_address'], listener['protocol_port']))

        fields = self.convert_unicode_to_str(fields)

        return fields

    def delete_record(self, port):
        # Nothing needs to be done to delete an lbaas; it goes away
        # when the instance holding the lbaas is deleted.
        pass
