"""Shared helpers for the complaint router coded tools.

Every timeline comes from a charter file in the data folder, which carries its own source label.
Set COMPLAINTROUTER_DATA_DIR to point at a different data folder.

Which district the portal serves is a "district pack": its charter (charter_<district>.json), its zone
and ward files (<district>_zones.csv, <district>_wards.csv) and its list of departments. The default is
Kalaburagi (Solvathon 2026). The Chennai pack from the first version of this project is still included,
and the older tests run against it. Choose a pack with the PORTAL_DISTRICT environment variable, or in
code with set_district().
"""

import json
import os
from pathlib import Path
from typing import Any, List

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DEFAULT_DISTRICT = "kalaburagi"
DISTRICTS = ("kalaburagi", "chennai")

# Callbacks run when the district changes, so modules that keep a copy of pack data can refresh it.
_listeners: List[Any] = []
_district = os.environ.get("PORTAL_DISTRICT", DEFAULT_DISTRICT).strip().lower() or DEFAULT_DISTRICT
if _district not in DISTRICTS:
    raise ValueError(f"PORTAL_DISTRICT must be one of {', '.join(DISTRICTS)}, not '{_district}'.")


def data_dir() -> Path:
    """Return the folder that holds the charter data."""
    return Path(os.environ.get("COMPLAINTROUTER_DATA_DIR", DEFAULT_DATA_DIR))


def district() -> str:
    """Return the active district pack: 'kalaburagi' or 'chennai'."""
    return _district


def set_district(name: str) -> None:
    """Switch the active district pack. Tests use this; the running portal sets it once, from PORTAL_DISTRICT."""
    global _district  # pylint: disable=global-statement
    name = (name or "").strip().lower()
    if name not in DISTRICTS:
        raise ValueError(f"Unknown district '{name}'. Use one of: {', '.join(DISTRICTS)}.")
    _district = name
    for listener in _listeners:
        listener()


def on_district_change(callback: Any) -> None:
    """Register a function to call whenever set_district() runs."""
    _listeners.append(callback)


def charter_filename() -> str:
    """The Chennai pack keeps its original file name; other packs use charter_<district>.json."""
    return "charter.json" if _district == "chennai" else f"charter_{_district}.json"


def load_charter() -> Any:
    """Load the active district's charter data file."""
    with open(data_dir() / charter_filename(), encoding="utf-8") as handle:
        return json.load(handle)


def parse_arg(value: Any, default: Any) -> Any:
    """Accept a native value or a JSON string produced by an LLM."""
    if value is None:
        return default
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
    return value


def parse_bool(value: Any) -> bool:
    """Read a boolean that an LLM may have sent as text."""
    return str(value).strip().lower() in ("true", "1", "yes")
