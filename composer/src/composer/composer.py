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

import json
import os
import sys
import inspect
import re
import base64
import marshal
import types
import copy

from composer import __version__

undefined = object() # special undefined value
composer = types.SimpleNamespace() # Simple object with attributes

composer.util = {
    'version': __version__
}

# Utility functions

def get_value(env, args):
    return env['value']

def set_params(env, args):
    env['params'] = args

def get_params(env, args):
    return env['params']

def retain_result(env, args):
    return { 'params': env['params'], 'result': args }

def retain_nested_result(env, args):
    return { 'params': args['params'], 'result': args['result']['result'] }

def dec_count(env, args):
    c = env['count']
    env['count'] -= 1
    return c > 0

def set_nested_params(env, args):
    return { 'params': args }

def get_nested_params(env, args):
    return args['params']

def set_nested_result(env, args):
    return { 'result': args }

def get_nested_result(env, args):
    return args['result']

def retry_cond(env, args):
    result = args['result']
    count = env['count']
    env['count'] -= 1
    return 'error' in result and count > 0

# lowerer

lowerer = types.SimpleNamespace()

loweropt = lambda f: setattr(lowerer, f.__name__, f)

@loweropt
def literal(value):
    return composer.let({ 'value': value }, lambda env, args: env['value'])

@loweropt
def retain(*components):
    return composer.let(
        { 'params': None },
        composer.ensure(
            set_params,
            composer.seq(composer.mask(*components), retain_result)))

@loweropt
def retain_catch(*components):
    return composer.seq(
        composer.retain(
            composer.ensure(
                composer.seq(*components),
                lambda env, args: { 'result' : args })),
        retain_nested_result)

@loweropt
def when(test, consequent, alternate):
    return composer.let(
        { 'params': None },
        set_params,
        composer.ensure(
            set_params,
            composer.when_nosave(
                composer.mask(test),
                composer.ensure(get_params, composer.mask(consequent)),
                composer.ensure(get_params, composer.mask(alternate)))))

@loweropt
def loop(test, body):
    return composer.let(
        { 'params': None },
        composer.ensure(
            set_params,
            composer.seq(composer.loop_nosave(
                composer.mask(test),
                composer.ensure(get_params, composer.seq(composer.mask(body), set_params))),
            get_params)))

@loweropt
def doloop(body, test):
    return composer.let(
        { 'params': None },
        composer.ensure(
            set_params,
            composer.seq(composer.doloop_nosave(
                composer.ensure(get_params, composer.seq(composer.mask(body), set_params)),
                composer.mask(test)),
            get_params)))

@loweropt
def repeat(count, *components):
   return composer.let(
      { 'count': count },
      composer.loop(
        dec_count,
        composer.mask(*components)))

@loweropt
def retry(count, *components):
    return composer.let(
        { 'count': count },
        set_nested_params,
        composer.doloop(
            composer.ensure(get_nested_params, composer.mask(composer.retain_catch(*components))),
            retry_cond),
        get_nested_result)

@loweropt
def merge (*components):
    return composer.seq(composer.retain(*components), lambda env, args: args['params'].update(args['result']))

# == Done lowerer

def visit(composition, f):
    ''' apply f to all fields of type composition '''
    composition = copy.copy(composition if isinstance(composition, dict) else composition.__dict__)

    combinator = composition['.combinator']()
    if 'components' in combinator:
        composition['components'] = list(map(lambda v: f(v, None), composition['components']))

    if 'args' in combinator:
        for arg in combinator['args']:
            if 'type' not in arg and arg['name'] in composition:
                composition[arg['name']] = f(composition[arg['name']], arg['name'])

    return Composition(composition)

def label(composition):
    ''' recursively label combinators with the json path '''
    def label(path):
        def labeler(composition, name=None, array=False):
            nonlocal path
            segment = ''
            if name is not None:
                if array:
                    segment = '['+name+']'
                else:
                    segment = '.'+name

            p = path + segment
            composition = visit(composition, label(p))
            composition.path = p
            return composition

        return labeler

    return label('')(composition)

