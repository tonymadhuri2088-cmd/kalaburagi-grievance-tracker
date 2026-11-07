"""Tests for the Solvathon 2026 version: the Kalaburagi pack, reminders, history, police pilot and Kannada.

These run on the Kalaburagi pack (the `kalaburagi` fixture switches to it for one test). The older tests run on
the Chennai pack. No model, internet or SMS provider is needed.
"""

import base64
import http.client
import importlib.util
import json
import sys
import threading
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "complaint_tools"))

# pylint: disable=wrong-import-position
from complaintrouter import common  # noqa: E402
from complaint_portal.auth import Sessions, hash_password  # noqa: E402
from complaint_portal.language import detect_language  # noqa: E402
from complaint_portal.locations import load_locations, match_zones  # noqa: E402
from complaint_portal.rules import DISTRICT_HEAD, FIELDS  # noqa: E402
from complaint_portal.store import Store  # noqa: E402
from complaint_portal.workflow import Portal, PortalError  # noqa: E402

_spec = importlib.util.spec_from_file_location("portal_server", ROOT / "portal" / "server.py")
portal_server = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(portal_server)

NOW = datetime(2026, 11, 9, 9, 0, tzinfo=timezone.utc)
HASH = hash_password("portal-test-pass")
LEVELS = ["depot", "deputy_ae", "area_engineer", "superintendent_engineer"]
CONTACT = "9876543210"
POTHOLE = "There is a big pothole on the main road near the bus stand and bikes are falling."
KANNADA_LIGHT = "ನಮ್ಮ ಬೀದಿಯಲ್ಲಿ ಬೀದಿ ದೀಪ ಕೆಲಸ ಮಾಡುತ್ತಿಲ್ಲ"  # the streetlight on our street is not working
CYBER = "A caller asked for my OTP and I lost 20000 rupees in an online fraud."
HOME_WARD = 5


def iso(moment):
    return moment.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def jpeg():
    return "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8\xff\xe0" + b"0" * 64).decode()


def pdf():
    return "data:application/pdf;base64," + base64.b64encode(b"%PDF-1.4 test document").decode()


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "portal.db")


@pytest.fixture
def portal(kalaburagi, store):
    return Portal(store)


@pytest.fixture
def staffed(kalaburagi, store):
    """One officer per department and level, plus the DC Office."""
    for field in FIELDS:
        for level in LEVELS:
            store.insert_officer(f"{field}.{level}", f"{FIELDS[field]} {level}", field, level, HASH)
    store.insert_officer("district.head", "DC Office", "all", DISTRICT_HEAD, HASH)
    return store


def file_complaint(portal, text=POTHOLE, now=NOW, **extra):
    return portal.register("Ravi Kumar", CONTACT, text, ward_number=HOME_WARD, use_llm=False, now=now, **extra)


# ------------------------------------------------------------------ the Kalaburagi pack
def test_default_pack_is_kalaburagi_and_tests_pin_chennai():
    assert common.district() == "chennai"  # the conftest pins it; the real portal defaults to Kalaburagi
    assert common.DEFAULT_DISTRICT == "kalaburagi"


def test_kalaburagi_locations(kalaburagi):
    data = load_locations()
    assert data.district == "Kalaburagi"
    assert len(data.zones) == 11 and data.total == 65
    assert data.zone(1).ward_to == 55  # the City Corporation's 55 wards
    names = {zone.name for zone in data.zones.values()}
    assert {"Kalaburagi City", "Aland", "Afzalpur", "Chincholi", "Chitapur", "Jewargi", "Sedam",
            "Kamalapur", "Kalagi", "Shahabad", "Yedrami"} == names
    assert data.ward(60).zone_name == "Jewargi"


@pytest.mark.parametrize("address, zone", [
    ("Near Jagat Circle, Gulbarga, Karnataka", 1),
    ("Station Road, Sedam, Kalaburagi district", 7),
    ("Main Road, Jevargi", 6),   # the other spelling
    ("Bus stand, Kalgi", 9),
])
def test_addresses_match_taluks(kalaburagi, address, zone):
    assert match_zones(address, load_locations())[0][0] == zone


def test_departments_come_from_the_charter(kalaburagi):
    assert list(FIELDS) == ["water", "roads", "health", "sanitation", "police", "general"]


def test_ward_number_limits_follow_the_district(portal):
    with pytest.raises(PortalError) as raised:
        portal.register("Ravi", CONTACT, POTHOLE, ward_number=66, use_llm=False, now=NOW)
    assert "wards 1 to 65" in raised.value.message


