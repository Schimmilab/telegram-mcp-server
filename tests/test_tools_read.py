import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from telegram_mcp_server import server


def _patch_client(monkeypatch, client):
    monkeypatch.setattr(server, "_get_client", AsyncMock(return_value=client))


def test_get_me(monkeypatch):
    client = MagicMock()
    client.get_me = AsyncMock(
        return_value=SimpleNamespace(id=1, username="schimmi", first_name="Jürgen", phone="49x")
    )
    _patch_client(monkeypatch, client)
    out = asyncio.run(server.get_me())
    assert out == {"id": 1, "username": "schimmi", "first_name": "Jürgen", "phone": "49x"}


def test_list_chats_shapes_and_filters(monkeypatch):
    dialogs = [
        SimpleNamespace(id=10, name="Arcanara Juni", is_group=True, is_channel=False,
                        is_user=False, unread_count=3),
        SimpleNamespace(id=11, name="Familie", is_group=False, is_channel=False,
                        is_user=True, unread_count=0),
    ]
    client = MagicMock()
    client.get_dialogs = AsyncMock(return_value=dialogs)
    _patch_client(monkeypatch, client)

    out_all = asyncio.run(server.list_chats())
    assert len(out_all) == 2
    assert out_all[0] == {"id": 10, "title": "Arcanara Juni", "type": "group", "unread": 3}

    out_filtered = asyncio.run(server.list_chats(query="arca"))
    assert [c["id"] for c in out_filtered] == [10]
