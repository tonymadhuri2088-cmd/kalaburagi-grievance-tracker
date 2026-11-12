"""Tests for the final-round additions: kept logins, the saved copy of the data, the QR and share pages,
the How-it-works facts, and Claude as an optional classifier. No internet, model or Postgres is needed."""

import importlib.util
import json
import sys
import threading
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "complaint_tools"))

# pylint: disable=wrong-import-position
from complaint_portal import durable  # noqa: E402
from complaint_portal.about import about_info  # noqa: E402
from complaint_portal.auth import Sessions  # noqa: E402
from complaint_portal.store import Store  # noqa: E402
from complaint_portal.workflow import Portal  # noqa: E402
from complaintrouter import llm_classify  # noqa: E402
from complaintrouter.common import load_charter  # noqa: E402

_spec = importlib.util.spec_from_file_location("portal_server", ROOT / "portal" / "server.py")
portal_server = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(portal_server)

NOW = datetime(2026, 11, 12, 9, 0, tzinfo=timezone.utc)


def test_sessions_survive_a_restart(tmp_path):
    store = Store(tmp_path / "p.db")
    token = Sessions(store, "citizen").create("9876543210", NOW, NOW + timedelta(days=1))
    again = Sessions(store, "citizen")   # a new object, as after a restart
    assert again.who(token, NOW) == "9876543210"
    assert Sessions(store, "worker").who(token, NOW) is None   # a citizen's token is not a worker's
    assert again.who(token, NOW + timedelta(days=2)) is None   # expired
    again.drop(token)
    assert Sessions(store, "citizen").who(token, NOW) is None


def test_officer_sessions_keep_the_numeric_id(tmp_path):
    store = Store(tmp_path / "p.db")
    token = Sessions(store, "officer").create(7, NOW)
    assert Sessions(store, "officer").officer_id(token, NOW) == 7


def test_the_store_tells_the_saver_when_data_changes(tmp_path):
    store = Store(tmp_path / "p.db")
    calls = []
    store.on_change = lambda: calls.append(1)
    store.count_events("x")
    assert not calls                      # a read changes nothing
    store.save_session("h", "citizen", '"1"', NOW.isoformat())
    assert calls                          # a write does


def test_the_saved_copy_holds_the_database_and_photos(tmp_path):
    store = Store(tmp_path / "data" / "portal.db")
    store.save_session("h", "citizen", '"9000000001"', NOW.isoformat())
    photos = tmp_path / "data" / "photos"
    photos.mkdir()
    (photos / "CMP-1-1.jpg").write_bytes(b"jpeg")
    packed = durable._pack(tmp_path / "data" / "portal.db")
    other = tmp_path / "new" / "portal.db"
    durable._unpack(packed, other)
    assert Store(other).get_session("h", "citizen")["subject"] == '"9000000001"'
    assert (other.parent / "photos" / "CMP-1-1.jpg").read_bytes() == b"jpeg"


def test_unpack_ignores_paths_that_try_to_leave_the_folder(tmp_path):
    archive = tmp_path / "x.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("portal.db", b"db")
        z.writestr("photos/../../evil.txt", b"no")
        z.writestr("../evil2.txt", b"no")
    durable._unpack(archive.read_bytes(), tmp_path / "out" / "portal.db")
    assert not (tmp_path / "evil.txt").exists() and not (tmp_path / "evil2.txt").exists()
    assert not (tmp_path / "out" / "evil.txt").exists()


def test_without_database_url_nothing_is_saved_and_the_portal_still_runs(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert "not set" in durable.restore(str(tmp_path / "p.db"))
    saver = durable.Saver(str(tmp_path / "p.db"))
    assert not saver.enabled
    saver.start()
    saver.stop()


def test_an_unreachable_database_does_not_stop_the_portal(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "postgresql://nobody:x@127.0.0.1:1/none")
    messages = []
    result = durable.restore(str(tmp_path / "p.db"), log=messages.append)
    assert result == "unavailable" and messages


@pytest.fixture
def server(kalaburagi, tmp_path):
    portal = Portal(Store(tmp_path / "portal.db"), demo_minutes=3)
    httpd = portal_server.make_server("127.0.0.1", 0, portal, Sessions())
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}", portal
    finally:
        httpd.shutdown()
        httpd.server_close()


def get(url):
    with urllib.request.urlopen(url, timeout=10) as response:
        return response.status, response.headers.get("Content-Type"), response.read()


def test_share_and_about_pages_and_the_qr_codes(server, monkeypatch):
    monkeypatch.delenv("PUBLIC_URL", raising=False)
    base, _ = server
    for path in ("/share", "/about"):
        status, kind, body = get(base + path)
        assert status == 200 and "text/html" in kind and b"Kalaburagi" in body
    status, kind, body = get(base + "/qr.svg")
    assert status == 200 and kind == "image/svg+xml" and body.lstrip().startswith(b"<svg")
    status, kind, body = get(base + "/qr.png")
    assert status == 200 and body[:8] == b"\x89PNG\r\n\x1a\n"
    with pytest.raises(urllib.error.HTTPError) as error:
        get(base + "/qr.svg?u=javascript:alert(1)")
    assert error.value.code == 400


def test_share_info_uses_public_url_and_lists_demo_officers(server, monkeypatch):
    base, portal = server
    from complaint_portal.auth import hash_password
    portal.store.insert_officer("water.depot", "Water: section", "water", "depot", hash_password("portal-test-pass"))
    monkeypatch.setenv("PUBLIC_URL", "https://neuroroute.example.com/")
    info = json.loads(get(base + "/api/share")[2])
    assert info["url"] == "https://neuroroute.example.com"
    assert info["links"]["worker"].endswith("/worker/signup")
    assert info["demo_minutes"] == 3
    assert [o["username"] for o in info["officers"]] == ["water.depot"]
    assert "password" not in json.dumps(info).lower()


def test_about_facts_match_the_charter(kalaburagi, tmp_path):
    portal = Portal(Store(tmp_path / "p.db"))
    info = about_info(portal)
    charter = load_charter()
    assert len(info["time_limits"]["rows"]) == len(charter["complaint_types"])
    road = next(row for row in info["time_limits"]["rows"] if row["key"] == "road_damage")
    assert road["ladder"][0]["days"] == charter["complaint_types"]["road_damage"]["fix_days"]
    assert road["total_days"] == sum(step["days"] for step in road["ladder"])
    assert {agent["kind"] for agent in info["agents"]} == {"Rules", "Coded tool", "LLM"}
    assert "sample" in info["time_limits"]["note"].lower()
    assert info["limits"]


def test_claude_picks_a_type_but_only_from_the_charter(kalaburagi, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(llm_classify, "ask_claude", lambda prompt, settings: '{"complaint_type": "streetlight_fault", "subtype": null}')
    result = llm_classify.classify("The lamp outside our house is dark", use_llm=True)
    assert result["complaint_type"] == "streetlight_fault" and result["classifier"] == "llm"
    assert "Claude" in result["llm_status"]

    monkeypatch.setattr(llm_classify, "ask_claude", lambda prompt, settings: '{"complaint_type": "make_it_free", "subtype": null}')
    monkeypatch.setattr(llm_classify, "ask_ollama", lambda prompt, settings: None)
    result = llm_classify.classify("The lamp outside our house is dark", use_llm=True)
    assert result["classifier"] == "keyword"     # an invented type is rejected


def test_claude_is_skipped_without_a_key_and_after_the_daily_limit(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert llm_classify.claude_settings() is None
    settings = {"key": "k", "model": "m", "timeout": 1, "daily_limit": 0}
    assert llm_classify.ask_claude("x", settings) is None