def test_pack_switches_back_after_a_kalaburagi_test():
    assert common.district() == "chennai"
    assert "sewerage" in FIELDS


def test_pothole_goes_to_roads(portal, staffed):
    view = file_complaint(portal)
    assert view["complaint_label"] == "Damaged road or pothole"
    assert view["field"] == "Roads and streetlights"
    assert view["deadline"] == iso(NOW + timedelta(days=7))
    assert view["zone"] == "Kalaburagi City zone"


# ------------------------------------------------------------------ Kannada
def test_language_detection():
    assert detect_language(POTHOLE) == "en"
    assert detect_language(KANNADA_LIGHT) == "kn"
    assert detect_language("street light ಕೆಲಸ ಮಾಡುತ್ತಿಲ್ಲ ದಯವಿಟ್ಟು ಸರಿ ಮಾಡಿ") == "kn"
    assert detect_language("") == "en" and detect_language("12345") == "en" and detect_language(None) == "en"


def test_kannada_complaint_is_classified_and_followed_up_in_kannada(portal, staffed):
    view = file_complaint(portal, KANNADA_LIGHT)
    assert view["complaint_label"] == "Streetlight not working"
    assert view["language"] == "kn"
    first = view["messages"][0]
    assert first["language"] == "kn" and "ನಿಮ್ಮ ದೂರು" in first["text"] and view["id"] in first["text"]


def test_english_complaint_gets_english_follow_up(portal, staffed):
    view = file_complaint(portal)
    assert view["language"] == "en"
    assert view["messages"][0]["text"].startswith(f"Your complaint {view['id']}")


# ------------------------------------------------------------------ police pilot
@pytest.mark.parametrize("category, label", [
    ("cybercrime", "Cybercrime and online fraud"),
    ("financial_fraud", "Financial fraud"),
    ("lost_property", "Lost property"),
    ("traffic_safety", "Public safety and traffic"),
    ("complaint_individuals", "Complaint involving individuals"),
])
def test_police_categories_fix_the_type_and_carry_the_notice(portal, staffed, category, label):
    # The wording is about a leak, but the citizen chose the police category, so the category decides.
    view = file_complaint(portal, "Please look into this matter, water was leaking near the house too.",
                          kind="police", category=category, photos=[])
    assert view["complaint_label"] == label and view["field"] == "Police (pilot)"
    assert view["category_label"] == label
    assert "only registers and tracks" in view["police_notice"] and "FIR" in view["police_notice"]
    assert "FIR" in view["router_message"]


def test_police_complaint_needs_no_documents_but_takes_up_to_three(portal, staffed, tmp_path):
    assert file_complaint(portal, CYBER, kind="police", category="cybercrime", photos=[])["photo_count"] == 0
    view = file_complaint(portal, CYBER, kind="police", category="cybercrime", photos=[pdf(), jpeg(), pdf()])
    assert view["photo_count"] == 3
    saved = sorted(p.suffix for p in (tmp_path / "photos").iterdir())
    assert saved == [".jpg", ".pdf", ".pdf"]
    with pytest.raises(PortalError) as too_many:
        file_complaint(portal, CYBER, kind="police", category="cybercrime", photos=[jpeg()] * 4)
    assert "at most 3" in too_many.value.message


def test_a_fake_pdf_is_refused(portal, staffed):
    fake = "data:application/pdf;base64," + base64.b64encode(b"not a pdf at all").decode()
    with pytest.raises(PortalError) as raised:
        file_complaint(portal, CYBER, kind="police", category="cybercrime", photos=[fake])
    assert "PDF" in raised.value.message


def test_police_kind_is_not_offered_on_the_chennai_pack(store):
    portal = Portal(store)
    with pytest.raises(PortalError):
        portal.register("Ravi", CONTACT, "Water leaking from a pipe near my house",
                        ward_number=115, use_llm=False, now=NOW, kind="police", category="cybercrime", photos=[])


def test_police_keywords_work_without_a_category(portal, staffed):
    assert file_complaint(portal, CYBER)["complaint_label"] == "Cybercrime and online fraud"
    assert file_complaint(portal, "I lost my wallet near the railway station yesterday")["complaint_label"] == "Lost property"


# ------------------------------------------------------------------ reminders
def history(store, cid, kind):
    return [event for event in store.get_events(cid) if event["kind"] == kind]


