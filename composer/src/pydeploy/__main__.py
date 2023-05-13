#!/usr/bin/env python3
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

import argparse
import json
import composer
import conductor
import sys

def keyValue(a):
    parts = a.partition('=')
    if parts[1] != '=':
        raise 'Annotation syntax must be "KEY=VALUE"'
    return { 'key': parts[0], 'value': parts[2] }

def keyValueFromFile(a):
    parts = a.partition('=')
    if parts[1] != '=':
        raise 'Annotation syntax must be "KEY=FILE"'

    with open(parts[2], encoding='UTF-8') as f:
        value = json.load(f)

    return { 'key': parts[0], 'value': value }


def main():
    parser = argparse.ArgumentParser(description='deploy composition', prog='pydeploy', usage='%(prog)s composition composition.json [flags]')
    parser.add_argument('name', metavar='composition', type=str, help='composition name')
    parser.add_argument('file', metavar='composition', type=str, help='composition')
    parser.add_argument('--apihost', action='store', metavar='HOST', help='API HOST')
    parser.add_argument('-i', '--insecure', action='store_true', help='bypass certificate checking')
    parser.add_argument('-u', '--auth', metavar='KEY', help='authorization KEY')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s '+ composer.__version__)
    parser.add_argument('-a', '--annotation', action='append', nargs=1, help='add KEY annotation with VALUE')
    parser.add_argument('-A', '--annotation-file', action='append', nargs=1, help='add KEY annotation with FILE content')
    parser.add_argument('-w', '--overwrite',  action='store_true', help='overwrite actions if already defined')

    args = parser.parse_args()

    try:
        filename = args.file

        with open(filename, encoding='UTF-8') as f:
            composition = json.load(f)

        if 'ast' not in composition:
            raise 'Composition must have a field "ast" of type dictionary'
        if 'composition' not in composition:
            raise 'Composition must have a field "composition" of type dictionary'
        if 'version' not in composition:
            raise 'Composition must have a field "composition" of type dictionary'
        if 'actions' in composition:
            if not isinstance(composition['actions'], list):
                raise 'Optional field "actions" must be an array'

        composition['annotations'] = []

        if args.annotation is not None:
            composition['annotations'].extend([keyValue(a[0]) for a in args.annotation])

        if args.annotation is not None:
            composition['annotations'].extend([keyValueFromFile(a[0]) for a in args.annotation_file])

    except Exception as err:
        print(err)
        sys.exit(422 - 256) # Unprocessable Entity


    options = { 'ignore_certs': args.insecure }
    if args.apihost is not None:
        options['apihost'] = args.apihost
    if args.auth is not None:
        options['api_key'] = args.auth

    try:
        composition['name'] = composer.parse_action_name(args.name)
    except Exception as err:
        print(err)
        sys.exit(400 - 256) # Bad Request

    try:
        actions = conductor.openwhisk(options).compositions.deploy(composition, args.overwrite)
        names = ' '.join([n['name'] for n in actions])
        print('ok: created action'+ ('s' if len(names) > 1 else '') + '' + names)
    except Exception as err:
        print(err.error)
        sys.exit(500 - 256)

if __name__ == '__main__':
    main()