def declare(combinators, prefix=None):
    '''
        derive combinator methods from combinator table
        check argument count and map argument positions to argument names
        delegate to Composition constructor for the rest of the validation
    '''
    if not isinstance(combinators, dict):
        raise ComposerError('Invalid argument "combinators" in "declare"', combinators)

    if prefix is not None and not isinstance(prefix, str):
        raise ComposerError('Invalid argument "prefix" in "declare"', prefix)

    composer = types.SimpleNamespace()
    for key in combinators:
        type_ = prefix + '.' + key if prefix is not None else key
        combinator = combinators[key]

        if not isinstance(combinator, dict) or ('args' in combinator and not isinstance(combinator['args'], list)):
            raise ComposerError('Invalid "'+type_+'" combinator specification in "declare"', combinator)

        if 'args' in combinator:
            for arg in combinator['args']:
                if not isinstance(arg['name'], str):
                    raise ComposerError('Invalid "'+type_+'" combinator specification in "declare"', combinator)

        # Javascript capturing rules differ from python3 ones.
        def capture(combinator=combinator, type_=type_):
            def combine(*arguments):
                composition = { 'type': type_, '.combinator': lambda : combinator }
                skip = len(combinator.get('args', []))
                if 'components' not in combinator and len(arguments) > skip:
                    raise ComposerError('Too many arguments in "'+type_+'" combinator')

                for i in range(skip):
                    composition[combinator['args'][i]['name']] = arguments[i]

                if 'components' in combinator:
                    composition['components'] = arguments[skip:]

                return Composition(composition)
            return combine

        setattr(composer, key, capture())

    return composer

def serialize(obj):
    return obj.__dict__

class Composition:
    def __init__(self, composition):
        '''  construct a composition object with the specified fields '''
        # shallow copy of obj attributes
        items = composition.items() if isinstance(composition, dict) else composition.__dict__.items() if isinstance(composition, Composition) else None
        if items is None:
            raise ComposerError('Invalid argument', composition)
        for k, v in items:
            setattr(self, k, v)

        combinator = composition['.combinator']()

        if 'args' in combinator:
            for arg in combinator['args']:
                optional = arg.get('optional', False)
                if arg['name'] not in composition and optional and 'type' in arg:
                    continue
                if 'type' not in arg:
                    try:
                        value = composition.get(arg['name'], None if optional else undefined)
                        setattr(self, arg['name'], composer.task(value))
                    except Exception:
                        raise ComposerError('Invalid argument "'+arg['name']+'" in "'+composition['type']+' combinator"', value)
                elif arg['type'] == 'name':
                    try:
                        setattr(self, arg['name'], parse_action_name(composition.get(arg['name'])))
                    except ComposerError as ce:
                        raise ComposerError(ce.message + ' in "'+composition['type']+' combinator"', composition.get(arg['name']))
                elif arg['type'] == 'value':
                    if callable(composition.get(arg['name'])) or arg['name'] not in composition:
                        raise ComposerError('Invalid argument "' + arg['name']+'" in "'+ composition['type']+' combinator"', composition.get(arg['name']))
                elif arg['type'] == 'object':
                    if not isinstance(composition.get(arg['name']), dict):
                        raise ComposerError('Invalid argument "' + arg['name']+'" in "'+ composition['type']+' combinator"', composition.get(arg['name']))
                else:
                    if type(composition.get(arg['name'])).__name__ != arg['type']:
                        raise ComposerError('Invalid argument "' + arg['name']+'" in "'+ composition['type']+' combinator"', composition.get(arg['name']))

        if 'components' in combinator:
            self.components = list(map(composer.task, composition.get('components', [])))


    def __str__(self):
        return json.dumps(self.__dict__, default=serialize, ensure_ascii=True)

    def compile(self):
        '''  compile composition. Returns a dictionary '''
        actions = []

        def flatten(composition, _=None):
            composition = visit(composition, flatten)

            if composition.type == 'action' and hasattr(composition, 'action'): # pylint: disable=E1101
                actions.append({ 'name': composition.name, 'action': composition.action })
                del composition.action # pylint: disable=E1101
            return composition

        obj = { 'composition': label(flatten(self)).lower(), 'ast': self, 'version': __version__ }
        if len(actions) > 0:
            obj['actions'] = actions
        return obj

    def lower(self, combinators = []):
        ''' recursively lower combinators to the desired set of combinators (including primitive combinators) '''
        if not isinstance(combinators, list) and not isinstance(combinators, str):
            raise ComposerError('Invalid argument "combinators" in "lower"', combinators)

        def lower(composition, _):
            # repeatedly lower root combinator

            while 'def' in getattr(composition, '.combinator')():
                path = composition.path if hasattr(composition, 'path') else None
                combinator = getattr(composition, '.combinator')()
                if isinstance(combinator, list) and combinator.indexOf(composition.type) >= 0:
                    break

                # map argument names to positions
                args = []
                skip = len(combinator.get('args', []))
                for i in range(skip):
                    args.append(getattr(composition, combinator['args'][i]['name']))

                if 'components' in combinator:
                    args.extend(composition.components)

                composition = combinator['def'](*args)

                # preserve path
                if path is not None:
                    composition.path = path

            return visit(composition, lower)

        return lower(self, None)