def test_reminders_are_sent_at_half_and_at_eighty_percent_and_only_once(portal, staffed):
    cid = file_complaint(portal)["id"]            # roads: a 7-day limit
    assert portal.send_reminders(NOW + timedelta(days=3)) == []        # 43%
    sent = portal.send_reminders(NOW + timedelta(days=4))              # 57%
    assert [item["kind"] for item in sent] == ["half"] and sent[0]["complaint_id"] == cid
    assert portal.send_reminders(NOW + timedelta(days=4, hours=2)) == []   # never twice
    final = portal.send_reminders(NOW + timedelta(days=6))             # 86%
    assert [item["kind"] for item in final] == ["final"]
    assert portal.send_reminders(NOW + timedelta(days=6, hours=5)) == []
    assert portal.store.count_reminders() == 2
    assert len(history(staffed, cid, "reminder")) == 2


def test_a_reminder_is_written_into_the_history_and_the_communication_log(portal, staffed):
    cid = file_complaint(portal)["id"]
    portal.send_reminders(NOW + timedelta(days=4))
    event = history(staffed, cid, "reminder")[0]
    assert event["actor"] == "system" and "Reminder 1 of 2" in event["message"]
    assert "Roads and streetlights section office" in event["message"] or "Reminder 1 of 2 sent to" in event["message"]
    officer_notes = [m for m in staffed.get_messages(cid, "officer") if m["subject"] == "reminder_half"]
    assert len(officer_notes) == 1 and cid in officer_notes[0]["body"] and "half" in officer_notes[0]["body"]
    citizen_notes = [m for m in staffed.get_messages(cid, "citizen") if m["subject"] == "citizen_reminded"]
    assert len(citizen_notes) == 1


def test_a_reminder_also_appears_as_a_notice_for_the_officer_and_the_dc(portal, staffed):
    cid = file_complaint(portal)["id"]
    portal.send_reminders(NOW + timedelta(days=4))
    portal.send_reminders(NOW + timedelta(days=6))
    row = portal.store.get_complaint(cid)
    officer = portal.store.get_officer(row["assigned_officer_id"])
    mine = [n for n in portal.officer_notices(officer) if n["kind"] == "reminder"]
    assert sorted(n["reminder_kind"] for n in mine) == ["final", "half"]
    assert all(n["complaint_id"] == cid and n["moved_to"] for n in mine)
    head = next(o for o in portal.store.list_officers() if o["level"] == "district_head")
    assert len([n for n in portal.officer_notices(head) if n["kind"] == "reminder"]) == 2
    portal.send_reminders(NOW + timedelta(days=6, hours=5))
    assert len([n for n in portal.officer_notices(head) if n["kind"] == "reminder"]) == 2   # not repeated


def test_the_final_reminder_says_where_the_complaint_goes_next(portal, staffed):
    cid = file_complaint(portal)["id"]
    portal.send_reminders(NOW + timedelta(days=6))
    final = [m for m in staffed.get_messages(cid, "officer") if m["subject"] == "reminder_final"]
    assert len(final) == 1 and "Sub-division officer" in final[0]["body"]


def test_if_the_portal_was_down_only_the_latest_reminder_is_sent(portal, staffed):
    cid = file_complaint(portal)["id"]
    sent = portal.send_reminders(NOW + timedelta(days=6))       # 86%: both steps have passed
    assert [item["kind"] for item in sent] == ["final"]
    assert portal.send_reminders(NOW + timedelta(days=6, hours=1)) == []   # the half step is not sent late
    assert len(history(staffed, cid, "reminder")) == 1


def test_overdue_complaints_escalate_and_the_supervisor_and_citizen_are_told(portal, staffed):
    cid = file_complaint(portal)["id"]
    assert portal.run_checks(NOW + timedelta(days=8))["escalated"] == [cid]
    row = staffed.get_complaint(cid)
    assert row["stage"] == "deputy_ae"
    to_officer = [m for m in staffed.get_messages(cid, "officer") if m["subject"] == "escalated_to_you"]
    assert len(to_officer) == 1 and "Roads and streetlights section office" in to_officer[0]["body"]
    assert "Sub-division officer" in to_officer[0]["body"]
    to_citizen = [m for m in staffed.get_messages(cid, "citizen") if m["subject"] == "citizen_escalated"]
    assert len(to_citizen) == 1 and "Sub-division officer" in to_citizen[0]["body"]


def test_each_new_stage_gets_its_own_reminders(portal, staffed):
    cid = file_complaint(portal)["id"]
    portal.run_checks(NOW + timedelta(days=8))                  # moved to the sub-division officer (2-day limit)
    sent = portal.send_reminders(NOW + timedelta(days=8, hours=30))   # 62% of 2 days
    assert [item["kind"] for item in sent] == ["half"] and sent[0]["complaint_id"] == cid
    assert sent[0]["office"] == "Sub-division officer"


