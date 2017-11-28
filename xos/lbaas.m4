
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


tosca_definitions_version: tosca_simple_yaml_1_0

# compile this with "m4 lbaas.m4 > lbaas.yaml"

# include macros
include(macros.m4)

node_types:
    tosca.nodes.LbService:
        derived_from: tosca.nodes.Root
        description: >
            Lb Service
        capabilities:
            xos_base_service_caps
        properties:
            xos_base_props
            xos_base_service_props
            service_name:
                type: string
                required: false

    tosca.nodes.Loadbalancer:
        derived_from: tosca.nodes.Root
        description: >
            A Tenant of loadbalancer
        properties:
            xos_base_tenant_props
            loadbalancer_id:
                type: string
                required: false
            listener_id:
                type: string
                required: false
            ptr_listener_id:
                type: string
                required: false
            pool_id:
                type: string
                required: false
            ptr_pool_id:
                type: string
                required: false
            description:
                type: string
                required: false
            vip_subnet_id:
                type: string
                required: false
            slice_name:
                type: string
                required: false
            vip_address:
                type: string
                required: false
            admin_state_up:
                type: boolean
                required: false
            operating_status:
                type: string
                required: false
            provisioning_status:
                type: string
                required: false

    tosca.nodes.Listener:
        derived_from: tosca.nodes.Root
        description: >
            A Tenant of the listener
        capabilities:
            xos_base_service_caps
        properties:
            xos_base_props
            name:
                type: string
                required: false
            listener_id:
                type: string
                required: false
            protocol:
                type: string
                required: false
            protocol_port:
                type: integer
                required: false
            stat_port:
                type: integer
                required: false
            description:
                type: string
                required: false
            admin_state_up:
                type: boolean
                required: false
            connection_limit:
                type: integer
                required: false

    tosca.nodes.Pool:
        derived_from: tosca.nodes.Root
        description: >
            A Tenant of the pool
        properties:
            xos_base_props
            name:
                type: string
                required: false
            pool_id:
                type: string
                required: false
            health_monitor_id:
                type: string
                required: false
            ptr_health_monitor_id:
                type: string
                required: false
            lb_algorithm:
                type: string
                required: false
            description:
                type: string
                required: false
            protocol:
                type: string
                required: false
            admin_state_up:
                type: boolean
                required: false
            status:
                type: string
                required: false

    tosca.nodes.Member:
        derived_from: tosca.nodes.Root
        description: >
            A Tenant of the member
        properties:
            xos_base_props
            member_id:
                type: string
                required: false
            pool_id:
                type: string
                required: false
            ptr_pool_id:
                type: string
                required: false
            address:
                type: string
                required: false
            protocol_port:
                type: integer
                required: false
            weight:
                type: integer
                required: false
            admin_state_up:
                type: boolean
                required: false
            operating_status:
                type: string
                required: false
            provisioning_status:
                type: string
                required: false

    tosca.nodes.Healthmonitor:
        derived_from: tosca.nodes.Root
        description: >
            A Tenant of the Healthmonitor
        properties:
            xos_base_props
            name:
                type: string
                required: false
            health_monitor_id:
                type: string
                required: false
            type:
                type: string
                required: false
            delay:
                type: integer
                required: false
            max_retries:
                type: integer
                required: false
            timeout:
                type: integer
                required: false
            http_method:
                type: string
                required: false
            url_path:
                type: string
                required: false
            expected_codes:
                type: string
                required: false
            admin_state_up:
                type: boolean
                required: false

    tosca.relationships.PoolOfMember:
            derived_from: tosca.relationships.Root
            valid_target_types: [ tosca.capabilities.xos.Pool ]

    tosca.relationships.PoolOfLoadbalancer:
            derived_from: tosca.relationships.Root
            valid_target_types: [ tosca.capabilities.xos.Pool ]

    tosca.relationships.HealthmonitorOfPool:
            derived_from: tosca.relationships.Root
            valid_target_types: [ tosca.capabilities.xos.Healthmonitor ]

    tosca.relationships.ListenerOfLoadbalancer:
            derived_from: tosca.relationships.Root
            valid_target_types: [ tosca.capabilities.xos.Listener ]

    tosca.relationships.PoolOfLoadbalancer:
            derived_from: tosca.relationships.Root
            valid_target_types: [ tosca.capabilities.xos.Pool ]
