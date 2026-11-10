"""The WhatsApp side of the portal: receiving citizens' messages and sending ours.

Two providers can carry the WhatsApp chat. Pick one with environment variables (see .env.example):

- Twilio WhatsApp (the free sandbox works for a demo)
    WHATSAPP_PROVIDER=twilio   TWILIO_ACCOUNT_SID  TWILIO_AUTH_TOKEN  TWILIO_WHATSAPP_FROM=+14155238886
  Twilio posts each incoming message as a web form to /api/whatsapp. We check its X-Twilio-Signature.
- WhatsApp Cloud API (Meta)
    WHATSAPP_PROVIDER=meta   WHATSAPP_TOKEN  WHATSAPP_PHONE_NUMBER_ID  WHATSAPP_VERIFY_TOKEN  WHATSAPP_APP_SECRET
  Meta posts JSON to /api/whatsapp and first calls it with GET to check WHATSAPP_VERIFY_TOKEN. We check
  X-Hub-Signature-256 with WHATSAPP_APP_SECRET.

PUBLIC_URL (for example https://kalaburagi-grievance-tracker.onrender.com) should be set when the portal is behind a
proxy, because Twilio signs the public address of the webhook.

This module only moves messages. What the bot says is in wa_bot.py. Nothing here talks to the network except through
the `http` function, which tests replace with a fake.
"""

import base64
import hashlib
import hmac
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

TIMEOUT_SECONDS = 15
MAX_MEDIA_BYTES = 6_000_000
MAX_REDIRECTS = 3
TWILIO_TEXT_LIMIT = 1500   # Twilio refuses more than 1600 characters in one message
META_TEXT_LIMIT = 3800     # WhatsApp allows 4096

# (method, url, headers, body or None) -> (HTTP status, response bytes). Tests swap this for a fake.
Http = Callable[[str, str, Dict[str, str], Optional[bytes]], Tuple[int, bytes]]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # noqa: D401 - urllib hook
        return None


def http_call(method: str, url: str, headers: Dict[str, str], body: Optional[bytes] = None) -> Tuple[int, bytes]:
    """One HTTPS request. Redirects are followed by hand, and the Authorization header is not sent to another host
    (Twilio redirects media to a storage host that must not get our token)."""
    opener = urllib.request.build_opener(_NoRedirect)
    origin = urllib.parse.urlsplit(url).netloc
    for _ in range(MAX_REDIRECTS + 1):
        sent = dict(headers)
        if urllib.parse.urlsplit(url).netloc != origin:
            sent.pop("Authorization", None)
        request = urllib.request.Request(url, data=body, headers=sent, method=method)
        try:
            with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
                return response.status, response.read(MAX_MEDIA_BYTES + 1)
        except urllib.error.HTTPError as error:
            if error.code in (301, 302, 303, 307, 308) and error.headers.get("Location"):
                url = urllib.parse.urljoin(url, error.headers["Location"])
                if error.code == 303:
                    method, body = "GET", None
                continue
            return error.code, error.read(MAX_MEDIA_BYTES + 1)
    return 508, b""


@dataclass
class Media:
    """A photo or document that came with a message. ref is a URL (Twilio) or a media ID (Meta)."""
    ref: str
    mime: str


@dataclass
class Inbound:
    message_id: str
    mobile: str                      # the sender's 10-digit Indian mobile number
    text: str = ""
    media: List[Media] = field(default_factory=list)
    location: Optional[Tuple[float, float, str]] = None   # latitude, longitude, a label or address

    @property
    def has_content(self) -> bool:
        return bool(self.text.strip() or self.media or self.location)