def test_the_last_level_has_no_limit_so_no_reminder(portal, staffed):
    cid = file_complaint(portal)["id"]
    for step in range(1, 7):
        portal.check_overdue(NOW + timedelta(days=8 * step))
    assert staffed.get_complaint(cid)["stage"] == DISTRICT_HEAD
    assert portal.send_reminders(NOW + timedelta(days=400)) == []


def test_without_an_officer_the_reminder_goes_to_the_dc_office(portal, store):
    cid = file_complaint(portal)["id"]       # nobody is set up
    sent = portal.send_reminders(NOW + timedelta(days=4))
    assert sent and "no officer" in sent[0]["to"]
    note = store.get_messages(cid, "district head")
    assert len(note) == 1 and note[0]["subject"] == "no_officer"


def test_resolved_complaints_get_no_reminders(portal, staffed):
    view = file_complaint(portal)
    officer = staffed.get_officer(staffed.get_complaint(view["id"])["assigned_officer_id"])
    portal.resolve(officer, view["id"], "Pothole filled.", now=NOW + timedelta(days=1))
    assert portal.send_reminders(NOW + timedelta(days=6)) == []


def test_demo_minutes_make_reminders_fast(store, staffed, kalaburagi):
    portal = Portal(store, demo_minutes=2)
    file_complaint(portal)
    assert portal.send_reminders(NOW + timedelta(seconds=30)) == []
    assert [i["kind"] for i in portal.send_reminders(NOW + timedelta(seconds=70))] == ["half"]
    assert [i["kind"] for i in portal.send_reminders(NOW + timedelta(seconds=100))] == ["final"]


# ------------------------------------------------------------------ what each person sees
def test_officer_detail_shows_language_messages_and_files(portal, staffed):
    view = file_complaint(portal, CYBER, kind="police", category="cybercrime", photos=[pdf()])
    row = staffed.get_complaint(view["id"])
    officer = staffed.get_officer(row["assigned_officer_id"])
    detail = portal.officer_detail(officer, view["id"], NOW)
    assert detail["language_name"] == "English"
    assert detail["messages"] and detail["files"] == [{"n": 1, "name": f"{view['id']}-1.pdf", "type": "application/pdf"}]
    data, content_type, _ = portal.officer_file(officer, view["id"], 1)
    assert data.startswith(b"%PDF-") and content_type == "application/pdf"
    with pytest.raises(PortalError):
        portal.officer_file(officer, view["id"], 2)
    with pytest.raises(PortalError):
        portal.officer_file(officer, view["id"], 0)


def test_another_officer_cannot_open_the_file(portal, staffed):
    view = file_complaint(portal, CYBER, kind="police", category="cybercrime", photos=[pdf()])
    other = staffed.get_officer_by_username("water.depot")
    with pytest.raises(PortalError):
        portal.officer_file(other, view["id"], 1)


def test_the_citizen_sees_only_messages_meant_for_them(portal, staffed):
    view = file_complaint(portal)
    portal.send_reminders(NOW + timedelta(days=4))
    tracked = portal.track(view["id"], CONTACT)
    assert {m["to"] for m in tracked["messages"]} == {"citizen"}
    assert tracked["follow_up_due"] == view["deadline"]


# ------------------------------------------------------------------ over HTTP
@pytest.fixture
def server_url(portal, staffed):
    httpd = portal_server.make_server("127.0.0.1", 0, portal, Sessions())
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address[:2]
    yield f"http://{host}:{port}"
    httpd.shutdown()
    httpd.server_close()


def call(base, method, path, payload=None, cookie=None, cookie_name="portal_session"):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"} if data is not None else {}
    if cookie:
        headers["Cookie"] = f"{cookie_name}={cookie}"
    request = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, response.read(), response.headers
    except urllib.error.HTTPError as error:
        return error.code, error.read(), error.headers


def as_json(raw):
    return json.loads(raw.decode("utf-8"))


def citizen_cookie(base):
    call(base, "POST", "/api/citizen/signup", {"name": "Ravi Kumar", "contact": CONTACT,
                                               "address": "12 Main Road, Kalaburagi", "ward_number": HOME_WARD})
    _, body, _ = call(base, "POST", "/api/citizen/login", {"contact": CONTACT})
    _, _, headers = call(base, "POST", "/api/citizen/verify", {"contact": CONTACT, "code": as_json(body)["code"]})
    return headers.get("Set-Cookie").split(";")[0].split("=", 1)[1]


