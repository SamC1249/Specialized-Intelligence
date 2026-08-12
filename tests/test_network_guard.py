"""Meta-test: prove the offline autouse guard actually blocks the net.

If someone rips out the socket guard in `conftest.py`, or if a new
adapter reaches for the network at import time, this test will scream.
"""

from __future__ import annotations

import socket

import httpx
import pytest


def test_direct_socket_connect_is_blocked() -> None:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    with pytest.raises(RuntimeError, match="offline"):
        s.connect(("example.com", 80))


def test_httpx_client_is_blocked() -> None:
    client = httpx.Client()
    try:
        with pytest.raises(RuntimeError, match="offline"):
            client.get("https://example.com/")
    finally:
        client.close()


def test_localhost_is_still_allowed() -> None:
    resolved = socket.getaddrinfo("127.0.0.1", 0)
    assert resolved, "loopback lookup must still succeed"
