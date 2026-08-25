"""Prove the offline-only guard actually fires.

The autouse ``_block_live_network`` fixture in ``conftest.py`` patches
``httpx.Client.send`` so that any real HTTP call during unit tests
raises ``LiveNetworkBlockedError``. This test asserts that behaviour
so a future refactor that weakens the guard fails loudly.
"""

from __future__ import annotations

import httpx
import pytest

from tests.conftest import LiveNetworkBlockedError


def test_httpx_client_get_is_blocked_by_default():
    with httpx.Client() as client, pytest.raises(LiveNetworkBlockedError):
        client.get("https://example.invalid/should-never-hit")


def test_async_httpx_client_send_is_blocked_by_default():
    with pytest.raises(LiveNetworkBlockedError):
        client = httpx.AsyncClient()
        try:
            client.send(httpx.Request("GET", "https://example.invalid/x"))
        finally:
            pass


@pytest.mark.integration
def test_integration_marker_disables_the_guard(monkeypatch):
    """Integration-marked tests bypass the guard.

    We do not actually make a request — that would violate AGENTS.md
    rule #4 in CI. We only assert that ``httpx.Client.send`` is no
    longer the patched function.
    """
    original_send = httpx.Client.send
    assert original_send.__name__ != "_refuse_send"
