"""The public receiver speaks the same contract as quickpass.apply_webhook."""
import hashlib
import hmac
import io
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import didit_webhook_relay as relay


def _post(body, secret="secret", headers=None):
    raw = json.dumps(body).encode("utf-8") if not isinstance(body, bytes) else body
    sig = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    environ = {
        "REQUEST_METHOD": "POST",
        "PATH_INFO": "/didit/webhook",
        "CONTENT_LENGTH": str(len(raw)),
        "wsgi.input": io.BytesIO(raw),
        "HTTP_X_SIGNATURE": sig,
        "HTTP_X_TIMESTAMP": str(int(time.time())),
    }
    if headers:
        environ.update(headers)
    captured = {}

    def start_response(status, headers_out):
        captured["status"] = status

    chunks = relay.create_app("secret")(environ, start_response)
    return captured["status"], json.loads(b"".join(chunks))


def test_relay_accepts_a_signed_approval():
    status, payload = _post({"session_id": "s1", "status": "Approved"})
    assert status == "200 OK"
    assert payload["applied"] is True
    assert payload["status"] == "verified"
    assert payload["patch"]["last_event_id"]


def test_relay_refuses_a_forged_signature():
    raw = json.dumps({"session_id": "s1", "status": "Approved"}).encode()
    environ = {
        "REQUEST_METHOD": "POST",
        "PATH_INFO": "/didit/webhook",
        "CONTENT_LENGTH": str(len(raw)),
        "wsgi.input": io.BytesIO(raw),
        "HTTP_X_SIGNATURE": "forged",
    }
    captured = {}
    chunks = relay.create_app("secret")(
        environ, lambda status, h: captured.setdefault("status", status))
    payload = json.loads(b"".join(chunks))
    assert captured["status"] == "401 Unauthorized"
    assert payload["ok"] is False


def test_relay_health_is_open():
    captured = {}
    chunks = relay.create_app("secret")(
        {"REQUEST_METHOD": "GET", "PATH_INFO": "/health"},
        lambda status, h: captured.setdefault("status", status))
    assert captured["status"] == "200 OK"
    assert json.loads(b"".join(chunks))["ready"] is True


def test_relay_unknown_path_is_404():
    captured = {}
    chunks = relay.create_app("secret")(
        {"REQUEST_METHOD": "POST", "PATH_INFO": "/nope"},
        lambda status, h: captured.setdefault("status", status))
    assert captured["status"] == "404 Not Found"
