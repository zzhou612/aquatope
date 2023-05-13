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

import composer
import conductor
import pytest
import os

name = 'TestAction'

wsk = conductor.openwhisk({ 'ignore_certs': 'IGNORE_CERTS' in os.environ and os.environ['IGNORE_CERTS'] == 'true' })

def define(action):
    ''' deploy action '''
    try:
        wsk.actions.delete(action['name'])
    except:
        pass
    wsk.actions.create(action)


def invoke(composition, params = {}, blocking = True):
   ''' deploy and invoke composition '''

   try:
       extended = { 'name': name }
       extended.update(composition.compile())
       wsk.compositions.deploy(extended, True)
       return wsk.actions.invoke({ 'name': name, 'params': params, 'blocking': blocking })
   except Exception as err:
       raise err

@pytest.fixture(scope="session", autouse=True)
def deploy_actions():
    define({ 'name': 'echo', 'action': 'const main = x=>x', 'kind': 'nodejs:default' })
    define({ 'name': 'DivideByTwo', 'action': 'function main({n}) { return { n: n / 2 } }', 'kind': 'nodejs:default'})
    define({ 'name': 'TripleAndIncrement', 'action': 'function main({n}) { return { n: n * 3 + 1 } }', 'kind': 'nodejs:default' })
    define({ 'name': 'isNotOne', 'action': 'function main({n}) { return { value: n != 1 } }', 'kind': 'nodejs:default' })
    define({ 'name': 'isEven', 'action': 'function main({n}) { return { value: n % 2 == 0 } }', 'kind': 'nodejs:default'})

def isEven(env, args):
    return args['n'] % 2 == 0

def set_then_true(env, args):
    args['then'] = True

def set_else_true(env, args):
    args['else'] = True

def dec_n(env, args):
    return {'n': args['n'] - 1 }

def cond_false(env, args):
    return False

def cond_nosave(env, args):
    return { 'n': args['n'], 'value': args['n'] != 1 }

def cond_true(env, args):
    return True

def return_error_message(env, args):
    return {'message': args['error']}

def set_error(env, args):
    return { 'error': 'foo' }

def set_p_4(env, args):
    return { 'p': 4 }

def nest_params(env, args):
    return { 'params': args }

def get_x(env, args):
    return env['x']

def get_x_plus_y(env, args):
    return env['x'] + env['y']

def get_value_plus_x(env, args):
    return args['value'] + env['x']

def noop(env, args):
    pass

class TestBlockingInvocations:
    def test_action_true(self):
        ''' action must return true '''
        activation = invoke(composer.action('isNotOne'), { 'n': 0 })
        assert activation['response']['result'] == { 'value': True }

    def test_action_false(self):
        ''' action must return false '''
        activation = invoke(composer.action('isNotOne'), { 'n': 1 })
        assert activation['response']['result'] == { 'value': False }

    def test_action_activation_id(self):
        ''' action must return activationId '''
        activation = invoke(composer.asynchronous('isNotOne'), { 'n': 1 }, False)
        assert 'activationId' in activation


    def test_parse_action_name(self):
        combos = [
            { "n": 42, "s": False, "e": "Name must be a string" },
            { "n": "", "s": False, "e": "Name is not valid" },
            { "n": " ", "s": False, "e": "Name is not valid" },
            { "n": "/", "s": False, "e": "Name is not valid" },
            { "n": "//", "s": False, "e": "Name is not valid" },
            { "n": "/a", "s": False, "e": "Name is not valid" },
            { "n": "/a/b/c/d", "s": False, "e": "Name is not valid" },
            { "n": "/a/b/c/d/", "s": False, "e": "Name is not valid" },
            { "n": "a/b/c/d", "s": False, "e": "Name is not valid" },
            { "n": "/a/ /b", "s": False, "e": "Name is not valid" },
            { "n": "a", "e": False, "s": "/_/a" },
            { "n": "a/b", "e": False, "s": "/_/a/b" },
            { "n": "a/b/c", "e": False, "s": "/a/b/c" },
            { "n": "/a/b", "e": False, "s": "/a/b" },
            { "n": "/a/b/c", "e": False, "s": "/a/b/c" }
        ]
        for combo in combos:
            if combo["s"] is not False:
                # good cases
                assert composer.parse_action_name(combo["n"]) == combo["s"]
            else:
                # error cases
                try:
                    composer.parse_action_name(combo["n"])
                    assert False
                except composer.ComposerError as error:
                    assert error.message == combo["e"]

    def test_invalid(self):
        '''invalid options'''
        try:
            invoke(composer.action('foo', 42))
            assert False
        except composer.ComposerError as error:
            assert error.message.startswith('Invalid argument')

