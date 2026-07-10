import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from telegram_mcp_server import server


def _patch_client(monkeypatch, client):
    monkeypatch.setattr(server, "_get_client", AsyncMock(return_value=client))


def _media_msg(id, kind="photo"):
    if kind == "photo":
        return SimpleNamespace(id=id, photo=object(), document=None, media=object())
    return SimpleNamespace(
        id=id, photo=None,
        document=SimpleNamespace(mime_type="application/pdf", attributes=[]),
        media=object(),
    )


def test_download_media_writes_and_returns_paths(monkeypatch, tmp_path):
    client = MagicMock()
    client.get_messages = AsyncMock(return_value=[_media_msg(1), _media_msg(2)])
    client.download_media = AsyncMock(side_effect=lambda m, file: file)
    _patch_client(monkeypatch, client)
    monkeypatch.setattr(server, "_resolve_entity",
                        AsyncMock(return_value=SimpleNamespace(title="Arcanara Juni")))

    out = asyncio.run(server.download_media("Arcanara Juni", [1, 2], dest_dir=str(tmp_path)))
    assert [r["message_id"] for r in out] == [1, 2]
    assert out[0]["path"].endswith("arcanara-juni_1")
    assert (tmp_path).exists()


def test_download_media_empty_ids_raises(monkeypatch):
    import pytest
    with pytest.raises(server.TelegramMCPError):
        asyncio.run(server.download_media("x", []))


def test_download_media_skips_non_media(monkeypatch, tmp_path):
    client = MagicMock()
    no_media = SimpleNamespace(id=9, photo=None, document=None, media=None)
    client.get_messages = AsyncMock(return_value=[no_media])
    client.download_media = AsyncMock(side_effect=lambda m, file: file)
    _patch_client(monkeypatch, client)
    monkeypatch.setattr(server, "_resolve_entity",
                        AsyncMock(return_value=SimpleNamespace(title="X")))

    out = asyncio.run(server.download_media("X", [9], dest_dir=str(tmp_path)))
    assert out == []


def test_get_recent_media_filters_by_kind(monkeypatch, tmp_path):
    client = MagicMock()
    client.get_messages = AsyncMock(
        return_value=[_media_msg(1, "photo"), _media_msg(2, "document")]
    )
    client.download_media = AsyncMock(side_effect=lambda m, file: file)
    _patch_client(monkeypatch, client)
    monkeypatch.setattr(server, "_resolve_entity",
                        AsyncMock(return_value=SimpleNamespace(title="Arcanara")))

    out = asyncio.run(
        server.get_recent_media("Arcanara", limit=10, kind="photo", dest_dir=str(tmp_path))
    )
    assert [r["message_id"] for r in out] == [1]
    assert out[0]["kind"] == "photo"


def test_download_media_skips_failed_download(monkeypatch, tmp_path):
    client = MagicMock()
    client.get_messages = AsyncMock(return_value=[_media_msg(1)])
    client.download_media = AsyncMock(return_value=None)  # telethon can't download this type
    _patch_client(monkeypatch, client)
    monkeypatch.setattr(server, "_resolve_entity",
                        AsyncMock(return_value=SimpleNamespace(title="X")))
    out = asyncio.run(server.download_media("X", [1], dest_dir=str(tmp_path)))
    assert out == []


def test_get_recent_media_skips_failed_download(monkeypatch, tmp_path):
    client = MagicMock()
    client.get_messages = AsyncMock(return_value=[_media_msg(1, "photo")])
    client.download_media = AsyncMock(return_value=None)
    _patch_client(monkeypatch, client)
    monkeypatch.setattr(server, "_resolve_entity",
                        AsyncMock(return_value=SimpleNamespace(title="X")))
    out = asyncio.run(server.get_recent_media("X", limit=5, dest_dir=str(tmp_path)))
    assert out == []


def test_get_recent_media_rejects_unknown_kind():
    import pytest
    with pytest.raises(server.TelegramMCPError):
        asyncio.run(server.get_recent_media("X", kind="image"))


def test_download_media_returns_absolute_path_for_relative_dest(monkeypatch, tmp_path):
    import os
    client = MagicMock()
    client.get_messages = AsyncMock(return_value=[_media_msg(1)])
    client.download_media = AsyncMock(side_effect=lambda m, file: file)
    _patch_client(monkeypatch, client)
    monkeypatch.setattr(server, "_resolve_entity",
                        AsyncMock(return_value=SimpleNamespace(title="Arcanara")))
    monkeypatch.chdir(tmp_path)
    out = asyncio.run(server.download_media("Arcanara", [1], dest_dir="media"))
    assert out and os.path.isabs(out[0]["path"])
