"""The WhatsApp bot of the Kalaburagi Grievance Tracker.

A citizen chats with the portal's WhatsApp number. The bot does what the website does, and the WhatsApp number
itself proves who the citizen is (WhatsApp checks the phone), so there is no login:

  1  register a complaint (kind, category, description, place, photos, check, submit)
  2  track a complaint by its ID        3  list my complaints
  4  confirm that a problem is fixed (or say it is not: the complaint then moves up)
  5  a login code for the website       6  switch between English and Kannada

A citizen can also just describe the problem in their own words. With ANTHROPIC_API_KEY set, Claude works out the kind
and category (wa_ai.py), so the bot only asks for what is missing. Without a key, a few keywords decide and the bot
asks the rest. Everything the bot says comes from the fixed texts below, in English or Kannada, never from a model.

The other direction: when the portal sends a follow-up to a citizen who has written to the bot (registered, reminded,
escalated, marked resolved), it is also pushed to their WhatsApp (see deliver()). WhatsApp allows free-form messages
only within 24 hours of the person's last message, so later ones are kept in the portal log only (or sent through an
approved template when the Meta provider has one).

The Kannada texts are a first draft and should be read by a Kannada speaker before real use.
"""

import base64
import json
import threading
import time
import traceback
from collections import OrderedDict, deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

from complaint_portal import messages as texts
from complaint_portal.categories import (
    CIVIC, EMERGENCY, KIND_LABELS, MAX_PHOTO_BYTES, PHOTO_TYPES, PHOTOS_REQUIRED, POLICE, POLICE_NOTICE,
    available_kinds, categories_for, category_label,
)
from complaint_portal.language import detect_language
from complaint_portal.rules import AWAITING, CLOSED, OPEN, STATUS_TEXT
from complaint_portal.whatsapp import Inbound, Media, chunks
from complaint_portal.wa_ai import keyword_understanding
from complaint_portal.workflow import PortalError, iso, utcnow

WINDOW = timedelta(hours=23)      # WhatsApp: free-form replies are allowed for 24 hours after the person's message
STATE_MAX_AGE = timedelta(hours=12)   # a half-finished chat is forgotten after this long without a message
RATE_LIMIT = (20, 60.0)           # at most this many messages from one number per this many seconds
SEEN_LIMIT = 2000
LIST_LIMIT = 6
MIN_COMPLAINT_CHARS = 10
MAX_COMPLAINT_CHARS = 2000

YES = {"1", "yes", "y", "ok", "okay", "yeah", "haan", "ಹೌದು", "submit"}
NO = {"2", "no", "n", "nahi", "ಇಲ್ಲ"}
HOME = {"0", "menu", "cancel", "back", "stop", "ಮೆನು", "ರದ್ದು", "ಹಿಂದೆ"}

KIND_KN = {EMERGENCY: "ತುರ್ತು ಪರಿಸ್ಥಿತಿ", CIVIC: "ತುರ್ತು ಅಲ್ಲ (ದೈನಂದಿನ ನಾಗರಿಕ ಸಮಸ್ಯೆ)", POLICE: "ಪೊಲೀಸ್ ದೂರು"}
CATEGORY_KN = {
    "emergency_rescue": "ತುರ್ತು ರಕ್ಷಣೆ", "fire_smoke": "ಬೆಂಕಿ ಮತ್ತು ಹೊಗೆ", "ambulance_medical": "ಆಂಬ್ಯುಲೆನ್ಸ್ ಮತ್ತು ವೈದ್ಯಕೀಯ ತುರ್ತು",
    "lpg_leak": "ಎಲ್‌ಪಿಜಿ ಗ್ಯಾಸ್ ಸೋರಿಕೆ", "hazardous_gas": "ಅಪಾಯಕಾರಿ ಅನಿಲ ಅಥವಾ ರಾಸಾಯನಿಕ ಸೋರಿಕೆ",
    "flood_rescue": "ಪ್ರವಾಹ ರಕ್ಷಣೆ", "building_collapse": "ಕಟ್ಟಡ ಕುಸಿತ", "electrical_hazard": "ವಿದ್ಯುತ್ ಅಪಾಯ, ಬಿದ್ದ ತಂತಿ",
    "road_accident": "ರಕ್ಷಣೆ ಬೇಕಾದ ರಸ್ತೆ ಅಪಘಾತ", "lift_trapped": "ಲಿಫ್ಟ್‌ನಲ್ಲಿ ಸಿಲುಕಿರುವುದು", "tree_fall": "ಮರ ಬಿದ್ದಿರುವುದು",
    "drowning": "ಮುಳುಗುವಿಕೆ", "landslide": "ಭೂಕುಸಿತ",
    "water_supply": "ನೀರು ಸರಬರಾಜು", "drainage_sewerage": "ಚರಂಡಿ ಮತ್ತು ಒಳಚರಂಡಿ", "garbage_sanitation": "ಕಸ ಮತ್ತು ನೈರ್ಮಲ್ಯ",
    "roads_footpaths": "ರಸ್ತೆ ಮತ್ತು ಪಾದಚಾರಿ ಮಾರ್ಗ", "streetlights": "ಬೀದಿ ದೀಪಗಳು", "flooding_waterlogging": "ಪ್ರವಾಹ ಮತ್ತು ನೀರು ನಿಲ್ಲುವುದು",
    "public_health_strays": "ಸಾರ್ವಜನಿಕ ಆರೋಗ್ಯ ಮತ್ತು ಬೀದಿ ಪ್ರಾಣಿಗಳು", "parks_infrastructure": "ಉದ್ಯಾನ ಮತ್ತು ಸಾರ್ವಜನಿಕ ಸೌಕರ್ಯ",
    "municipal_services_taxes": "ನಗರ ಸೇವೆಗಳು ಮತ್ತು ತೆರಿಗೆ", "other_civic": "ಇತರ ದೂರುಗಳು",
    "cybercrime": "ಸೈಬರ್ ಅಪರಾಧ ಮತ್ತು ಆನ್‌ಲೈನ್ ವಂಚನೆ", "financial_fraud": "ಆರ್ಥಿಕ ವಂಚನೆ", "lost_property": "ಕಳೆದುಹೋದ ವಸ್ತು",
    "traffic_safety": "ಸಾರ್ವಜನಿಕ ಸುರಕ್ಷತೆ ಮತ್ತು ಸಂಚಾರ", "complaint_individuals": "ವ್ಯಕ್ತಿಗಳ ವಿರುದ್ಧ ದೂರು",
}
POLICE_NOTICE_KN = ("ಈ ವ್ಯವಸ್ಥೆ ನಿಮ್ಮ ದೂರನ್ನು ನೋಂದಾಯಿಸಿ ಟ್ರ್ಯಾಕ್ ಮಾತ್ರ ಮಾಡುತ್ತದೆ. ಅಪರಾಧ ನಡೆದಿದೆಯೇ ಮತ್ತು FIR ದಾಖಲಿಸಬೇಕೇ "
                    "ಎಂಬುದನ್ನು ಅಧಿಕೃತ ಪೊಲೀಸ್ ಅಧಿಕಾರಿಗಳು ಮಾತ್ರ ನಿರ್ಧರಿಸುತ್ತಾರೆ.")
