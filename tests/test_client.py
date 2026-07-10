import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from telegram_mcp_server import server


def test_get_client_missing_creds(monkeypatch):
    monkeypatch.delenv("TELEGRAM_API_ID", raising=False)
    monkeypatch.delenv("TELEGRAM_API_HASH", raising=False)
    server._client = None
    with pytest.raises(server.TelegramMCPError, match="TELEGRAM_API_ID"):
        asyncio.run(server._get_client())


def test_get_client_not_authorized(monkeypatch, tmp_path):
    monkeypatch.setenv("TELEGRAM_API_ID", "123")
    monkeypatch.setenv("TELEGRAM_API_HASH", "abc")
    monkeypatch.setenv("TELEGRAM_SESSION", str(tmp_path / "s.session"))
    server._client = None

    fake = MagicMock()
    fake.connect = AsyncMock()
    fake.disconnect = AsyncMock()
    fake.is_user_authorized = AsyncMock(return_value=False)
    monkeypatch.setattr(server, "TelegramClient", lambda *a, **k: fake)

    with pytest.raises(server.TelegramMCPError, match="login.py"):
        asyncio.run(server._get_client())
    fake.disconnect.assert_awaited()


def test_resolve_entity_by_username(monkeypatch):
    client = MagicMock()
    client.get_entity = AsyncMock(return_value="ENTITY")
    result = asyncio.run(server._resolve_entity(client, "@arcanara"))
    assert result == "ENTITY"
    client.get_entity.assert_awaited_with("@arcanara")


def test_resolve_entity_by_title_unique(monkeypatch):
    client = MagicMock()
    dialogs = [
        SimpleNamespace(name="Arcanara Juni", entity="E1"),
        SimpleNamespace(name="Something else", entity="E2"),
    ]
    client.get_dialogs = AsyncMock(return_value=dialogs)
    result = asyncio.run(server._resolve_entity(client, "arcanara juni"))
    assert result == "E1"


def test_resolve_entity_title_ambiguous_raises(monkeypatch):
    client = MagicMock()
    dialogs = [
        SimpleNamespace(name="Arcanara A", entity="E1"),
        SimpleNamespace(name="Arcanara B", entity="E2"),
    ]
    client.get_dialogs = AsyncMock(return_value=dialogs)
    with pytest.raises(server.TelegramMCPError, match="Ambiguous"):
        asyncio.run(server._resolve_entity(client, "arcanara"))


def test_resolve_entity_title_not_found_raises(monkeypatch):
    client = MagicMock()
    client.get_dialogs = AsyncMock(return_value=[SimpleNamespace(name="X", entity="E")])
    with pytest.raises(server.TelegramMCPError, match="No chat"):
        asyncio.run(server._resolve_entity(client, "nope"))
