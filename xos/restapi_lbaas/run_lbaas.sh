
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
DB_CMD="docker exec -it swarmservice_xos_db_1 psql -U postgres -d xos -P pager=off -x -c"

######################################################
# delete lb model info
######################################################
$DB_CMD "delete from lbaas_loadbalancer"
$DB_CMD "delete from lbaas_listener"
$DB_CMD "delete from lbaas_member"
$DB_CMD "delete from lbaas_pool"
$DB_CMD "delete from lbaas_healthmonitor"

######################################################
# create lb model info
######################################################
./add_loadbalancer.sh 
./add_listener.sh 
./add_pool.sh 
./add_healthmonitor.sh 

# get pool_id
RESULT=`$DB_CMD "select * from lbaas_pool limit 1" | grep pool_id`
POOL_ID=`echo ${RESULT::-1} | awk '{print $3}'`

# get health_monitor_id
RESULT=`$DB_CMD "select * from lbaas_healthmonitor limit 1" | grep health_monitor_id`
HEALTH_ID=`echo ${RESULT::-1} | awk '{print $3}'`

# get loadbalancer_id
RESULT=`$DB_CMD "select * from lbaas_loadbalancer limit 1" | grep loadbalancer_id`
LB_ID=`echo ${RESULT::-1} | awk '{print $3}'`

# get listener_id
RESULT=`$DB_CMD "select * from lbaas_listener limit 1" | grep listener_id`
LISTENER_ID=`echo ${RESULT::-1} | awk '{print $3}'`

./update_pool.sh $POOL_ID $HEALTH_ID
./add_member.sh $POOL_ID 10.10.2.241 9001
./add_member.sh $POOL_ID 10.10.2.242 9001
./update_loadbalancer.sh $LB_ID $LISTENER_ID $POOL_ID
