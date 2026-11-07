"""The kinds of complaint the citizen chooses between on Register Complaint.

Emergency: urgent problems that need someone at once. No photos are asked for.
Not emergency (civic): everyday civic problems. Three photos are required.
Police complaint (Kalaburagi pilot): cybercrime, financial fraud, lost property, public safety and traffic, and
complaints involving individuals. Documents or photos are optional (up to three). The system only registers and
tracks these; whether an offence took place or an FIR is registered is decided only by authorised officials.

The labels are shown exactly as the citizen sees them. The keys are stored in the database.
"""

from typing import Dict, List, Optional, Tuple

EMERGENCY = "emergency"
CIVIC = "civic"
POLICE = "police"
KINDS = (EMERGENCY, CIVIC, POLICE)
KIND_LABELS: Dict[str, str] = {EMERGENCY: "Emergency", CIVIC: "Not emergency", POLICE: "Police complaint"}

EMERGENCY_CATEGORIES: List[Tuple[str, str]] = [
    ("emergency_rescue", "Emergency Rescue"),
    ("fire_smoke", "Fire and smoke emergencies"),
    ("ambulance_medical", "Ambulance and medical emergencies"),
    ("lpg_leak", "LPG gas leakage"),
    ("hazardous_gas", "Hazardous gas or chemical leakage"),
    ("flood_rescue", "Flood rescue and evacuation"),
    ("building_collapse", "Building collapse and trapped persons"),
    ("electrical_hazard", "Electrical hazards and fallen live wires"),
    ("road_accident", "Road accidents requiring rescue"),
    ("lift_trapped", "People trapped in lifts or confined spaces"),
    ("tree_fall", "Tree falls blocking access or threatening lives"),
    ("drowning", "Drowning and water rescue"),
    ("landslide", "Landslides and structural hazards"),
]

CIVIC_CATEGORIES: List[Tuple[str, str]] = [
    ("water_supply", "Water Supply"),
    ("drainage_sewerage", "Drainage and Sewerage"),
    ("garbage_sanitation", "Garbage and Sanitation"),
    ("roads_footpaths", "Roads and Footpaths"),
    ("streetlights", "Streetlights"),
    ("flooding_waterlogging", "Flooding and Waterlogging"),
    ("public_health_strays", "Public Health and Stray Animals"),
    ("parks_infrastructure", "Parks and Public Infrastructure"),
    ("municipal_services_taxes", "Municipal Services and Taxes"),
    ("other_civic", "Other Complaints"),
]

# The police categories use the same key as their complaint type in data/charter_kalaburagi.json.
POLICE_CATEGORIES: List[Tuple[str, str]] = [
    ("cybercrime", "Cybercrime and online fraud"),
    ("financial_fraud", "Financial fraud"),
    ("lost_property", "Lost property"),
    ("traffic_safety", "Public safety and traffic"),
    ("complaint_individuals", "Complaint involving individuals"),
]
POLICE_NOTICE = ("This system only registers and tracks your complaint. Whether an offence took place, and whether "
                 "an FIR is registered, is decided only by authorised police officials.")

PHOTOS_REQUIRED = 3
MAX_PHOTO_BYTES = 4 * 1024 * 1024
PHOTO_TYPES = ("image/jpeg", "image/png", "image/webp", "application/pdf")


def categories_for(kind: str) -> List[Tuple[str, str]]:
    if kind == EMERGENCY:
        return EMERGENCY_CATEGORIES
    if kind == POLICE:
        return POLICE_CATEGORIES
    return CIVIC_CATEGORIES


def category_key_for_type(kind: Optional[str], category: Optional[str]) -> Optional[str]:
    """The complaint type a chosen category fixes. Only police categories do: their key is the type key."""
    return category if kind == POLICE else None


def type_hints_for(kind: Optional[str], category: Optional[str]) -> List[str]:
    """The complaint types that fit a not-emergency category the citizen chose. Empty where the charter lists none."""
    if kind != CIVIC or not category:
        return []
    from complaintrouter.common import load_charter  # the charter of the active pack
    charter = load_charter()
    return [key for key in charter.get("category_types", {}).get(category, []) if key in charter["complaint_types"]]


def available_kinds() -> Tuple[str, ...]:
    """The kinds this district offers. Police complaints exist only where the charter has the police types."""
    from complaintrouter.common import load_charter  # imported here so the charter of the active pack is read
    types = load_charter()["complaint_types"]
    if all(key in types for key, _ in POLICE_CATEGORIES):
        return KINDS
    return (EMERGENCY, CIVIC)


def category_label(kind: str, key: str) -> str:
    for code, label in categories_for(kind):
        if code == key:
            return label
    return ""