class InboundRejected(Exception):
    """The request did not come from the provider (bad signature) or is not usable."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def indian_mobile(raw: str) -> Optional[str]:
    """'whatsapp:+919876543210' or '919876543210' -> '9876543210'. Other countries give None."""
    digits = "".join(ch for ch in (raw or "") if ch.isdigit())
    if len(digits) == 12 and digits.startswith("91"):
        return digits[2:]
    return None


def chunks(text: str, limit: int) -> List[str]:
    """Split a long reply at blank lines or line ends so that no piece passes the provider's limit."""
    text = text.strip()
    if len(text) <= limit:
        return [text] if text else []
    pieces: List[str] = []
    current = ""
    for line in text.split("\n"):
        while len(line) > limit:
            if current:
                pieces.append(current.rstrip())
                current = ""
            pieces.append(line[:limit])
            line = line[limit:]
        if len(current) + len(line) + 1 > limit:
            pieces.append(current.rstrip())
            current = ""
        current += line + "\n"
    if current.strip():
        pieces.append(current.rstrip())
    return pieces


class TwilioChannel:
    name = "twilio"
    free_text_hours = 24

    def __init__(self, account_sid: str, auth_token: str, sender: str, public_url: str = "",
                 http: Optional[Http] = None) -> None:
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.sender = sender.removeprefix("whatsapp:")
        self.public_url = public_url.rstrip("/")
        self.http = http or http_call

    # Receiving

    def public_address(self, path: str, headers: Mapping[str, str]) -> str:
        if self.public_url:
            return self.public_url + path
        proto = headers.get("x-forwarded-proto") or "http"
        host = headers.get("x-forwarded-host") or headers.get("host") or ""
        return f"{proto}://{host}{path}"

    def expected_signature(self, address: str, params: Mapping[str, str]) -> str:
        data = address + "".join(key + params[key] for key in sorted(params))
        digest = hmac.new(self.auth_token.encode("utf-8"), data.encode("utf-8"), hashlib.sha1).digest()
        return base64.b64encode(digest).decode("ascii")

    def parse(self, path: str, headers: Mapping[str, str], raw: bytes) -> List[Inbound]:
        headers = {key.lower(): value for key, value in headers.items()}
        try:
            params = {key: values[0] for key, values in urllib.parse.parse_qs(
                raw.decode("utf-8"), keep_blank_values=True).items()}
        except UnicodeDecodeError:
            raise InboundRejected(400, "Not a form.") from None
        given = headers.get("x-twilio-signature", "")
        address = self.public_address(path, headers)
        if not given or not hmac.compare_digest(given, self.expected_signature(address, params)):
            raise InboundRejected(403, f"Bad signature. Twilio signs {address} - set PUBLIC_URL if that is not "
                                       "the address in the Twilio console.")
        mobile = indian_mobile(params.get("From", ""))
        if mobile is None:
            return []
        media = []
        try:
            count = min(int(params.get("NumMedia", "0") or 0), 5)
        except ValueError:
            count = 0
        for index in range(count):
            url = params.get(f"MediaUrl{index}", "")
            if url:
                media.append(Media(url, params.get(f"MediaContentType{index}", "")))
        location = None
        if params.get("Latitude") and params.get("Longitude"):
            try:
                location = (float(params["Latitude"]), float(params["Longitude"]),
                            params.get("Address") or params.get("Label") or "")
            except ValueError:
                location = None
        message = Inbound(params.get("MessageSid") or params.get("SmsMessageSid") or "", mobile,
                          params.get("Body", ""), media, location)
        return [message] if message.has_content else []

    def reply_to_webhook(self) -> Tuple[bytes, str]:
        return b"<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response></Response>", "text/xml; charset=utf-8"

    def verify_challenge(self, query: Mapping[str, str]) -> Optional[str]:
        return None

    # Sending

    def send_text(self, mobile: str, text: str) -> Tuple[bool, str]:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{urllib.parse.quote(self.account_sid)}/Messages.json"
        token = base64.b64encode(f"{self.account_sid}:{self.auth_token}".encode("utf-8")).decode("ascii")
        headers = {"Authorization": f"Basic {token}", "Content-Type": "application/x-www-form-urlencoded"}
        for piece in chunks(text, TWILIO_TEXT_LIMIT):
            body = urllib.parse.urlencode({"To": f"whatsapp:+91{mobile}", "From": f"whatsapp:{self.sender}",
                                           "Body": piece}).encode("utf-8")
            try:
                status, reply = self.http("POST", url, headers, body)
            except (OSError, ValueError) as error:
                return False, f"Twilio could not be reached ({error})."
            if not 200 <= status < 300:
                try:
                    message = json.loads(reply).get("message")
                except ValueError:
                    message = None
                return False, f"Twilio said: {message or reply[:120] or status}"
        return True, "sent"

    def fetch_media(self, media: Media) -> Tuple[bytes, str]:
        parts = urllib.parse.urlsplit(media.ref)
        if parts.scheme != "https" or parts.hostname != "api.twilio.com":
            raise ValueError("Unexpected media address.")
        token = base64.b64encode(f"{self.account_sid}:{self.auth_token}".encode("utf-8")).decode("ascii")
        status, data = self.http("GET", media.ref, {"Authorization": f"Basic {token}"}, None)
        if status != 200 or not data or len(data) > MAX_MEDIA_BYTES:
            raise ValueError(f"Media download failed ({status}).")
        return data, media.mime