# primitive combinators
combinators = {
  'sequence': { 'components': True, 'since': '0.4.0' },
  # if_nosave
  'when_nosave': { 'args': [{ 'name': 'test' }, { 'name': 'consequent' }, { 'name': 'alternate', 'optional': True }], 'since': '0.4.0' },
  # while_nosave
  'loop_nosave': { 'args': [{ 'name': 'test' }, { 'name': 'body' }], 'since': '0.4.0' },
  # dowhile_nosave
  'doloop_nosave': { 'args': [{ 'name': 'body' }, { 'name': 'test' }], 'since': '0.4.0' },
  # try
  'do': { 'args': [{ 'name': 'body' }, { 'name': 'handler' }], 'since': '0.4.0' },
  # finally
  'ensure': { 'args': [{ 'name': 'body' }, { 'name': 'finalizer' }], 'since': '0.4.0' },
  'let': { 'args': [{ 'name': 'declarations', 'type': 'object' }], 'components': True, 'since': '0.4.0' },
  'mask': { 'components': True, 'since': '0.4.0' },
  'action': { 'args': [{ 'name': 'name', 'type': 'name' }, { 'name': 'action', 'type': 'object', 'optional': True }], 'since': '0.4.0' },
  'function': { 'args': [{ 'name': 'function', 'type': 'object' }], 'since': '0.4.0' },
  'asynchronous': { 'components': True, 'since': '0.6.0' },
  'execute': { 'since': '0.5.2' },
  'map': { 'components': True, 'since': '0.6.0' },
  'composition': { 'args': [{ 'name': 'name', 'type': 'name' }], 'since': '0.6.0' }
}

composer.__dict__.update(declare(combinators).__dict__)

# derived combinators
extra = {
  'empty': { 'since': '0.4.0', 'def': composer.sequence },
  'seq': { 'components': True, 'since': '0.4.0', 'def': composer.sequence },
  # if
  'when': { 'args': [{ 'name': 'test' }, { 'name': 'consequent' }, { 'name': 'alternate', 'optional': True }], 'since': '0.4.0', 'def': lowerer.when },
  # while
  'loop': { 'args': [{ 'name': 'test' }, { 'name': 'body' }], 'since': '0.4.0', 'def': lowerer.loop },
  # dowhile
  'doloop': { 'args': [{ 'name': 'body' }, { 'name': 'test' }], 'since': '0.4.0', 'def': lowerer.doloop },
  'repeat': { 'args': [{ 'name': 'count', 'type': 'int' }], 'components': True, 'since': '0.4.0', 'def': lowerer.repeat },
  'retry': { 'args': [{ 'name': 'count', 'type': 'int' }], 'components': True, 'since': '0.4.0', 'def': lowerer.retry },
  'retain': { 'components': True, 'since': '0.4.0', 'def': lowerer.retain },
  'retain_catch': { 'components': True, 'since': '0.4.0', 'def': lowerer.retain_catch },
  'value': { 'args': [{ 'name': 'value', 'type': 'value' }], 'since': '0.4.0', 'def': lowerer.literal },
  'literal': { 'args': [{ 'name': 'value', 'type': 'value' }], 'since': '0.4.0', 'def': lowerer.literal },
  'merge': { 'components': True, 'since': '0.13.0', 'def': lowerer.merge }
}

composer.__dict__.update(declare(extra).__dict__)

# add or override definitions of some combinators

combinator = lambda f: setattr(composer, f.__name__, f)

def task(task):
    ''' detect task type and create corresponding composition object '''
    if task is undefined:
        raise ComposerError('Invalid argument in "task" combinator', task)

    if task is None:
        return composer.empty()

    if isinstance(task, Composition):
        return task

    if callable(task):
        return composer.function(task)

    if isinstance(task, str): # python3 only
        return composer.action(task)

    raise ComposerError('Invalid argument "task" in "task" combinator', task)

composer.task = task

