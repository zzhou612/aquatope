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

""" Minimal OpenWhisk Client for Python """
import urllib.parse
import os
import requests
import base64
import json

class Client:
    def __init__(self, options=None):
        self.options = self.parse_options(options if options is not None else {})
        self.actions = Action(self)

    def parse_options(self, options):
        api_key = options['api_key'] if 'api_key' in options else (os.environ['__OW_API_KEY'] if '__OW_API_KEY' in os.environ else None)
        ignore_certs = options['ignore_certs'] if 'ignore_certs' in options else False
        # if apihost is available, parse this into full API url
        api = options['api'] if 'api' in options else self.url_from_apihost(options['apihost'] if 'apihost' in options else (os.environ['__OW_APIHOST'] if '__OW_API___OW_APIHOST' in os.environ else None))

        if api_key is None:
            raise Exception(invalid_options_error, 'Missing api_key parameter.')
        elif api is None:
            raise Exception(invalid_options_error, 'Missing either api or apihost parameters.')

        namespace = options['namespace'] if 'namespace' in options else None
        return {'api_key':api_key, 'api': api, 'ignore_certs':ignore_certs, 'namespace': namespace }

    def url_from_apihost(self, apihost):
        if apihost is None:
            return apihost
        url = apihost+'/api/v1/'

        # if apihost does not the protocol, assume HTTPS
        if not url.startswith('http') :
            url = 'https://' + url

        return url

    def request(self, method, path, options):
        url = self.path_url(path)
        params = options['qs'] if 'qs' in options else None
        body = options['body'] if 'body' in options else None

        serializer = options['serializer'] if 'serializer' in options else None
        payload = json.dumps(body, default=serializer)
        headers = { 'Authorization': self.auth_header(), 'Content-Type': 'application/json' }
        verify = not self.options['ignore_certs']

        resp = requests.request(method, url, params=params, data=payload, headers=headers, verify=verify)

        if resp.status_code >= 400:
            # we turn >=400 statusCode responses into exceptions
            error = Exception()
            error.status_code = resp.status_code
            error.error = resp.json()
            raise error
        else:
            # otherwise, the response body is the expected return value
            return resp.json()

    def path_url(self, url_path):
        endpoint = self.api_url()
        return urllib.parse.urlunparse(urllib.parse.ParseResult(endpoint.scheme, endpoint.netloc,  urllib.parse.urljoin(endpoint.path, url_path), endpoint.params, endpoint.query, endpoint.fragment))

    def api_url(self):
        return urllib.parse.urlparse(self.options['api'] if self.options['api'].endswith('/') else self.options['api'] + '/')

    def auth_header(self):
        return 'Basic '+ base64.b64encode(self.options['api_key'].encode()).decode()

default_namespace = os.environ['__OW_NAMESPACE'] if '__OW_NAMESPACE' in os.environ else '_'

class BaseOperation:
    def __init__(self, client, resource):
        self.client = client
        self.resource = resource

    def request(self, params):
        namespace = self.namespace(params['options'])
        path = self.resource_path(namespace, params['id'])
        return self.client.request(params['method'], path, params['options'])

    def resource_path(self, namespace, id=None):
        path = 'namespaces/'+namespace+'/'+self.resource

        if id is not None:
            path += '/'+id

        return path

    def namespace(self, options=None):

        if options is not None and isinstance(options['namespace'], str):
            return urllib.parse.quote(options['namespace'].encode('utf-8'))

        if 'namespace' in self.client.options and isinstance(self.client.options['namespace'], str):
            return urllib.parse.quote(self.client.options['namespace'].encode('utf-8'))
        return urllib.parse.quote(default_namespace)

    def qs(self, options, names):
        filtered = {}
        for name in names:
            if name in options:
                filtered[name] = options[name]
        return filtered

class Resource(BaseOperation):
    def __init__(self, client, resource):
        super(Resource, self).__init__(client, resource)
        self.identifiers = ['name']
        self.qs_options = {}

    def list(self, options):
        return self.operation('GET', options)

    def get(self, options):
        return self.operation_with_id('GET', options)

    def invoke(self, options=None):
        options = options if options is not None else {}

        if isinstance(options, dict):
            options['qs'] = self.qs(options, self.qs_options['invoke'] if 'invoke' in self.qs_options else [])
            options['body'] = self.payload(options)

        return self.operation_with_id('POST', options)

    def create(self, options):
        return self.operation_with_id('PUT', options)

    def delete(self, options):
        return self.operation_with_id('DELETE', options)

    def update(self, options):
        options = self.parse_options(options)
        options['overwrite'] = True
        return self.create(options)

    def operation(self, method, options):
        options = self.parse_options(options)
        id = options['id']
        return self.request({ 'method':method, 'id':id, 'options':options })

    def operation_with_id(self, method, options):
        if isinstance(options, list):
            return list(map(lambda i: self.operation_with_id(method, i), options))

        options = self.parse_options(options)
        options['namespace'] = self.parse_namespace(options)
        options['id'] = self.parse_id(options)
        return self.operation(method, options)

    def parse_options(self, options=None):
        if isinstance(options, str):
            options = { 'name': options }

        return options if options is not None else {}

    def parse_id(self, options):
        id = self.retrieve_id(options)
        return parse_id(id)

    def parse_namespace(self, options):
        id = self.retrieve_id(options)

        if id.startswith('/'):
            return parse_namespace(id)

        return options['namespace'] if 'namespace' in options else None

    def retrieve_id(self, options=None):
        options = options if options is not None else {}
        id = next((x for x in self.identifiers if x in options))

        if id is None:
            raise Exception('Missing resource identifier from parameters, supported parameter names: '+', '.join(self.identifiers))

        return options[id]

    def payload(self, options):
        if not 'params' in options:
            return {}

        if isinstance(options['params'], dict):
            return options['params']

        raise Exception('Invalid payload type, must be an dictionary.')

