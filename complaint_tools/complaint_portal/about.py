"""The facts behind the "How it works" page: the agents and models, where the time limits come from, and the data.

Everything numeric is read from the charter and the data files, so the page can never disagree with what the portal
actually does. What is a sample value and what is not is stated on the page, not hidden.
"""

import csv
import os
from pathlib import Path
from typing import Any, Dict, List

from complaintrouter import llm_classify
from complaintrouter.common import limit_overrides, load_charter

from . import durable
from .rules import DEPOT, DISTRICT_HEAD, STAGES, level_name, stage_window

ROOT = Path(__file__).resolve().parents[2]

# Where real, published timelines come from. The portal's numbers are samples until a department replaces them.
REFERENCES = [
    {"text": "Karnataka Sakala Services Act, 2011: the State's law that fixes a number of days for notified public services.",
     "url": "https://en.wikipedia.org/wiki/Karnataka_Sakala_Services_Act,_2011"},
    {"text": "CPGRAMS (Government of India grievance portal): the national time limit to resolve a public grievance was cut "
             "to 21 days in 2024.",
     "url": "https://www.tribuneindia.com/news/india/centre-cuts-public-grievances-redressal-time-to-21-days"},
]


def _count_rows(name: str) -> int:
    path = ROOT / "data" / name
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            return max(sum(1 for _ in csv.reader(handle)) - 1, 0)
    except OSError:
        return 0


def _days(window: Any) -> Any:
    if window is None:
        return None
    days = window.total_seconds() / 86400
    return int(days) if float(days).is_integer() else round(days, 2)


