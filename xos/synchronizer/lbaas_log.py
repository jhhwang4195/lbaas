
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


import inspect

from xos.logger import Logger, logging
from os.path import basename

logger = Logger(level=logging.DEBUG)
logger.setLevel(logging.DEBUG)


def debug(msg):
    logger.debug(basename(str(inspect.stack()[1][1])) + ':' +
                 str(inspect.stack()[1][2]) + ' ' +
                 str(inspect.stack()[1][3]) + '()  ' +
                 str(msg))


def info(msg):
    logger.info(basename(str(inspect.stack()[1][1])) + ':' +
                str(inspect.stack()[1][2]) + ' ' +
                str(inspect.stack()[1][3]) + '()  ' +
                str(msg))


def error(msg):
    logger.error(basename(str(inspect.stack()[1][1])) + ':' +
                 str(inspect.stack()[1][2]) + ' ' +
                 str(inspect.stack()[1][3]) + '()  ' +
                 str(msg))