class Action(Resource):
    def __init__(self, client):
        super(Action, self).__init__(client, 'actions')
        self.identifiers.append('actionName')
        self.qs_options['invoke'] = ['blocking']

    def list(self, options=None):
        options = options if options is not None else {}
        options['qs'] = self.qs(options, ['skip', 'limit'])

        return super().list(options)

    def invoke(self, options=None):
        options = options if options is not None else {}

        if 'blocking' in options and 'result' in options:
            return super().invoke(options)['response']['result']

        return super().invoke(options)

    def create(self, options):
        options['qs'] = self.qs(options, ['overwrite'])
        options['body'] = self.action_body(options)

        return super().create(options)

    def action_body(self, options):
        if 'action' not in options:
            raise Exception(missing_action_body_error)
        if isinstance(options['action'], dict):
            return options['action']

        body = { 'exec': { 'kind': options['kind'] if 'kind' in options else 'python:3', 'code': options['action'] } }

        if isinstance(options['action'], bytes):
            body['exec']['code'] = base64.encodebytes(options['action'])

        if 'limits' in options:
            body['limits'] = options['limits']

        if 'annotations' in options and isinstance(options['annotations'], dict):
            annotations = []
            for key, value in options['annotations']:
                annotations.append({ 'key':key, 'value': value})
            body['annotations'] = annotations

        return body


def parse_id_and_ns(name):
    name = name.strip()
    if len(name) == 0:
        raise Exception('Name is not specified')
    parts = name.split('/')

    n = len(parts) - 1
    leadingSlash = name[0] == '/' if len(name) > 0 else False

    if n == 0 or (n == 1 and not leadingSlash):
        return { 'namespace': default_namespace, 'id': name }

    # checking for `/namespace/resource_name` and `namespace/package/resource_name`
    if n == 2:
        if leadingSlash:
            return { 'namespace': parts[1], 'id': parts[2] }
        else:
            return { 'namespace': parts[0], 'id': parts[1]+'/'+parts[2] }

    # checking for `/namespace/package/resource_name`
    if n == 3 and leadingSlash:
        return { 'namespace': parts[1], 'id': parts[2]+'/'+parts[3] }

    raise Exception(invalid_resource_error)

def parse_id(name):
    return parse_id_and_ns(name)['id']

def parse_namespace(name):
    return parse_id_and_ns(name)['namespace']

missing_feed_name_error= 'Missing mandatory feedName or id parameters from options.',
missing_feed_trigger_error= 'Missing mandatory trigger parameter from options.',
missing_action_error= 'Missing mandatory actionName parameter from options.',
invalid_action_error= 'Invalid actionName parameter from options. Should be "action", "/namespace/action" or "/namespace/package/action".',
invalid_resource_error= 'Invalid resource identifier from options. Should be "resource", "/namespace/resource" or "/namespace/package/resource".',
missing_action_body_error= 'Missing mandatory action parameter from options.',
missing_rule_error= 'Missing mandatory ruleName parameter from options.',
missing_trigger_error= 'Missing mandatory triggerName parameter from options.',
missing_package_error= 'Missing mandatory packageName parameter from options.',
missing_activation_id_error= 'Missing mandatory activation parameter from options.',
missing_rule_action_error= 'Missing mandatory action parameter from options.',
missing_rule_trigger_error= 'Missing mandatory trigger parameter from options.',
missing_trigger_body_error= 'Missing mandatory trigger parameter from options.',
missing_package_body_error= 'Missing mandatory package parameter from options.',
missing_namespace_error= 'Missing namespace from options, please set a default namespace or pass one in the options.',
invalid_options_error= 'Invalid constructor options.',
missing_basepath_error= 'Missing mandatory parameters: basepath or name.',
invalid_basepath_error= 'Invalid parameters: use basepath or name, not both.'