STATUS_KN = {OPEN: "ತೆರೆದಿದೆ. ಕ್ರಮ ನಡೆಯುತ್ತಿದೆ.",
             AWAITING: "ಪರಿಹಾರವಾಗಿದೆ ಎಂದು ಗುರುತಿಸಲಾಗಿದೆ. ನಿಮ್ಮ ದೃಢೀಕರಣಕ್ಕಾಗಿ ಕಾಯುತ್ತಿದೆ.",
             CLOSED: "ಮುಚ್ಚಲಾಗಿದೆ. ಸಮಸ್ಯೆ ಸರಿಯಾಗಿದೆ ಎಂದು ನೀವು ದೃಢೀಕರಿಸಿದ್ದೀರಿ."}

S: Dict[str, Dict[str, str]] = {
    "menu": {
        "en": ("*Kalaburagi Grievance Tracker*\nReply with a number:\n"
               "1 - Register a complaint\n2 - Track a complaint\n3 - My complaints\n"
               "4 - Tell us a problem is fixed\n5 - Login code for the website\n6 - ಕನ್ನಡ\n\n"
               "Or just write your problem in your own words. Send *0* any time to come back to this menu.\n"
               "_Student demo with invented data. Not an official government service._"),
        "kn": ("*ಕಲಬುರಗಿ ದೂರು ಟ್ರ್ಯಾಕರ್*\nಒಂದು ಸಂಖ್ಯೆಯೊಂದಿಗೆ ಉತ್ತರಿಸಿ:\n"
               "1 - ದೂರು ನೋಂದಾಯಿಸಿ\n2 - ದೂರಿನ ಸ್ಥಿತಿ ನೋಡಿ\n3 - ನನ್ನ ದೂರುಗಳು\n"
               "4 - ಸಮಸ್ಯೆ ಪರಿಹಾರವಾಗಿದೆ ಎಂದು ತಿಳಿಸಿ\n5 - ವೆಬ್‌ಸೈಟ್‌ಗೆ ಲಾಗಿನ್ ಕೋಡ್\n6 - English\n\n"
               "ಅಥವಾ ನಿಮ್ಮ ಸಮಸ್ಯೆಯನ್ನು ನಿಮ್ಮ ಮಾತಿನಲ್ಲೇ ಬರೆಯಿರಿ. ಈ ಮೆನುಗೆ ಮರಳಲು ಯಾವಾಗ ಬೇಕಾದರೂ *0* ಕಳುಹಿಸಿ.\n"
               "_ಕಾಲ್ಪನಿಕ ಮಾಹಿತಿಯ ವಿದ್ಯಾರ್ಥಿ ಡೆಮೊ. ಇದು ಅಧಿಕೃತ ಸರ್ಕಾರಿ ಸೇವೆ ಅಲ್ಲ._"),
    },
    "send_text_first": {
        "en": "Thank you. To register a complaint, first write what the problem is (or send 1). I will ask for photos at the end.",
        "kn": "ಧನ್ಯವಾದಗಳು. ದೂರು ನೋಂದಾಯಿಸಲು ಮೊದಲು ಸಮಸ್ಯೆ ಏನೆಂದು ಬರೆಯಿರಿ (ಅಥವಾ 1 ಕಳುಹಿಸಿ). ಕೊನೆಯಲ್ಲಿ ಫೋಟೋ ಕೇಳುತ್ತೇನೆ."},
    "cancelled": {"en": "Cancelled.", "kn": "ರದ್ದುಪಡಿಸಲಾಗಿದೆ."},
    "unclear": {"en": "I did not understand that. Here is the menu.", "kn": "ಅದು ನನಗೆ ಅರ್ಥವಾಗಲಿಲ್ಲ. ಇಗೋ ಮೆನು."},
    "oops": {"en": "Something went wrong on our side. Please try again. Send 0 for the menu.",
             "kn": "ನಮ್ಮ ಕಡೆ ಏನೋ ತೊಂದರೆಯಾಯಿತು. ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ. ಮೆನುಗಾಗಿ 0 ಕಳುಹಿಸಿ."},
    "language_set": {"en": "Language set to English.", "kn": "ಭಾಷೆಯನ್ನು ಕನ್ನಡಕ್ಕೆ ಬದಲಿಸಲಾಗಿದೆ."},
    # sign-up
    "need_account": {
        "en": "To register a complaint I need a few details about you first. This takes four short questions.\nWhat is your name?",
        "kn": "ದೂರು ನೋಂದಾಯಿಸಲು ಮೊದಲು ನಿಮ್ಮ ಬಗ್ಗೆ ಕೆಲವು ವಿವರಗಳು ಬೇಕು. ನಾಲ್ಕು ಸಣ್ಣ ಪ್ರಶ್ನೆಗಳು.\nನಿಮ್ಮ ಹೆಸರೇನು?"},
    "bad_name": {"en": "Please send your name (2 to 100 letters).", "kn": "ದಯವಿಟ್ಟು ನಿಮ್ಮ ಹೆಸರು ಕಳುಹಿಸಿ (2 ರಿಂದ 100 ಅಕ್ಷರಗಳು)."},
    "ask_taluk": {"en": "Thank you, {name}. Which taluk do you live in? Reply with a number:\n{list}",
                  "kn": "ಧನ್ಯವಾದಗಳು, {name}. ನೀವು ಯಾವ ತಾಲ್ಲೂಕಿನಲ್ಲಿ ವಾಸಿಸುತ್ತೀರಿ? ಸಂಖ್ಯೆಯೊಂದಿಗೆ ಉತ್ತರಿಸಿ:\n{list}"},
    "bad_choice": {"en": "Please reply with one of the numbers shown.", "kn": "ದಯವಿಟ್ಟು ತೋರಿಸಿರುವ ಸಂಖ್ಯೆಗಳಲ್ಲಿ ಒಂದನ್ನು ಕಳುಹಿಸಿ."},
    "ask_ward": {"en": "Which ward do you live in? Send the ward number ({low} to {high}).",
                 "kn": "ನೀವು ಯಾವ ವಾರ್ಡ್‌ನಲ್ಲಿ ವಾಸಿಸುತ್ತೀರಿ? ವಾರ್ಡ್ ಸಂಖ್ಯೆ ಕಳುಹಿಸಿ ({low} ರಿಂದ {high})."},
    "bad_ward": {"en": "That ward number is not in this taluk. Send a number from {low} to {high}.",
                 "kn": "ಆ ವಾರ್ಡ್ ಸಂಖ್ಯೆ ಈ ತಾಲ್ಲೂಕಿನಲ್ಲಿಲ್ಲ. {low} ರಿಂದ {high} ರ ನಡುವಿನ ಸಂಖ್ಯೆ ಕಳುಹಿಸಿ."},
    "ask_home": {"en": "Last one: your home address, with street and area (at least 10 characters).",
                 "kn": "ಕೊನೆಯದು: ನಿಮ್ಮ ಮನೆ ವಿಳಾಸ, ರಸ್ತೆ ಮತ್ತು ಪ್ರದೇಶದೊಂದಿಗೆ (ಕನಿಷ್ಠ 10 ಅಕ್ಷರಗಳು)."},
    "bad_address": {"en": "Please give the address in more detail, with street and area (10 to 300 characters).",
                    "kn": "ದಯವಿಟ್ಟು ವಿಳಾಸವನ್ನು ರಸ್ತೆ ಮತ್ತು ಪ್ರದೇಶದೊಂದಿಗೆ ವಿವರವಾಗಿ ನೀಡಿ (10 ರಿಂದ 300 ಅಕ್ಷರಗಳು)."},
    "account_ready": {"en": "Thank you, you are set up.", "kn": "ಧನ್ಯವಾದಗಳು, ನಿಮ್ಮ ಖಾತೆ ಸಿದ್ಧವಾಗಿದೆ."},
    # registering a complaint
    "ask_kind": {"en": "What kind of complaint is it? Reply with a number:\n{list}",
                 "kn": "ಇದು ಯಾವ ರೀತಿಯ ದೂರು? ಸಂಖ್ಯೆಯೊಂದಿಗೆ ಉತ್ತರಿಸಿ:\n{list}"},
    "ask_category": {"en": "Which type? Reply with a number:\n{list}", "kn": "ಯಾವ ಪ್ರಕಾರ? ಸಂಖ್ಯೆಯೊಂದಿಗೆ ಉತ್ತರಿಸಿ:\n{list}"},
    "emergency_note": {"en": "If anyone is in danger right now, call *112* first. This service cannot send help instantly.",
                       "kn": "ಈಗ ಯಾರಾದರೂ ಅಪಾಯದಲ್ಲಿದ್ದರೆ ಮೊದಲು *112* ಗೆ ಕರೆ ಮಾಡಿ. ಈ ಸೇವೆ ತಕ್ಷಣ ಸಹಾಯ ಕಳುಹಿಸಲು ಸಾಧ್ಯವಿಲ್ಲ."},
    "ask_text": {"en": "Describe the problem in a few words (at least 10 characters).",
                 "kn": "ಸಮಸ್ಯೆಯನ್ನು ಕೆಲವು ಮಾತುಗಳಲ್ಲಿ ವಿವರಿಸಿ (ಕನಿಷ್ಠ 10 ಅಕ್ಷರಗಳು)."},
    "bad_text": {"en": "Please describe the problem in 10 to 2000 characters.",
                 "kn": "ದಯವಿಟ್ಟು ಸಮಸ್ಯೆಯನ್ನು 10 ರಿಂದ 2000 ಅಕ್ಷರಗಳಲ್ಲಿ ವಿವರಿಸಿ."},
    "ask_place": {"en": "Where is the problem? Send the street and area, or share a location pin. "
                        "Send *same* to use your home address.",
                  "kn": "ಸಮಸ್ಯೆ ಎಲ್ಲಿದೆ? ರಸ್ತೆ ಮತ್ತು ಪ್ರದೇಶ ಕಳುಹಿಸಿ ಅಥವಾ ಲೊಕೇಶನ್ ಪಿನ್ ಹಂಚಿಕೊಳ್ಳಿ. ನಿಮ್ಮ ಮನೆ ವಿಳಾಸಕ್ಕಾಗಿ *same* ಕಳುಹಿಸಿ."},
    "ask_photos_civic": {"en": "Photos are optional. You may send up to {n} photos of the problem. Send *done* when finished, or *skip* to go without. "
                               "({have} of {n} received)",
                         "kn": "ಫೋಟೋಗಳು ಐಚ್ಛಿಕ. ನೀವು ಸಮಸ್ಯೆಯ {n} ವರೆಗೆ ಫೋಟೋ ಕಳುಹಿಸಬಹುದು. ಮುಗಿದ ನಂತರ *done*, ಬೇಡವಾದರೆ *skip* ಕಳುಹಿಸಿ. ({have}/{n} ಬಂದಿವೆ)"},
    "ask_photos_police": {"en": "You may send up to {n} photos or PDF documents. Send *done* when finished, or *skip* to go without. "
                               "({have} of {n} received)",
                          "kn": "ನೀವು {n} ವರೆಗೆ ಫೋಟೋ ಅಥವಾ PDF ದಾಖಲೆಗಳನ್ನು ಕಳುಹಿಸಬಹುದು. ಮುಗಿದ ನಂತರ *done*, ಬೇಡವಾದರೆ *skip* ಕಳುಹಿಸಿ. ({have}/{n} ಬಂದಿವೆ)"},
    "photo_got": {"en": "Got it ({have} of {n}).", "kn": "ಬಂದಿದೆ ({have}/{n})."},
    "photo_need": {"en": "I still need {left} more photo(s).", "kn": "ಇನ್ನೂ {left} ಫೋಟೋ ಬೇಕು."},
    "photo_bad": {"en": "I could not use that file. Photos must be JPEG, PNG or WebP pictures (documents: PDF), under 4 MB.",
                  "kn": "ಆ ಫೈಲ್ ಬಳಸಲು ಆಗಲಿಲ್ಲ. ಫೋಟೋಗಳು JPEG, PNG ಅಥವಾ WebP ಆಗಿರಬೇಕು (ದಾಖಲೆಗಳು: PDF), 4 MB ಒಳಗೆ."},
    "photo_wait": {"en": "Please send a photo (or *0* to cancel).", "kn": "ದಯವಿಟ್ಟು ಫೋಟೋ ಕಳುಹಿಸಿ (ಅಥವಾ ರದ್ದುಪಡಿಸಲು *0*)."},
    "check": {"en": "Please check your complaint:\nKind: {kind}\nType: {category}\nProblem: {text}\nPlace: {place}\nFiles: {files}\n\n"
                    "Reply *1* to submit or *2* to cancel.",
              "kn": "ದಯವಿಟ್ಟು ನಿಮ್ಮ ದೂರನ್ನು ಪರಿಶೀಲಿಸಿ:\nರೀತಿ: {kind}\nಪ್ರಕಾರ: {category}\nಸಮಸ್ಯೆ: {text}\nಸ್ಥಳ: {place}\nಫೈಲ್‌ಗಳು: {files}\n\n"
                    "ಸಲ್ಲಿಸಲು *1*, ರದ್ದುಪಡಿಸಲು *2* ಕಳುಹಿಸಿ."},
    "registered": {"en": "Complaint registered.\nID: *{id}*\nType: {label}\nSent to: {office}\nAction expected by: {due}\n"
                         "I will message you here at each step. Send the ID any time to see the status.",
                   "kn": "ದೂರು ನೋಂದಾಯಿಸಲಾಗಿದೆ.\nಸಂಖ್ಯೆ: *{id}*\nಪ್ರಕಾರ: {label}\nಕಳುಹಿಸಿದ ಕಚೇರಿ: {office}\nಕ್ರಮ ನಿರೀಕ್ಷಿತ ಸಮಯ: {due}\n"
                         "ಪ್ರತಿ ಹಂತದಲ್ಲೂ ನಾನು ಇಲ್ಲೇ ಸಂದೇಶ ಕಳುಹಿಸುತ್ತೇನೆ. ಸ್ಥಿತಿ ತಿಳಿಯಲು ಯಾವಾಗ ಬೇಕಾದರೂ ದೂರು ಸಂಖ್ಯೆ ಕಳುಹಿಸಿ."},
    "files_none": {"en": "none", "kn": "ಇಲ್ಲ"},
    "files_n": {"en": "{n} attached", "kn": "{n} ಲಗತ್ತಿಸಲಾಗಿದೆ"},
    # tracking
    "ask_id": {"en": "Send your complaint ID (it looks like CMP-20261110-1234).",
               "kn": "ನಿಮ್ಮ ದೂರು ಸಂಖ್ಯೆ ಕಳುಹಿಸಿ (ಉದಾ. CMP-20261110-1234)."},
    "no_such": {"en": "I could not find a complaint with that ID for this mobile number. Check the ID, or send 3 to see your complaints.",
                "kn": "ಈ ಮೊಬೈಲ್ ಸಂಖ್ಯೆಗೆ ಆ ಸಂಖ್ಯೆಯ ದೂರು ಸಿಗಲಿಲ್ಲ. ಸಂಖ್ಯೆ ಪರಿಶೀಲಿಸಿ, ಅಥವಾ ನಿಮ್ಮ ದೂರುಗಳನ್ನು ನೋಡಲು 3 ಕಳುಹಿಸಿ."},
    "track": {"en": "*{id}* - {label}\nStatus: {status}\nWith: {office}\n{due}Latest update (in English): {latest}",
              "kn": "*{id}* - {label}\nಸ್ಥಿತಿ: {status}\nಈಗ ಇರುವ ಕಚೇರಿ: {office}\n{due}ಇತ್ತೀಚಿನ ಮಾಹಿತಿ (ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿ): {latest}"},
    "due": {"en": "Action due by: {due}\n", "kn": "ಕ್ರಮ ಕೈಗೊಳ್ಳಬೇಕಾದ ಸಮಯ: {due}\n"},
    "list_head": {"en": "Your complaints (newest first):\n{list}\n\nSend a number to see one, or 0 for the menu.",
                  "kn": "ನಿಮ್ಮ ದೂರುಗಳು (ಹೊಸದು ಮೊದಲು):\n{list}\n\nಒಂದನ್ನು ನೋಡಲು ಸಂಖ್ಯೆ ಕಳುಹಿಸಿ, ಮೆನುಗಾಗಿ 0."},
    "list_none": {"en": "You have no complaints yet. Send 1 to register one.", "kn": "ನಿಮಗೆ ಇನ್ನೂ ಯಾವ ದೂರೂ ಇಲ್ಲ. ನೋಂದಾಯಿಸಲು 1 ಕಳುಹಿಸಿ."},
    # confirming a fix
    "fix_none": {"en": "No complaint of yours is waiting for your confirmation right now.",
                 "kn": "ಈಗ ನಿಮ್ಮ ಯಾವ ದೂರೂ ನಿಮ್ಮ ದೃಢೀಕರಣಕ್ಕಾಗಿ ಕಾಯುತ್ತಿಲ್ಲ."},
    "fix_pick": {"en": "Which complaint? Reply with a number:\n{list}", "kn": "ಯಾವ ದೂರು? ಸಂಖ್ಯೆಯೊಂದಿಗೆ ಉತ್ತರಿಸಿ:\n{list}"},
    "fix_ask": {"en": "*{id}* ({label}) was marked resolved. Is the problem fixed?\n1 - Yes, it is fixed\n2 - No, it is not fixed",
                "kn": "*{id}* ({label}) ಪರಿಹಾರವಾಗಿದೆ ಎಂದು ಗುರುತಿಸಲಾಗಿದೆ. ಸಮಸ್ಯೆ ಸರಿಯಾಗಿದೆಯೇ?\n1 - ಹೌದು, ಸರಿಯಾಗಿದೆ\n2 - ಇಲ್ಲ, ಸರಿಯಾಗಿಲ್ಲ"},
    "fix_code_shown": {"en": "Thank you. To close the complaint, reply with this code: *{code}* (valid {minutes} minutes).",
                       "kn": "ಧನ್ಯವಾದಗಳು. ದೂರನ್ನು ಮುಚ್ಚಲು ಈ ಕೋಡ್‌ನೊಂದಿಗೆ ಉತ್ತರಿಸಿ: *{code}* ({minutes} ನಿಮಿಷ ಮಾನ್ಯ)."},
    "fix_code_sent": {"en": "Thank you. {note} Reply with the 6-digit code to close the complaint.",
                      "kn": "ಧನ್ಯವಾದಗಳು. {note} ದೂರನ್ನು ಮುಚ್ಚಲು 6 ಅಂಕಿಯ ಕೋಡ್‌ನೊಂದಿಗೆ ಉತ್ತರಿಸಿ."},
    "fix_closed": {"en": "Complaint {id} is closed. Thank you for confirming.", "kn": "ದೂರು {id} ಮುಚ್ಚಲಾಗಿದೆ. ದೃಢೀಕರಿಸಿದ್ದಕ್ಕೆ ಧನ್ಯವಾದಗಳು."},
    "fix_escalated": {"en": "Sorry the problem is not fixed. Complaint {id} is with {office} now.",
                      "kn": "ಸಮಸ್ಯೆ ಸರಿಯಾಗಿಲ್ಲದ್ದಕ್ಕೆ ಕ್ಷಮಿಸಿ. ದೂರು {id} ಈಗ {office} ಬಳಿ ಇದೆ."},
    "code_bad": {"en": "Send the 6-digit code, or 0 to cancel.", "kn": "6 ಅಂಕಿಯ ಕೋಡ್ ಕಳುಹಿಸಿ, ಅಥವಾ ರದ್ದುಪಡಿಸಲು 0."},
    # website login code
    "login_code": {"en": "Your website login code is *{code}*. It lasts {minutes} minutes. Do not share it.",
                   "kn": "ನಿಮ್ಮ ವೆಬ್‌ಸೈಟ್ ಲಾಗಿನ್ ಕೋಡ್ *{code}*. ಇದು {minutes} ನಿಮಿಷ ಮಾನ್ಯ. ಯಾರೊಂದಿಗೂ ಹಂಚಿಕೊಳ್ಳಬೇಡಿ."},
    "login_sent": {"en": "{note}", "kn": "{note}"},
    "login_need": {"en": "You have no account yet. Send 1 to register a complaint, and I will set up your account.",
                   "kn": "ನಿಮಗೆ ಇನ್ನೂ ಖಾತೆ ಇಲ್ಲ. ದೂರು ನೋಂದಾಯಿಸಲು 1 ಕಳುಹಿಸಿ, ನಿಮ್ಮ ಖಾತೆಯನ್ನು ನಾನು ಸಿದ್ಧಪಡಿಸುತ್ತೇನೆ."},
}


