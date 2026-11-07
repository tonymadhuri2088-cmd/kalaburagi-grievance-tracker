"""Invented citizens and complaints, so the dashboards are not empty on a fresh demo.

Everything here is made up: the names, the mobile numbers (the 90000 range) and the complaints. The complaints are
filed at different times in the past, so some are on time, some have had reminders, some are overdue and moved up,
and a few are resolved. Run it once on a fresh database; it does nothing if the database already has complaints.
"""

import base64
from datetime import datetime, timedelta
from typing import Dict, List

from complaint_portal.workflow import Portal, utcnow

# A tiny valid JPEG header is enough for the portal's file check; this is demo data, not a real photo.
_JPEG = "data:image/jpeg;base64," + base64.b64encode(bytes.fromhex("ffd8ffe000104a46494600010100000100010000ffdb004300") + b"\x00" * 200 + bytes.fromhex("ffd9")).decode()

CITIZENS = [
    ("Ravi Kumar", "9000000001", "Station Road, Super Market area, Kalaburagi", 1),
    ("Lakshmi Devi", "9000000002", "Jewargi Road, Kalaburagi", 1),
    ("Basavaraj Patil", "9000000003", "Main Road, Aland", 56),
    ("Shivakumar", "9000000004", "Bus stand road, Sedam", 61),
    ("Fatima Begum", "9000000005", "Market street, Shahabad", 64),
    ("Mahantesh", "9000000006", "Near temple, Afzalpur", 57),
]

# (citizen index, kind, category, text, age in days, resolved)
COMPLAINTS = [
    (0, "civic", "roads_footpaths", "There is a big pothole on the main road near the bus stand and bikes are falling.", 9, False),
    (1, "civic", "water_supply", "No water has come to our street for three days. Please fix it.", 3, False),
    (2, "civic", "water_supply", "ನಮ್ಮ ರಸ್ತೆಗೆ ಮೂರು ದಿನಗಳಿಂದ ನೀರು ಬಂದಿಲ್ಲ", 1, False),
    (3, "civic", "streetlights", "The street light in front of house number 12 has not worked for a week.", 2, False),
    (4, "civic", "garbage_sanitation", "Garbage has not been collected on our street for five days.", 1, False),
    (5, "civic", "public_health_strays", "There is no doctor at the primary health centre in the mornings.", 4, False),
    (0, "civic", "drainage_sewerage", "The drain near the market is blocked and overflowing onto the road.", 0.6, False),
    (1, "police", "cybercrime", "I lost money to an online fraud call asking for my OTP.", 2, False),
    (2, "police", "lost_property", "I lost my wallet near the railway station yesterday.", 0.3, False),
    (3, "civic", "roads_footpaths", "The road to the school is broken and full of pits.", 6, True),
    (4, "civic", "water_supply", "The tap water is brown and smells bad since Monday.", 5, True),
    (5, "civic", "municipal_services_taxes", "My property tax bill this year is much higher than usual.", 0.1, False),
]


def seed_sample_data(portal: Portal, now: datetime = None) -> Dict[str, int]:
    """Add the invented citizens and complaints. Return how many of each were added."""
    now = now or utcnow()
    if portal.store.list_complaints(limit=1):
        return {"citizens": 0, "complaints": 0}
    for name, mobile, address, ward in CITIZENS:
        portal.sign_up_citizen(name, mobile, address, ward, now - timedelta(days=12))
    filed: List[Dict] = []
    for index, kind, category, text, age, resolved in sorted(COMPLAINTS, key=lambda item: -item[4]):
        name, mobile, address, ward = CITIZENS[index]
        at = now - timedelta(days=age)
        view = portal.register(name, mobile, text, ward_number=ward, use_llm=False, now=at, address=address,
                               kind=kind, category=category, photos=[_JPEG] * 3 if kind == "civic" else [])
        filed.append({"id": view["id"], "mobile": mobile, "resolved": resolved, "at": at})
    # Resolved ones: the officer marks them resolved a day later and the citizen confirms.
    for item in filed:
        if not item["resolved"]:
            continue
        row = portal.store.get_complaint(item["id"])
        officer = portal.store.get_officer(row["assigned_officer_id"])
        later = item["at"] + timedelta(days=1)
        portal.resolve(officer, item["id"], "Repaired and checked on site.", later)
        confirmed_at = later + timedelta(hours=3)
        shown = portal.confirm(item["id"], item["mobile"], True, "Thank you", confirmed_at)
        portal.confirm_code(item["id"], item["mobile"], shown["demo_code"], confirmed_at)
    portal.run_checks(now)   # reminders and escalations that are due by now
    return {"citizens": len(CITIZENS), "complaints": len(filed)}
