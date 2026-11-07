"""Tells Kannada from English in a complaint, so follow-up messages go out in the complainant's language.

This only looks at the script of the letters (Kannada has its own block in Unicode). It does not translate.
A complaint written mostly in Kannada letters is "kn"; everything else is "en". Mixed text counts as Kannada
when at least a third of its letters are Kannada, because then the citizen is comfortable in Kannada.
"""

from typing import Any

KANNADA_FROM = "ಀ"
KANNADA_TO = "೿"
LANGUAGES = {"en": "English", "kn": "Kannada"}


def detect_language(text: Any) -> str:
    """Return 'kn' when the text is mostly Kannada, otherwise 'en'."""
    letters = [char for char in text if char.isalpha()] if isinstance(text, str) else []
    if not letters:
        return "en"
    kannada = sum(1 for char in letters if KANNADA_FROM <= char <= KANNADA_TO)
    return "kn" if kannada / len(letters) >= 1 / 3 else "en"


def language_name(code: Any) -> str:
    return LANGUAGES.get(code if isinstance(code, str) else "", "English")
