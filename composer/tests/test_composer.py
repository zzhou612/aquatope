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
import pytest

def check(combinator, n, name=None):
    # Check combinator type
    assert getattr(composer, combinator)(*['foo' for _ in range(n)]).type == name if name is not None else combinator

def empty():
    return {}

class TestAction:
    def test_combinator_type(self):
       assert getattr(composer.action('foo'), 'type') == 'action'

    def test_valid_and_invalid_names(self):
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
                assert composer.action(combo["n"]).name == combo["s"]
            else:
                # error cases
                try:
                    composer.action(combo["n"])
                    assert False
                except composer.ComposerError as error:
                    assert error.message.startswith(combo["e"])

    def test_valid_and_invalid_options(self):
        composer.action('foo', {})
        try:
            composer.action('foo', 42)
            assert False
        except composer.ComposerError as error:
            assert error.message.startswith('Invalid argument')

class TestComposition:
    def test_combinator_type(self):
       assert getattr(composer.composition('foo'), 'type') == 'composition'

    def test_valid_and_invalid_names(self):
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
                assert composer.composition(combo["n"]).name == combo["s"]
            else:
                # error cases
                try:
                    composer.composition(combo["n"])
                    assert False
                except composer.ComposerError as error:
                    assert error.message.startswith(combo["e"])


class TestFunction:
    def test_check(self):
        check('function', 1)

    def test_function(self):
        composer.function(lambda : {})

    def test_string(self):
        composer.function('lambda : {}')

    def test_number_invalid(self):
        try:
            composer.function(42)
        except composer.ComposerError as error:
            assert error.message.startswith('Invalid argument')

class TestLiteral:
    def test_check(self):
        check('literal', 1)

    def test_boolean(self):
        composer.literal(True)

    def test_number(self):
        composer.literal(42)

    def test_string(self):
        composer.literal('foo')

    def test_dict(self):
        composer.literal({ 'foo':42 })

    def test_function_invalid(self):
        try:
            composer.literal(lambda : {})
        except composer.ComposerError as error:
            assert error.message.startswith('Invalid argument')

class TestValue:
    def test_check(self):
        check('value', 1)

    def test_boolean(self):
        composer.value(True)

    def test_number(self):
        composer.value(42)

    def test_string(self):
        composer.value('foo')

    def test_dict(self):
        composer.value({ 'foo':42 })

    def test_function_invalid(self):
        try:
            composer.value(lambda : {})
        except composer.ComposerError as error:
            assert error.message.startswith('Invalid argument')

class TestParse:

    def test_combinator_type(self):
        composer.parse({
            'type': 'sequence',
            'components': [{
                'type': 'action',
                'name': 'echo'
            }, {
                'type': 'action',
                'name': 'echo'
            }]
        }).type == 'sequence'

class TestTask:
    def test_check(self):
        check('task', 1, 'action')

    def test_string(self):
        composer.task('isNotOne')

    def test_function(self):
        composer.task(empty)

    def test_lambda(self):
        composer.task(lambda : {})

    def test_none(self):
        composer.task(None)

    def test_boolean_invalid(self):
        try:
            composer.task(False)
            assert False
        except composer.ComposerError as error:
            assert error.message.startswith('Invalid argument')

    def test_dict_invalid(self):
        try:
            composer.task({ "foo": 42 })
            assert False
        except composer.ComposerError as error:
            assert error.message.startswith('Invalid argument')

class TestLet:

    def test_variable_argument_count(self):
        composer.let({})
        composer.let({}, 'foo')
        composer.let({}, 'foo', 'foo')

    def test_combinator_type(self):
        assert composer.let({}).type == 'let'

class TestRepeat:

     def test_variable_argument_count(self):
        composer.repeat(42)
        composer.repeat(42, 'foo')
        composer.repeat(42, 'foo', 'foo')

     def test_combinator_type(self):
        assert composer.repeat(42).type == 'repeat'

class TestRetry:

     def test_variable_argument_count(self):
        composer.retry(42)
        composer.retry(42, 'foo')
        composer.retry(42, 'foo', 'foo')

     def test_combinator_type(self):
        assert composer.retry(42).type == 'retry'

class TestWhen:

    def test_check(self):
        check('when', 2)

class TestWhenNoSave:

    def test_check(self):
        check('when_nosave', 2)

class TestLoop:

    def test_check(self):
        check('loop', 2)

class TestLoopNoSave:

    def test_check(self):
        check('loop_nosave', 2)

class TestDoLoop:

    def test_check(self):
        check('doloop', 2)

class TestDoLoopNoSave:

    def test_check(self):
        check('doloop_nosave', 2)

class TestDo:

    def test_check(self):
        check('do', 2)

class TestEnsure:

    def test_check(self):
        check('ensure', 2)

class TestExec:

    def test_check(self):
        check('exec', 0)

class TestEmpty:

    def test_check(self):
        check('empty', 0)

class TestMask:

    def test_check(self):
        check('mask', 0)

class TestAsync:

    def test_check(self):
        check('async', 0)

class TestMap:

    def test_check(self):
        check('map', 0)

class TestRetain:

    def test_check(self):
        check('retain', 0)

class TestRetainCatch:

    def test_check(self):
        check('retain_catch', 0)

class TestSequence:

    def test_check(self):
        check('sequence', 0)

class TestSeq:

    def test_check(self):
        check('seq', 0)

class TestMerge:

    def test_check(self):
        check('merge', 0)




