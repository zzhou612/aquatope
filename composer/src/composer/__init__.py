"""
 Licensed to the Apache Software Foundation (ASF) under one or more
 contributor license agreements.  See the NOTICE file distributed with
 this work for additional information regarding copyright ownership.
 The ASF licenses this file to You under the Apache License, Version 2.0
 (the "License"); you may not use this file except in compliance with
 the License.  You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
"""

__version__ = '0.15.1'

from .composer import composer as _composer
from .composer import ComposerError, serialize, Composition, get_value, get_params, set_params
from .composer import retain_result, retain_nested_result, dec_count, set_nested_params, get_nested_params
from .composer import set_nested_result, get_nested_result, retry_cond
from .composer import parse_action_name

# statically export composer combinators to avoid E1101 pylint errors


def action(name, *arguments):
    return _composer.action(name, *arguments)

def composition(name, *arguments):
    return _composer.composition(name, *arguments)

def literal(value):
    return _composer.literal(value)

def function(value):
    return _composer.function(value)

def value(value):
    return _composer.value(value)

def parse(composition):
    return _composer.parse(composition)

def seq(*arguments):
    return _composer.sequence(*arguments)

def sequence(*arguments):
    return _composer.sequence(*arguments)

def task(task):
    return _composer.task(task)

def when(test, consequent, alternate=None):
    return _composer.when(test, consequent, alternate)

def when_nosave(test, consequent, alternate=None):
    return _composer.when_nosave(test, consequent, alternate)

def loop(test, body):
    return _composer.loop(test, body)

def loop_nosave(test, body):
    return _composer.loop_nosave(test, body)

def do(body, handler):
    return _composer.do(body, handler)

def doloop(body, test):
    return _composer.doloop(body, test)

def doloop_nosave(body, test):
    return _composer.doloop_nosave(body, test)

def ensure(body, finalizer):
    return _composer.ensure(body, finalizer)

def let(declarations, *arguments):
    return _composer.let(declarations, *arguments)

def mask(*arguments):
    return _composer.mask(*arguments)

def retain(*arguments):
    return _composer.retain(*arguments)

def retain_catch(*arguments):
    return _composer.retain_catch(*arguments)

def repeat(count, *arguments):
    return _composer.repeat(count, *arguments)

def retry(count, *arguments):
    return _composer.retry(count, *arguments)

def asynchronous(*arguments):
    return _composer.asynchronous(*arguments)

def merge(*arguments):
    return _composer.merge(*arguments)
