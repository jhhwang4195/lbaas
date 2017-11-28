
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
set -e

CFG_FILE="/usr/local/etc/haproxy/haproxy.cfg"

# first arg is `-f` or `--some-option`
if [ "${1#-}" != "$1" ]; then
        set -- haproxy "$@"
fi

if [ "$1" = 'haproxy' ]; then
        # if the user wants "haproxy", let's use "haproxy-systemd-wrapper" instead so we can have proper reloadability implemented by upstream
        shift # "haproxy"
        set -- "$(which haproxy-systemd-wrapper)" -p /run/haproxy.pid "$@"
fi

while [ ! -f "$CFG_FILE" ]:
do
    echo "`date` Not found $CFG_FILE" >> /cksum.log
    sleep 2
done

echo "`date` Found $CFG_FILE" >> /cksum.log
/cksum.sh &
exec "$@"
