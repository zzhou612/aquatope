#!/bin/bash
tox -e py36 -- pytest -s "tests/test_conductor.py::TestBlockingInvocations::test_action_activation_id"