"""District, zones, and wards for the complaint portal.

Data files for the active district pack (in the project's data/ folder):
  <district>_zones.csv   the zones (for Kalaburagi: its 11 taluks) and their ward-number ranges
  <district>_wards.csv   one row per ward; ward_name is blank where no source gives it
The Chennai pack has 15 zones and 200 wards (chennai_zones.csv, chennai_wards.csv). Kalaburagi has 11 zones
and 65 wards: the 55 City Corporation wards plus one catch-all area for each of the other ten taluks.
cmwssb_sewer_zones.csv is CMWSSB's five wastewater zones (Chennai reference only; not used for routing).

The loader checks that the zone ranges and the ward rows agree before anything uses them.
"""

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from complaintrouter.common import data_dir, district, load_charter

# The Chennai pack's ward count. The Kalaburagi pack counts its own wards (LocationData.total).
TOTAL_WARDS = 200


@dataclass(frozen=True)
class Zone:
    number: int
    name: str
    ward_from: int
    ward_to: int
    assembly: str
    parliamentary: str
    taluks: str


@dataclass(frozen=True)
class Ward:
    number: int
    zone_number: int
    zone_name: str
    name: Optional[str]

    def label(self) -> str:
        """Short text for a screen, such as 'Ward 115, Teynampet' or 'Ward 115' when no name is known."""
        return f"Ward {self.number}, {self.name}" if self.name else f"Ward {self.number}"


class LocationData:
    """The district, its zones, and its wards, checked on load."""

    def __init__(self, zones: List[Zone], wards: List[Ward], district_name: str) -> None:
        self.district = district_name
        self.total = len(wards)
        self.zones = {zone.number: zone for zone in zones}
        self.wards = {ward.number: ward for ward in wards}

    def ward(self, number: int) -> Optional[Ward]:
        return self.wards.get(number)

    def zone(self, number: int) -> Optional[Zone]:
        return self.zones.get(number)

    def tree(self) -> Dict[str, Any]:
        """The district, zones, and wards in the shape the citizen page needs for its drop-down."""
        zones = []
        for zone in sorted(self.zones.values(), key=lambda item: item.number):
            wards = [
                {"number": ward.number, "name": ward.name, "label": ward.label()}
                for ward in sorted(self.wards.values(), key=lambda item: item.number)
                if ward.zone_number == zone.number
            ]
            zones.append({"number": zone.number, "name": zone.name, "wards": wards})
        return {"district": self.district, "state": load_charter().get("state", "Tamil Nadu"), "zones": zones, "ward_count": len(self.wards)}


def _read_csv(path: Path) -> List[Dict[str, str]]:
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_locations(folder: Optional[Path] = None) -> LocationData:
    """Read the zone and ward files and check that they agree. Raise ValueError if they do not."""
    base = Path(folder) if folder else data_dir()
    pack = district()
    zone_rows = _read_csv(base / f"{pack}_zones.csv")
    ward_rows = _read_csv(base / f"{pack}_wards.csv")

    zones: List[Zone] = []
    for row in zone_rows:
        zone = Zone(
            number=int(row["zone_number"]),
            name=row["zone_name"],
            ward_from=int(row["ward_from"]),
            ward_to=int(row["ward_to"]),
            assembly=row["assembly_constituencies"],
            parliamentary=row["parliamentary_constituencies"],
            taluks=row["taluks"],
        )
        if int(row["ward_count"]) != zone.ward_to - zone.ward_from + 1:
            raise ValueError(f"Zone {zone.number} ward_count does not match its range.")
        zones.append(zone)

    zones.sort(key=lambda item: item.ward_from)
    expected_next = 1
    for zone in zones:
        if zone.ward_from != expected_next:
            raise ValueError(f"Zone {zone.number} starts at ward {zone.ward_from}; expected {expected_next}.")
        expected_next = zone.ward_to + 1
    total = expected_next - 1
    if pack == "chennai" and total != TOTAL_WARDS:
        raise ValueError(f"Zones cover {total} wards; expected {TOTAL_WARDS}.")

    zone_by_number = {zone.number: zone for zone in zones}
    wards: List[Ward] = []
    for row in ward_rows:
        number = int(row["ward_number"])
        zone_number = int(row["zone_number"])
        zone = zone_by_number.get(zone_number)
        if zone is None or not zone.ward_from <= number <= zone.ward_to:
            raise ValueError(f"Ward {number} is listed under zone {zone_number}, which does not contain it.")
        name = (row.get("ward_name") or "").strip() or None
        wards.append(Ward(number=number, zone_number=zone_number, zone_name=zone.name, name=name))

    numbers = sorted(ward.number for ward in wards)
    if numbers != list(range(1, total + 1)):
        raise ValueError(f"{pack}_wards.csv must list wards 1 to {total} once each.")

    name = (zone_rows[0]["district"] or pack.title()).strip()
    return LocationData(zones, wards, name)


def parse_ward_number(raw: Any, maximum: int = TOTAL_WARDS) -> Optional[int]:
    """Accept a ward number as a number or as digits in text. Return None if it is not a ward number.

    maximum is the highest ward number of the district (the default is the Chennai pack's 200)."""
    if isinstance(raw, bool):
        return None
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw.isdigit():
            return None
        raw = int(raw)
    if isinstance(raw, int) and 1 <= raw <= maximum:
        return raw
    return None


def _words(text: str) -> str:
    """Lower-case the words of a name, with single spaces and a space at each end, for whole-word matching."""
    return " " + " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split()) + " "


def _names_in(field: str) -> List[str]:
    """Split a field such as 'Mylapore/Egmore' or 'Maduravoyal (part)/Alandur' into its names."""
    cleaned = re.sub(r"\(part\)", "", field)
    return [name.strip() for name in cleaned.split("/") if len(name.strip()) >= 3]


def match_zones(address: str, locations: LocationData) -> List[Tuple[int, int]]:
    """Find the zones an address points to, from the names in the data sets.

    The data sets give zone names, assembly constituencies, and taluks, but no street or ward
    level names. So an address can only narrow the choice to a zone. A zone name scores 3, an
    assembly constituency scores 2, and a taluk scores 1. Return (zone number, score) pairs,
    best first, for zones that score at least 1.
    """
    haystack = _words(address or "")
    scored: List[Tuple[int, int]] = []
    for zone in locations.zones.values():
        score = 0
        if _words(zone.name) in haystack:
            score += 3
        score += 2 * sum(1 for name in _names_in(zone.assembly) if _words(name) in haystack)
        score += sum(1 for name in _names_in(zone.taluks) if _words(name) in haystack)
        if score:
            scored.append((zone.number, score))
    return sorted(scored, key=lambda item: (-item[1], item[0]))


def cmwssb_sewer_zones(folder: Optional[Path] = None) -> List[Dict[str, str]]:
    """Return CMWSSB's five wastewater zones with their areas, for reference."""
    base = Path(folder) if folder else data_dir()
    return _read_csv(base / "cmwssb_sewer_zones.csv")


def load_for_portal() -> Tuple[LocationData, str]:
    """Load the locations once and return them with the data folder they came from."""
    base = data_dir()
    return load_locations(base), str(base)
