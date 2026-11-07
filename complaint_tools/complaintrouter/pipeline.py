"""Runs one complaint through the offline app's steps.

The steps are the same coded tools the agent network uses: classify, charter timeline,
route, escalation, and reply. The only model step is the optional classifier in
llm_classify.py. The reply text always comes from reply.build_reply, never from a model.
"""

from typing import Any, Dict, List, Optional

from .charter_lookup import lookup_timeline
from .common import load_charter
from .escalation import escalation_status
from .llm_classify import classify
from .reply import build_reply
from .router import route


def _whole_days(days: Optional[float]) -> Optional[Any]:
    """Show 10 rather than 10.0 when the citizen gave a whole number of days."""
    if days is None:
        return None
    return int(days) if float(days).is_integer() else float(days)


def run_complaint(
    complaint: str,
    days_elapsed: Optional[float],
    use_llm: bool = True,
    settings: Optional[Dict[str, Any]] = None,
    reference: Optional[str] = None,
    forced_type: Optional[str] = None,
    type_hints: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Run every step for one complaint and return the results, including the exact draft reply.

    reference is the complaint ID. The portal passes it so the reply names the real complaint.
    Left out, the reply says the reference is still to be assigned, as before.

    forced_type is a complaint type the citizen chose from a list (for example a police category). It replaces
    the classifier's choice, and the result says so.

    type_hints are the types that fit a broader category the citizen chose (for example Roads and Footpaths). The
    classifier's choice is kept when it is one of them; otherwise the first hint is used. Free text alone can be
    ambiguous ("pothole ... accident risk"), the category the citizen picked is not.
    """
    charter = load_charter()
    days = _whole_days(days_elapsed)

    classification = classify(complaint, use_llm=use_llm, settings=settings)
    if forced_type and forced_type in charter["complaint_types"]:
        classification = dict(
            classification, complaint_type=forced_type, subtype=None, classifier="citizen_choice",
            llm_status="The citizen chose the type from the list.", needs_human_review=False, notes=[],
        )
    hints = [key for key in (type_hints or []) if key in charter["complaint_types"]]
    if hints and not forced_type and classification["complaint_type"] not in hints:
        classification = dict(
            classification, complaint_type=hints[0], subtype=None, classifier="citizen_category",
            llm_status="The type follows the category the citizen chose.", needs_human_review=False, notes=[],
        )
    complaint_type = classification["complaint_type"]
    timeline = lookup_timeline(complaint_type, classification["subtype"], charter)
    routing = route(complaint_type, charter)
    escalation = escalation_status(routing.get("escalation_key"), days, charter)

    reply = build_reply({
        "reference": reference,
        "label": timeline.get("label") or "Not stated",
        "owner": routing.get("owner") or "to be assigned",
        "fix_days": timeline.get("fix_days"),
        "fix_hours": timeline.get("fix_hours"),
        "fix_note": timeline.get("fix_note") or "",
        "notice": timeline.get("notice") or "",
        "days_elapsed": days,
        "urgent": classification["urgent"],
        "escalation_key": routing.get("escalation_key"),
        "review_notes": classification["notes"],
    }, charter)

    return {
        "classification": classification,
        "timeline": timeline,
        "route": routing,
        "escalation": escalation,
        "reply": reply,
    }
