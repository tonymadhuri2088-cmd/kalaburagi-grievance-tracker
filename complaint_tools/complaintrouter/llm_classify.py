"""Local LLM classifier for the offline app.

The model (llama3.1 through a local Ollama server) reads the citizen's wording and
picks a charter complaint type and subtype. It never writes timelines, owners,
escalation days or reply text. Those come from data/charter.json through the coded tools.

Every answer is checked against charter.json. If Ollama is not running, or the answer
is not a valid charter choice, the keyword classifier in intake.py is used instead.
Urgency always comes from the keyword classifier, so the model cannot lower it.
"""

import json
import os
import re
import threading
import urllib.error
import urllib.request
from datetime import date
from typing import Any, Dict, Optional

from .common import load_charter
from .intake import classify_complaint

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.1"
DEFAULT_TIMEOUT_SECONDS = 120
CLAUDE_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_CLAUDE_MODEL = "claude-haiku-5-5"
DEFAULT_CLAUDE_DAILY_LIMIT = 300
CLAUDE_TIMEOUT_SECONDS = 20
_claude_use = {"day": None, "count": 0}
_claude_lock = threading.Lock()
_status = {"calls_ok": 0, "errors": 0, "last_error": "", "last_ok": ""}


def note_error(message: str) -> None:
    """Remember a failed Claude call (shown on the How-it-works page) and print the first few to the log."""
    with _claude_lock:
        _status["errors"] += 1
        _status["last_error"] = message[:300]
        if _status["errors"] <= 5:
            print(f"Claude call failed - {message[:300]}", flush=True)


def note_ok() -> None:
    with _claude_lock:
        _status["calls_ok"] += 1
        _status["last_ok"] = date.today().isoformat()


def status() -> dict:
    """Is a Claude key set, and have the calls worked since this service started?"""
    with _claude_lock:
        return {"configured": claude_settings() is not None, **_status}


def ollama_settings() -> Dict[str, Any]:
    """Read the Ollama address, model and timeout from the environment, with defaults."""
    return {
        "base_url": os.environ.get("COMPLAINTROUTER_OLLAMA_URL", DEFAULT_OLLAMA_URL),
        "model": os.environ.get("COMPLAINTROUTER_MODEL", DEFAULT_MODEL),
        "timeout": float(os.environ.get("COMPLAINTROUTER_LLM_TIMEOUT", DEFAULT_TIMEOUT_SECONDS)),
    }


def claude_settings() -> Optional[Dict[str, Any]]:
    """Settings for the Claude API, or None when no ANTHROPIC_API_KEY is set (then Ollama and keywords are used)."""
    key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if not key:
        return None
    try:
        limit = int(os.environ.get("COMPLAINTROUTER_CLAUDE_DAILY_LIMIT", DEFAULT_CLAUDE_DAILY_LIMIT))
    except ValueError:
        limit = DEFAULT_CLAUDE_DAILY_LIMIT
    return {"key": key, "model": os.environ.get("COMPLAINTROUTER_CLAUDE_MODEL", DEFAULT_CLAUDE_MODEL),
            "timeout": CLAUDE_TIMEOUT_SECONDS, "daily_limit": limit}


def ask_claude(prompt: str, settings: Dict[str, Any]) -> Optional[str]:
    """Send the prompt to the Claude API. Return the model's text, or None (no key, limit used up, or any error).

    The answer is only ever used after parse_llm_answer has checked it against the charter list, so a wrong or
    manipulated answer cannot create a type, a deadline or an owner.
    """
    with _claude_lock:
        today = date.today()
        if _claude_use["day"] != today:
            _claude_use["day"], _claude_use["count"] = today, 0
        if _claude_use["count"] >= settings["daily_limit"]:
            return None
        _claude_use["count"] += 1
    body = json.dumps({"model": settings["model"], "max_tokens": 120,
                       "messages": [{"role": "user", "content": prompt}]}).encode("utf-8")
    request = urllib.request.Request(
        CLAUDE_URL, data=body, method="POST",
        headers={"content-type": "application/json", "x-api-key": settings["key"],
                 "anthropic-version": "2023-06-01"},
    )
    try:
        with urllib.request.urlopen(request, timeout=settings["timeout"]) as response:
            payload = json.loads(response.read().decode("utf-8"))
        blocks = payload.get("content") if isinstance(payload, dict) else None
        for block in blocks or []:
            if isinstance(block, dict) and block.get("type") == "text":
                note_ok()
                return block.get("text")
    except urllib.error.HTTPError as error:
        try:
            detail = error.read().decode("utf-8", "replace")[:200]
        except OSError:
            detail = ""
        note_error(f"HTTP {error.code} {detail}")
        return None
    except (OSError, ValueError) as error:
        note_error(f"{error.__class__.__name__}: {error}")
        return None
    note_error("no text in the answer")
    return None


