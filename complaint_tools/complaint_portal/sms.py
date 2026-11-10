"""Sending the one-time codes by SMS.

Four providers are supported (two for SMS, two for WhatsApp). Pick one in the .env file (see .env.example)
or in environment variables:

- Fast2SMS (Indian numbers):  SMS_PROVIDER=fast2sms, FAST2SMS_API_KEY=..., FAST2SMS_OTP_ID=...
  Uses the Fast2SMS OTP API (POST https://www.fast2sms.com/dev/otp/send) with our own code in "otp".
  FAST2SMS_OTP_ID is the ID of an OTP template in the Fast2SMS dashboard.
- Twilio:  SMS_PROVIDER=twilio, TWILIO_ACCOUNT_SID=..., TWILIO_AUTH_TOKEN=..., TWILIO_FROM=+1...
  Sends to +91 followed by the 10-digit number.
- WhatsApp Cloud API (Meta):  SMS_PROVIDER=whatsapp, WHATSAPP_TOKEN=..., WHATSAPP_PHONE_NUMBER_ID=...,
  WHATSAPP_TEMPLATE=... (an approved "authentication" template whose body is {{1}}), WHATSAPP_LANGUAGE=en.
  Sends to 91 followed by the 10-digit number.
- Twilio WhatsApp:  SMS_PROVIDER=twilio_whatsapp, TWILIO_ACCOUNT_SID=..., TWILIO_AUTH_TOKEN=...,
  TWILIO_WHATSAPP_FROM=+14155238886 (the Twilio sandbox number, or your approved WhatsApp sender).
  In the sandbox each phone must first send the "join <word>" message shown in the Twilio console.

With no provider set, nothing is sent and the portal shows the code on screen, as before.
If sending fails, the portal also shows the code on screen and says why, so a demo never gets stuck.
"""

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable, Dict, Mapping, Optional, Tuple

TIMEOUT_SECONDS = 10

# (url, headers, body bytes) -> (HTTP status, response text). Tests swap this for a fake.
Transport = Callable[[str, Dict[str, str], bytes], Tuple[int, str]]


def _http_post(url: str, headers: Dict[str, str], body: bytes) -> Tuple[int, str]:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace")


class NoSms:
    """No provider set up: nothing is sent."""

    name = "none"
    channel = "SMS"
    configured = False

    def send_code(self, mobile: str, code: str, minutes: int, purpose: str) -> Tuple[bool, str]:
        return False, "SMS is not set up."


class Fast2Sms:
    """Fast2SMS OTP API. The code we made is sent in "otp", so the portal still checks it itself."""

    name = "fast2sms"
    channel = "SMS"
    configured = True
    url = "https://www.fast2sms.com/dev/otp/send"

    def __init__(self, api_key: str, otp_id: str, transport: Optional[Transport] = None) -> None:
        self.api_key = api_key
        self.otp_id = otp_id
        self.transport = transport or _http_post

    def send_code(self, mobile: str, code: str, minutes: int, purpose: str) -> Tuple[bool, str]:
        body = json.dumps({
            "mobile": mobile,
            "otp_id": self.otp_id,
            "otp": code,
            "otp_length": len(code),
            "otp_expiry": minutes,
        }).encode("utf-8")
        headers = {"Authorization": self.api_key, "Content-Type": "application/json"}
        try:
            status, text = self.transport(self.url, headers, body)
        except (OSError, ValueError) as error:
            return False, f"Fast2SMS could not be reached ({error})."
        try:
            data = json.loads(text)
        except ValueError:
            data = {}
        if 200 <= status < 300 and data.get("return") is True:
            return True, "sent"
        return False, f"Fast2SMS said: {data.get('message') or text[:120] or status}"


class TwilioSms:
    """Twilio Messages API."""

    name = "twilio"
    channel = "SMS"
    configured = True
    prefix = ""   # "whatsapp:" for the WhatsApp subclass

    def __init__(self, account_sid: str, auth_token: str, sender: str, transport: Optional[Transport] = None) -> None:
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.sender = sender
        self.transport = transport or _http_post

    def send_code(self, mobile: str, code: str, minutes: int, purpose: str) -> Tuple[bool, str]:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{urllib.parse.quote(self.account_sid)}/Messages.json"
        text = message_text(code, minutes, purpose)
        body = urllib.parse.urlencode(
            {"To": f"{self.prefix}+91{mobile}", "From": f"{self.prefix}{self.sender}", "Body": text}).encode("utf-8")
        token = base64.b64encode(f"{self.account_sid}:{self.auth_token}".encode("utf-8")).decode("ascii")
        headers = {"Authorization": f"Basic {token}", "Content-Type": "application/x-www-form-urlencoded"}
        try:
            status, reply = self.transport(url, headers, body)
        except (OSError, ValueError) as error:
            return False, f"Twilio could not be reached ({error})."
        if 200 <= status < 300:
            return True, "sent"
        try:
            message = json.loads(reply).get("message")
        except ValueError:
            message = None
        return False, f"Twilio said: {message or reply[:120] or status}"


