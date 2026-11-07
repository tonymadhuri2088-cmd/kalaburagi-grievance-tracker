"""The texts of reminders and follow-up messages, in English and Kannada.

Officers always get English. Citizens get their message in the language their complaint was written in.
The Kannada texts should be read by a Kannada speaker before real use.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

IST = timezone(timedelta(hours=5, minutes=30))

# subject -> language -> text. Placeholders: {id} {label} {office} {due} {next_office} {previous}
TEMPLATES: Dict[str, Dict[str, str]] = {
    # To the officer
    "reminder_half": {
        "en": "Reminder: complaint {id} ({label}) at {office} has used half of its time limit. Please act by {due}.",
    },
    "reminder_final": {
        "en": "Final reminder: complaint {id} ({label}) is due by {due}. If it is not resolved, it moves to {next_office}.",
    },
    "reminder_final_last": {
        "en": "Final reminder: complaint {id} ({label}) is due by {due}. It is already with the last level.",
    },
    "escalated_to_you": {
        "en": "Complaint {id} ({label}) has moved to you ({office}): the time limit at {previous} passed.",
    },
    "no_officer": {
        "en": "Complaint {id} ({label}) has no officer at {office}. Please assign someone. It is due by {due}.",
    },
    # To the citizen
    "citizen_registered": {
        "en": "Your complaint {id} ({label}) is registered with {office}. Action is expected by {due}. "
              "Use your complaint ID to see its status.",
        "kn": "ನಿಮ್ಮ ದೂರು {id} ({label}) ಅನ್ನು {office} ಗೆ ನೋಂದಾಯಿಸಲಾಗಿದೆ. {due} ರೊಳಗೆ ಕ್ರಮ ನಿರೀಕ್ಷಿಸಲಾಗಿದೆ. "
              "ಸ್ಥಿತಿ ತಿಳಿಯಲು ನಿಮ್ಮ ದೂರು ಸಂಖ್ಯೆಯನ್ನು ಬಳಸಿ.",
    },
    "citizen_reminded": {
        "en": "Update on complaint {id}: we have reminded {office}. Action is due by {due}.",
        "kn": "ದೂರು {id} ಬಗ್ಗೆ ಮಾಹಿತಿ: {office} ಗೆ ಜ್ಞಾಪನೆ ಕಳುಹಿಸಲಾಗಿದೆ. {due} ರೊಳಗೆ ಕ್ರಮ ಕೈಗೊಳ್ಳಬೇಕು.",
    },
    "citizen_escalated": {
        "en": "Update on complaint {id}: it was not resolved in time and has moved to {office}.",
        "kn": "ದೂರು {id} ಬಗ್ಗೆ ಮಾಹಿತಿ: ನಿಗದಿತ ಸಮಯದಲ್ಲಿ ಪರಿಹಾರವಾಗಿಲ್ಲ, ಆದ್ದರಿಂದ ಅದನ್ನು {office} ಗೆ ಕಳುಹಿಸಲಾಗಿದೆ.",
    },
}


def when_text(moment: Any) -> str:
    """A due time as text for a message, in India time, such as '9 Nov 2026, 5:30 PM'."""
    if not moment:
        return "the time limit"
    parsed = datetime.fromisoformat(moment) if isinstance(moment, str) else moment
    local = parsed.astimezone(IST)
    hour = local.hour % 12 or 12
    return f"{local.day} {local.strftime('%b %Y')}, {hour}:{local.minute:02d} {'AM' if local.hour < 12 else 'PM'}"


def render(subject: str, language: str, **values: Any) -> str:
    """Fill in a template. A language with no text for this subject falls back to English."""
    options = TEMPLATES[subject]
    if language == "kn":
        names = _kannada_names()
        values = {key: (names.get(value, value) if key in NAME_KEYS and isinstance(value, str) else value)
                  for key, value in values.items()}
    return options.get(language, options["en"]).format(**values)


# Values that are office, department or complaint type names. In Kannada text they are replaced by the charter's
# Kannada name when it has one.
NAME_KEYS = ("label", "office", "next_office")


def _kannada_names() -> Dict[str, str]:
    from complaintrouter.common import load_charter  # the charter of the active pack
    return load_charter().get("kannada_names", {})