def officer_cookie(base, username):
    _, _, headers = call(base, "POST", "/api/officer/login", {"username": username, "password": "portal-test-pass"})
    return headers.get("Set-Cookie").split(";")[0].split("=", 1)[1]


def test_large_uploads_pass_the_body_limit(server_url):
    """A complaint with three real-size photos used to be refused (the limit was 20 KB for every request)."""
    citizen = citizen_cookie(server_url)
    big = "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8\xff\xe0" + b"0" * 300_000).decode()
    status, body, _ = call(server_url, "POST", "/api/complaints",
                           {"complaint": POTHOLE, "use_llm": False, "kind": "civic", "category": "roads_footpaths",
                            "photos": [big, big, big]}, cookie=citizen, cookie_name="citizen_session")
    assert status == 201, body
    assert as_json(body)["photo_count"] == 3


def test_other_requests_keep_the_small_limit(server_url):
    huge = {"name": "x" * 50000, "contact": CONTACT, "address": "a", "ward_number": 1}
    status, _, _ = call(server_url, "POST", "/api/citizen/signup", huge)
    assert status == 413


def test_police_complaint_over_http(server_url):
    citizen = citizen_cookie(server_url)
    status, body, _ = call(server_url, "POST", "/api/complaints",
                           {"complaint": CYBER, "use_llm": False, "kind": "police", "category": "cybercrime",
                            "photos": [pdf()]}, cookie=citizen, cookie_name="citizen_session")
    assert status == 201
    view = as_json(body)
    assert view["field"] == "Police (pilot)" and view["police_notice"]
    status, body, _ = call(server_url, "POST", "/api/track", {"id": view["id"], "contact": CONTACT})
    assert status == 200 and as_json(body)["messages"]


# ------------------------------------------------------------------ the DC Office dashboard
def test_district_summary_counts(portal, staffed):
    head = staffed.get_officer_by_username("district.head")
    pothole = file_complaint(portal)                                   # roads, Kalaburagi City
    file_complaint(portal, "The doctor is not available and there is no medicine at the hospital")
    cyber = file_complaint(portal, CYBER, kind="police", category="cybercrime", photos=[])
    kannada = file_complaint(portal, KANNADA_LIGHT)
    portal.run_checks(NOW + timedelta(days=2))        # cyber (1-day limit) escalates; reminders go out
    roads_officer = staffed.get_officer(staffed.get_complaint(pothole["id"])["assigned_officer_id"])
    portal.resolve(roads_officer, pothole["id"], "Filled.", now=NOW + timedelta(days=1))
    portal.store.update_complaint(pothole["id"], status="closed", updated_at=iso(NOW + timedelta(days=1, hours=12)))

    summary = portal.district_summary(head, NOW + timedelta(days=2))
    totals = summary["totals"]
    assert totals["total"] == 4 and totals["closed"] == 1 and totals["open"] == 3
    assert totals["avg_resolution_hours"] == 36.0
    assert totals["escalated"] >= 1 and totals["unassigned"] == 0
    assert summary["district"] == "Kalaburagi"
    departments = {item["key"]: item for item in summary["by_department"]}
    assert departments["roads"]["total"] == 2 and departments["roads"]["closed"] == 1
    assert departments["police"]["escalated"] == 1
    assert [item["label"] for item in summary["by_taluk"]][0] == "Kalaburagi City"
    assert summary["by_taluk"][0]["total"] == 4
    assert summary["languages"] == {"en": 3, "kn": 1}
    assert summary["activity"]["escalations"] >= 1
    assert len(summary["oldest_open"]) == 3 and summary["oldest_open"][0]["age_days"] == 2.0


def test_only_the_dc_office_sees_the_district_summary(portal, staffed):
    with pytest.raises(PortalError) as raised:
        portal.district_summary(staffed.get_officer_by_username("roads.depot"))
    assert raised.value.status == 403


def test_district_summary_over_http(server_url):
    status, _, _ = call(server_url, "GET", "/api/district/summary")
    assert status == 401
    status, _, _ = call(server_url, "GET", "/api/district/summary", cookie=officer_cookie(server_url, "roads.depot"))
    assert status == 403
    status, body, _ = call(server_url, "GET", "/api/district/summary", cookie=officer_cookie(server_url, "district.head"))
    summary = as_json(body)
    assert status == 200 and summary["totals"]["total"] == 0 and len(summary["by_taluk"]) == 11


