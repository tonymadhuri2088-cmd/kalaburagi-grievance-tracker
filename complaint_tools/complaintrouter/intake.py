"""Classifies a citizen complaint into a charter complaint type and subtype.

This is a keyword classifier, not a trained model. It returns notes whenever a
subtype or timeline had to be assumed, so a human can confirm before action.
"""

import json
from typing import Any, Dict, List

from neuro_san.interfaces.coded_tool import CodedTool

from .common import district, load_charter

# Specific types. "general_grievance" is used only when none of these match.
TYPE_KEYWORDS = {
    "unsafe_cleaning": ["manual scavenging", "unsafe cleaning", "cleaning sewer without", "died while cleaning", "without safety gear"],
    "water_leakage": ["leak", "pipe burst", "pipeline burst", "water wastage", "water flowing on the road", "water flowing on road"],
    "water_pollution": ["contaminated", "dirty water", "polluted", "muddy water", "smelly water", "sewage in water", "water quality", "discoloured water", "discolored water"],
    "no_water_supply": ["no water", "no supply", "water not coming", "water supply stopped", "defective water supply", "defective supply"],
    "defective_meter": ["water meter", "meter defective", "meter faulty", "meter not working", "meter stopped"],
    "handpump_repair": ["hand pump", "handpump", "india mark"],
    "sewer_main_blockage": ["sewer main", "main sewer", "sewer blocked", "sewer blockage", "manhole overflow", "sewage overflow", "sewer overflow"],
    "house_sewer_blockage": ["house sewer", "house drain", "toilet blocked", "drain blocked at home", "toilet not flushing"],
    "damaged_sewer_line": ["sewer line damaged", "damaged sewer", "broken sewer", "sewer pipe broken", "sewer line broken"],
    "tax_charges": ["water bill", "tax", "charges", "arrears", "bill is wrong", "payment not reflected", "excess bill"],
    "tanker_supply": ["tanker", "water lorry"],
    "new_connection_delay": ["new connection", "connection not given", "application pending", "connection pending"],
    "street_water_no_piped": ["no piped", "public tap", "street water", "no pipe connection", "standpipe"],
    "septic_tank_clearance": ["septic", "desludging", "tank clearance", "tank cleaning"],
}

# Types of the Kalaburagi pack (data/charter_kalaburagi.json). Each list has English and Kannada words.
# Only the types the active charter has are used. The Kannada words should be reviewed by a Kannada speaker.
KALABURAGI_TYPE_KEYWORDS = {
    "cybercrime": ["cyber", "online fraud", "otp", "phishing", "hacked", "fake call", "upi fraud", "social media",
                   "ಸೈಬರ್", "ಆನ್‌ಲೈನ್ ವಂಚನೆ", "ಆನ್ಲೈನ್ ವಂಚನೆ", "ಓಟಿಪಿ", "ನಕಲಿ ಕರೆ"],
    "financial_fraud": ["fraud", "cheated", "cheating", "scam", "money taken", "loan fraud", "bank fraud",
                        "ವಂಚನೆ", "ಮೋಸ", "ಹಣ ಮೋಸ", "ಹಣ ಕಳೆದುಕೊಂಡ"],
    "lost_property": ["lost my", "lost phone", "lost wallet", "lost mobile", "lost property", "missing phone",
                      "stolen", "theft", "robbery", "ಕಳೆದುಹೋಗಿದೆ", "ಕಳೆದು ಹೋಗಿದೆ", "ಕಳ್ಳತನ", "ಕಳವು"],
    "traffic_safety": ["traffic", "accident", "rash driving", "signal", "illegal parking", "drunk driving", "unsafe road",
                       "ಸಂಚಾರ", "ಅಪಘಾತ", "ಟ್ರಾಫಿಕ್", "ವಾಹನ ನಿಲುಗಡೆ"],
    "complaint_individuals": ["threat", "threatening", "harass", "harassment", "neighbour", "neighbor", "assault",
                              "ಬೆದರಿಕೆ", "ಕಿರುಕುಳ", "ಜಗಳ", "ಹಲ್ಲೆ"],
    "hospital_service": ["hospital", "doctor", "medicine", "no beds", "nurse", "ward boy", "phc", "health centre",
                         "health center", "ambulance", "ಆಸ್ಪತ್ರೆ", "ವೈದ್ಯ", "ಔಷಧ", "ಹಾಸಿಗೆ", "ದಾದಿ"],
    "no_water_supply": ["no water", "no supply", "water not coming", "water supply stopped", "drinking water",
                        "ನೀರು ಬರುತ್ತಿಲ್ಲ", "ನೀರು ಬಂದಿಲ್ಲ", "ನೀರಿಲ್ಲ", "ನೀರು ಪೂರೈಕೆ", "ಕುಡಿಯುವ ನೀರು"],
    "water_leakage": ["leak", "pipe burst", "pipeline burst", "water wastage", "ಸೋರಿಕೆ", "ಪೈಪ್ ಒಡೆದ", "ಪೈಪ್ ಒಡೆ"],
    "water_pollution": ["contaminated", "dirty water", "polluted water", "muddy water", "smelly water",
                        "ಕೊಳಕು ನೀರು", "ಕಲುಷಿತ ನೀರು", "ದುರ್ವಾಸನೆ ನೀರು"],
    "handpump_repair": ["hand pump", "handpump", "borewell", "bore well", "ಕೈ ಪಂಪ್", "ಕೊಳವೆ ಬಾವಿ", "ಬೋರ್‌ವೆಲ್"],
    "road_damage": ["pothole", "road damaged", "bad road", "broken road", "road repair", "ಗುಂಡಿ", "ರಸ್ತೆ ಹಾಳು", "ರಸ್ತೆ ದುರಸ್ತಿ"],
    "streetlight_fault": ["street light", "streetlight", "street lamp", "light not working", "ಬೀದಿ ದೀಪ", "ಬೀದಿದೀಪ"],
    "garbage_sanitation": ["garbage", "rubbish", "waste not collected", "dustbin", "dumping", "mosquito", "ಕಸ", "ಸ್ವಚ್ಛತೆ", "ನೈರ್ಮಲ್ಯ"],
    "drainage_blockage": ["drain", "drainage", "sewage", "sewer", "gutter", "manhole", "ಚರಂಡಿ", "ಒಳಚರಂಡಿ", "ಮ್ಯಾನ್‌ಹೋಲ್"],
    "property_tax_billing": ["property tax", "tax", "water bill", "bill is wrong", "excess bill", "ತೆರಿಗೆ", "ಬಿಲ್"],
}

