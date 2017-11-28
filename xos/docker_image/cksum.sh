
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


#!/bin/sh
CFG_FILE="/usr/local/etc/haproxy/haproxy.cfg"
OLD_CKSUM=""
CUR_CKSUM=""

echo "`date` Start cksum.sh" >> /cksum.log

while :
do
    CUR_CKSUM=`cksum $CFG_FILE | awk '{print $1}'`

    if [ "$CUR_CKSUM" != "$OLD_CKSUM" ] && [ "$OLD_CKSUM" != "" ]
    then
        service haproxy reload
        echo "`date` Reload $CFG_FILE" >> /cksum.log
    fi

    sleep 2
    OLD_CKSUM=$CUR_CKSUM
done
