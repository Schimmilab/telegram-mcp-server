"""Telegram MCP server.

Exposes Telegram (via a user account / MTProto through Telethon) as MCP tools:
list chats, read messages, download media, and send messages/files.
All access uses a persistent, lazily-connected TelegramClient.
"""

from __future__ import annotations

import logging
import os
import sys
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


def main() -> None:
    """Entry point: run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