def build_prompt(complaint: str, charter: Dict[str, Any]) -> str:
    """Return the instruction and the list of allowed charter types for the model."""
    lines = [
        charter.get("classifier_intro", "You classify a citizen's water or sewer complaint for Chennai's water board."),
        "Choose exactly one complaint_type from the list below, based on the main problem.",
        "Choose a subtype only if the type lists subtypes; otherwise use null.",
        "If no type fits, use general_grievance. Do not invent types or subtypes.",
        'Answer with JSON only, in this form: {"complaint_type": "...", "subtype": "..." or null}',
        "",
        "Allowed types:",
    ]
    for key, entry in charter["complaint_types"].items():
        subtypes = entry.get("subtypes")
        if subtypes:
            lines.append(f"- {key}: {entry['label']}. Subtypes: {', '.join(subtypes)}")
        else:
            lines.append(f"- {key}: {entry['label']}")
    lines += ["", "Complaint:", complaint.strip(), "", "JSON:"]
    return "\n".join(lines)


def parse_llm_answer(raw: Optional[str], charter: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return a valid charter choice, or None when the answer cannot be used.

    An unknown or missing subtype is returned as None, so the caller can apply the default and say so.
    """
    match = re.search(r"\{.*\}", raw or "", re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None

    complaint_type = data.get("complaint_type")
    if not isinstance(complaint_type, str) or complaint_type not in charter["complaint_types"]:
        return None

    entry = charter["complaint_types"][complaint_type]
    subtype = data.get("subtype")
    if entry.get("subtypes"):
        subtype = subtype if isinstance(subtype, str) and subtype in entry["subtypes"] else None
    else:
        subtype = None
    return {"complaint_type": complaint_type, "subtype": subtype}


def ask_ollama(prompt: str, settings: Dict[str, Any]) -> Optional[str]:
    """Send the prompt to the local Ollama server. Return the model's text, or None if unreachable."""
    body = json.dumps({
        "model": settings["model"],
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
    }).encode("utf-8")
    request = urllib.request.Request(
        settings["base_url"].rstrip("/") + "/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=settings["timeout"]) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError):
        return None
    text = payload.get("response") if isinstance(payload, dict) else None
    return text if isinstance(text, str) else None


def _merge(keyword: Dict[str, Any], choice: Dict[str, Any], charter: Dict[str, Any], model: str,
           who: str = "the local LLM") -> Dict[str, Any]:
    """Combine the model's valid choice with the keyword result (urgency and matched terms)."""
    complaint_type = choice["complaint_type"]
    entry = charter["complaint_types"][complaint_type]
    notes = [f"Type chosen by {who} ({model}). Confirm it matches the complaint."]

    subtype = choice["subtype"]
    if entry.get("subtypes") and subtype is None:
        subtype = entry["default_subtype"]
        notes.append(f"Subtype not stated; defaulted to {subtype}. Confirm before relying on the deadline.")
        if complaint_type == "water_leakage":
            notes.append("Leak location not stated. The shortest deadline (service line) is used.")

    keyword_type = keyword["complaint_type"]
    if keyword_type != complaint_type:
        keyword_label = charter["complaint_types"].get(keyword_type, {}).get("label", keyword_type)
        notes.append(f"The keyword classifier chose: {keyword_label}. Confirm the type.")

    urgent = bool(keyword["urgent"]) or bool(entry.get("always_urgent"))
    return {
        "complaint_type": complaint_type,
        "subtype": subtype,
        "urgent": urgent,
        "matched_terms": keyword["matched_terms"],
        "needs_human_review": True,
        "notes": notes,
        "classifier": "llm",
        "llm_status": f"Type and subtype chosen by {who} ({model}).",
    }


def classify(complaint: str, use_llm: bool = True, settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Classify a complaint with the local LLM when requested, falling back to keywords."""
    charter = load_charter()
    keyword = classify_complaint(complaint)
    fallback = dict(keyword, classifier="keyword")

    if not use_llm:
        fallback["llm_status"] = "Not requested; keyword classifier used."
        return fallback

    prompt = build_prompt(complaint, charter)
    claude = claude_settings() if settings is None else None
    if claude is not None:   # Claude first when a key is set; Ollama and keywords stay as the fallbacks
        choice = parse_llm_answer(ask_claude(prompt, claude), charter)
        if choice is not None:
            return _merge(keyword, choice, charter, claude["model"], who="Claude")

    settings = settings or ollama_settings()
    raw = ask_ollama(prompt, settings)
    if raw is None:
        fallback["llm_status"] = (
            f"Local LLM not reachable at {settings['base_url']}; keyword classifier used."
        )
        return fallback

    choice = parse_llm_answer(raw, charter)
    if choice is None:
        fallback["llm_status"] = "Local LLM answer was not a valid charter type; keyword classifier used."
        return fallback

    return _merge(keyword, choice, charter, settings["model"])
