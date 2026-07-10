"""Telegram MCP server.

Exposes Telegram (via a user account / MTProto through Telethon) as MCP tools:
list chats, read messages, download media, and send messages/files.
All access uses a persistent, lazily-connected TelegramClient.
"""

from __future__ import annotations

import logging
import sys

from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("telegram-mcp")

mcp = FastMCP("telegram")


def main() -> None:
    """Entry point: run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