class TestLiteral:

    def test_boolean(self):
        activation = invoke(composer.literal(True))
        assert activation['response']['result'] == { 'value': True }

    def test_number(self):
        activation = invoke(composer.literal(42))
        assert activation['response']['result'] == { 'value': 42 }

    def test_invalid_arg(self):
        try:
            composer.literal(lambda x:x)
            assert False
        except composer.ComposerError as error:
            assert error.message.startswith('Invalid argument')

class TestFunction:

    def test_function_true(self):
         activation = invoke(composer.function(isEven), { 'n': 4 })
         assert activation['response']['result'] == { 'value': True }

    def test_lambda(self):
         activation = invoke(composer.function(lambda env, args: args['n'] % 2 == 0), { 'n': 4 })
         assert activation['response']['result'] == { 'value': True }

class TestTasks:

    def test_task_action(self):
        activation = invoke(composer.task('isNotOne'), { 'n': 0 })
        assert activation['response']['result'] == { 'value': True }

    def test_task_function(self):
        activation = invoke(composer.task(isEven), { 'n': 4 })
        assert activation['response']['result'] == { 'value': True }

    def test_task_none(self):
        activation = invoke(composer.task(None), { 'foo': 'foo' })
        assert activation['response']['result'] == { 'foo': 'foo' }

    def test_task_fail(self):
        '''none task must fail on error input'''
        try:
            invoke(composer.task(None), { 'error': 'foo' })
            assert False
        except Exception as error:
            print(error)

class TestSequence:

    def test_flat(self):
        activation = invoke(composer.sequence('TripleAndIncrement', 'DivideByTwo', 'DivideByTwo'), { 'n': 5 })
        assert activation['response']['result'] == { 'n': 4 }

    def test_nested_right(self):
        activation = invoke(composer.sequence('TripleAndIncrement', composer.sequence('DivideByTwo', 'DivideByTwo')), { 'n': 5 })
        assert activation['response']['result'] == { 'n': 4 }

    def test_nested_left(self):
        activation = invoke(composer.sequence(composer.sequence('TripleAndIncrement', 'DivideByTwo'), 'DivideByTwo'), { 'n': 5 })
        assert activation['response']['result'] == { 'n': 4 }

    def test_seq(self):
        activation = invoke(composer.seq('TripleAndIncrement', 'DivideByTwo', 'DivideByTwo'), { 'n': 5 })
        assert activation['response']['result'] == { 'n': 4 }

class TestIf:
    def test_condition_true(self):
        activation = invoke(composer.when('isEven', 'DivideByTwo', 'TripleAndIncrement'), { 'n': 4 })
        assert activation['response']['result'] == { 'n': 2 }

    def test_condition_false(self):
        activation =  invoke(composer.when('isEven', 'DivideByTwo', 'TripleAndIncrement'), { 'n': 3 })
        assert activation['response']['result'] == { 'n': 10 }

    def test_condition_true_then_branch_only(self):
        activation =  invoke(composer.when('isEven', 'DivideByTwo'), { 'n': 4 })
        assert activation['response']['result'] == { 'n': 2 }

    def test_condition_false_then_branch_only(self):
        activation =  invoke(composer.when('isEven', 'DivideByTwo'), { 'n': 3 })
        assert activation['response']['result'] == { 'n': 3 }

    def test_condition_true_nosave_option(self):
        activation =  invoke(composer.when_nosave('isEven', set_then_true, set_else_true), { 'n': 2 })
        assert activation['response']['result'] == { 'value': True, 'then': True }

    def test_condition_false_nosave_option(self):
        activation = invoke(composer.when_nosave('isEven', set_then_true, set_else_true), { 'n': 3 })
        assert activation['response']['result'] == { 'value': False, 'else': True }

