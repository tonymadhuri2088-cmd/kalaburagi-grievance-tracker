"""Tests for the DC Office time limits, Claude's photo and summary check, and the install-as-an-app files."""

import base64
import importlib.util
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "complaint_tools"))

# pylint: disable=wrong-import-position
from complaint_portal import ai_check  # noqa: E402
from complaint_portal.auth import Sessions  # noqa: E402
from complaint_portal.seed import seed_demo_officers  # noqa: E402
from complaint_portal.store import Store  # noqa: E402
from complaint_portal.workflow import Portal, PortalError  # noqa: E402
from complaintrouter import llm_classify  # noqa: E402
from complaintrouter.common import limit_overrides, load_charter, set_limit_overrides  # noqa: E402

_spec = importlib.util.spec_from_file_location("portal_server", ROOT / "portal" / "server.py")
portal_server = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(portal_server)

NOW = datetime(2026, 11, 12, 9, 0, tzinfo=timezone.utc)
PHONE = "9876543210"


def photo():
    return "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8\xff\xe0" + b"0" * 40).decode()


@pytest.fixture
def desk(kalaburagi, tmp_path):
    store = Store(tmp_path / "portal.db")
    seed_demo_officers(store, "a-long-password")
    portal = Portal(store)
    portal.sign_up_citizen("Ravi Kumar", PHONE, "12 Main Road, Kalaburagi", 5, now=NOW)
    try:
        yield portal
    finally:
        set_limit_overrides({})


def file_road(portal, **extra):
    options = dict(use_llm=False, now=NOW, address="Near the school, Station Road, Kalaburagi", kind="civic",
                   category="roads_footpaths", photos=[photo()] * 3)
    options.update(extra)
    return portal.register("Ravi Kumar", PHONE, "There is a big pothole near the school", ward_number=5, **options)


def head(portal):
    return portal.store.get_officer_by_username("district.head")


def test_only_the_district_head_sees_or_changes_the_limits(desk):
    other = desk.store.get_officer_by_username("general.depot")
    with pytest.raises(PortalError) as error:
        desk.limits_view(other)
    assert error.value.status == 403
    with pytest.raises(PortalError):
        desk.set_limit(other, {"type": "road_damage", "days": 3})


def test_a_changed_limit_applies_to_new_complaints_only_and_is_logged(desk):
    before = file_road(desk)
    old_days = load_charter()["complaint_types"]["road_damage"]["fix_days"]
    view = desk.set_limit(head(desk), {"type": "road_damage", "days": 2}, now=NOW)
    road = next(t for t in view["types"] if t["key"] == "road_damage")
    assert road["days"] == 2 and road["default"] == old_days and road["changed"]
    assert view["log"][0]["old_value"] == str(old_days) and view["log"][0]["new_value"] == "2"
    after = file_road(desk)
    first = desk.store.get_complaint(before["id"])
    second = desk.store.get_complaint(after["id"])
    assert first["fix_days"] == old_days                  # a complaint already filed keeps its limit
    assert second["fix_days"] == 2
    assert datetime.fromisoformat(second["stage_deadline"]) - NOW == timedelta(days=2)


def test_escalation_days_can_be_changed_too(desk):
    view = desk.set_limit(head(desk), {"matrix": "standard", "stage": "deputy_ae", "days": 5}, now=NOW)
    level = next(l for l in view["levels"] if l["matrix"] == "standard" and l["stage"] == "deputy_ae")
    assert level["days"] == 5 and level["changed"]
    assert load_charter()["escalation_matrix"]["standard"]["deputy_ae"] == 5


def test_limits_are_checked_and_survive_a_restart(desk, tmp_path):
    for bad in (0, 61, -1, "3", 2.5, True, None):
        with pytest.raises(PortalError) as error:
            desk.set_limit(head(desk), {"type": "road_damage", "days": bad})
        assert error.value.status == 400
    with pytest.raises(PortalError):
        desk.set_limit(head(desk), {"type": "invented", "days": 3})
    with pytest.raises(PortalError):
        desk.set_limit(head(desk), {"matrix": "standard", "stage": "depot", "days": 3})
    desk.set_limit(head(desk), {"type": "road_damage", "days": 4}, now=NOW)
    set_limit_overrides({})
    Portal(desk.store)                                     # a new Portal, as after a restart
    assert load_charter()["complaint_types"]["road_damage"]["fix_days"] == 4