def T(key: str, lang: str, **values: Any) -> str:
    options = S[key]
    return options.get(lang, options["en"]).format(**values)


def kind_label(kind: str, lang: str) -> str:
    return KIND_KN[kind] if lang == "kn" else KIND_LABELS[kind]


def cat_label(kind: str, key: str, lang: str) -> str:
    return CATEGORY_KN.get(key, category_label(kind, key)) if lang == "kn" else category_label(kind, key)


def _numbered(items: List[str]) -> str:
    return "\n".join(f"{number} - {item}" for number, item in enumerate(items, start=1))


def _number(text: str) -> Optional[int]:
    text = text.strip()
    return int(text) if text.isdigit() and len(text) < 6 else None


class Chat:
    """One incoming message being handled: who, their language, their saved place in a conversation, and the replies."""

    def __init__(self, mobile: str, lang: str, state: Dict[str, Any], now: datetime) -> None:
        self.mobile, self.lang, self.state, self.now = mobile, lang, state, now
        self.replies: List[str] = []

    def say(self, key: str, **values: Any) -> None:
        self.replies.append(T(key, self.lang, **values))

    @property
    def step(self) -> Optional[str]:
        return self.state.get("step")

    @property
    def data(self) -> Dict[str, Any]:
        return self.state.setdefault("d", {})

    def go(self, step: Optional[str]) -> None:
        self.state["step"] = step


