<!--
#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
-->
# composer-python

[![Build Status](https://travis-ci.org/apache/openwhisk-composer-python.svg?branch=master)](https://travis-ci.org/apache/openwhisk-composer-python)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Join
Slack](https://img.shields.io/badge/join-slack-9B69A0.svg)](http://slack.openwhisk.org/)

This repository provides a Python library for [Composer](https://github.com/apache/openwhisk-composer). For convenience, the Composer documentation is repeated below using Python bindings instead of JavaScript.

Composer is a new programming model for composing cloud functions built on
[Apache OpenWhisk](https://github.com/apache/openwhisk). With
Composer, developers can build even more serverless applications including using
it for IoT, with workflow orchestration, conversation services, and devops
automation, to name a few examples.

This repository includes:
* the [composer](src/composer/composer.py) Python library for authoring compositions using Python,
* the [pycompose](src/pycompose/__main__.py) and [pydeploy](src/pydeploy/__main__.py)
  [commands](docs/COMMANDS.md) for compiling and deploying compositions,
* [documentation](docs), [examples](samples), and [tests](tests).

## Installation

You need python3.6 installed on your system.

### From github

```bash
$ git clone https://github.com/apache/openwhisk-composer-python.git
$ cd composer-python
$ pip3 install -e .
$ pycompose -h
usage: pycompose composition.py command [flags]
$ pydeploy -h
usage: pydeploy composition composition.json [flags]
```

### From PyPi (**Not available yet**)

Composer will eventually be distributed on [PyPi](https://pypi.org/). Once it is available, to install this package, use `pip`:
```
$ pip3 install openwhisk-composer
```
Shell embeds the Composer package, so there is no need to install
Composer for Python explicitly when using Shell.

## Defining a composition

A composition is typically defined by means of a Python expression as
illustrated in [samples/demo.py](samples/demo.py):

```python
import composer

def main():
    return composer.when(
        composer.action('authenticate',  { 'action': lambda args: { 'value': args['password'] == 'abc123' } }),
        composer.action('success', { 'action': lambda args: { 'message': 'success' } }),
        composer.action('failure', { 'action': lambda args: { 'message': 'failure' } }))
```
Compositions compose actions using [combinator](docs/COMBINATORS.md) methods. These methods
implement the typical control-flow constructs of a sequential imperative
programming language. This example composition composes three actions named
`authenticate`, `success`, and `failure` using the `composer.when` combinator,
which implements the usual conditional construct. It take three actions (or
compositions) as parameters. It invokes the first one and, depending on the
result of this invocation, invokes either the second or third action.

## Deploying a composition

One way to deploy a composition is to use the `pycompose` and `pydeploy` commands:
```
pycompose demo.py > demo.json
pydeploy demo demo.json -w
```
```
ok: created /_/authenticate,/_/success,/_/failure,/_/demo
```
The `pycompose` command compiles the composition code to a portable JSON format.
The `pydeploy` command deploys the JSON-encoded composition creating an action
with the given name. It also deploys the composed actions if definitions are
provided for them. The `-w` option authorizes the `deploy` command to overwrite
existing definitions.

## Running a composition

The `demo` composition may be invoked like any action, for instance using the
OpenWhisk CLI:
```
wsk action invoke demo -p password passw0rd
```
```
ok: invoked /_/demo with id 4f91f9ed0d874aaa91f9ed0d87baaa07
```
The result of this invocation is the result of the last action in the
composition, in this case the `failure` action since the password in incorrect:
```
wsk activation result 4f91f9ed0d874aaa91f9ed0d87baaa07
```
```json
{
    "message": "failure"
}
```
## Execution traces

This invocation creates a trace, i.e., a series of activation records:
```
wsk activation list
```
```
activations
fd89b99a90a1462a89b99a90a1d62a8e demo
eaec119273d94087ac119273d90087d0 failure
3624ad829d4044afa4ad829d40e4af60 demo
a1f58ade9b1e4c26b58ade9b1e4c2614 authenticate
3624ad829d4044afa4ad829d40e4af60 demo
4f91f9ed0d874aaa91f9ed0d87baaa07 demo
```
The entry with the earliest start time (`4f91f9ed0d874aaa91f9ed0d87baaa07`)
summarizes the invocation of the composition while other entries record later
activations caused by the composition invocation. There is one entry for each
invocation of a composed action (`a1f58ade9b1e4c26b58ade9b1e4c2614` and
`eaec119273d94087ac119273d90087d0`). The remaining entries record the beginning
and end of the composition as well as the transitions between the composed
actions.

Compositions are implemented by means of OpenWhisk conductor actions. The
[documentation of conductor
actions](https://github.com/apache/openwhisk/blob/master/docs/conductors.md)
explains execution traces in greater details.
