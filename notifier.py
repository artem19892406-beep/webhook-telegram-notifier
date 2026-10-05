"""Minimal webhook -> Telegram notifier. Standard library only.

POST /webhook with a JSON body (name, phone, email, message, source) and the
notifier forwards a short formatted message to a Telegram chat.
"""
import hmac
import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MAX_BODY = 64 * 1024
FIELDS = (
    ("name", "Name"),
    ("phone", "Phone"),
    ("email", "Email"),
    ("source", "Source"),
    ("message", "Message"),
)


def format_message(payload):
    """Build the Telegram text from a lead payload. Returns None if empty."""
    lines = []
    for key, label in FIELDS:
        value = payload.get(key)
        if value is None:
            continue
        value = str(value).strip()
        if value:
            lines.append(f"{label}: {value[:1000]}")
    if not lines:
        return None
    return "New lead\n" + "\n".join(lines)


def send_telegram(text, token, chat_id, api_base="https://api.telegram.org"):
    url = f"{api_base}/bot{token}/sendMessage"
    data = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status


def make_handler(config):
    class Handler(BaseHandler):
        cfg = config

    return Handler


class BaseHandler(BaseHTTPRequestHandler):
    cfg = {}

    def _reply(self, code, body):
        data = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):  # keep logs free of payload data
        pass

    def do_GET(self):
        if self.path == "/health":
            self._reply(200, {"status": "ok"})
        else:
            self._reply(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/webhook":
            return self._reply(404, {"error": "not found"})

        secret = self.cfg.get("secret")
        if secret:
            given = self.headers.get("X-Webhook-Secret", "")
            if not hmac.compare_digest(given.encode(), secret.encode()):
                return self._reply(401, {"error": "unauthorized"})

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self._reply(400, {"error": "bad content-length"})
        if length <= 0 or length > MAX_BODY:
            return self._reply(413 if length > MAX_BODY else 400, {"error": "bad body size"})

        try:
            payload = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            return self._reply(400, {"error": "invalid json"})
        if not isinstance(payload, dict):
            return self._reply(400, {"error": "json object expected"})

        text = format_message(payload)
        if text is None:
            return self._reply(422, {"error": "no known fields"})

        try:
            send_telegram(
                text, self.cfg["token"], self.cfg["chat_id"], self.cfg["api_base"]
            )
        except (urllib.error.URLError, OSError):
            return self._reply(502, {"error": "telegram delivery failed"})
        self._reply(200, {"status": "sent"})


def load_config():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
    return {
        "token": token,
        "chat_id": chat_id,
        "secret": os.environ.get("WEBHOOK_SECRET", ""),
        "api_base": os.environ.get("TELEGRAM_API_BASE", "https://api.telegram.org"),
    }


def main():
    cfg = load_config()
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer(("0.0.0.0", port), make_handler(cfg))
    print(f"Listening on :{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