class WhatsAppBot:
    """Handles one citizen message at a time (process) and pushes portal messages to WhatsApp (deliver)."""

    def __init__(self, portal: Any, channel: Any, understanding: Any = None, clock=utcnow,
                 background: bool = True) -> None:
        self.portal = portal
        self.channel = channel
        self.understanding = understanding
        self.clock = clock
        self.background = background
        self._locks: Dict[str, threading.Lock] = {}
        self._guard = threading.Lock()
        self._seen: "OrderedDict[str, bool]" = OrderedDict()
        self._recent: Dict[str, Deque[float]] = {}

    # ------------------------------------------------------------------ entry points

    def handle_async(self, messages: List[Inbound]) -> None:
        """Answer in the background, so the provider's webhook gets its 200 at once."""
        def work() -> None:
            for message in messages:
                try:
                    for reply in self.process(message):
                        sent, detail = self.channel.send_text(message.mobile, reply)
                        if not sent:
                            print(f"WhatsApp reply failed: {detail}")
                except Exception:
                    traceback.print_exc()
        threading.Thread(target=work, daemon=True).start()

    def process(self, message: Inbound) -> List[str]:
        """Work out the replies to one message. Safe to call from several threads."""
        with self._lock_for(message.mobile):
            if self._duplicate(message.message_id) or self._too_fast(message.mobile):
                return []
            now = self.clock()
            store = self.portal.store
            contact = store.wa_touch(message.mobile, iso(now), detect_language(message.text))
            try:
                state = json.loads(contact["state"] or "{}")
            except ValueError:
                state = {}
            # A conversation left alone for a long time starts again from the menu.
            last = state.get("at")
            if last and now - datetime.fromisoformat(last) > STATE_MAX_AGE:
                self._clear_files(state)
                state = {}
            chat = Chat(message.mobile, contact["language"], state, now)
            try:
                self._dispatch(chat, message)
            except PortalError as error:
                chat.replies.append(error.message)
            except Exception:
                traceback.print_exc()
                self._clear_files(chat.state)
                chat.state = {}
                chat.say("oops")
            chat.state["at"] = iso(now)
            store.wa_save(message.mobile, chat.lang, json.dumps(chat.state))
            return chat.replies

    def deliver(self, mobile: str, text: str) -> str:
        """Push a portal message to this citizen's WhatsApp. Returns "whatsapp" if one is on its way, else "portal"."""
        contact = self.portal.store.wa_get(mobile)
        if not contact:
            return "portal"
        inside = self.clock() - datetime.fromisoformat(contact["last_inbound"]) < WINDOW
        templated = hasattr(self.channel, "send_update_template") and bool(getattr(self.channel, "update_template", ""))
        if not inside and not templated:
            return "portal"

        def send() -> None:
            if inside:
                sent, detail = self.channel.send_text(mobile, text)
            else:
                sent, detail = self.channel.send_update_template(mobile, text)
            if not sent:
                print(f"WhatsApp push to {mobile[:2]}XXXXXX{mobile[-2:]} failed: {detail}")

        if self.background:
            threading.Thread(target=send, daemon=True).start()
        else:
            send()
        return "whatsapp"

    # ------------------------------------------------------------------ guards

    def _lock_for(self, mobile: str) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(mobile, threading.Lock())

    def _duplicate(self, message_id: str) -> bool:
        """Providers repeat a message when we are slow. Each ID is handled once."""
        if not message_id:
            return False
        with self._guard:
            if message_id in self._seen:
                return True
            self._seen[message_id] = True
            while len(self._seen) > SEEN_LIMIT:
                self._seen.popitem(last=False)
        return False

    def _too_fast(self, mobile: str) -> bool:
        limit, seconds = RATE_LIMIT
        now = time.monotonic()
        with self._guard:
            queue = self._recent.setdefault(mobile, deque())
            while queue and now - queue[0] > seconds:
                queue.popleft()
            if len(queue) >= limit:
                return True
            queue.append(now)
        return False

    # ------------------------------------------------------------------ conversation

    def _dispatch(self, chat: Chat, message: Inbound) -> None:
        text = message.text.strip()
        low = text.lower()
        if low in HOME and not message.media:
            was_busy = chat.step is not None
            self._clear_files(chat.state)
            chat.state = {}
            if was_busy and low not in ("0", "menu", "ಮೆನು"):
                chat.say("cancelled")
            chat.say("menu")
            return
        step = chat.step
        if step:
            handler = getattr(self, f"_step_{step}", None)
            if handler is None:
                chat.state = {}
                chat.say("menu")
                return
            handler(chat, message)
            return
        self._idle(chat, message)

    def _idle(self, chat: Chat, message: Inbound) -> None:
        text = message.text.strip()
        number = _number(text)
        if message.media or message.location:
            # A photo or pin with no complaint open: it would be lost, so say how to start.
            chat.say("send_text_first")
            return
        if number is not None and 1 <= number <= 6:
            {1: lambda: self._start_registration(chat, {}), 2: lambda: self._ask_for_id(chat),
             3: lambda: self._show_list(chat), 4: lambda: self._start_fix(chat),
             5: lambda: self._send_login_code(chat), 6: lambda: self._toggle_language(chat)}[number]()
            return
        answer = None
        if self.understanding is not None:
            answer = self.understanding.understand(text, "no conversation open")
        if answer is None:
            answer = keyword_understanding(text)
        if answer.get("language") in ("en", "kn") and answer["intent"] != "show_menu":
            chat.lang = answer["language"]
        intent = answer["intent"]
        if intent == "register_complaint":
            chat.lang = answer.get("language") or chat.lang
            self._start_registration(chat, {"text": text, "kind": answer.get("kind"), "category": answer.get("category")})
        elif intent == "track_complaint":
            if answer.get("complaint_id"):
                self._show_one(chat, answer["complaint_id"])
            else:
                self._ask_for_id(chat)
        elif intent == "my_complaints":
            self._show_list(chat)
        elif intent == "confirm_fix":
            self._start_fix(chat)
        elif intent == "login_code":
            self._send_login_code(chat)
        elif intent == "change_language":
            wanted = "kn" if "ಕನ್ನಡ" in text or "kannada" in text.lower() else "en" if "english" in text.lower() else None
            if wanted:
                chat.lang = wanted
                chat.say("language_set")
                chat.say("menu")
            else:
                self._toggle_language(chat)
        elif intent == "show_menu":
            chat.say("menu")
        else:
            chat.say("unclear")
            chat.say("menu")

    def _toggle_language(self, chat: Chat) -> None:
        chat.lang = "en" if chat.lang == "kn" else "kn"
        chat.say("language_set")
        chat.say("menu")

    # ---- sign-up (only for someone who has no account yet)

    def _citizen(self, chat: Chat) -> Optional[Dict[str, Any]]:
        return self.portal.store.get_citizen(chat.mobile)

    def _step_signup_name(self, chat: Chat, message: Inbound) -> None:
        name = " ".join(message.text.split())
        if not 2 <= len(name) <= 100:
            chat.say("bad_name")
            return
        chat.data["name"] = name
        zones = self.portal.locations.tree()["zones"]
        names = texts._kannada_names() if chat.lang == "kn" else {}
        chat.say("ask_taluk", name=name.split(" ")[0],
                 list=_numbered([names.get(zone["name"], zone["name"]) for zone in zones]))
        chat.go("signup_taluk")

    def _step_signup_taluk(self, chat: Chat, message: Inbound) -> None:
        zones = self.portal.locations.tree()["zones"]
        number = _number(message.text)
        if number is None or not 1 <= number <= len(zones):
            chat.say("bad_choice")
            return
        zone = zones[number - 1]
        wards = [ward["number"] for ward in zone["wards"]]
        chat.data["zone"] = zone["number"]
        if len(wards) == 1:
            chat.data["ward"] = wards[0]
            chat.say("ask_home")
            chat.go("signup_home")
        else:
            chat.say("ask_ward", low=min(wards), high=max(wards))
            chat.go("signup_ward")

    def _step_signup_ward(self, chat: Chat, message: Inbound) -> None:
        zone = next(item for item in self.portal.locations.tree()["zones"] if item["number"] == chat.data["zone"])
        wards = [ward["number"] for ward in zone["wards"]]
        number = _number(message.text)
        if number is None or number not in wards:
            chat.say("bad_ward", low=min(wards), high=max(wards))
            return
        chat.data["ward"] = number
        chat.say("ask_home")
        chat.go("signup_home")

    def _step_signup_home(self, chat: Chat, message: Inbound) -> None:
        address = " ".join(message.text.split())
        if not 10 <= len(address) <= 300:
            chat.say("bad_address")
            return
        self.portal.sign_up_citizen(chat.data["name"], chat.mobile, address, chat.data["ward"], now=chat.now)
        chat.say("account_ready")
        chat.data.pop("name", None), chat.data.pop("zone", None), chat.data.pop("ward", None)
        chat.data.pop("after", None)
        chat.go(None)
        self._advance_registration(chat)

    # ---- registering a complaint

    def _start_registration(self, chat: Chat, prefill: Dict[str, Any]) -> None:
        chat.state = {"d": {key: value for key, value in prefill.items() if value}}
        written = chat.data.get("text")
        if written is not None:
            written = " ".join(written.split())[:MAX_COMPLAINT_CHARS]
            if len(written) < MIN_COMPLAINT_CHARS:
                chat.data.pop("text")
            else:
                chat.data["text"] = written
        if self._citizen(chat) is None:
            chat.data["after"] = "register"
            chat.say("need_account")
            chat.go("signup_name")
            return
        self._advance_registration(chat)

    def _advance_registration(self, chat: Chat) -> None:
        """Ask for the next thing the complaint still needs."""
        data = chat.data
        kinds = list(available_kinds())
        if data.get("kind") not in kinds:
            data.pop("kind", None)
            data.pop("category", None)
        if "kind" not in data:
            chat.say("ask_kind", list=_numbered([kind_label(kind, chat.lang) for kind in kinds]))
            chat.go("reg_kind")
            return
        kind = data["kind"]
        keys = [key for key, _ in categories_for(kind)]
        if data.get("category") not in keys:
            data.pop("category", None)
        if "category" not in data:
            if kind == EMERGENCY:
                chat.say("emergency_note")
            if kind == POLICE:
                chat.replies.append(POLICE_NOTICE_KN if chat.lang == "kn" else POLICE_NOTICE)
            chat.say("ask_category", list=_numbered([cat_label(kind, key, chat.lang) for key in keys]))
            chat.go("reg_category")
            return
        if "text" not in data:
            chat.say("ask_text")
            chat.go("reg_text")
            return
        if "place" not in data:
            chat.say("ask_place")
            chat.go("reg_place")
            return
        photos = data.get("photos", [])
        if kind == CIVIC and not data.get("photos_done"):
            chat.say("ask_photos_civic", n=PHOTOS_REQUIRED, have=len(photos))
            chat.go("reg_photos")
            return
        if kind == POLICE and not data.get("photos_done"):
            chat.say("ask_photos_police", n=PHOTOS_REQUIRED, have=len(photos))
            chat.go("reg_photos")
            return
        files = len(data.get("photos", []))
        chat.say("check", kind=kind_label(kind, chat.lang), category=cat_label(kind, data["category"], chat.lang),
                 text=self._short(data["text"]), place=self._short(data["place"], 120),
                 files=T("files_n", chat.lang, n=files) if files else T("files_none", chat.lang))
        chat.go("reg_check")

    @staticmethod
    def _short(text: str, limit: int = 300) -> str:
        text = " ".join(text.split())
        return text if len(text) <= limit else text[: limit - 1] + "…"

    def _step_reg_kind(self, chat: Chat, message: Inbound) -> None:
        kinds = list(available_kinds())
        number = _number(message.text)
        if number is None or not 1 <= number <= len(kinds):
            chat.say("bad_choice")
            return
        chat.data["kind"] = kinds[number - 1]
        chat.data.pop("category", None)
        self._advance_registration(chat)

    def _step_reg_category(self, chat: Chat, message: Inbound) -> None:
        keys = [key for key, _ in categories_for(chat.data["kind"])]
        number = _number(message.text)
        if number is None or not 1 <= number <= len(keys):
            chat.say("bad_choice")
            return
        chat.data["category"] = keys[number - 1]
        self._advance_registration(chat)

    def _step_reg_text(self, chat: Chat, message: Inbound) -> None:
        text = " ".join(message.text.split())
        if not MIN_COMPLAINT_CHARS <= len(text) <= MAX_COMPLAINT_CHARS:
            chat.say("bad_text")
            return
        chat.data["text"] = text
        self._advance_registration(chat)

    @staticmethod
    def _place_from_pin(location: Tuple[float, float, str]) -> str:
        latitude, longitude, label = location
        base = f"Pinned location {latitude:.5f}, {longitude:.5f}"
        return f"{label.strip()[:150]} ({base})" if label.strip() else base

    def _step_reg_place(self, chat: Chat, message: Inbound) -> None:
        if message.location:
            chat.data["place"] = self._place_from_pin(message.location)
        elif message.text.strip().lower() in ("same", "home", "ಅದೇ", "ಮನೆ"):
            citizen = self._citizen(chat)
            chat.data["place"] = citizen["address"] if citizen else ""
        else:
            place = " ".join(message.text.split())
            if not 10 <= len(place) <= 300:
                chat.say("bad_address")
                return
            chat.data["place"] = place
        self._advance_registration(chat)

    def _step_reg_photos(self, chat: Chat, message: Inbound) -> None:
        data = chat.data
        kind = data["kind"]
        photos = data.setdefault("photos", [])
        if message.media:
            for item in message.media:
                if len(photos) >= PHOTOS_REQUIRED:
                    break
                saved = self._save_media(chat.mobile, item, len(photos))
                if saved is None:
                    chat.say("photo_bad")
                    continue
                photos.append(saved)
                chat.say("photo_got", have=len(photos), n=PHOTOS_REQUIRED)
            if len(photos) >= PHOTOS_REQUIRED:
                data["photos_done"] = True
                self._advance_registration(chat)
            return
        word = message.text.strip().lower()
        if kind in (CIVIC, POLICE) and word in ("done", "skip", "no", "ಮುಗಿದಿದೆ", "ಬೇಡ"):
            data["photos_done"] = True
            self._advance_registration(chat)
            return
        chat.say("photo_wait")

    def _step_reg_check(self, chat: Chat, message: Inbound) -> None:
        word = message.text.strip().lower()
        if word in NO:
            self._clear_files(chat.state)
            chat.state = {}
            chat.say("cancelled")
            chat.say("menu")
            return
        if word not in YES:
            chat.say("bad_choice")
            return
        data = chat.data
        citizen = self._citizen(chat)
        urls = []
        for name, mime in data.get("photos", []):
            raw = self._temp_folder() / name
            urls.append(f"data:{mime};base64," + base64.b64encode(raw.read_bytes()).decode("ascii"))
        with self.portal.muted():
            try:
                view = self.portal.register(
                    citizen["name"], chat.mobile, data["text"], ward_number=citizen["ward_number"], use_llm=False,
                    now=chat.now, address=data["place"], kind=data["kind"], category=data["category"],
                    photos=urls if data["kind"] in (CIVIC, POLICE) else None)
            except PortalError as error:
                # Most likely a photo the portal refused: ask for the photos again and say why.
                self._clear_files(chat.state)
                data.pop("photos", None)
                data.pop("photos_done", None)
                chat.replies.append(error.message)
                self._advance_registration(chat)
                return
        self._clear_files(chat.state)
        chat.state = {}
        due = texts.when_text(view["deadline"])
        reply = T("registered", chat.lang, id=view["id"], label=self._type_label(view, chat.lang),
                  office=self._office(view["current_office"], chat.lang), due=due)
        if data["kind"] == EMERGENCY:
            reply += "\n\n" + T("emergency_note", chat.lang)
        if view.get("police_notice"):
            reply += "\n\n" + (POLICE_NOTICE_KN if chat.lang == "kn" else view["police_notice"])
        chat.replies.append(reply)

    # ---- photos kept on disk while the chat is going on

    def _temp_folder(self) -> Path:
        folder = Path(self.portal.store.path).parent / "wa_tmp"
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def _save_media(self, mobile: str, item: Media, index: int) -> Optional[List[str]]:
        try:
            raw, mime = self.channel.fetch_media(item)
        except Exception as error:
            print(f"WhatsApp media download failed: {error}")
            return None
        mime = (mime or item.mime or "").split(";")[0].strip().lower()
        if mime not in PHOTO_TYPES or not raw or len(raw) > MAX_PHOTO_BYTES:
            return None
        name = f"{mobile}-{index + 1}-{int(time.time() * 1000) % 100000}.bin"
        (self._temp_folder() / name).write_bytes(raw)
        return [name, mime]

    def _clear_files(self, state: Dict[str, Any]) -> None:
        for name, _ in (state.get("d") or {}).get("photos", []):
            try:
                (self._temp_folder() / name).unlink(missing_ok=True)
            except OSError:
                pass

    # ---- tracking

    def _ask_for_id(self, chat: Chat) -> None:
        chat.state = {}
        chat.say("ask_id")
        chat.go("track_id")

    def _step_track_id(self, chat: Chat, message: Inbound) -> None:
        found = keyword_understanding(message.text).get("complaint_id")
        if not found:
            chat.say("ask_id")
            return
        chat.state = {}
        self._show_one(chat, found)

    def _show_one(self, chat: Chat, complaint_id: str) -> None:
        try:
            view = self.portal.track(complaint_id, chat.mobile)
        except PortalError:
            chat.say("no_such")
            return
        status = view["status_text"]
        if chat.lang == "kn" and status == STATUS_TEXT.get(view["status"]):
            status = STATUS_KN[view["status"]]
        due = T("due", chat.lang, due=texts.when_text(view["deadline"])) if view["status"] == OPEN and view["deadline"] else ""
        events = view.get("events") or []
        chat.say("track", id=view["id"], label=self._type_label(view, chat.lang), status=status,
                 office=self._office(view["current_office"], chat.lang), due=due,
                 latest=self._short(events[-1]["message"], 250) if events else "-")

    def _show_list(self, chat: Chat) -> None:
        chat.state = {}
        rows = self.portal.citizen_complaints(chat.mobile)[:LIST_LIMIT]
        if not rows:
            chat.say("list_none")
            return
        lines = []
        for number, row in enumerate(rows, start=1):
            status = (STATUS_KN if chat.lang == "kn" else {OPEN: "Open", AWAITING: "Resolved, please confirm",
                                                           CLOSED: "Closed"})[row["status"]]
            lines.append(f"{number} - {row['id']} - {self._type_label(row, chat.lang)} - {status.split('.')[0]}")
        chat.say("list_head", list="\n".join(lines))
        chat.data["ids"] = [row["id"] for row in rows]
        chat.go("pick_complaint")

    def _step_pick_complaint(self, chat: Chat, message: Inbound) -> None:
        ids = chat.data.get("ids", [])
        number = _number(message.text)
        found = keyword_understanding(message.text).get("complaint_id")
        if number is not None and 1 <= number <= len(ids):
            found = ids[number - 1]
        if not found:
            chat.say("bad_choice")
            return
        chat.state = {}
        self._show_one(chat, found)

    # ---- confirming a fix

    def _start_fix(self, chat: Chat) -> None:
        chat.state = {}
        waiting = [row for row in self.portal.citizen_complaints(chat.mobile) if row["status"] == AWAITING]
        if not waiting:
            chat.say("fix_none")
            return
        chat.data["ids"] = [row["id"] for row in waiting]
        chat.data["labels"] = {row["id"]: self._type_label(row, chat.lang) for row in waiting}
        if len(waiting) == 1:
            self._ask_fixed(chat, waiting[0]["id"])
        else:
            chat.say("fix_pick", list="\n".join(f"{n} - {row['id']} - {self._type_label(row, chat.lang)}"
                                                for n, row in enumerate(waiting, start=1)))
            chat.go("fix_pick")

    def _step_fix_pick(self, chat: Chat, message: Inbound) -> None:
        ids = chat.data.get("ids", [])
        number = _number(message.text)
        if number is None or not 1 <= number <= len(ids):
            chat.say("bad_choice")
            return
        self._ask_fixed(chat, ids[number - 1])

    def _ask_fixed(self, chat: Chat, complaint_id: str) -> None:
        chat.data["id"] = complaint_id
        chat.say("fix_ask", id=complaint_id, label=chat.data.get("labels", {}).get(complaint_id, ""))
        chat.go("fix_answer")

    def _step_fix_answer(self, chat: Chat, message: Inbound) -> None:
        word = message.text.strip().lower()
        complaint_id = chat.data["id"]
        if word in YES:
            view = self.portal.confirm(complaint_id, chat.mobile, True, now=chat.now)
            if view.get("demo_code"):
                chat.say("fix_code_shown", code=view["demo_code"], minutes=view.get("demo_code_minutes", 10))
            else:
                chat.say("fix_code_sent", note=view.get("code_note", ""))
            chat.state = {"d": {"id": complaint_id}}
            chat.go("fix_code")
        elif word in NO:
            view = self.portal.confirm(complaint_id, chat.mobile, False, "Said on WhatsApp.", now=chat.now)
            chat.state = {}
            chat.say("fix_escalated", id=complaint_id, office=self._office(view["current_office"], chat.lang))
        else:
            chat.say("bad_choice")

    def _step_fix_code(self, chat: Chat, message: Inbound) -> None:
        code = "".join(ch for ch in message.text if ch.isdigit())
        if len(code) != 6:
            chat.say("code_bad")
            return
        complaint_id = chat.data["id"]
        self.portal.confirm_code(complaint_id, chat.mobile, code, now=chat.now)
        chat.state = {}
        chat.say("fix_closed", id=complaint_id)

    # ---- login code for the website

    def _send_login_code(self, chat: Chat) -> None:
        chat.state = {}
        if self._citizen(chat) is None:
            chat.say("login_need")
            return
        result = self.portal.start_citizen_login(chat.mobile, now=chat.now)
        if result.get("code"):   # no code provider is set up, and this chat proves the number, so the code goes here
            chat.say("login_code", code=result["code"], minutes=result["minutes"])
        else:
            chat.say("login_sent", note=result["note"])

    # ---- small helpers

    def _type_label(self, view: Dict[str, Any], lang: str) -> str:
        label = view.get("complaint_label", "")
        return texts._kannada_names().get(label, label) if lang == "kn" else label

    def _office(self, office: str, lang: str) -> str:
        return texts._kannada_names().get(office, office) if lang == "kn" else office