class TestLoop:

    def test_a_few_iterations(self) :
        activation = invoke(composer.loop('isNotOne', lambda env, args: {'n': args['n'] - 1 }), { 'n': 4 })
        assert activation['response']['result'] == { 'n': 1 }

    def test_no_iteration(self):
        activation = invoke(composer.loop(cond_false, dec_n), { 'n': 1 })
        assert activation['response']['result'] == { 'n': 1 }

    def test_nosave_option(self) :
        activation = invoke(composer.loop_nosave(cond_nosave, dec_n), { 'n': 4 })
        assert activation['response']['result'] == { 'value': False, 'n': 1 }

class TestDoLoop:

    def test_a_few_iterations(self) :
        activation = invoke(composer.doloop(dec_n, 'isNotOne'), { 'n': 4 })
        assert activation['response']['result'] == { 'n': 1 }

    def test_one_iteration(self) :
        activation = invoke(composer.doloop(dec_n, cond_false), { 'n': 1 })
        assert activation['response']['result'] == { 'n': 0 }

    def test_nosave_option(self) :
        activation = invoke(composer.doloop_nosave(dec_n, cond_nosave), { 'n': 4 })
        assert activation['response']['result'] == { 'value': False, 'n': 1 }

class TestDo: # Try
    def test_no_error(self):
        activation = invoke(composer.do(cond_true, return_error_message), {})
        assert activation['response']['result'] == { 'value': True }

    def test_error(self) :
        activation = invoke(composer.do(set_error, return_error_message), {})
        assert activation['response']['result'] == { 'message': 'foo' }

    def test_try_must_throw(self) :
        activation = invoke(composer.do(composer.task(None), return_error_message), { 'error': 'foo' })
        assert activation['response']['result'] == { 'message': 'foo' }

    def test_while_must_throw(self) :
        activation = invoke(composer.do(composer.loop(composer.literal(False), None), return_error_message), { 'error': 'foo' })
        assert activation['response']['result'] == { 'message': 'foo' }

    def test_if_must_throw(self) :
        activation = invoke(composer.do(composer.when(composer.literal(False), None), return_error_message), { 'error': 'foo' })
        assert activation['response']['result'] == { 'message': 'foo' }

    def test_retain(self) :
        activation = invoke(composer.retain(composer.do(set_p_4, None)), { 'n': 3 })
        assert activation['response']['result'] == { 'params': { 'n': 3 }, 'result': { 'p': 4 } }

class TestEnsure: # Finally

    def test_no_error(self) :
        activation = invoke(composer.ensure(cond_true, nest_params), {})
        assert activation['response']['result'] == { 'params': { 'value': True } }

    def test_error(self) :
        activation = invoke(composer.ensure(set_error, nest_params), {})
        assert activation['response']['result'] == { 'params': { 'error': 'foo' } }

class TestLet:

    def test_one_variable(self) :
        activation = invoke(composer.let({ 'x': 42 }, get_x), {})
        assert activation['response']['result'] == { 'value': 42 }

    def test_masking(self) :
        activation = invoke(composer.let({ 'x': 42 }, composer.let({ 'x': 69 }, get_x)), {})
        assert activation['response']['result'] == { 'value': 69 }

    def test_two_variables(self) :
        activation = invoke(composer.let({ 'x': 42 }, composer.let({ 'y': 69 }, get_x_plus_y)), {})
        assert activation['response']['result'] == { 'value': 111 }

    def test_two_variables_combined(self) :
        activation = invoke(composer.let({ 'x': 42, 'y': 69 }, get_x_plus_y), {})
        assert activation['response']['result'] == { 'value': 111 }

    def test_scoping(self) :
        activation = invoke(composer.let({ 'x': 42 }, composer.let({ 'x': 69 }, get_x), get_value_plus_x), {})
        assert activation['response']['result'] == { 'value': 111 }

    def test_invalid_argument(self):
        try:
            invoke(composer.let(invoke))
            assert False
        except composer.ComposerError as error:
            assert error.message.startswith('Invalid argument')

