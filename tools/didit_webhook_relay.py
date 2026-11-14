"""A public HTTPS endpoint for Didit webhooks, in one dependency-free file.

The peg has no inbound HTTP surface: a Workpeg Function runs from the platform's
save hooks, so Didit cannot call it directly. This is the missing public piece.
It is a plain WSGI app, so it runs unchanged on any host that speaks WSGI
(Gunicorn, uWSGI, Vercel's Python runtime, Cloud Run, a VPS, a Fly machine).

What it does, in order:

1. accepts ``POST /didit/webhook`` (and ``POST /webhook``) with the raw body;
2. verifies the Didit HMAC signature using the same code the function uses
   (``quickpass.apply_webhook``), including the 300s replay window;
3. answers ``200`` with the normalized patch and idempotency key, or ``401``
   when the signature does not match, or ``400`` when the body is unusable.

It writes nothing itself. Persisting the patch is the function's job
(``quickpass_webhook_apply``), because only the function holds the table
credentials; this endpoint's contract is deliberately "verify, then hand over".

Run it locally::

    DIDIT_WEBHOOK_SECRET=... python3 tools/didit_webhook_relay.py 8080

Deploy it anywhere public, then register the URL with Didit::

    POST /v3/webhook/destinations/
    {"label": "PegPower", "url": "https://your-host/didit/webhook",
     "subscribed_events": ["status.updated"]}

Set the same secret on the endpoint and on the function's environment.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "function"))

from app import quickpass  # noqa: E402

PATHS = ("/didit/webhook", "/webhook", "/")
MAX_BODY = 1024 * 1024


def _headers(environ: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in environ.items():
        if key.startswith("HTTP_"):
            name = key[5:].replace("_", "-")
            out[name] = value
    if environ.get("CONTENT_TYPE"):
        out["Content-Type"] = environ["CONTENT_TYPE"]
    return out


def _respond(start_response: Callable[..., Any], status: str, payload: dict) -> Iterable[bytes]:
    body = json.dumps(payload).encode("utf-8")
    start_response(status, [
        ("Content-Type", "application/json"),
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"),
    ])
    return [body]


def create_app(secret: str | None = None) -> Callable[..., Iterable[bytes]]:
    """Build the WSGI app. The secret is read per request if not passed in."""

    def app(environ: dict[str, Any], start_response: Callable[..., Any]):
        path = environ.get("PATH_INFO") or "/"
        method = (environ.get("REQUEST_METHOD") or "GET").upper()

        if path == "/health":
            return _respond(start_response, "200 OK",
                            {"ok": True, "ready": True})

        if path not in PATHS:
            return _respond(start_response, "404 Not Found",
                            {"ok": False, "error": "No such endpoint."})
        if method != "POST":
            return _respond(start_response, "405 Method Not Allowed",
                            {"ok": False, "error": "Use POST."})

        try:
            length = int(environ.get("CONTENT_LENGTH") or 0)
        except ValueError:
            length = 0
        if length > MAX_BODY:
            return _respond(start_response, "413 Payload Too Large",
                            {"ok": False, "error": "Body is too large."})
        raw = environ["wsgi.input"].read(length) if length else b""

        key = secret if secret is not None else os.environ.get(
            "DIDIT_WEBHOOK_SECRET", "")
        result = quickpass.apply_webhook(raw, _headers(environ), key)

        if not result.get("ok"):
            return _respond(start_response, "401 Unauthorized", {
                "ok": False,
                "error": result.get("error") or "The webhook was refused.",
            })

        return _respond(start_response, "200 OK", {
            "ok": True,
            "applied": bool(result.get("applied")),
            "duplicate": bool(result.get("duplicate")),
            "stale": bool(result.get("stale")),
            "needs_fetch": bool(result.get("needs_fetch")),
            "session_id": result.get("session_id"),
            "event_id": result.get("event_id"),
            "status": result.get("status"),
            "patch": result.get("patch"),
        })

    return app


app = create_app()


def main(argv: list[str]) -> int:
    port = int(argv[1]) if len(argv) > 1 else 8080
    try:
        from wsgiref.simple_server import make_server
    except Exception:
        print("wsgiref is unavailable; deploy create_app() with your host.",
              file=sys.stderr)
        return 1
    with make_server("0.0.0.0", port, app) as server:
        print("Didit webhook receiver on http://0.0.0.0:" + str(port))
        print("POST /didit/webhook   GET /health")
        server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
