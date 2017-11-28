
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

if [[ "$#" -ne 3 ]]; then
    echo "Syntax: $0 <pool_id> <member_ip> <port>"
    exit -1
fi

POOL_ID=$1
MEMBER_IP=$2
PORT=$3

DATA=$(cat <<EOF
{
    "ptr_pool_id": "$POOL_ID",
    "address": "$MEMBER_IP",
    "protocol_port": $PORT
}
EOF
)

curl -H "Accept: application/json; indent=4" -H "Content-Type: application/json" -u $AUTH -X POST -d "$DATA" $HOST/api/tenant/pools/$POOL_ID/members/
