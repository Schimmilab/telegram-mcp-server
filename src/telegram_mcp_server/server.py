"""Telegram MCP server.

Exposes Telegram (via a user account / MTProto through Telethon) as MCP tools:
list chats, read messages, download media, and send messages/files.
All access uses a persistent, lazily-connected TelegramClient.
"""

from __future__ import annotations

import logging
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("telegram-mcp")

mcp = FastMCP("telegram")


class TelegramMCPError(Exception):
    """Raised for expected, user-facing errors (bad args, no session, no access)."""


def _load_config() -> dict[str, Optional[str]]:
    """Read server configuration from the environment."""
    home = Path.home()
    return {
        "api_id": os.environ.get("TELEGRAM_API_ID"),
        "api_hash": os.environ.get("TELEGRAM_API_HASH"),
        "session": os.environ.get("TELEGRAM_SESSION")
        or str(home / ".telegram-mcp" / "schimmi.session"),
        "download_dir": os.environ.get("TELEGRAM_DOWNLOAD_DIR")
        or str(home / "Downloads" / "telegram-mcp"),
    }


_UMLAUT_MAP = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}


def _slugify_chat(title: Optional[str]) -> str:
    """Slugify a chat title for use in media filenames."""
    t = (title or "").lower()
    for k, v in _UMLAUT_MAP.items():
        t = t.replace(k, v)
    # Strip remaining diacritics (e.g. "café" -> "cafe") without over-transliterating
    # the German umlauts already handled above.
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^\w\s-]", "", t)
    t = re.sub(r"[\s_-]+", "-", t).strip("-")
    return t or "chat"


def _build_media_filename(chat_slug: str, message_id: int, original_name: Optional[str]) -> str:
    """Collision-light filename: <chat-slug>_<message-id>[.<ext>]."""
    base = f"{chat_slug}_{message_id}"
    if original_name:
        ext = original_name.rpartition(".")[2]
        if ext and ext != original_name and re.fullmatch(r"[A-Za-z0-9]+", ext):
            return f"{base}.{ext.lower()}"
    return base


def _telethon_original_name(msg: Any) -> Optional[str]:
    """Extract the original file name from a message's document, if any."""
    doc = getattr(msg, "document", None)
    if doc is None:
        return None
    for attr in getattr(doc, "attributes", None) or []:
        name = getattr(attr, "file_name", None)
        if name:
            return name
    return None


def _media_kind(msg: Any) -> Optional[str]:
    """Classify a message's media as photo/video/document/other, or None."""
    if getattr(msg, "photo", None) is not None:
        return "photo"
    doc = getattr(msg, "document", None)
    if doc is not None:
        mime = getattr(doc, "mime_type", "") or ""
        if mime.startswith("video/"):
            return "video"
        return "document"
    if getattr(msg, "media", None) is not None:
        return "other"
    return None


def _format_message(msg: Any) -> dict[str, Any]:
    """Serialize a Telethon message into a plain dict."""
    kind = _media_kind(msg)
    date = getattr(msg, "date", None)
    return {
        "id": msg.id,
        "date": date.isoformat() if date is not None else None,
        "sender_id": getattr(msg, "sender_id", None),
        "text": getattr(msg, "message", "") or "",
        "has_media": kind is not None,
        "media_type": kind,
    }


def _parse_chat_ref(chat: Any) -> tuple[str, Any]:
    """Classify a chat reference as ('id', int) / ('username', str) / ('title', str)."""
    if isinstance(chat, bool):
        raise TelegramMCPError("chat must be an id, @username, or title — not a bool")
    if isinstance(chat, int):
        return ("id", chat)
    s = str(chat).strip()
    if not s:
        raise TelegramMCPError("chat must not be empty")
    if s.lstrip("-").isdigit():
        # Looks like a numeric chat id. Accept a single optional leading '-';
        # a malformed variant like "--123" is a bad id, not a title.
        if re.fullmatch(r"-?\d+", s):
            return ("id", int(s))
        raise TelegramMCPError(f"malformed chat id: {s!r}")
    if s.startswith("@"):
        return ("username", s)
    return ("title", s)


def _validate_limit(limit: Any, maximum: int = 200) -> int:
    """Validate a positive-int limit and cap it at `maximum`."""
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise TelegramMCPError("limit must be a positive integer")
    return min(limit, maximum)


def _dialog_type(dialog: Any) -> str:
    """Map a Telethon dialog to 'group' / 'channel' / 'user' / 'unknown'."""
    if getattr(dialog, "is_group", False):
        return "group"
    if getattr(dialog, "is_channel", False):
        return "channel"
    if getattr(dialog, "is_user", False):
        return "user"
    return "unknown"


def main() -> None:
    """Entry point: run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
