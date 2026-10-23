"""Messaging ``/kanban`` and ``/curator`` answer an unclosed quote with a named error.

Regression for #140803. Both handlers ran ``shlex.split`` on the raw argument without a guard, so
an apostrophe (``/kanban show it's``, ``/curator it's``) raised ``ValueError: No closing
quotation`` out of the handler: the user got the generic internal-error reply and no command
output. ``/resume`` already answers the same input with a parse-error reply; these two now do too.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest


def _runner():
    from gateway.run import GatewayRunner

    runner = object.__new__(GatewayRunner)
    runner._owns_kanban_dispatcher_lock = lambda: True
    return runner


@pytest.mark.asyncio
async def test_kanban_unclosed_quote_returns_a_parse_error():
    from gateway.run import GatewayRunner

    event = SimpleNamespace(text="/kanban show it's", source=None)
    reply = await GatewayRunner._handle_kanban_command(_runner(), event)
    assert "No closing quotation" in reply


@pytest.mark.asyncio
async def test_curator_unclosed_quote_returns_a_parse_error():
    from gateway.run import GatewayRunner

    event = SimpleNamespace(text="/curator it's", get_command_args=lambda: "it's", source=None)
    reply = await GatewayRunner._handle_curator_command(_runner(), event)
    assert "No closing quotation" in reply
