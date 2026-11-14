"""QuickPass: guest identity verification behind a replaceable provider.

The module never talks to a document scanner of its own. It asks a provider to
run a verification session, hands the guest the provider's hosted URL, and
records the provider's outcome. Two providers implement that seam:

* :class:`DiditProvider` — the real integration. `POST /v3/session/` creates a
  session (``x-api-key``), the guest completes it on ``verification_url``, and
  `GET /v3/session/{id}/decision/` retrieves the decision. Webhook payloads can
  be verified with :func:`verify_webhook` using the documented HMAC procedure.
* :class:`DemoProvider` — the fallback used when no credentials are configured
  or the network is unavailable. It is explicitly labelled ``demo`` everywhere
  and never pretends to have checked a real document.

Deliberate boundaries
---------------------
* A verified identity does **not** approve a check-in. It sets the verification
  to ``verified``; a receptionist still has to approve. `guestops.approve_check_in`
  enforces that separation.
* Only the provider's session id and normalized outcome are kept. No document
  image, selfie or biometric template is stored by this module.
* Provider statuses are mapped, never guessed: an unmapped provider string
  becomes ``error`` rather than silently counting as a pass. Didit's statuses
  are exact, case-sensitive strings (``"Kyc Expired"`` has a single capital K).

Credentials live in environment variables on the function's side only
(``DIDIT_API_KEY``, ``DIDIT_WORKFLOW_ID``, ``DIDIT_WEBHOOK_SECRET``); no secret
is ever handed to the browser.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Optional

#: The internal states this application reasons about.
PENDING = "pending"
VERIFIED = "verified"
REJECTED = "rejected"
REVIEW_REQUIRED = "review_required"
EXPIRED = "expired"
ERROR = "error"

STATES = (PENDING, VERIFIED, REJECTED, REVIEW_REQUIRED, EXPIRED, ERROR)

#: Statuses a receptionist may still act on without a fresh provider check.
ACTIONABLE = (VERIFIED, REVIEW_REQUIRED)

#: Didit's documented status strings, exactly as the API returns them.
DIDIT_STATUSES = (
    "Not Started",
    "In Progress",
    "Approved",
    "Declined",
    "In Review",
    "Awaiting User",
    "Resubmitted",
    "Expired",
    "Abandoned",
    "Kyc Expired",
)

#: Didit status -> internal state. An unrecognised string maps to ERROR, because
#: treating an unknown verdict as a pass is the one failure that matters.
DIDIT_STATUS_MAP = {
    "Not Started": PENDING,
    "In Progress": PENDING,
    "Awaiting User": PENDING,
    "Resubmitted": PENDING,
    "Approved": VERIFIED,
    "Declined": REJECTED,
    "In Review": REVIEW_REQUIRED,
    "Expired": EXPIRED,
    "Abandoned": EXPIRED,
    "Kyc Expired": EXPIRED,
}

DIDIT_BASE = os.environ.get("DIDIT_BASE_URL", "https://verification.didit.me")

#: A webhook older than this is refused (documented replay window).
WEBHOOK_TOLERANCE_SECONDS = 300

_counter = {"session": 0}


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def normalize_status(provider_status: Any) -> str:
    """Map a provider's status string onto an internal state.

    Matching is exact and case-sensitive on purpose: Didit documents its status
    strings as exact, so a near-miss is a bug worth seeing rather than a pass.
    """
    text = str(provider_status or "").strip()
    if not text:
        return PENDING
    return DIDIT_STATUS_MAP.get(text, ERROR)


def normalize_result(decision: dict[str, Any]) -> dict[str, Any]:
    """Read a Didit decision payload into what this application records."""
    status = normalize_status(decision.get("status"))
    out: dict[str, Any] = {
        "status": status,
        "provider_status": decision.get("status"),
        "session_id": decision.get("session_id"),
        "vendor_data": decision.get("vendor_data"),
        "expires_at": decision.get("expires_at"),
        "provider": "didit",
        "decision": None,
    }
    reviews = decision.get("reviews")
    if isinstance(reviews, list) and reviews:
        latest = reviews[-1] if isinstance(reviews[-1], dict) else {}
        out["decision"] = latest.get("comment") or latest.get("status")
    override = decision.get("status_override")
    if isinstance(override, dict):
        out["manual_override"] = True
        out["provider_status"] = override.get("automatic_status") or out["provider_status"]
    return out


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

class ProviderError(RuntimeError):
    """A provider call failed. The message is safe to show to an operator."""


class DemoProvider:
    """The fallback. No document is inspected; the session is local."""

    name = "demo"
    is_real = False

    def create_session(self, *, booking_id: str, guest_label: str,
                       room_code: Optional[str] = None,
                       metadata: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        _counter["session"] += 1
        session_id = f"demo-session-{_counter['session']:04d}"
        return {
            "provider": self.name,
            "session_id": session_id,
            "verification_url": "",
            "status": PENDING,
            "provider_status": "Not Started",
            "guest_label": guest_label,
            "booking_id": booking_id,
            "room_code": room_code,
            "metadata": metadata or {},
            "is_demo": True,
        }

    def fetch_decision(self, session_id: str) -> dict[str, Any]:
        return {
            "session_id": session_id,
            "status": "In Progress",
            "vendor_data": None,
        }


class DiditProvider:
    """Didit's Sessions API: create a session, then read its decision."""

    name = "didit"
    is_real = True

    def __init__(self, api_key: Optional[str] = None,
                 workflow_id: Optional[str] = None,
                 base_url: Optional[str] = None,
                 timeout: int = 15) -> None:
        self.api_key = api_key or os.environ.get("DIDIT_API_KEY", "")
        self.workflow_id = workflow_id or os.environ.get("DIDIT_WORKFLOW_ID", "")
        self.base_url = (base_url or DIDIT_BASE).rstrip("/")
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.workflow_id)

    def _call(self, method: str, path: str,
              body: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        if not self.configured:
            raise ProviderError(
                "Didit is not configured: set DIDIT_API_KEY and "
                "DIDIT_WORKFLOW_ID on the function."
            )
        url = self.base_url + path
        payload = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(url, data=payload, method=method)
        request.add_header("x-api-key", self.api_key)
        request.add_header("Content-Type", "application/json")
        request.add_header("Accept", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8")[:300]
            except Exception:  # pragma: no cover - best effort only
                detail = ""
            raise ProviderError(
                f"Didit returned {exc.code} for {path}. {detail}".strip()
            ) from exc
        except urllib.error.URLError as exc:
            raise ProviderError(f"Could not reach Didit: {exc.reason}") from exc
        try:
            return json.loads(raw) if raw else {}
        except ValueError as exc:
            raise ProviderError("Didit returned a body that is not JSON.") from exc

    def create_session(self, *, booking_id: str, guest_label: str,
                       room_code: Optional[str] = None,
                       metadata: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        body: dict[str, Any] = {
            "workflow_id": self.workflow_id,
            # vendor_data is Didit's stable correlation key; the booking id is
            # the honest one to use because it survives across sessions.
            "vendor_data": booking_id,
            "metadata": {
                "booking_id": booking_id,
                "room_code": room_code or "",
                **(metadata or {}),
            },
        }
        callback = os.environ.get("DIDIT_CALLBACK_URL", "")
        if callback:
            body["callback"] = callback
        created = self._call("POST", "/v3/session/", body)
        session_id = created.get("session_id") or ""
        if not session_id:
            raise ProviderError("Didit created no session_id; nothing to record.")
        return {
            "provider": self.name,
            "session_id": session_id,
            "verification_url": (created.get("url")
                                 or created.get("verification_url") or ""),
            "status": normalize_status(created.get("status")),
            "provider_status": created.get("status"),
            "guest_label": guest_label,
            "booking_id": booking_id,
            "room_code": room_code,
            "metadata": metadata or {},
            "is_demo": False,
        }

    def fetch_decision(self, session_id: str) -> dict[str, Any]:
        if not session_id:
            raise ProviderError("A decision needs a session_id.")
        return self._call("GET", f"/v3/session/{session_id}/decision/")


#: The live provider registry. `didit` is chosen only when it is configured, so
#: a fresh install still runs end to end on the demo provider.
def provider_for(name: Optional[str] = None) -> Any:
    key = (name or os.environ.get("QUICKPASS_PROVIDER") or "").strip().lower()
    didit = DiditProvider()
    if key == "didit":
        return didit
    if key == "demo":
        return DemoProvider()
    return didit if didit.configured else DemoProvider()


# ---------------------------------------------------------------------------
# Starting a verification
# ---------------------------------------------------------------------------

def start_verification(
    *,
    booking_id: str,
    guest_label: str,
    room_code: Optional[str] = None,
    provider_name: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Create a provider session and return the `verifications` row to save.

    A provider failure falls back to the demo provider **and says so** in
    ``note``, rather than leaving the guest with a dead button.
    """
    if not booking_id:
        return {"ok": False, "error": "A verification needs the booking it belongs to."}

    provider = provider_for(provider_name)
    note = ""
    try:
        session = provider.create_session(
            booking_id=booking_id,
            guest_label=guest_label,
            room_code=room_code,
            metadata=metadata,
        )
    except ProviderError as exc:
        if provider.name == "demo":
            return {"ok": False, "error": str(exc)}
        fallback = DemoProvider()
        session = fallback.create_session(
            booking_id=booking_id,
            guest_label=guest_label,
            room_code=room_code,
            metadata=metadata,
        )
        note = (f"Didit was unreachable ({exc}); this session is a demo "
                "verification, not a real identity check.")

    now = _now_iso()
    row = {
        "verification_id": "VER-" + str(int(time.time() * 1000)),
        "booking_id": booking_id,
        "guest_label": guest_label,
        "room_code": room_code or "",
        "provider": session["provider"],
        "session_id": session["session_id"],
        "verification_url": session.get("verification_url") or "",
        "provider_status": session.get("provider_status") or "",
        "status": session.get("status") or PENDING,
        "decision": None,
        "created_at": now,
        "updated_at": now,
    }
    return {
        "ok": True,
        "verification": row,
        "is_demo": bool(session.get("is_demo")),
        "note": note,
    }


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Refreshing a verification (polling; the documented fallback to webhooks)
# ---------------------------------------------------------------------------

def refresh_verification(row: dict[str, Any],
                         provider_name: Optional[str] = None) -> dict[str, Any]:
    """Ask the provider what it decided, and return the fields to update.

    Polling is used rather than a webhook because a Workpeg Function is invoked
    by the platform's save hooks; it has no inbound HTTP endpoint of its own, so
    the honest integration here is "the screen asks the provider" (and
    :func:`verify_webhook` is provided for a deployment that does have one).
    """
    session_id = str(row.get("session_id") or "")
    provider = provider_for(provider_name or row.get("provider"))
    if provider.name == "demo":
        status = row.get("status") or PENDING
        if status == PENDING:
            status = VERIFIED
        return {
            "ok": True,
            "is_demo": True,
            "status": status,
            "provider_status": "Approved (demo)",
            "note": ("The demo provider marks the guest verified without "
                     "checking a document."),
            "updated_at": _now_iso(),
        }
    try:
        decision = provider.fetch_decision(session_id)
    except ProviderError as exc:
        return {"ok": False, "error": str(exc), "status": ERROR}

    result = normalize_result(decision)
    return {
        "ok": True,
        "is_demo": False,
        "status": result["status"],
        "provider_status": result["provider_status"],
        "decision": result["decision"],
        "expires_at": result.get("expires_at"),
        "updated_at": _now_iso(),
    }


# ---------------------------------------------------------------------------
# Webhook verification (documented HMAC procedure)
# ---------------------------------------------------------------------------

def _canonical(value: Any) -> str:
    """Didit's X-Signature-V2 canonical form: sorted keys, whole floats as ints,
    unescaped Unicode, no whitespace."""
    def short(item: Any) -> Any:
        if isinstance(item, float) and item.is_integer():
            return int(item)
        if isinstance(item, dict):
            return {k: short(v) for k, v in item.items()}
        if isinstance(item, list):
            return [short(v) for v in item]
        return item
    return json.dumps(short(value), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def verify_webhook(
    raw_body: bytes,
    headers: dict[str, str],
    secret: str,
    *,
    now: Optional[int] = None,
    tolerance: int = WEBHOOK_TOLERANCE_SECONDS,
) -> dict[str, Any]:
    """Verify a Didit webhook's signature.

    Three headers can carry a signature; V2 is recommended because it survives
    middleware re-encoding, so it is tried first, then the raw-bytes header,
    then the deprecated envelope-only one (which authenticates the envelope but
    not the decision, so the caller must re-fetch the decision in that case).

    Returns ``{"ok": True, "scheme": ...}`` or ``{"ok": False, "error": ...}``.
    """
    lowered = {str(k).lower(): v for k, v in (headers or {}).items()}
    timestamp = lowered.get("x-timestamp", "")
    if tolerance and timestamp:
        try:
            age = abs((now if now is not None else int(time.time()))
                      - int(timestamp))
        except ValueError:
            return {"ok": False, "error": "X-Timestamp is not a whole number."}
        if age > tolerance:
            return {"ok": False, "error": "Webhook timestamp is outside the replay window."}
    if not secret:
        return {"ok": False, "error": "No webhook secret is configured."}

    def matches(signature: str, message: bytes) -> bool:
        expected = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature.strip())

    def candidate(name: str) -> list[str]:
        out = []
        primary = lowered.get(name, "")
        if primary:
            out.append(primary)
        previous = lowered.get(name + "-previous", "")
        if previous:
            out.append(previous)
        return out

    v2 = candidate("x-signature-v2")
    if v2:
        try:
            body = json.loads(raw_body.decode("utf-8"))
        except Exception:
            body = None
        if body is not None:
            message = _canonical(body).encode("utf-8")
            for signature in v2:
                if matches(signature, message):
                    return {"ok": True, "scheme": "X-Signature-V2"}

    raw = candidate("x-signature")
    for signature in raw:
        if matches(signature, raw_body):
            return {"ok": True, "scheme": "X-Signature"}

    simple = candidate("x-signature-simple")
    if simple:
        try:
            body = json.loads(raw_body.decode("utf-8"))
        except Exception:
            body = {}
        envelope = "{0}:{1}:{2}:{3}".format(
            timestamp,
            body.get("session_id", ""),
            body.get("status", ""),
            body.get("webhook_type", ""),
        )
        for signature in simple:
            if matches(signature, envelope.encode("utf-8")):
                return {
                    "ok": True,
                    "scheme": "X-Signature-Simple",
                    "trust_decision": False,
                    "note": ("This scheme authenticates the envelope only. "
                             "Re-fetch the decision before acting on it."),
                }

    return {"ok": False, "error": "No signature matched."}


# ---------------------------------------------------------------------------
# Hook: what the platform calls when a verification row is saved
# ---------------------------------------------------------------------------

def on_verification_post_save(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate a saved `verifications` row.

    Refused: an unknown internal state, or ``verified`` with no provider session
    behind it. Accepted: everything else, because a pending verification is a
    legitimate row.
    """
    status = str(payload.get("status") or PENDING).strip().lower()
    if status not in STATES:
        return {
            "ok": False,
            "refused": True,
            "error": (f"'{status}' is not a verification state. Known: "
                      + ", ".join(STATES)),
        }
    if status == VERIFIED and not payload.get("session_id"):
        return {
            "ok": False,
            "refused": True,
            "error": ("A verification cannot be marked verified without a "
                      "provider session: there would be nothing behind it."),
        }
    note = ""
    if status == VERIFIED:
        note = ("Identity verified. This does not approve check-in; a "
                "receptionist still has to approve the guest.")
    return {"ok": True, "status": status, "note": note}
