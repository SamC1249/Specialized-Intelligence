"""Assert that the offline-only invariant from AGENTS.md is enforced.

If a future contributor removes `--disable-socket` from pyproject.toml
or the conftest hook, these tests catch it before CI merges.
"""

from __future__ import annotations

import socket

import pytest


@pytest.mark.filterwarnings("ignore:A test tried to use socket.socket:UserWarning")
def test_socket_is_disabled_by_default():
    """`pytest-socket` should have replaced socket.socket with a guard."""
    with pytest.raises(Exception) as excinfo:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("example.com", 80))
    assert "socket" in str(type(excinfo.value)).lower() or "disabled" in str(excinfo.value).lower()


def test_unix_sockets_still_allowed():
    """Local IPC (e.g. between test workers) must still work."""
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.close()
