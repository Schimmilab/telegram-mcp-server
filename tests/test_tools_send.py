import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from telegram_mcp_server import server


def _patch_client(monkeypatch, client):
    monkeypatch.setattr(server, "_get_client", AsyncMock(return_value=client))


def test_send_message(monkeypatch):
    client = MagicMock()
    client.send_message = AsyncMock(return_value=SimpleNamespace(id=55))
    _patch_client(monkeypatch, client)
    monkeypatch.setattr(server, "_resolve_entity", AsyncMock(return_value="ENT"))

    out = asyncio.run(server.send_message("@arcanara", "hallo"))
    assert out == {"sent": True, "message_id": 55}
    client.send_message.assert_awaited_with("ENT", "hallo")


def test_send_message_empty_text_raises(monkeypatch):
    # mock the client so the guard is what raises — not a fall-through to _get_client
    _patch_client(monkeypatch, MagicMock())
    monkeypatch.setattr(server, "_resolve_entity", AsyncMock(return_value="ENT"))
    with pytest.raises(server.TelegramMCPError):
        asyncio.run(server.send_message("@arcanara", "   "))


def test_send_file_missing_file_raises(monkeypatch, tmp_path):
    _patch_client(monkeypatch, MagicMock())
    monkeypatch.setattr(server, "_resolve_entity", AsyncMock(return_value="ENT"))
    with pytest.raises(server.TelegramMCPError, match="not found"):
        asyncio.run(server.send_file("@arcanara", str(tmp_path / "nope.jpg")))


def test_send_file_ok(monkeypatch, tmp_path):
    f = tmp_path / "pic.jpg"
    f.write_bytes(b"x")
    client = MagicMock()
    client.send_file = AsyncMock(return_value=SimpleNamespace(id=77))
    _patch_client(monkeypatch, client)
    monkeypatch.setattr(server, "_resolve_entity", AsyncMock(return_value="ENT"))

    out = asyncio.run(server.send_file("@arcanara", str(f), caption="hi"))
    assert out == {"sent": True, "message_id": 77}
    client.send_file.assert_awaited_with("ENT", str(f), caption="hi")
