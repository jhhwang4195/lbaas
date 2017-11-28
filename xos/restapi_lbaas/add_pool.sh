
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

source ./config.sh

if [[ "$#" -ne 1 ]]; then
    #echo "Syntax: $0"

DATA=$(cat <<EOF
{
    "name": "sona_pool",
    "lb_algorithm": "ROUND_ROBIN",
    "protocol": "HTTP",
    "description": "sona_pool"
}
EOF
)

else
    #echo "Syntax: $0 <health_monitor_id>"
    HEALTH_ID=$1

DATA=$(cat <<EOF
{
    "name": "sona_pool",
    "ptr_health_monitor_id": "$HEALTH_ID",
    "lb_algorithm": "ROUND_ROBIN",
    "protocol": "HTTP",
    "description": "sona_pool"
}
EOF
)

fi
curl -H "Accept: application/json; indent=4" -H "Content-Type: application/json" -u $AUTH -X POST -d "$DATA" $HOST/api/tenant/pools/