def function(fun):
    ''' function combinator: stringify def/lambda code '''
    if getattr(fun, '__name__', '') == '<lambda>':
        exc = str(base64.b64encode(marshal.dumps(fun.__code__)), 'ASCII')
    elif callable(fun):
        try:
            exc = inspect.getsource(fun)
        except OSError:
            raise ComposerError('Invalid argument', fun)
    else:
        exc = fun

    if isinstance(exc, str):
        if exc.startswith('def'):
            # standardize function name
            pattern = re.compile(r'def\s+([a-zA-Z_][a-zA-Z_0-9]*)\s*\(')
            match = pattern.match(exc)
            functionName = match.group(1)

            exc = { 'kind': 'python:3', 'code': exc, 'functionName': functionName }
        else: # lambda
            exc = { 'kind': 'python:3+lambda', 'code': exc }

    if not isinstance(exc, dict) or exc is None:
        raise ComposerError('Invalid argument "function" in "function" combinator', fun)

    return Composition({'type':'function', 'function':{ 'exec': exc }, '.combinator': lambda: combinators['function'] })

composer.function = function

def action(name, options = {}):
    ''' action combinator '''
    if not isinstance(options, dict):
        raise ComposerError('Invalid argument "options" in "action" combinator', options)
    exc = None
    if 'sequence' in options and isinstance(options['sequence'], list): # native sequence
        exc = { 'kind': 'sequence', 'components': tuple(map(parse_action_name, options['sequence'])) }
    elif 'filename' in options and isinstance(options['filename'], str): # read action code from file
        raise ComposerError('read from file not implemented')
        # exc = fs.readFileSync(options.filename, { encoding: 'utf8' })

    elif 'action' in options and callable(options['action']):
        if options['action'].__name__ == '<lambda>':
            l = str(base64.b64encode(marshal.dumps(options['action'].__code__)), 'ASCII')
            exc = '''import types\nimport marshal\nimport base64
__code__= types.FunctionType(marshal.loads(base64.b64decode(bytearray(\''''+ l +'''\', 'ASCII'))), {})
def main(args):
    return __code__(args)
'''
        else:
            try:
                exc = inspect.getsource(options['action'])
            except OSError:
                raise ComposerError('Invalid argument "options" in "action" combinator', options['action'])
    elif 'action' in options and (isinstance(options['action'], str) or isinstance(options['action'],  dict)):
        exc = options['action']

    if isinstance(exc, str):
        exc = { 'kind': 'python:3', 'code': exc }

    composition = { 'type': 'action', 'name': name, '.combinator': lambda: combinators['action']}
    if exc is not None:
        composition['action'] = { 'exec': exc }

    return Composition(composition)

composer.action = action

@combinator
def parse(composition):
    ''' recursively deserialize composition '''
    if not isinstance(composition, dict):
        raise ComposerError('Invalid argument "composition" in "parse" combinator', composition)

    combinator = composition['.combinator']() if '.combinator' in composition and callable(composition['.combinator']) else combinators[composition['type']]

    if not isinstance(combinator, dict):
        raise ComposerError('Invalid composition type in "parse" combinator', composition)

    extended = { '.combinator': lambda : combinator }
    extended.update(composition)
    return visit(extended, lambda composition, _: composer.parse(composition))

composer.action = action

def parse_action_name(name):
    '''
      Parses a (possibly fully qualified) resource name and validates it. If it's not a fully qualified name,
      then attempts to qualify it.

      Examples string to namespace, [package/]action name
        foo => /_/foo
        pkg/foo => /_/pkg/foo
        /ns/foo => /ns/foo
        /ns/pkg/foo => /ns/pkg/foo
    '''
    if not isinstance(name, str):
        raise ComposerError('Name must be a string')
    name = name.strip()
    if len(name) == 0:
        raise ComposerError('Name is not valid')

    delimiter = '/'
    parts = name.split(delimiter)
    n = len(parts)
    leadingSlash = name[0] == delimiter if len(name) > 0 else False
    # no more than /ns/p/a
    if n < 1 or n > 4 or (leadingSlash and n == 2) or (not leadingSlash and n == 4):
        raise ComposerError('Name is not valid')

    # skip leading slash, all parts must be non empty (could tighten this check to match EntityName regex)
    for part in parts[1:]:
        if len(part.strip()) == 0:
            raise ComposerError('Name is not valid')

    newName = delimiter.join(parts)
    if leadingSlash:
        return newName
    elif n < 3:
        return delimiter+'_'+delimiter+newName
    else:
        return delimiter+newName

class ComposerError(Exception):
    def __init__(self, message, *arguments):
       self.message = message
       self.argument = arguments