def _time_limits(charter: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for key, entry in charter["complaint_types"].items():
        escalation_key = entry.get("escalation_key")
        ladder = []
        for stage in STAGES:
            if stage == DISTRICT_HEAD:
                continue
            window = stage_window(entry.get("fix_days"), entry.get("fix_hours"), escalation_key, stage, charter)
            if window is not None:
                ladder.append({"office": level_name(stage, charter) if stage != DEPOT else charter["owners"][entry["owner"]],
                               "days": _days(window)})
        rows.append({
            "key": key, "label": entry["label"], "department": charter["fields"].get(entry["field"], entry["field"]),
            "ladder": ladder, "total_days": sum(step["days"] for step in ladder if step["days"] is not None),
        })
    return rows


def about_info(portal: Any) -> Dict[str, Any]:
    charter = load_charter()
    tree = portal.locations.tree()
    zones = tree.get("zones", [])
    claude = bool((os.environ.get("ANTHROPIC_API_KEY") or "").strip())
    model = os.environ.get("COMPLAINTROUTER_CLAUDE_MODEL", "claude-haiku-5-5")
    whatsapp_live = bool(getattr(portal, "whatsapp_info", None))
    saving = durable.database_url() is not None
    return {
        "district": tree.get("district"),
        "demo_minutes": getattr(portal, "demo_minutes", 0) or 0,
        "time_limits": {
            "note": charter.get("label"),
            "rule": charter.get("escalation_rule"),
            "after_last": charter.get("after_last_level"),
            "who_sets": "The District Head Office (DC Office) can change the days for any complaint type, and for each "
                        "escalation level, on the Time limits page after logging in as district.head. Every change is "
                        "written to a change log with who made it and when. A new limit applies to new complaints; a "
                        "complaint already filed keeps the limit it was given.",
            "changed": bool(limit_overrides()),
            "reminders": "Reminders go to the officer at 50% and 80% of each time limit. When the limit passes, the "
                         "complaint moves up to the next office automatically.",
            "rows": _time_limits(charter),
            "references": REFERENCES,
        },
        "claude": llm_classify.status() | {"model": model, "configured": claude},
        "agents": [
            {"name": "Complaint form", "kind": "Rules", "model": None, "live": True,
             "does": "The citizen picks emergency, civic or police and a category from fixed lists, then adds photos and the "
                     "address. The address is matched to a taluk or city zone."},
            {"name": "Intake agent", "kind": "Coded tool", "model": None, "live": True,
             "does": "Reads the wording for urgent words in English and Kannada. Urgency always comes from this tool, so a "
                     "model can never lower it."},
            {"name": "Classifier", "kind": "LLM", "model": model if claude else "llama3.1 (Ollama, on a laptop)",
             "live": claude,
             "does": "A language model reads the free text and picks one complaint type from the charter list. It cannot "
                     "write days, owners or replies. A wrong or invented answer is rejected and the keyword rules are used."
                     + ("" if claude else " In this deployment no model key is set, so the keyword rules decide.")},
            {"name": "Photo and summary check", "kind": "LLM", "model": model if claude else None, "live": claude,
             "does": "Claude reads the complaint and up to three photos and writes a one-line English summary and whether "
                     "the photos match the category. It is a note for the officer to verify. It never changes the type, "
                     "owner or deadline."},
            {"name": "Charter agent", "kind": "Coded tool", "model": None, "live": True,
             "does": "Looks up the time limit and notice for the type in the charter file. Nothing is generated."},
            {"name": "Router agent", "kind": "Coded tool", "model": None, "live": True,
             "does": "Finds the owning office and department from the charter; the portal then picks the officer for that "
                     "department and zone."},
            {"name": "Escalation agent", "kind": "Coded tool", "model": None, "live": True,
             "does": "Returns the ladder: how many days each level has, and who is next. The 30-second background check "
                     "applies it."},
            {"name": "Reply agent", "kind": "Coded tool", "model": None, "live": True,
             "does": "Fills the follow-up message from a template, in English or Kannada. It is marked DRAFT for the "
                     "department to review."},
            {"name": "Coordinator", "kind": "LLM", "model": "llama3.1 (Ollama) or Gemini", "live": False,
             "does": "In the Neuro-SAN agent network (registries/complaintrouter.hocon) a coordinator model calls the five "
                     "tools above in order. The website runs the same five tools directly in code, so registering a "
                     "complaint never depends on a model being online."},
            {"name": "WhatsApp assistant", "kind": "LLM", "model": model if claude else None, "live": claude and whatsapp_live,
             "does": "Understands a free-text WhatsApp message and only chooses the kind and category from fixed lists. "
                     "Registering, tracking and login codes are done by code."},
        ],
        "data": [
            {"name": "Complaint charter", "file": "data/charter_kalaburagi.json",
             "detail": f"{len(charter['complaint_types'])} complaint types, {len(charter['fields'])} departments, "
                       f"{len(charter['stage_order']) + 1} escalation levels, Kannada names. Every day count, owner and "
                       "message comes from here."},
            {"name": "Zones and wards", "file": "data/kalaburagi_zones.csv, data/kalaburagi_wards.csv",
             "detail": f"{len(zones)} zones (Kalaburagi City and the taluks), {tree.get('ward_count')} wards. Used to match "
                       "an address to a zone and to choose the officer."},
            {"name": "Labelled test complaints", "file": "data/eval_complaints.csv",
             "detail": f"{_count_rows('eval_complaints.csv')} hand-written complaints with the correct type, used to "
                       "measure the classifier (written for the earlier Chennai version)."},
            {"name": "Demo data", "file": "portal/seed_sample.py",
             "detail": "Invented citizens and complaints (mobile numbers 90000xxxxx) so the dashboards are not empty. "
                       "No real person's data is used."},
        ],
        "storage": {"saved_copy": saving,
                    "text": "Complaints, accounts and logins are stored in the portal's database. A copy is also kept in a "
                            "Postgres database and restored after a restart." if saving else
                            "Complaints are stored in the portal's SQLite database on this host."},
        "limits": [
            "Time limits start as sample numbers set by the project team, not an official citizen's charter. The District "
            "Head Office changes them on the Time limits page (or a department replaces them in one JSON file).",
            "Wards 56 to 65 are placeholders, and Kannada text is a first draft that a native speaker should review.",
            "Complaint text is sent to the Claude API only when a key is set; use invented data in the demo.",
            "Police complaints are only registered and tracked. The portal never decides on an FIR.",
        ],
    }