def test_officer_can_open_an_uploaded_document_over_http(server_url):
    citizen = citizen_cookie(server_url)
    _, body, _ = call(server_url, "POST", "/api/complaints",
                      {"complaint": CYBER, "use_llm": False, "kind": "police", "category": "cybercrime", "photos": [pdf()]},
                      cookie=citizen, cookie_name="citizen_session")
    cid = as_json(body)["id"]
    cookie = officer_cookie(server_url, "district.head")
    status, data, headers = call(server_url, "GET", f"/api/officer/complaints/{cid}/files/1", cookie=cookie)
    assert status == 200 and data.startswith(b"%PDF-") and headers["Content-Type"] == "application/pdf"
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert call(server_url, "GET", f"/api/officer/complaints/{cid}/files/9", cookie=cookie)[0] == 404
    assert call(server_url, "GET", f"/api/officer/complaints/{cid}/files/1")[0] == 401
    status, body, _ = call(server_url, "POST", "/api/officer/check-overdue", {}, cookie=cookie)
    assert status == 200 and set(as_json(body)) == {"escalated", "reminders"}


# ------------------------------------------------------------------ the chosen category helps the classifier
def test_a_chosen_category_beats_an_ambiguous_text(portal, staffed):
    """'pothole ... accident risk' alone ties between roads and traffic; the Roads category settles it."""
    text = "There is a big pothole on the main road near the bus stand, accident risk"
    view = file_complaint(portal, text, kind="civic", category="roads_footpaths", photos=[jpeg()] * 3)
    assert view["complaint_label"] == "Damaged road or pothole"
    assert view["field"] == "Roads and streetlights"


def test_the_kannada_water_complaint_is_not_left_as_general(portal, staffed):
    view = file_complaint(portal, "ನಮ್ಮ ರಸ್ತೆಗೆ ಮೂರು ದಿನಗಳಿಂದ ನೀರು ಬಂದಿಲ್ಲ", kind="civic", category="water_supply",
                          photos=[jpeg()] * 3)
    assert view["complaint_label"] == "No drinking water supply" and view["language"] == "kn"


def test_category_hints_keep_a_matching_classifier_choice(kalaburagi):
    from complaintrouter.pipeline import run_complaint
    leak = run_complaint("water pipe leak near our house", None, use_llm=False,
                         type_hints=["no_water_supply", "water_leakage", "water_pollution"])
    assert leak["classification"]["complaint_type"] == "water_leakage"
    pothole = run_complaint("There is a big pothole on the main road near the bus stand, accident risk", None,
                            use_llm=False, type_hints=["road_damage"])
    assert pothole["classification"]["complaint_type"] == "road_damage"
    assert pothole["classification"]["classifier"] in ("citizen_category", "keywords", "rules")
    kannada = run_complaint("ನಮ್ಮ ರಸ್ತೆಗೆ ಮೂರು ದಿನಗಳಿಂದ ನೀರು ಬಂದಿಲ್ಲ", None, use_llm=False)
    assert kannada["classification"]["complaint_type"] == "no_water_supply"
    unrelated = run_complaint("something odd", None, use_llm=False, type_hints=["garbage_sanitation"])
    assert unrelated["classification"]["complaint_type"] == "garbage_sanitation"


# ------------------------------------------------------------------ sample data and hosting
def test_sample_data_fills_the_dashboard_once(portal, staffed):
    from complaint_portal.seed_sample import seed_sample_data
    first = seed_sample_data(portal, NOW)
    assert first == {"citizens": 6, "complaints": 12}
    assert seed_sample_data(portal, NOW) == {"citizens": 0, "complaints": 0}      # only on an empty database
    head = portal.store.get_officer_by_username("district.head")
    summary = portal.district_summary(head, NOW)
    assert summary["totals"]["total"] == 12 and summary["totals"]["closed"] == 2
    assert summary["activity"]["escalations"] >= 1 and summary["activity"]["reminders_sent"] >= 1


def test_the_routing_tools_import_without_neuro_san():
    import subprocess, sys
    code = ("import sys; sys.modules['neuro_san']=None; sys.path.insert(0,'complaint_tools');"
            "import complaintrouter.intake, complaintrouter.router, complaintrouter.reply, "
            "complaintrouter.escalation, complaintrouter.charter_lookup; print('ok')")
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=str(__import__('pathlib').Path(__file__).resolve().parents[1]))
    assert result.stdout.strip() == "ok", result.stderr
