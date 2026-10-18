# SPDX-License-Identifier: AGPL-3.0-only
"""CI contract tests must work without network access or neural inference packages."""
import importlib.abc
import os
import socket
import sys

import pytest


@pytest.fixture(autouse=True)
def offline_contract_guard(monkeypatch):
    if os.environ.get('YOLO_TEST_OFFLINE') != '1':
        yield
        return

    def blocked(*args, **kwargs):
        raise AssertionError('network access forbidden in software contract tests')

    for name in ('create_connection', 'getaddrinfo'):
        monkeypatch.setattr(socket, name, blocked)
    for name in ('connect', 'connect_ex'):
        monkeypatch.setattr(socket.socket, name, blocked)

    class NoNeuralImports(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split('.')[0] in ('torch', 'torchvision', 'ultralytics'):
                raise AssertionError('real neural backend forbidden in software contract tests')
            return None

    finder = NoNeuralImports()
    sys.meta_path.insert(0, finder)
    try:
        yield
    finally:
        sys.meta_path.remove(finder)