GENERAL_KEYWORDS = ["complaint", "grievance", "vigilance", "corruption", "employee", "rude", "ದೂರು", "ಭ್ರಷ್ಟಾಚಾರ", "ಲಂಚ"]

URGENT_TERMS = [
    "died", "death", "collapse", "child", "injury", "injured", "electrocut", "sick",
    "hospital", "fever", "diarrhoea", "diarrhea", "vomit", "contaminated", "unsafe",
    "manhole", "ambulance", "threat", "ಸಾವು", "ಗಾಯ", "ಜ್ವರ", "ಬೆದರಿಕೆ",
]


def _keywords_for(charter: Dict[str, Any]) -> Dict[str, List[str]]:
    """The keyword lists for the types the active charter has. The Chennai pack keeps its original lists."""
    merged: Dict[str, List[str]] = {}
    sources = (TYPE_KEYWORDS,) if district() == "chennai" else (TYPE_KEYWORDS, KALABURAGI_TYPE_KEYWORDS)
    for source in sources:
        for complaint_type, terms in source.items():
            if complaint_type in charter["complaint_types"]:
                merged.setdefault(complaint_type, [])
                merged[complaint_type] += [term for term in terms if term not in merged[complaint_type]]
    return merged


def _subtype(complaint_type: str, text: str) -> Dict[str, Any]:
    """Pick a subtype from the text. Report whether it was stated or assumed."""
    lowered = text.lower()
    if complaint_type == "water_leakage":
        if "transmission" in lowered:
            return {"subtype": "transmission_main", "stated": True}
        if "distribution" in lowered or " main" in lowered:
            return {"subtype": "distribution_main", "stated": True}
        if "service" in lowered:
            return {"subtype": "service_line", "stated": True}
        return {"subtype": "service_line", "stated": False}
    if complaint_type == "water_pollution":
        if any(term in lowered for term in ["not identified", "unknown source", "cannot find", "source unknown"]):
            return {"subtype": "not_identified", "stated": True}
        if any(term in lowered for term in ["at the tap", "from the tap", "pipe", "tank"]):
            return {"subtype": "identified_point", "stated": True}
        return {"subtype": "identified_point", "stated": False}
    if complaint_type == "handpump_repair":
        if "india mark" in lowered:
            return {"subtype": "india_mark_pump", "stated": True}
        return {"subtype": "hand_pump", "stated": "hand pump" in lowered or "handpump" in lowered}
    return {"subtype": None, "stated": True}


def classify_complaint(text: str) -> Dict[str, Any]:
    """Return the complaint type, subtype, urgency, and any notes for a human."""
    charter = load_charter()
    lowered = text.lower()
    urgent_hits = [term for term in URGENT_TERMS if term in lowered]
    matches: Dict[str, List[str]] = {}
    for complaint_type, terms in _keywords_for(charter).items():
        hits = [term for term in terms if term in lowered]
        if hits:
            matches[complaint_type] = hits

    notes: List[str] = []
    if not matches:
        general = [term for term in GENERAL_KEYWORDS if term in lowered]
        if general:
            complaint_type, hits = "general_grievance", general
        else:
            return {
                "complaint_type": "unclassified", "subtype": None, "urgent": bool(urgent_hits),
                "matched_terms": [], "needs_human_review": True,
                "notes": ["No charter complaint type matched."],
            }
    else:
        ranked = sorted(matches.items(), key=lambda item: len(item[1]), reverse=True)
        complaint_type, hits = ranked[0]
        if len(ranked) > 1 and len(ranked[1][1]) == len(hits):
            notes.append(f"Tie between {complaint_type} and {ranked[1][0]}; confirm the type.")

    entry = charter["complaint_types"][complaint_type]
    subtype_info = _subtype(complaint_type, text) if entry.get("subtypes") else {"subtype": None, "stated": True}
    subtype = subtype_info["subtype"]
    if entry.get("subtypes") and not subtype_info["stated"]:
        notes.append(f"Subtype not stated; defaulted to {subtype}. Confirm before relying on the deadline.")
    if complaint_type == "water_leakage" and not subtype_info["stated"]:
        notes.append("Leak location not stated. The shortest deadline (service line) is used.")

    urgent = bool(urgent_hits) or bool(entry.get("always_urgent"))
    return {
        "complaint_type": complaint_type,
        "subtype": subtype,
        "urgent": urgent,
        "matched_terms": hits,
        "needs_human_review": bool(notes) or urgent,
        "notes": notes,
    }


class ComplaintIntake(CodedTool):
    """CodedTool that classifies one complaint."""

    async def async_invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> str:
        return json.dumps(classify_complaint(str(args.get("complaint_text", ""))))
