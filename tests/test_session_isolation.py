"""The session file must not be shared between server processes.

Measured 2026-09-14: two processes on one Telethon session silently clobber
each other's ``update_state`` (``insert or replace``, no comparison). These
tests pin both halves -- the defect being avoided, and the guarantee the fix
has to keep.

Verified by sabotage: with ``_private_session_copy`` reduced to ``return
source``, five of these go red -- different_file, leaves_the_original_untouched,
two_copies_cannot_see_each_other, not_world_readable, missing_source. The other
three (carries_the_auth_key, carries_the_entity_cache, survives_a_concurrent_
writer) stay green on purpose: they assert what the copy must CARRY OVER, which
is trivially true when copy and source are the same file. Do not read those
three as proof of isolation.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from telegram_mcp_server.server import _private_session_copy


def _make_session(path: Path, *, auth_key: bytes = b"A" * 256, pts: int = 1000) -> None:
    """Build a minimal file with the tables Telethon's SQLiteSession uses."""
    conn = sqlite3.connect(str(path))
    conn.executescript(
        """
        create table version (version integer primary key);
        create table sessions (
            dc_id integer primary key, server_address text, port integer,
            auth_key blob, takeout_id integer, tmp_auth_key blob);
        create table update_state (
            id integer primary key, pts integer, qts integer,
            date integer, seq integer);
        create table entities (
            id integer primary key, hash integer not null,
            username text, phone integer, name text, date integer);
        create table sent_files (
            md5_digest blob, file_size integer, type integer,
            id integer, hash integer, primary key(md5_digest, file_size, type));
        """
    )
    conn.execute("insert into version values (8)")
    conn.execute("insert into sessions values (?,?,?,?,?,?)",
                 (2, "149.154.167.51", 443, auth_key, None, b""))
    conn.execute("insert into update_state values (0,?,0,0,0)", (pts,))
    conn.execute("insert into entities values (7,99,'someone',None,'Someone',0)"
                 .replace("None", "null"))
    conn.commit()
    conn.close()


def test_copy_is_a_different_file(tmp_path: Path) -> None:
    original = tmp_path / "schimmi.session"
    _make_session(original)
    copy = _private_session_copy(original)
    assert copy != original
    assert copy.exists()


def test_copy_carries_the_auth_key(tmp_path: Path) -> None:
    """Without the auth key the copy is useless -- reading and sending need it."""
    original = tmp_path / "schimmi.session"
    _make_session(original, auth_key=b"K" * 256)
    copy = _private_session_copy(original)
    row = sqlite3.connect(str(copy)).execute(
        "select dc_id, server_address, port, auth_key from sessions").fetchone()
    assert row[0] == 2
    assert row[1] == "149.154.167.51"
    assert row[2] == 443
    assert row[3] == b"K" * 256


def test_copy_carries_the_entity_cache(tmp_path: Path) -> None:
    """The cache is why we copy instead of starting empty."""
    original = tmp_path / "schimmi.session"
    _make_session(original)
    copy = _private_session_copy(original)
    n = sqlite3.connect(str(copy)).execute("select count(*) from entities").fetchone()[0]
    assert n == 1


def test_writing_the_copy_leaves_the_original_untouched(tmp_path: Path) -> None:
    """This is the defect the fix exists for: a blind overwrite must not escape."""
    original = tmp_path / "schimmi.session"
    _make_session(original, pts=1000)
    before = original.read_bytes()

    copy = _private_session_copy(original)
    conn = sqlite3.connect(str(copy))
    # exactly what Telethon's set_update_state does -- no compare, last one wins
    conn.execute("insert or replace into update_state values (0,?,0,0,0)", (3,))
    conn.commit()
    conn.close()

    assert original.read_bytes() == before
    assert sqlite3.connect(str(original)).execute(
        "select pts from update_state where id = 0").fetchone()[0] == 1000


def test_two_copies_cannot_see_each_other(tmp_path: Path) -> None:
    """Two server processes: neither may observe the other's update position."""
    original = tmp_path / "schimmi.session"
    _make_session(original, pts=1000)

    first, second = _private_session_copy(original), _private_session_copy(original)
    assert first != second

    a = sqlite3.connect(str(first))
    a.execute("insert or replace into update_state values (0,?,0,0,0)", (6000,))
    a.commit()
    a.close()

    b_pts = sqlite3.connect(str(second)).execute(
        "select pts from update_state where id = 0").fetchone()[0]
    assert b_pts == 1000, "second process saw the first process's write"


def test_copy_is_not_world_readable(tmp_path: Path) -> None:
    """The session is a credential; the copy must not widen access to it."""
    original = tmp_path / "schimmi.session"
    _make_session(original)
    copy = _private_session_copy(original)
    assert oct(copy.stat().st_mode)[-3:] == "600"


def test_copy_survives_a_concurrent_writer(tmp_path: Path) -> None:
    """A plain file copy can capture a torn page; the backup API must not.

    Holds an open write transaction on the source while copying, then checks
    the copy is a valid, complete database.
    """
    original = tmp_path / "schimmi.session"
    _make_session(original, pts=1000)

    writer = sqlite3.connect(str(original))
    writer.execute("begin")
    writer.execute("insert or replace into update_state values (0,?,0,0,0)", (4242,))
    try:
        copy = _private_session_copy(original)
    finally:
        writer.rollback()
        writer.close()

    check = sqlite3.connect(str(copy))
    assert check.execute("pragma integrity_check").fetchone()[0] == "ok"
    # the uncommitted value must not be in the copy
    assert check.execute(
        "select pts from update_state where id = 0").fetchone()[0] == 1000


def test_missing_source_is_not_silently_swallowed(tmp_path: Path) -> None:
    """A vanished session must raise, not hand back an empty database.

    An empty session would fail later as "No valid session", pointing the user
    at login.py instead of at the missing file.
    """
    with pytest.raises(sqlite3.OperationalError):
        _private_session_copy(tmp_path / "does-not-exist.session")
