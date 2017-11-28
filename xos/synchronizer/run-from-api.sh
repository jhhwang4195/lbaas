
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
PROC1="python lbaas-synchronizer.py"
PROC2="python sync_config.py"

$PROC1 &
$PROC2 &

sleep 60

while :
do
    RESULT=`ps -ef | grep "$PROC1" | grep -v 'grep'`
    if [ "${RESULT:-null}" = null ]; then
        echo "${PROC1} not running, starting "$PROC1
        $PROC1 &
    else
        echo "${PROC1} running"
    fi

    RESULT=`ps -ef | grep "$PROC2" | grep -v 'grep'`
    if [ "${RESULT:-null}" = null ]; then
        echo "${PROC2} not running, starting "$PROC2
        $PROC2 &
    else
        echo "${PROC2} running"
    fi

    sleep 10
done