class TwilioWhatsApp(TwilioSms):
    """Twilio Messages API over WhatsApp. Works with the free sandbox number after each phone has joined it."""

    name = "twilio_whatsapp"
    channel = "WhatsApp"
    prefix = "whatsapp:"


class WhatsAppCloud:
    """WhatsApp Business Cloud API (Meta). Sends an approved authentication template with our code in it."""

    name = "whatsapp"
    channel = "WhatsApp"
    configured = True
    version = "v21.0"

    def __init__(self, token: str, phone_number_id: str, template: str, language: str = "en",
                 transport: Optional[Transport] = None) -> None:
        self.token = token
        self.phone_number_id = phone_number_id
        self.template = template
        self.language = language
        self.transport = transport or _http_post

    def send_code(self, mobile: str, code: str, minutes: int, purpose: str) -> Tuple[bool, str]:
        url = f"https://graph.facebook.com/{self.version}/{urllib.parse.quote(self.phone_number_id)}/messages"
        body = json.dumps({
            "messaging_product": "whatsapp",
            "to": f"91{mobile}",
            "type": "template",
            "template": {
                "name": self.template,
                "language": {"code": self.language},
                "components": [
                    {"type": "body", "parameters": [{"type": "text", "text": code}]},
                    # Authentication templates carry a "copy code" button that needs the code again.
                    {"type": "button", "sub_type": "url", "index": "0",
                     "parameters": [{"type": "text", "text": code}]},
                ],
            },
        }).encode("utf-8")
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        try:
            status, reply = self.transport(url, headers, body)
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


class ChannelCodes:
    """Sends the codes through the WhatsApp chat provider (whatsapp.py) when no SMS or WhatsApp-code provider is set.

    If the message cannot be sent (for example the person has not joined the sandbox, or WhatsApp's 24-hour window
    is closed) the portal shows the code on screen instead, as it does without any provider."""

    name = "whatsapp chat"
    channel = "WhatsApp"
    configured = True

    def __init__(self, chat_channel) -> None:
        self.chat_channel = chat_channel

    def send_code(self, mobile: str, code: str, minutes: int, purpose: str) -> Tuple[bool, str]:
        return self.chat_channel.send_text(mobile, message_text(code, minutes, purpose))


def message_text(code: str, minutes: int, purpose: str) -> str:
    """The SMS text, for providers that take free text (Twilio)."""
    if purpose == "complete":
        return (f"{code} is the code for your complaint. Give it to the worker only if the "
                f"problem is fixed. It lasts {minutes} minutes.")
    if purpose == "confirm":
        return f"{code} is your code to close your complaint. It lasts {minutes} minutes."
    return f"{code} is your complaint portal login code. It lasts {minutes} minutes. Do not share it."


def sender_from_env(env: Optional[Mapping[str, str]] = None):
    """Pick the SMS provider from the environment. Missing settings mean no SMS."""
    env = os.environ if env is None else env
    provider = (env.get("SMS_PROVIDER") or "").strip().lower()
    if provider == "fast2sms":
        key, otp_id = (env.get("FAST2SMS_API_KEY") or "").strip(), (env.get("FAST2SMS_OTP_ID") or "").strip()
        if key and otp_id:
            return Fast2Sms(key, otp_id)
    if provider == "twilio":
        sid = (env.get("TWILIO_ACCOUNT_SID") or "").strip()
        token = (env.get("TWILIO_AUTH_TOKEN") or "").strip()
        sender = (env.get("TWILIO_FROM") or "").strip()
        if sid and token and sender:
            return TwilioSms(sid, token, sender)
    if provider == "twilio_whatsapp":
        sid = (env.get("TWILIO_ACCOUNT_SID") or "").strip()
        token = (env.get("TWILIO_AUTH_TOKEN") or "").strip()
        sender = (env.get("TWILIO_WHATSAPP_FROM") or "").strip().removeprefix("whatsapp:")
        if sid and token and sender:
            return TwilioWhatsApp(sid, token, sender)
    if provider == "whatsapp":
        token = (env.get("WHATSAPP_TOKEN") or "").strip()
        number_id = (env.get("WHATSAPP_PHONE_NUMBER_ID") or "").strip()
        template = (env.get("WHATSAPP_TEMPLATE") or "").strip()
        if token and number_id and template:
            return WhatsAppCloud(token, number_id, template, (env.get("WHATSAPP_LANGUAGE") or "en").strip())
    return NoSms()


def load_env_file(path: Path) -> None:
    """Read KEY=VALUE lines from a .env file into the environment. Settings already in the environment win."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value
