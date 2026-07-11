"""One-time interactive login for the Telegram MCP server.

Reads TELEGRAM_API_ID / TELEGRAM_API_HASH / TELEGRAM_PHONE from the
environment, prompts for the Telegram code (and 2FA password if set),
and writes the session file that server.py will reuse.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from telethon import TelegramClient


async def _run() -> None:
    api_id = os.environ.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH")
    phone = os.environ.get("TELEGRAM_PHONE")
    session = os.environ.get("TELEGRAM_SESSION") or str(
        Path.home() / ".telegram-mcp" / "telegram.session"
    )
    if not (api_id and api_hash and phone):
        print(
            "Set TELEGRAM_API_ID, TELEGRAM_API_HASH and TELEGRAM_PHONE first.",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        api_id_int = int(api_id)
    except ValueError:
        print(f"TELEGRAM_API_ID must be numeric, got {api_id!r}.", file=sys.stderr)
        sys.exit(1)

    # Restrict permissions on everything this process creates: Telethon's SQLite
    # session file is created (0644 under the default umask) the moment the client
    # is constructed — before start() and before any chmod — and holds full account
    # access. umask 077 makes the dir, session file and journal owner-only from
    # creation; the explicit chmod below also fixes a pre-existing loose-perm file.
    os.umask(0o077)

    session_path = Path(session)
    session_path.parent.mkdir(parents=True, exist_ok=True)

    client = TelegramClient(str(session_path), api_id_int, api_hash)
    await client.start(phone=phone)  # interactive: prompts code + 2FA password
    me = await client.get_me()
    await client.disconnect()

    try:
        os.chmod(session_path, 0o600)
    except OSError as exc:
        print(
            f"WARNING: could not chmod session file to 600 ({exc}) — "
            f"restrict {session_path} manually.",
            file=sys.stderr,
        )

    print(f"Logged in as {me.first_name} (@{me.username}). Session: {session_path}")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
