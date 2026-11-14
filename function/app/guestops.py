"""Guest Experience & Ops: check-in approval, checkout, requests and tasks.

This module owns the moment that everything else in PegPower depends on: a
receptionist approving a guest's check-in. It is deliberately strict, because
it is the only place a paid booking turns into physical access:

    payment confirmed  ->  eligible
    identity verified  ->  eligible
    reception approves ->  PegPower Core issues the grant
    RoomPower consumes the grant to power the room

Rules, all enforced here rather than in the UI:

* Payment alone never authorises a room. A confirmed payment only makes the
  booking *eligible* for check-in.
* A verified identity alone never authorises a room. Verification is what makes
  a guest reviewable; the receptionist decides.
* Approval is idempotent per booking. Approving twice returns the same grant
  event instead of minting a second one, so a double-click cannot double-power
  a room or extend a stay by accident.
* Checkout revokes the grant first, then applies the business's energy policy.
  The policy may be "hold", "saving" or "full_shutdown", and a blanket shutdown
  is refused unless the business explicitly allowed it.
* Housekeeping is raised as a task row, not fired off as an invisible side
  effect: somebody can see it on a board.

Nothing here stores a document image, a selfie or a biometric template.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from . import commands, quickpass

# ---------------------------------------------------------------------------
# States
# ---------------------------------------------------------------------------

CHECK_IN_APPROVED = "approved"
CHECK_IN_CHECKED_OUT = "checked_out"

REQUEST_CATEGORIES = ("room_service", "housekeeping", "maintenance", "concierge")

REQUEST_FLOW = {
    "requested": {"accepted", "in_progress", "cancelled", "done"},
    "accepted": {"in_progress", "done", "cancelled"},
    "in_progress": {"done", "cancelled"},
    "done": set(),
    "cancelled": set(),
}

#: How long a granted activation stays in force by default.
DEFAULT_GRANT_HOURS = 12


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _stable_id(prefix: str, *parts: Any) -> str:
    """A deterministic id, so a retried request cannot mint a second event."""
    seed = "|".join(str(part) for part in parts).encode("utf-8")
    return prefix + hashlib.sha256(seed).hexdigest()[:16].upper()


# ---------------------------------------------------------------------------
# Eligibility
# ---------------------------------------------------------------------------

def check_in_eligibility(
    *,
    booking: Optional[dict[str, Any]],
    payment: Optional[dict[str, Any]],
    verification: Optional[dict[str, Any]],
    room: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """May this booking be checked in, and if not, what is missing?

    Returns ``{"ok": bool, "reasons": [...], "server_approved_review": bool}``.
    The reasons are written for a receptionist, not for a log.
    """
    reasons: list[str] = []
    if not booking:
        return {"ok": False, "reasons": ["No reservation to check in."]}
    status = str(booking.get("booking_status") or "").lower()
    if status in ("cancelled", "canceled"):
        reasons.append("The reservation was cancelled.")
    if not payment:
        reasons.append("No payment is recorded against this reservation.")
    elif str(payment.get("payment_status") or "").lower() != "confirmed":
        reasons.append("The payment is not confirmed yet.")

    if not verification:
        reasons.append("Identity verification has not been started.")
    else:
        state = str(verification.get("status") or "").lower()
        if state in quickpass.STATES and state not in quickpass.ACTIONABLE:
            reasons.append(f"Identity verification is {state.replace('_', ' ')}.")

    if not booking.get("room_code"):
        reasons.append("No room is assigned to this reservation.")

    return {
        "ok": not reasons,
        "reasons": reasons,
        "review_required": bool(verification)
        and str(verification.get("status") or "") == quickpass.REVIEW_REQUIRED,
    }


# ---------------------------------------------------------------------------
# Approval -> Core grant
# ---------------------------------------------------------------------------

def approve_check_in(
    *,
    business_id: str,
    booking: dict[str, Any],
    payment: Optional[dict[str, Any]],
    verification: Optional[dict[str, Any]],
    actor: str = "reception",
    override_review: bool = False,
    ttl_hours: int = DEFAULT_GRANT_HOURS,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Issue the room-activation grant for an approved check-in.

    Returns the rows to write: the `authorizations` event and the `check_ins`
    record. The caller (the page) saves them; this function owns the decision.
    """
    eligibility = check_in_eligibility(
        booking=booking,
        payment=payment,
        verification=verification,
        room={"room_code": booking.get("room_code")} if booking else None,
    )
    review = (verification or {}).get("status") == quickpass.REVIEW_REQUIRED
    if not eligibility["ok"]:
        if review and override_review and len(eligibility["reasons"]) == 1:
            # A receptionist may accept a flagged identity in person; that is a
            # decision, not an automatic pass, and it is recorded as one.
            pass
        else:
            return {
                "ok": False,
                "error": " / ".join(eligibility["reasons"]),
                "reasons": eligibility["reasons"],
                "review_required": review,
            }
    if review and not override_review:
        return {
            "ok": False,
            "error": ("Identity verification needs review. Approve the review "
                      "explicitly if the guest is standing at the desk."),
            "reasons": ["Identity verification needs review."],
            "review_required": True,
        }

    booking_id = str(booking.get("booking_id") or "")
    room_code = str(booking.get("room_code") or "")
    at = now or _now()
    event_id = _stable_id("AUTH-", business_id, booking_id, room_code, "grant")
    expires = at + timedelta(hours=max(1, int(ttl_hours)))

    event = {
        "event_id": event_id,
        "business_id": business_id,
        "room_code": room_code,
        "authorization_type": "room_activation",
        "status": "granted",
        "source": (verification or {}).get("provider") or "quickpass",
        "issued_by": actor,
        "issued_at": _iso(at),
        "expires_at": _iso(expires),
        "metadata": {
            "booking_id": booking_id,
            "guest_label": booking.get("guest_label"),
            "verification_id": (verification or {}).get("verification_id"),
            "review_overridden": bool(review and override_review),
        },
    }
    check_in = {
        "check_in_id": _stable_id("CI-", business_id, booking_id),
        "booking_id": booking_id,
        "room_code": room_code,
        "guest_label": booking.get("guest_label") or "",
        "arrived_at": _iso(at),
        "verified_at": (verification or {}).get("updated_at") or "",
        "approved_at": _iso(at),
        "check_in_status": CHECK_IN_APPROVED,
    }
    return {
        "ok": True,
        "authorization_event": event,
        "check_in": check_in,
        "idempotent": True,
        "note": ("Grant issued. The room powers on only when the controller "
                 "acknowledges the command."),
    }


