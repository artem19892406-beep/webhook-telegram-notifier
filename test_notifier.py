import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from http.server import ThreadingHTTPServer

import notifier


class FakeTelegram(BaseHTTPRequestHandler):
    received = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeTelegram.received.append((self.path, body))
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def log_message(self, *a):
        pass


def start(server):
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server


def post(port, path, body, headers=None):
    data = body if isinstance(body, bytes) else json.dumps(body).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}", data=data, method="POST",
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


class NotifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tg = start(HTTPServer(("127.0.0.1", 0), FakeTelegram))
        tg_port = cls.tg.server_address[1]
        cfg = {
            "token": "TESTTOKEN", "chat_id": "42", "secret": "s3cret",
            "api_base": f"http://127.0.0.1:{tg_port}",
        }
        cls.app = start(ThreadingHTTPServer(("127.0.0.1", 0), notifier.make_handler(cfg)))
        cls.port = cls.app.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.app.shutdown()
        cls.tg.shutdown()

    def setUp(self):
        FakeTelegram.received.clear()

    def test_format_message(self):
        text = notifier.format_message({"name": " Ann ", "phone": "", "message": "Hi"})
        self.assertEqual(text, "New lead\nName: Ann\nMessage: Hi")
        self.assertIsNone(notifier.format_message({"unknown": 1}))

    def test_sends_to_telegram(self):
        code = post(self.port, "/webhook", {"name": "Ann", "message": "Hi"},
                    {"X-Webhook-Secret": "s3cret"})
        self.assertEqual(code, 200)
        path, body = FakeTelegram.received[0]
        self.assertEqual(path, "/botTESTTOKEN/sendMessage")
        self.assertEqual(body["chat_id"], "42")
        self.assertIn("Name: Ann", body["text"])

    def test_rejects_wrong_secret(self):
        self.assertEqual(post(self.port, "/webhook", {"name": "x"}, {"X-Webhook-Secret": "no"}), 401)
        self.assertEqual(post(self.port, "/webhook", {"name": "x"}), 401)
        self.assertEqual(FakeTelegram.received, [])

    def test_bad_input(self):
        h = {"X-Webhook-Secret": "s3cret"}
        self.assertEqual(post(self.port, "/webhook", b"not json", h), 400)
        self.assertEqual(post(self.port, "/webhook", [1, 2], h), 400)
        self.assertEqual(post(self.port, "/webhook", {"foo": "bar"}, h), 422)
        self.assertEqual(post(self.port, "/other", {"name": "x"}, h), 404)

    def test_health(self):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/health") as r:
            self.assertEqual(json.load(r), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
