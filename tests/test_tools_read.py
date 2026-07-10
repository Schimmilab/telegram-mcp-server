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


def test_list_chats_scans_all_when_query(monkeypatch):
    client = MagicMock()
    client.get_dialogs = AsyncMock(return_value=[])
    _patch_client(monkeypatch, client)
    asyncio.run(server.list_chats(query="x", limit=10))
    client.get_dialogs.assert_awaited_with(limit=None)
    asyncio.run(server.list_chats(limit=10))
    client.get_dialogs.assert_awaited_with(limit=10)


def test_list_chats_caps_results_to_limit(monkeypatch):
    dialogs = [
        SimpleNamespace(id=i, name=f"chat{i}", is_group=True, is_channel=False,
                        is_user=False, unread_count=0)
        for i in range(5)
    ]
    client = MagicMock()
    client.get_dialogs = AsyncMock(return_value=dialogs)
    _patch_client(monkeypatch, client)
    out = asyncio.run(server.list_chats(limit=3))
    assert len(out) == 3


def test_get_me_handles_missing_optional_fields(monkeypatch):
    client = MagicMock()
    client.get_me = AsyncMock(return_value=SimpleNamespace(id=1, first_name="Jürgen"))
    _patch_client(monkeypatch, client)
    out = asyncio.run(server.get_me())
    assert out == {"id": 1, "username": None, "first_name": "Jürgen", "phone": None}


def test_list_chats_missing_unread_defaults_zero(monkeypatch):
    dialogs = [
        SimpleNamespace(id=10, name="X", is_group=True, is_channel=False, is_user=False)
    ]
    client = MagicMock()
    client.get_dialogs = AsyncMock(return_value=dialogs)
    _patch_client(monkeypatch, client)
    out = asyncio.run(server.list_chats())
    assert out[0]["unread"] == 0


def _msg(id, text="", photo=None):
    return SimpleNamespace(
        id=id, date=None, sender_id=None, message=text,
        photo=photo, document=None, media=(photo or None),
    )


def test_get_messages_resolves_and_formats(monkeypatch):
    client = MagicMock()
    client.get_messages = AsyncMock(return_value=[_msg(1, "a"), _msg(2, "b", photo=object())])
    _patch_client(monkeypatch, client)
    monkeypatch.setattr(server, "_resolve_entity", AsyncMock(return_value="ENT"))

    out = asyncio.run(server.get_messages("Arcanara Juni", limit=5))
    assert [m["id"] for m in out] == [1, 2]
    assert out[1]["has_media"] is True
    client.get_messages.assert_awaited_with("ENT", limit=5)


def test_get_messages_passes_offset_and_search(monkeypatch):
    client = MagicMock()
    client.get_messages = AsyncMock(return_value=[])
    _patch_client(monkeypatch, client)
    monkeypatch.setattr(server, "_resolve_entity", AsyncMock(return_value="ENT"))

    asyncio.run(server.get_messages("@arcanara", limit=10, before_id=100, search="foto"))
    client.get_messages.assert_awaited_with("ENT", limit=10, offset_id=100, search="foto")


def test_get_messages_includes_chat_id(monkeypatch):
    client = MagicMock()
    m = _msg(1, "hi")
    m.chat_id = -100999
    client.get_messages = AsyncMock(return_value=[m])
    _patch_client(monkeypatch, client)
    monkeypatch.setattr(server, "_resolve_entity", AsyncMock(return_value="ENT"))
    out = asyncio.run(server.get_messages("@arcanara", limit=1))
    assert out[0]["chat_id"] == -100999


def test_search_messages_empty_query_raises(monkeypatch):
    import pytest
    with pytest.raises(server.TelegramMCPError):
        asyncio.run(server.search_messages("   "))


def test_search_messages_in_chat(monkeypatch):
    client = MagicMock()
    client.get_messages = AsyncMock(return_value=[_msg(3, "treffen")])
    _patch_client(monkeypatch, client)
    monkeypatch.setattr(server, "_resolve_entity", AsyncMock(return_value="ENT"))

    out = asyncio.run(server.search_messages("treffen", chat="@arcanara", limit=5))
    assert out[0]["id"] == 3
    client.get_messages.assert_awaited_with("ENT", limit=5, search="treffen")


def test_search_messages_global(monkeypatch):
    # _search_global is mocked directly so this test checks search_messages'
    # wiring without rebuilding the Telethon request (see note at plan end).
    client = MagicMock()
    _patch_client(monkeypatch, client)
    monkeypatch.setattr(
        server, "_search_global", AsyncMock(return_value=[_msg(4, "global hit")])
    )

    out = asyncio.run(server.search_messages("global", limit=5))
    assert out[0]["id"] == 4
    server._search_global.assert_awaited()
