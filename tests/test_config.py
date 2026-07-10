from pathlib import Path

from telegram_mcp_server import server


def test_load_config_uses_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_API_ID", "123")
    monkeypatch.setenv("TELEGRAM_API_HASH", "abc")
    monkeypatch.setenv("TELEGRAM_SESSION", "/tmp/x.session")
    monkeypatch.setenv("TELEGRAM_DOWNLOAD_DIR", "/tmp/dl")
    cfg = server._load_config()
    assert cfg["api_id"] == "123"
    assert cfg["api_hash"] == "abc"
    assert cfg["session"] == "/tmp/x.session"
    assert cfg["download_dir"] == "/tmp/dl"


def test_load_config_defaults(monkeypatch):
    monkeypatch.delenv("TELEGRAM_API_ID", raising=False)
    monkeypatch.delenv("TELEGRAM_SESSION", raising=False)
    monkeypatch.delenv("TELEGRAM_DOWNLOAD_DIR", raising=False)
    cfg = server._load_config()
    assert cfg["session"] == str(Path.home() / ".telegram-mcp" / "schimmi.session")
    assert cfg["download_dir"] == str(Path.home() / "Downloads" / "telegram-mcp")
    assert cfg["api_id"] is None


def test_error_class_exists():
    assert issubclass(server.TelegramMCPError, Exception)
