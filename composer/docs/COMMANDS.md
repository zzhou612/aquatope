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

# Commands

The `pycompose` command compiles composition code to a portable JSON format. The
`pydeploy` command deploys JSON-encoded compositions. These commands are intended
as a minimal complement to the OpenWhisk CLI. The OpenWhisk CLI already has the
capability to configure, invoke, and delete compositions since these are just
OpenWhisk actions but lacks the capability to create composition actions. The
`pycompose` and `pydeploy` commands bridge this gap. They make it possible to deploy
compositions as part of the development cycle or in shell scripts. They do not
replace the OpenWhisk CLI however as they do not duplicate existing OpenWhisk
CLI capabilities.

## Compose

```
pycompose
```
```
Usage:
  compose composition.py [flags]
Flags:
  --ast                  only output the ast for the composition
  -v, --version          output the composer version
```
The `pycompose` command takes a Python script that defines `main()` returning a
composition object (for example [demo.py](../samples/demo.py)) and compiles this object to a
portable JSON format on the standard output.
```
compose demo.py > demo.json
```
If the `--ast` option is specified, the `pycompose` command only outputs a JSON
representation of the Abstract Syntax Tree for the composition.

# Deploy

```
pydeploy
```
```
Usage:
  pydeploy composition composition.json [flags]
Flags:
  -a, --annotation KEY=VALUE        add KEY annotation with VALUE
  -A, --annotation-file KEY=FILE    add KEY annotation with FILE content
  --apihost HOST                    API HOST
  -i, --insecure                    bypass certificate checking
  -u, --auth KEY                    authorization KEY
  -v, --version                     output the composer version
  -w, --overwrite                   overwrite actions if already defined
```
The `pydeploy` command deploys a JSON-encoded composition with the given name.
```
pydeploy demo demo.json -w
```
```
ok: created /_/authenticate,/_/success,/_/failure,/_/demo
```

The `pydeploy` command synthesizes and deploys a conductor action that implements
the composition with the given name. It also deploys the composed actions for
which definitions are provided as part of the composition.

The `pydeploy` command outputs the list of deployed actions or an error result. If
an error occurs during deployment, the state of the various actions is unknown.

The `-w` option authorizes the `pydeploy` command to overwrite existing
definitions. More precisely, it deletes the deployed actions before recreating
them. As a result, default parameters, limits, and annotations on preexisting
actions are lost.

### Annotations

The `pydeploy` command implicitly annotates the deployed composition action with
the required `conductor` annotations. Other annotations may be specified by
means of the flags:
```
  -a, --annotation KEY=VALUE        add KEY annotation with VALUE
  -A, --annotation-file KEY=FILE    add KEY annotation with FILE content
```

### OpenWhisk instance

Like the OpenWhisk CLI, the `pydeploy` command supports the following flags for
specifying the OpenWhisk instance to use:
```
  --apihost HOST                    API HOST
  -i, --insecure                    bypass certificate checking
  -u, --auth KEY                    authorization KEY
```
If the `--apihost` flag is absent, the environment variable `__OW_API_HOST` is
used in its place. If neither is available, the `pydeploy` command extracts the
`APIHOST` key from the whisk property file for the current user.

If the `--auth` flag is absent, the environment variable `__OW_API_KEY` is used
in its place. If neither is available, the `pydeploy` command extracts the `AUTH`
key from the whisk property file for the current user.

The default path for the whisk property file is `$HOME/.wskprops`. It can be
altered by setting the `WSK_CONFIG_FILE` environment variable.