def revoke_check_in(
    *,
    business_id: str,
    booking: dict[str, Any],
    actor: str = "reception",
    reason: str = "guest checked out",
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """The revocation half of the contract: a `revoked` event for the room."""
    booking_id = str(booking.get("booking_id") or "")
    room_code = str(booking.get("room_code") or "")
    if not room_code:
        return {"ok": False, "error": "This reservation has no room to revoke."}
    at = now or _now()
    event = {
        "event_id": _stable_id("AUTH-", business_id, booking_id, room_code, "revoke"),
        "business_id": business_id,
        "room_code": room_code,
        "authorization_type": "room_activation",
        "status": "revoked",
        "source": "quickpass",
        "issued_by": actor,
        "issued_at": _iso(at),
        "expires_at": None,
        "metadata": {"booking_id": booking_id, "reason": reason},
    }
    return {"ok": True, "authorization_event": event}


# ---------------------------------------------------------------------------
# Checkout: revoke, save energy, raise housekeeping
# ---------------------------------------------------------------------------

def checkout(
    *,
    business_id: str,
    booking: dict[str, Any],
    device_code: Optional[str],
    actor: str = "reception",
    reason: str = "guest checked out",
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Everything checkout means, as rows and a plan.

    The energy step obeys the business's configured policy through
    `commands.plan_checkout`: checkout does not default to cutting a room's
    power, and a blanket shutdown needs explicit permission.
    """
    revoked = revoke_check_in(
        business_id=business_id,
        booking=booking,
        actor=actor,
        reason=reason,
        now=now,
    )
    if not revoked["ok"]:
        return revoked

    room_code = booking.get("room_code")
    at = now or _now()
    energy: dict[str, Any]
    if device_code:
        energy = commands.plan_checkout(
            business_id,
            device_code,
            room_code=room_code,
            authorization_event_id=revoked["authorization_event"]["event_id"],
            idempotency_key=f"checkout:{booking.get('booking_id')}",
            actor=actor,
        )
    else:
        energy = {
            "ok": True,
            "action": "none",
            "reason": "no controller is assigned to this room",
            "command": None,
        }

    task = {
        "task_id": _stable_id("TASK-", business_id, booking.get("booking_id"), "housekeeping"),
        "business_id": business_id,
        "kind": "housekeeping",
        "room_code": room_code or "",
        "detail": (f"Turn the room after {booking.get('guest_label') or 'the guest'} "
                   "checked out."),
        "status": "open",
        "assigned_to": "",
        "created_at": _iso(at),
    }
    return {
        "ok": True,
        "authorization_event": revoked["authorization_event"],
        "energy": energy,
        "command": energy.get("command"),
        "task": task,
        "note": ("Authorisation revoked and the energy policy applied. The "
                 "relay changes when the controller reports it."),
    }


# ---------------------------------------------------------------------------
# Guest requests
# ---------------------------------------------------------------------------

def validate_request(payload: dict[str, Any]) -> dict[str, Any]:
    """Shape and category check for a new guest request."""
    category = str(payload.get("category") or "").strip().lower().replace(" ", "_")
    if category not in REQUEST_CATEGORIES:
        return {
            "ok": False,
            "error": (f"'{category or 'empty'}' is not a request category. "
                      "Known: " + ", ".join(REQUEST_CATEGORIES)),
        }
    if not payload.get("booking_id"):
        return {"ok": False, "error": "A request must name the stay it belongs to."}
    detail = str(payload.get("detail") or "").strip()
    if len(detail) > 500:
        return {"ok": False, "error": "Keep the request under 500 characters."}
    return {
        "ok": True,
        "request": {
            "category": category,
            "detail": detail,
            "status": "requested",
        },
    }


def on_service_request_post_save(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate a saved `service_requests` row and its status transition."""
    status = str(payload.get("status") or "requested").strip().lower()
    category = str(payload.get("category") or "").strip().lower()
    if category not in REQUEST_CATEGORIES:
        return {
            "ok": False,
            "refused": True,
            "error": (f"'{category}' is not a request category. Known: "
                      + ", ".join(REQUEST_CATEGORIES)),
        }
    if status not in REQUEST_FLOW:
        return {
            "ok": False,
            "refused": True,
            "error": (f"'{status}' is not a request status. Known: "
                      + ", ".join(REQUEST_FLOW)),
        }
    return {"ok": True, "status": status}


# ---------------------------------------------------------------------------
# Hooks
# ---------------------------------------------------------------------------

def on_authorization_post_save(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate a saved `authorizations` row.

    The contract is small and the check is small with it: a room, a status of
    granted or revoked, and an event id. A grant must also carry an expiry, so
    a room cannot be authorised indefinitely by an accident.
    """
    status = str(payload.get("status") or "").strip().lower()
    if status not in ("granted", "revoked"):
        return {
            "ok": False,
            "refused": True,
            "error": "An authorization event is 'granted' or 'revoked'.",
        }
    if not payload.get("room_code"):
        return {"ok": False, "refused": True,
                "error": "An authorization event must name a room."}
    if status == "granted" and not payload.get("expires_at"):
        return {
            "ok": False,
            "refused": True,
            "error": ("A grant needs an expires_at; an activation that never "
                      "expires is a room nobody can take back."),
        }
    return {"ok": True, "status": status}


#: Continuity check used by the UI: is a grant still in force?
def grant_is_live(event: Optional[dict[str, Any]], now: Optional[datetime] = None) -> bool:
    if not event:
        return False
    if str(event.get("status") or "").lower() != "granted":
        return False
    expires = event.get("expires_at")
    if not expires:
        return False
    try:
        deadline = datetime.fromisoformat(str(expires).replace("Z", "+00:00"))
    except ValueError:
        return False
    return (now or _now()) < deadline


def didit_configured() -> bool:
    """Whether real Didit credentials are present in this environment."""
    return quickpass.DiditProvider().configured


def provider_summary() -> dict[str, Any]:
    """What the UI may say about verification without leaking a secret."""
    configured = didit_configured()
    return {
        "provider": "didit" if configured else "demo",
        "real": configured,
        "note": (
            "Didit credentials are configured on the function."
            if configured else
            "No Didit credentials are configured, so QuickPass is running the "
            "demo provider. Add DIDIT_API_KEY and DIDIT_WORKFLOW_ID to use "
            "Didit's sandbox."
        ),
    }


def env_flag(name: str) -> bool:
    return str(os.environ.get(name, "")).strip().lower() in ("1", "true", "yes", "on")
