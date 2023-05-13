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

def main():
    parser = argparse.ArgumentParser(description='comppile compositions', prog='pycompose', usage='%(prog)s composition.py command [flags]')
    parser.add_argument('file', metavar='composition', type=str, help='the composition')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s '+ composer.__version__)
    parser.add_argument('--ast', action='store_true', help='output ast')

    args = parser.parse_args()

    filename = args.file
    with open(filename, encoding='UTF-8') as f:
        source = f.read()

    main = '''exec(code + "\\n__out__['value'] = main()", {'__out__':__out__})'''

    try:
        out = {'value': None}
        exec(main, {'code': source, '__out__': out})

        composition = out['value']
        composition = composition.compile()

        if args.ast:
            composition = composition['ast']

        print(json.dumps(composition, default=composer.serialize, ensure_ascii=True))
    except Exception as err:
        print(err)
        return

if __name__ == '__main__':
    main()