class MetaChannel:
    name = "meta"
    free_text_hours = 24
    version = "v21.0"

    def __init__(self, token: str, phone_number_id: str, verify_token: str, app_secret: str,
                 update_template: str = "", language: str = "en", http: Optional[Http] = None) -> None:
        self.token = token
        self.phone_number_id = phone_number_id
        self.verify_token = verify_token
        self.app_secret = app_secret
        self.update_template = update_template   # an approved utility template with one {{1}} text, for late updates
        self.language = language
        self.http = http or http_call

    # Receiving

    def verify_challenge(self, query: Mapping[str, str]) -> Optional[str]:
        """The one-time GET Meta makes when the webhook is set up. Returns the text to echo, or None."""
        if (query.get("hub.mode") == "subscribe" and self.verify_token
                and hmac.compare_digest(query.get("hub.verify_token", ""), self.verify_token)):
            return query.get("hub.challenge", "")
        return None

    def parse(self, path: str, headers: Mapping[str, str], raw: bytes) -> List[Inbound]:
        headers = {key.lower(): value for key, value in headers.items()}
        expected = "sha256=" + hmac.new(self.app_secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(headers.get("x-hub-signature-256", ""), expected):
            raise InboundRejected(403, "Bad signature. Check WHATSAPP_APP_SECRET.")
        try:
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise InboundRejected(400, "Not JSON.") from None
        found: List[Inbound] = []
        for entry in data.get("entry", []) if isinstance(data, dict) else []:
            for change in entry.get("changes", []):
                for item in (change.get("value") or {}).get("messages", []) or []:
                    mobile = indian_mobile(str(item.get("from", "")))
                    if mobile is None:
                        continue
                    kind = item.get("type")
                    text, media, location = "", [], None
                    if kind == "text":
                        text = (item.get("text") or {}).get("body", "")
                    elif kind in ("image", "document"):
                        body = item.get(kind) or {}
                        if body.get("id"):
                            media.append(Media(str(body["id"]), body.get("mime_type", "")))
                        text = body.get("caption", "")
                    elif kind == "location":
                        place = item.get("location") or {}
                        try:
                            location = (float(place["latitude"]), float(place["longitude"]),
                                        place.get("address") or place.get("name") or "")
                        except (KeyError, TypeError, ValueError):
                            location = None
                    elif kind in ("button", "interactive"):
                        reply = item.get("button") or (item.get("interactive") or {}).get("button_reply") \
                            or (item.get("interactive") or {}).get("list_reply") or {}
                        text = reply.get("text") or reply.get("title") or ""
                    message = Inbound(str(item.get("id", "")), mobile, text, media, location)
                    if message.has_content:
                        found.append(message)
        return found

    def reply_to_webhook(self) -> Tuple[bytes, str]:
        return b"ok", "text/plain; charset=utf-8"

    # Sending

    def _post(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        url = f"https://graph.facebook.com/{self.version}/{urllib.parse.quote(self.phone_number_id)}/messages"
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        try:
            status, reply = self.http("POST", url, headers, json.dumps(payload).encode("utf-8"))
        except (OSError, ValueError) as error:
            return False, f"WhatsApp could not be reached ({error})."
        try:
            data = json.loads(reply)
        except ValueError:
            data = {}
        if 200 <= status < 300 and data.get("messages"):
            return True, "sent"
        message = (data.get("error") or {}).get("message") if isinstance(data, dict) else None
        return False, f"WhatsApp said: {message or reply[:120] or status}"

    def send_text(self, mobile: str, text: str) -> Tuple[bool, str]:
        for piece in chunks(text, META_TEXT_LIMIT):
            done, detail = self._post({"messaging_product": "whatsapp", "to": f"91{mobile}", "type": "text",
                                       "text": {"body": piece, "preview_url": False}})
            if not done:
                return done, detail
        return True, "sent"

    def send_update_template(self, mobile: str, text: str) -> Tuple[bool, str]:
        """A late update (after the 24-hour window) goes through an approved template whose body is {{1}}."""
        if not self.update_template:
            return False, "No WHATSAPP_UPDATE_TEMPLATE is set."
        flat = " ".join(text.split())[:900]   # template parameters cannot contain line breaks
        return self._post({"messaging_product": "whatsapp", "to": f"91{mobile}", "type": "template",
                           "template": {"name": self.update_template, "language": {"code": self.language},
                                        "components": [{"type": "body", "parameters": [{"type": "text", "text": flat}]}]}})

    def fetch_media(self, media: Media) -> Tuple[bytes, str]:
        headers = {"Authorization": f"Bearer {self.token}"}
        info_url = f"https://graph.facebook.com/{self.version}/{urllib.parse.quote(media.ref)}"
        status, reply = self.http("GET", info_url, headers, None)
        try:
            info = json.loads(reply)
        except ValueError:
            info = {}
        url = info.get("url", "") if isinstance(info, dict) else ""
        parts = urllib.parse.urlsplit(url)
        allowed = (".fbsbx.com", ".facebook.com", ".whatsapp.net", ".fbcdn.net")
        if status != 200 or parts.scheme != "https" or not (parts.hostname or "").endswith(allowed):
            raise ValueError("Media lookup failed.")
        status, data = self.http("GET", url, headers, None)
        if status != 200 or not data or len(data) > MAX_MEDIA_BYTES:
            raise ValueError(f"Media download failed ({status}).")
        return data, info.get("mime_type") or media.mime


def channel_from_env(env: Optional[Mapping[str, str]] = None) -> Tuple[Optional[Any], str]:
    """Pick the WhatsApp chat provider. Returns (channel or None, a line saying what is set up or what is missing)."""
    env = os.environ if env is None else env

    def get(key: str) -> str:
        return (env.get(key) or "").strip()

    provider = get("WHATSAPP_PROVIDER").lower()
    if not provider:   # the code-by-WhatsApp setting already says which provider is in use
        provider = {"twilio_whatsapp": "twilio", "whatsapp": "meta"}.get(get("SMS_PROVIDER").lower(), "")
    if provider == "twilio":
        missing = [key for key in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_WHATSAPP_FROM") if not get(key)]
        if missing:
            return None, "WhatsApp chat is off: missing " + ", ".join(missing) + "."
        return TwilioChannel(get("TWILIO_ACCOUNT_SID"), get("TWILIO_AUTH_TOKEN"), get("TWILIO_WHATSAPP_FROM"),
                             get("PUBLIC_URL")), "WhatsApp chat is on (Twilio)."
    if provider == "meta":
        missing = [key for key in ("WHATSAPP_TOKEN", "WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_VERIFY_TOKEN",
                                   "WHATSAPP_APP_SECRET") if not get(key)]
        if missing:
            return None, "WhatsApp chat is off: missing " + ", ".join(missing) + "."
        return MetaChannel(get("WHATSAPP_TOKEN"), get("WHATSAPP_PHONE_NUMBER_ID"), get("WHATSAPP_VERIFY_TOKEN"),
                           get("WHATSAPP_APP_SECRET"), get("WHATSAPP_UPDATE_TEMPLATE"),
                           get("WHATSAPP_LANGUAGE") or "en"), "WhatsApp chat is on (WhatsApp Cloud API)."
    return None, "WhatsApp chat is off (WHATSAPP_PROVIDER is not set)."
