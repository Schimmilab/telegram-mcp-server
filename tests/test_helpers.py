from types import SimpleNamespace

import pytest

from telegram_mcp_server import server


# --- _slugify_chat ---
def test_slugify_basic():
    assert server._slugify_chat("Arcanara Juni-Treffen") == "arcanara-juni-treffen"


def test_slugify_umlauts_and_symbols():
    assert server._slugify_chat("Café Grün! #1") == "cafe-gruen-1"


def test_slugify_empty_falls_back():
    assert server._slugify_chat("") == "chat"
    assert server._slugify_chat(None) == "chat"


# --- _build_media_filename ---
def test_media_filename_keeps_extension_lowercased():
    assert server._build_media_filename("arcanara", 42, "IMG_1.JPG") == "arcanara_42.jpg"


def test_media_filename_no_original():
    assert server._build_media_filename("arcanara", 42, None) == "arcanara_42"


def test_media_filename_no_extension():
    assert server._build_media_filename("arcanara", 7, "photo") == "arcanara_7"


# --- _telethon_original_name ---
def test_original_name_from_document_attribute():
    msg = SimpleNamespace(
        document=SimpleNamespace(attributes=[SimpleNamespace(file_name="report.pdf")])
    )
    assert server._telethon_original_name(msg) == "report.pdf"


def test_original_name_none_for_photo():
    msg = SimpleNamespace(document=None)
    assert server._telethon_original_name(msg) is None


# --- _media_kind ---
def test_media_kind_photo():
    msg = SimpleNamespace(photo=object(), document=None, media=object())
    assert server._media_kind(msg) == "photo"


def test_media_kind_video_by_mime():
    msg = SimpleNamespace(
        photo=None, document=SimpleNamespace(mime_type="video/mp4"), media=object()
    )
    assert server._media_kind(msg) == "video"


def test_media_kind_document():
    msg = SimpleNamespace(
        photo=None, document=SimpleNamespace(mime_type="application/pdf"), media=object()
    )
    assert server._media_kind(msg) == "document"


def test_media_kind_none():
    msg = SimpleNamespace(photo=None, document=None, media=None)
    assert server._media_kind(msg) is None


# --- _format_message ---
def test_format_message_text():
    import datetime

    msg = SimpleNamespace(
        id=5,
        date=datetime.datetime(2026, 6, 1, 12, 0, 0),
        sender_id=99,
        message="hallo",
        photo=None,
        document=None,
        media=None,
    )
    out = server._format_message(msg)
    assert out == {
        "id": 5,
        "date": "2026-06-01T12:00:00",
        "sender_id": 99,
        "text": "hallo",
        "has_media": False,
        "media_type": None,
    }


def test_format_message_with_photo():
    msg = SimpleNamespace(
        id=6, date=None, sender_id=None, message=None,
        photo=object(), document=None, media=object(),
    )
    out = server._format_message(msg)
    assert out["has_media"] is True
    assert out["media_type"] == "photo"
    assert out["text"] == ""


# --- _parse_chat_ref ---
def test_parse_chat_ref_int():
    assert server._parse_chat_ref(-100123) == ("id", -100123)


def test_parse_chat_ref_numeric_string():
    assert server._parse_chat_ref("-100123") == ("id", -100123)


def test_parse_chat_ref_username():
    assert server._parse_chat_ref("@arcanara") == ("username", "@arcanara")


def test_parse_chat_ref_title():
    assert server._parse_chat_ref("Arcanara Juni") == ("title", "Arcanara Juni")


def test_parse_chat_ref_empty_raises():
    with pytest.raises(server.TelegramMCPError):
        server._parse_chat_ref("   ")


# --- _validate_limit ---
def test_validate_limit_ok():
    assert server._validate_limit(30) == 30


def test_validate_limit_caps():
    assert server._validate_limit(9999, maximum=200) == 200


def test_validate_limit_rejects_zero():
    with pytest.raises(server.TelegramMCPError):
        server._validate_limit(0)


# --- _dialog_type ---
def test_dialog_type_group():
    d = SimpleNamespace(is_group=True, is_channel=False, is_user=False)
    assert server._dialog_type(d) == "group"


def test_dialog_type_channel():
    d = SimpleNamespace(is_group=False, is_channel=True, is_user=False)
    assert server._dialog_type(d) == "channel"


def test_dialog_type_user():
    d = SimpleNamespace(is_group=False, is_channel=False, is_user=True)
    assert server._dialog_type(d) == "user"