class TestMask:

    def test_let_let_mask(self) :
        activation = invoke(composer.let({ 'x': 42 }, composer.let({ 'x': 69 }, composer.mask(get_x))), {})
        assert activation['response']['result'] == { 'value': 42 }

    def test_let_mask_let(self) :
        activation = invoke(composer.let({ 'x': 42 }, composer.mask(composer.let({ 'x': 69 }, get_x))), {})
        assert activation['response']['result'] == { 'value': 69 }

    def test_let_let_try_mask(self) :
        activation = invoke(composer.let({ 'x': 42 }, composer.let({ 'x': 69 },
            composer.do(composer.mask(get_x), noop))))
        assert activation['response']['result'] == { 'value': 42 }

    def test_let_let_let_mask(self) :
        activation = invoke(composer.let({ 'x': 42 }, composer.let({ 'x': 69 },
            composer.let({ 'x': -1 }, composer.mask(get_x)))))
        assert activation['response']['result'] == { 'value': 69 }

    def test_let_let_let_mask_mask(self) :
        activation = invoke(composer.let({ 'x': 42 }, composer.let({ 'x': 69 },
            composer.let({ 'x': -1 }, composer.mask(composer.mask(get_x))))), {})
        assert activation['response']['result'] == { 'value': 42 }

    def test_let_let_mask_let_mask(self) :
        activation = invoke(composer.let({ 'x': 42 }, composer.let({ 'x': 69 },
            composer.mask(composer.let({ 'x': -1 }, composer.mask(get_x))))))
        assert activation['response']['result'] == { 'value': 42 }

class TestRetain:

    def test_base_case(self) :
        activation = invoke(composer.retain('TripleAndIncrement'), { 'n': 3 })
        assert activation['response']['result'] == { 'params': { 'n': 3 }, 'result': { 'n': 10 } }

    def test_throw_error(self) :
        try:
            invoke(composer.retain(set_error), { 'n': 3 })
            assert False
        except Exception as err:
            assert err.error['response']['result'] == { 'error': 'foo' }

    def test_catch_error(self) :
        activation = invoke(composer.retain_catch(set_error), { 'n': 3 })
        assert activation['response']['result'] == { 'params': { 'n': 3 }, 'result': { 'error': 'foo' } }

class TestRepeat:

    def test_a_few_iterations(self) :
        activation = invoke(composer.repeat(3, 'DivideByTwo'), { 'n': 8 })
        assert activation['response']['result'] == { 'n': 1 }

    def test_invalid_argument(self) :
        try:
            invoke(composer.repeat('foo'))
            assert False
        except composer.ComposerError as error:
            assert error.message.startswith('Invalid argument')

def retry_test(env, args):
    x = env['x']
    env['x'] -= 1
    return { 'error': 'foo' } if x > 0 else 42

class TestRetry:

    def test_success(self) :
        activation = invoke(composer.let({ 'x': 2 }, composer.retry(2, retry_test)))
        assert activation['response']['result'] == { 'value': 42 }

    def test_failure(self) :
        try:
            invoke(composer.let({ 'x': 2 }, composer.retry(1, retry_test)))
            assert False
        except Exception as err:
            assert err.error['response']['result'] == { 'error': 'foo' }

    def test_invalid_argument(self) :
        try:
            invoke(composer.retry('foo'))
            assert False
        except composer.ComposerError as error:
            assert error.message.startswith('Invalid argument')