def test_reset_returns_to_the_charter_file(desk):
    default = load_charter(with_overrides=False)["complaint_types"]["road_damage"]["fix_days"]
    desk.set_limit(head(desk), {"type": "road_damage", "days": 4}, now=NOW)
    view = desk.set_limit(head(desk), {"reset": True}, now=NOW)
    assert limit_overrides() == {} and load_charter()["complaint_types"]["road_damage"]["fix_days"] == default
    assert "reset" in view["log"][0]["what"].lower()


def test_the_about_page_says_who_sets_the_days(desk):
    from complaint_portal.about import about_info
    info = about_info(desk)
    assert "District Head Office" in info["time_limits"]["who_sets"]
    assert "status" not in info["claude"] and "calls_ok" in info["claude"]
    assert any(a["name"] == "Photo and summary check" for a in info["agents"])


# Claude's photo and summary check

@pytest.fixture(autouse=True)
def no_real_models(monkeypatch):
    monkeypatch.setattr(llm_classify, "ask_claude", lambda prompt, settings: None)
    monkeypatch.setattr(llm_classify, "ask_ollama", lambda prompt, settings: None)


def test_the_ai_note_reaches_the_officer_but_not_the_citizen(desk, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    done = threading.Event()

    def fake(text, label, images):
        done.set()
        return {"summary_en": "A pothole near the school.", "language": "English", "photos": "match", "photo_note": "Road with a hole."}
    desk.ai_review = fake
    view = file_road(desk, use_llm=True)
    assert done.wait(5)
    for _ in range(50):
        if any(e["kind"] == "ai_check" for e in desk.store.get_events(view["id"])):
            break
        time.sleep(0.05)
    events = desk.store.get_events(view["id"])
    note = next(e for e in events if e["kind"] == "ai_check")
    assert "AI review" in note["message"] and "pothole" in note["message"]
    citizen = desk.track(view["id"], PHONE)
    assert all("AI review" not in e["message"] for e in citizen["events"])
    stored = desk.store.get_complaint(view["id"])
    assert stored["fix_days"] == load_charter()["complaint_types"]["road_damage"]["fix_days"]   # type and days untouched


def test_a_failing_ai_review_never_breaks_registration(desk, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    def boom(text, label, images):
        raise RuntimeError("network down")
    desk.ai_review = boom
    view = file_road(desk, use_llm=True)
    assert view["id"]
    time.sleep(0.3)
    assert not any(e["kind"] == "ai_check" for e in desk.store.get_events(view["id"]))


def test_no_ai_review_without_a_key(desk, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    calls = []
    desk.ai_review = lambda *a: calls.append(a)
    file_road(desk, use_llm=True)
    time.sleep(0.2)
    assert not calls


def test_ai_check_sends_photos_and_validates_the_answer(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    seen = {}

    class Reply:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self):
            return json.dumps({"content": [{"type": "text", "text": json.dumps(
                {"summary_en": "Pothole near school.", "language": "English", "photos": "match", "photo_note": ""})}]}).encode()

    def fake_open(request, timeout=0):
        seen["body"] = json.loads(request.data.decode())
        return Reply()
    monkeypatch.setattr(urllib.request, "urlopen", fake_open)
    result = ai_check.review("Pothole near school", "Roads and Footpaths", [photo(), photo(), "not-a-data-url"])
    assert result and result["photos"] == "match"
    blocks = seen["body"]["messages"][0]["content"]
    assert sum(1 for b in blocks if b["type"] == "image") == 2     # the bad one is dropped
    assert "AI review" in ai_check.event_text(result)


# The app files

@pytest.fixture
def server(kalaburagi, tmp_path):
    portal = Portal(Store(tmp_path / "portal.db"))
    seed_demo_officers(portal.store, "a-long-password")
    httpd = portal_server.make_server("127.0.0.1", 0, portal, Sessions())
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        set_limit_overrides({})


def fetch(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return r.status, r.headers.get("Content-Type"), r.read()


def test_the_manifest_service_worker_and_icons_are_served(server):
    status, kind, body = fetch(server + "/manifest.webmanifest")
    manifest = json.loads(body)
    assert status == 200 and "manifest" in kind
    assert manifest["display"] == "standalone" and manifest["start_url"].startswith("/")
    sizes = {i["sizes"] for i in manifest["icons"]}
    assert {"192x192", "512x512"} <= sizes
    for icon in manifest["icons"]:
        status, kind, data = fetch(server + icon["src"])
        assert status == 200 and data[:8] == b"\x89PNG\r\n\x1a\n"
    status, kind, js = fetch(server + "/sw.js")
    assert status == 200 and "javascript" in kind and b"/api/" in js    # the worker leaves /api alone
    assert fetch(server + "/assets/pwa.js")[0] == 200 and fetch(server + "/offline")[0] == 200


def test_every_page_links_the_manifest_and_the_app_script(server):
    for path in ("/", "/signup", "/home", "/register", "/track", "/officer", "/worker", "/worker/signup", "/share", "/about", "/limits"):
        html = fetch(server + path)[2]
        assert b'rel="manifest"' in html and b"/assets/pwa.js" in html, path


def test_the_limits_api_needs_a_district_head_login(server):
    for method in ("GET",):
        with pytest.raises(urllib.error.HTTPError) as error:
            fetch(server + "/api/district/limits")
        assert error.value.code == 401
    request = urllib.request.Request(server + "/api/district/limits", data=b'{"type":"road_damage","days":2}',
                                     headers={"Content-Type": "application/json"}, method="POST")
    with pytest.raises(urllib.error.HTTPError) as error:
        urllib.request.urlopen(request, timeout=10)
    assert error.value.code == 401
    assert fetch(server + "/limits")[0] == 200


def test_the_first_page_has_the_install_bar_and_a_visible_language_switch(server):
    html = fetch(server + "/")[2].decode("utf-8")
    assert "data-install-bar" in html and "data-install-now" in html
    assert 'data-set-lang="en"' in html and 'data-set-lang="kn"' in html
    kannada = (ROOT / "portal" / "assets" / "i18n.js").read_text(encoding="utf-8")
    assert '"Install this app on your phone"' in kannada


# One device, several roles

class Browser:
    """A tiny browser: keeps cookies, so one 'device' can hold several logins."""

    def __init__(self, base):
        import http.cookiejar
        self.base = base
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def call(self, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(self.base + path, data=data, headers={"Content-Type": "application/json"} if data else {},
                                         method="POST" if data else "GET")
        try:
            with self.opener.open(request, timeout=10) as response:
                return response.status, json.loads(response.read() or b"{}")
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read() or b"{}")


def test_one_device_can_be_citizen_and_officer_at_once(kalaburagi, tmp_path):
    store = Store(tmp_path / "portal.db")
    seed_demo_officers(store, "a-long-password")
    portal = Portal(store)
    portal.sign_up_citizen("Ravi Kumar", PHONE, "12 Main Road, Kalaburagi", 5, now=NOW)
    httpd = portal_server.make_server("127.0.0.1", 0, portal, Sessions())
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        device = Browser(f"http://127.0.0.1:{httpd.server_address[1]}")
        code = device.call("/api/citizen/login", {"contact": PHONE})[1]["code"]
        assert device.call("/api/citizen/verify", {"contact": PHONE, "code": code})[0] == 200
        assert device.call("/api/officer/login", {"username": "district.head", "password": "a-long-password"})[0] == 200
        roles = [s["role"] for s in device.call("/api/sessions")[1]["sessions"]]
        assert roles == ["citizen", "officer"]                       # both are logged in on the same device
        assert device.call("/api/me?role=citizen")[1]["role"] == "citizen"
        assert device.call("/api/me?role=officer")[1]["role"] == "officer"
        assert device.call("/api/me?role=worker")[0] == 401
        assert device.call("/api/me?role=admin")[0] == 400
        # logging out of one role leaves the other open
        assert device.call("/api/logout", {"role": "officer"})[0] == 200
        assert [s["role"] for s in device.call("/api/sessions")[1]["sessions"]] == ["citizen"]
        assert device.call("/api/me?role=officer")[0] == 401
        # no role: everything on this device ends
        assert device.call("/api/logout", {})[0] == 200
        assert device.call("/api/sessions")[1]["sessions"] == []
    finally:
        httpd.shutdown()
        httpd.server_close()
        set_limit_overrides({})


def test_the_first_page_lists_open_logins_and_does_not_hide_the_login_tabs(server):
    html = fetch(server + "/")[2].decode("utf-8")
    assert 'id="openSessions"' in html and "/api/sessions" in html and "switch" in html


# Removing the invented demo data

def test_purging_the_sample_data_keeps_real_complaints(desk):
    from complaint_portal.seed_sample import purge_sample_data, seed_sample_data
    real = file_road(desk)                                           # a real complaint filed first
    assert desk.store.list_complaints()
    store = desk.store
    # seed_sample_data only runs on an empty database, so add the invented citizens and complaints directly
    store_complaints = len(store.list_complaints())
    from complaint_portal import seed_sample
    for name, mobile, address, ward in seed_sample.CITIZENS[:2]:
        desk.sign_up_citizen(name, mobile, address, ward, now=NOW)
        desk.register(name, mobile, "No water has come to our street for three days. Please fix it.", ward_number=ward,
                      use_llm=False, now=NOW, address=address, kind="civic", category="water_supply", photos=[photo()] * 3)
    assert len(store.list_complaints()) == store_complaints + 2
    done = purge_sample_data(desk)
    assert done["complaints"] == 2 and done["citizens"] == 2
    left = [row["id"] for row in store.list_complaints()]
    assert left == [real["id"]]
    assert store.get_citizen(PHONE) is not None                      # the real citizen stays
    assert purge_sample_data(desk) == {"citizens": 0, "complaints": 0}   # safe to run again


def test_the_district_head_can_start_fresh_and_keeps_officers_and_limits(desk):
    file_road(desk)
    desk.set_limit(head(desk), {"type": "road_damage", "days": 4}, now=NOW)
    other = desk.store.get_officer_by_username("general.depot")
    with pytest.raises(PortalError) as denied:
        desk.reset_demo(other, {"confirm": "RESET"})
    assert denied.value.status == 403
    with pytest.raises(PortalError) as unconfirmed:
        desk.reset_demo(head(desk), {})
    assert unconfirmed.value.status == 400 and desk.store.list_complaints()
    result = desk.reset_demo(head(desk), {"confirm": "RESET"}, now=NOW)
    assert result["removed"]["complaints"] == 1 and result["removed"]["citizens"] == 1
    assert not desk.store.list_complaints() and desk.store.get_citizen(PHONE) is None
    assert desk.store.get_officer_by_username("district.head") is not None       # officers stay
    assert load_charter()["complaint_types"]["road_damage"]["fix_days"] == 4      # time limits stay
    desk.sign_up_citizen("Ravi Kumar", PHONE, "12 Main Road, Kalaburagi", 5, now=NOW)   # and people can sign up again
    assert file_road(desk)["id"]


def test_the_share_page_shows_the_start_fresh_button(server, monkeypatch):
    html = fetch(server + "/share")[2].decode("utf-8")
    assert 'id="freshBtn"' in html and "/api/district/reset-demo" in html
    request = urllib.request.Request(server + "/api/district/reset-demo", data=b'{"confirm":"RESET"}',
                                     headers={"Content-Type": "application/json"}, method="POST")
    monkeypatch.setenv("ALLOW_OPEN_RESET", "0")
    with pytest.raises(urllib.error.HTTPError) as error:
        urllib.request.urlopen(request, timeout=10)
    assert error.value.code == 401          # with the switch off, a visitor who is not logged in cannot wipe anything
    monkeypatch.delenv("ALLOW_OPEN_RESET")
    assert json.loads(urllib.request.urlopen(request, timeout=10).read())["removed"]["complaints"] == 0   # open by default


def test_the_demo_password_can_start_fresh_without_an_officer_login(server, monkeypatch):
    monkeypatch.setenv("DEMO_PASSWORD", "the-demo-password")
    def attempt(password):
        request = urllib.request.Request(server + "/api/district/reset-demo",
                                         data=json.dumps({"confirm": "RESET", "password": password}).encode(),
                                         headers={"Content-Type": "application/json"}, method="POST")
        return urllib.request.urlopen(request, timeout=10)
    with pytest.raises(urllib.error.HTTPError) as wrong:
        attempt("guess")
    assert wrong.value.code == 403
    with pytest.raises(urllib.error.HTTPError) as empty:
        attempt("")
    assert empty.value.code == 403
    good = json.loads(attempt("the-demo-password").read())
    assert good["removed"] == {"complaints": 0, "citizens": 0, "workers": 0}
    html = fetch(server + "/share")[2].decode("utf-8")
    assert "Only the DC Office login" not in html and 'id="freshSection"' in html and 'id="freshSection" hidden' not in html


def test_every_officer_sees_the_late_complaint_notices(desk):
    view = desk.register("Ravi Kumar", PHONE, "water pipe is leaking badly", ward_number=12, use_llm=False, now=NOW,
                         address="Station Road", kind="civic", category="water_supply")
    desk.check_overdue(NOW + timedelta(days=10))
    roads_officer = desk.store.find_officer("roads", "depot", None) or next(
        o for o in desk.store.list_officers() if o["username"] == "roads.depot")
    seen = [n for n in desk.officer_notices(roads_officer) if n["complaint_id"] == view["id"]]
    assert seen, "an officer from another department still sees the time-limit notice"
    assert not [n for n in seen if n.get("kind") == "reminder"]
