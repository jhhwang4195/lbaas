
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


#!/bin/bash
#DB_CMD="docker exec -it swarmservice_xos_db_1 psql -U postgres -d xos -P pager=off -x -c"
DB_CMD="docker exec -it swarmservice_xos_db_1 psql -U postgres -d xos -P pager=off -c"

echo "[Loadbalancer]"
RESULT=`$DB_CMD "select tenantwithcontainer_ptr_id, loadbalancer_id, provisioning_status from lbaas_loadbalancer"`
echo "$RESULT"

echo "[Listener]"
RESULT=`$DB_CMD "select id, listener_id from lbaas_listener"`
echo "$RESULT"

echo "[Pool]"
RESULT=`$DB_CMD "select id, pool_id from lbaas_pool"`
echo "$RESULT"

echo "[Member]"
RESULT=`$DB_CMD "select id, ptr_pool_id, member_id from lbaas_member"`
echo "$RESULT"

echo "[Healthmonitor]"
RESULT=`$DB_CMD "select id, health_monitor_id from lbaas_healthmonitor"`
echo "$RESULT"

