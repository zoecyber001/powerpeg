"""QuickPass + Guest Experience & Ops: the connected check-in contract.

These tests are the reason the workflow is safe to demo: they pin the rule that
a payment does not open a door, a verified face does not open a door, and only
an explicit reception approval issues the grant RoomPower consumes.
"""

import hashlib
import hmac
import json
import time

import pytest

from app import guestops, quickpass


# ---------------------------------------------------------------------------
# Status normalization
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("provider_status,expected", [
    ("Not Started", "pending"),
    ("In Progress", "pending"),
    ("Awaiting User", "pending"),
    ("Resubmitted", "pending"),
    ("Approved", "verified"),
    ("Declined", "rejected"),
    ("In Review", "review_required"),
    ("Expired", "expired"),
    ("Abandoned", "expired"),
    ("Kyc Expired", "expired"),
])
def test_didit_statuses_map_to_internal_states(provider_status, expected):
    assert quickpass.normalize_status(provider_status) == expected


def test_unknown_provider_status_is_an_error_not_a_pass():
    assert quickpass.normalize_status("Totally Approved Honestly") == "error"
    assert quickpass.normalize_status("approved") == "error"  # case-sensitive on purpose


def test_empty_status_is_pending():
    assert quickpass.normalize_status(None) == "pending"
    assert quickpass.normalize_status("  ") == "pending"


def test_decision_extracts_manual_override_and_vendor_data():
    result = quickpass.normalize_result({
        "session_id": "s1",
        "vendor_data": "BKG-1",
        "status": "Declined",
        "status_override": {"automatic_status": "Approved"},
        "reviews": [{"status": "declined", "comment": "document expired"}],
    })
    assert result["status"] == "rejected"
    assert result["manual_override"] is True
    assert result["provider_status"] == "Approved"
    assert result["decision"] == "document expired"


# ---------------------------------------------------------------------------
# Starting a verification
# ---------------------------------------------------------------------------

def test_start_verification_with_demo_provider_returns_a_row():
    out = quickpass.start_verification(
        booking_id="BKG-1", guest_label="Ada", room_code="ROOM-101",
        provider_name="demo",
    )
    assert out["ok"] is True
    assert out["is_demo"] is True
    row = out["verification"]
    assert row["provider"] == "demo"
    assert row["session_id"]
    assert row["status"] == "pending"
    assert row["booking_id"] == "BKG-1"


def test_start_verification_needs_a_booking():
    out = quickpass.start_verification(booking_id="", guest_label="Ada",
                                       provider_name="demo")
    assert out["ok"] is False
    assert "booking" in out["error"]


def test_unconfigured_didit_falls_back_to_demo_and_says_so(monkeypatch):
    monkeypatch.delenv("DIDIT_API_KEY", raising=False)
    monkeypatch.delenv("DIDIT_WORKFLOW_ID", raising=False)
    out = quickpass.start_verification(
        booking_id="BKG-2", guest_label="Ada", provider_name="didit",
    )
    assert out["ok"] is True
    assert out["is_demo"] is True
    assert "Didit is not configured" in out["note"]


def test_provider_choice_prefers_didit_when_configured(monkeypatch):
    monkeypatch.setenv("DIDIT_API_KEY", "k")
    monkeypatch.setenv("DIDIT_WORKFLOW_ID", "w")
    assert quickpass.provider_for().name == "didit"
    assert quickpass.provider_for("demo").name == "demo"


# ---------------------------------------------------------------------------
# Polling a verification
# ---------------------------------------------------------------------------

def test_refresh_on_demo_session_promotes_pending_to_verified():
    out = quickpass.refresh_verification(
        {"session_id": "demo-1", "provider": "demo", "status": "pending"}
    )
    assert out["ok"] is True
    assert out["status"] == "verified"
    assert "without checking a document" in out["note"]


def test_refresh_reports_provider_failure_as_error(monkeypatch):
    class Broken(quickpass.DiditProvider):
        def fetch_decision(self, session_id):
            raise quickpass.ProviderError("Didit returned 401")

    monkeypatch.setattr(quickpass, "provider_for", lambda name=None: Broken())
    out = quickpass.refresh_verification(
        {"session_id": "s1", "provider": "didit", "status": "pending"}
    )
    assert out["ok"] is False
    assert out["status"] == "error"
    assert "401" in out["error"]


# ---------------------------------------------------------------------------
# Webhook signature verification
# ---------------------------------------------------------------------------

def _raw(body: dict) -> bytes:
    return json.dumps(body).encode("utf-8")


def test_webhook_raw_signature_is_accepted():
    body = {"session_id": "s1", "status": "Approved", "webhook_type": "status.updated"}
    raw = _raw(body)
    sig = hmac.new(b"secret", raw, hashlib.sha256).hexdigest()
    out = quickpass.verify_webhook(
        raw, {"X-Signature": sig, "X-Timestamp": str(int(time.time()))}, "secret"
    )
    assert out["ok"] is True
    assert out["scheme"] == "X-Signature"


def test_webhook_canonical_v2_signature_is_accepted():
    body = {"status": "Approved", "session_id": "s1", "amount": 2.0}
    raw = _raw(body)
    canonical = json.dumps({"amount": 2, "session_id": "s1", "status": "Approved"},
                           sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    sig = hmac.new(b"secret", canonical.encode("utf-8"), hashlib.sha256).hexdigest()
    out = quickpass.verify_webhook(raw, {"X-Signature-V2": sig}, "secret", tolerance=0)
    assert out["ok"] is True
    assert out["scheme"] == "X-Signature-V2"


def test_webhook_rejects_a_bad_signature():
    raw = _raw({"session_id": "s1", "status": "Approved"})
    out = quickpass.verify_webhook(raw, {"X-Signature": "deadbeef"}, "secret",
                                   tolerance=0)
    assert out["ok"] is False


def test_webhook_rejects_a_replayed_timestamp():
    raw = _raw({"session_id": "s1", "status": "Approved"})
    sig = hmac.new(b"secret", raw, hashlib.sha256).hexdigest()
    old = str(int(time.time()) - 3600)
    out = quickpass.verify_webhook(raw, {"X-Signature": sig, "X-Timestamp": old},
                                   "secret")
    assert out["ok"] is False
    assert "replay window" in out["error"]


def test_webhook_simple_scheme_does_not_trust_the_decision():
    body = {"session_id": "s1", "status": "Approved", "webhook_type": "status.updated"}
    ts = str(int(time.time()))
    raw = _raw(body)
    envelope = f"{ts}:s1:Approved:status.updated"
    sig = hmac.new(b"secret", envelope.encode(), hashlib.sha256).hexdigest()
    out = quickpass.verify_webhook(
        raw, {"X-Signature-Simple": sig, "X-Timestamp": ts}, "secret"
    )
    assert out["ok"] is True
    assert out["trust_decision"] is False


def test_webhook_needs_a_secret():
    out = quickpass.verify_webhook(b"{}", {"X-Signature": "x"}, "")
    assert out["ok"] is False


# ---------------------------------------------------------------------------
# Verifications hook
# ---------------------------------------------------------------------------

def test_verification_hook_accepts_pending():
    assert quickpass.on_verification_post_save(
        {"status": "pending", "session_id": "s1"}
    )["ok"] is True


def test_verification_hook_refuses_unknown_state():
    out = quickpass.on_verification_post_save({"status": "probably_fine"})
    assert out["ok"] is False and out["refused"] is True


def test_verification_hook_refuses_verified_without_a_session():
    out = quickpass.on_verification_post_save({"status": "verified"})
    assert out["ok"] is False
    assert "nothing behind it" in out["error"]


def test_verification_hook_says_verified_does_not_approve_checkin():
    out = quickpass.on_verification_post_save(
        {"status": "verified", "session_id": "s1"}
    )
    assert out["ok"] is True
    assert "does not approve check-in" in out["note"]


# ---------------------------------------------------------------------------
# Eligibility: payment is not access, identity is not access
# ---------------------------------------------------------------------------

BOOKING = {
    "booking_id": "BKG-1",
    "room_code": "ROOM-101",
    "guest_label": "Ada Obi",
    "booking_status": "confirmed",
}
PAID = {"payment_status": "confirmed", "amount": 240000}
VERIFIED = {"status": "verified", "provider": "didit",
            "verification_id": "VER-1", "updated_at": "2026-11-14T10:00:00Z"}


def test_eligible_when_paid_verified_and_roomed():
    out = guestops.check_in_eligibility(
        booking=BOOKING, payment=PAID, verification=VERIFIED
    )
    assert out["ok"] is True


def test_unpaid_guest_is_not_eligible():
    out = guestops.check_in_eligibility(
        booking=BOOKING, payment={"payment_status": "pending"},
        verification=VERIFIED,
    )
    assert out["ok"] is False
    assert any("not confirmed" in reason for reason in out["reasons"])


def test_missing_payment_is_not_eligible():
    out = guestops.check_in_eligibility(
        booking=BOOKING, payment=None, verification=VERIFIED
    )
    assert out["ok"] is False
    assert any("No payment" in reason for reason in out["reasons"])


def test_unverified_guest_is_not_eligible():
    out = guestops.check_in_eligibility(
        booking=BOOKING, payment=PAID,
        verification={"status": "pending"},
    )
    assert out["ok"] is False
    assert any("pending" in reason for reason in out["reasons"])


def test_booking_without_a_room_is_not_eligible():
    booking = dict(BOOKING, room_code="")
    out = guestops.check_in_eligibility(
        booking=booking, payment=PAID, verification=VERIFIED
    )
    assert out["ok"] is False


def test_cancelled_booking_is_not_eligible():
    booking = dict(BOOKING, booking_status="cancelled")
    out = guestops.check_in_eligibility(
        booking=booking, payment=PAID, verification=VERIFIED
    )
    assert out["ok"] is False


# ---------------------------------------------------------------------------
# Approval -> grant
# ---------------------------------------------------------------------------

def test_approval_issues_a_grant_for_the_room():
    out = guestops.approve_check_in(
        business_id="biz-1", booking=BOOKING, payment=PAID,
        verification=VERIFIED, actor="front-desk",
    )
    assert out["ok"] is True
    event = out["authorization_event"]
    assert event["status"] == "granted"
    assert event["room_code"] == "ROOM-101"
    assert event["expires_at"]
    assert event["issued_by"] == "front-desk"
    assert event["metadata"]["booking_id"] == "BKG-1"
    assert out["check_in"]["check_in_status"] == "approved"


def test_approval_is_refused_without_payment():
    out = guestops.approve_check_in(
        business_id="biz-1", booking=BOOKING, payment=None,
        verification=VERIFIED,
    )
    assert out["ok"] is False
    assert "payment" in out["error"].lower()


def test_approval_is_refused_without_verified_identity():
    out = guestops.approve_check_in(
        business_id="biz-1", booking=BOOKING, payment=PAID,
        verification={"status": "pending"},
    )
    assert out["ok"] is False


def test_review_required_needs_an_explicit_human_override():
    flagged = {"status": "review_required", "verification_id": "VER-1"}
    refused = guestops.approve_check_in(
        business_id="biz-1", booking=BOOKING, payment=PAID, verification=flagged,
    )
    assert refused["ok"] is False
    assert refused["review_required"] is True

    allowed = guestops.approve_check_in(
        business_id="biz-1", booking=BOOKING, payment=PAID, verification=flagged,
        override_review=True,
    )
    assert allowed["ok"] is True
    assert allowed["authorization_event"]["metadata"]["review_overridden"] is True


def test_approval_is_idempotent_per_booking():
    first = guestops.approve_check_in(
        business_id="biz-1", booking=BOOKING, payment=PAID, verification=VERIFIED,
    )
    second = guestops.approve_check_in(
        business_id="biz-1", booking=BOOKING, payment=PAID, verification=VERIFIED,
    )
    assert first["authorization_event"]["event_id"] == second["authorization_event"]["event_id"]
    assert first["check_in"]["check_in_id"] == second["check_in"]["check_in_id"]


def test_grant_expiry_is_bounded():
    out = guestops.approve_check_in(
        business_id="biz-1", booking=BOOKING, payment=PAID,
        verification=VERIFIED, ttl_hours=2,
    )
    event = out["authorization_event"]
    assert event["expires_at"] > event["issued_at"]


# ---------------------------------------------------------------------------
# Authorization hook
# ---------------------------------------------------------------------------

def test_authorization_hook_refuses_grant_without_expiry():
    out = guestops.on_authorization_post_save(
        {"status": "granted", "room_code": "ROOM-101"}
    )
    assert out["ok"] is False


def test_authorization_hook_refuses_bad_status():
    out = guestops.on_authorization_post_save(
        {"status": "maybe", "room_code": "ROOM-101", "expires_at": "2030-01-01"}
    )
    assert out["ok"] is False


def test_authorization_hook_accepts_revocation_without_expiry():
    out = guestops.on_authorization_post_save(
        {"status": "revoked", "room_code": "ROOM-101"}
    )
    assert out["ok"] is True


# ---------------------------------------------------------------------------
# Checkout: revoke, energy, housekeeping
# ---------------------------------------------------------------------------

def test_checkout_revokes_and_raises_housekeeping():
    out = guestops.checkout(
        business_id="biz-1", booking=BOOKING, device_code=None,
    )
    assert out["ok"] is True
    assert out["authorization_event"]["status"] == "revoked"
    assert out["task"]["kind"] == "housekeeping"
    assert out["task"]["status"] == "open"
    assert out["energy"]["action"] == "none"


def test_checkout_applies_the_energy_policy_when_a_device_exists():
    out = guestops.checkout(
        business_id="biz-1", booking=BOOKING, device_code="AZ3166-101",
    )
    assert out["ok"] is True
    assert out["energy"]["action"] in ("hold", "cut_non_essential")
    if out["energy"]["action"] == "cut_non_essential":
        assert out["command"]["command"] == "CUT_NON_ESSENTIAL"


def test_checkout_without_a_room_is_refused():
    out = guestops.checkout(
        business_id="biz-1", booking=dict(BOOKING, room_code=""), device_code=None,
    )
    assert out["ok"] is False


# ---------------------------------------------------------------------------
# Guest requests and tasks
# ---------------------------------------------------------------------------

def test_service_request_hook_accepts_known_category_and_status():
    out = guestops.on_service_request_post_save(
        {"category": "room_service", "status": "requested"}
    )
    assert out["ok"] is True


def test_service_request_hook_refuses_unknown_category():
    out = guestops.on_service_request_post_save(
        {"category": "yacht", "status": "requested"}
    )
    assert out["ok"] is False


def test_service_request_hook_refuses_unknown_status():
    out = guestops.on_service_request_post_save(
        {"category": "housekeeping", "status": "eventually"}
    )
    assert out["ok"] is False


def test_validate_request_normalizes_spaces():
    out = guestops.validate_request(
        {"booking_id": "BKG-1", "category": "Room Service", "detail": "Jollof"}
    )
    assert out["ok"] is True
    assert out["request"]["category"] == "room_service"


def test_validate_request_rejects_missing_booking():
    out = guestops.validate_request({"category": "housekeeping"})
    assert out["ok"] is False


def test_grant_is_live_respects_status_and_expiry():
    assert guestops.grant_is_live({"status": "granted",
                                  "expires_at": "2999-01-01T00:00:00+00:00"}) is True
    assert guestops.grant_is_live({"status": "revoked",
                                  "expires_at": "2999-01-01T00:00:00+00:00"}) is False
    assert guestops.grant_is_live({"status": "granted",
                                  "expires_at": "2000-01-01T00:00:00+00:00"}) is False
    assert guestops.grant_is_live(None) is False


# ---------------------------------------------------------------------------
# Applying a webhook (the receiver's contract)
# ---------------------------------------------------------------------------

def _signed(body: dict, secret: str = "secret", timestamp: str = ""):
    raw = _raw(body)
    sig = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    headers = {"X-Signature": sig}
    if timestamp:
        headers["X-Timestamp"] = timestamp
    return raw, headers


def test_webhook_application_normalizes_an_approval():
    raw, headers = _signed({"session_id": "s1", "status": "Approved"})
    out = quickpass.apply_webhook(raw, headers, "secret", now=int(time.time()))
    assert out["ok"] is True
    assert out["applied"] is True
    assert out["status"] == quickpass.VERIFIED
    assert out["patch"]["last_event_id"] == "s1:Approved:"


def test_webhook_application_refuses_an_unauthentic_body():
    raw = _raw({"session_id": "s1", "status": "Approved"})
    out = quickpass.apply_webhook(raw, {"X-Signature": "nope"}, "secret",
                                  now=int(time.time()))
    assert out["ok"] is False
    assert out["applied"] is False
    assert "patch" not in out


def test_webhook_application_never_turns_an_unknown_status_into_a_pass():
    raw, headers = _signed({"session_id": "s1", "status": "Approved by vibes"})
    out = quickpass.apply_webhook(raw, headers, "secret", now=int(time.time()))
    assert out["applied"] is True
    assert out["status"] == quickpass.ERROR


def test_webhook_application_does_not_apply_the_same_event_twice():
    raw, headers = _signed({"session_id": "s1", "status": "Approved"})
    first = quickpass.apply_webhook(raw, headers, "secret", now=int(time.time()))
    again = quickpass.apply_webhook(
        raw, headers, "secret", now=int(time.time()),
        current={"status": quickpass.VERIFIED,
                 "last_event_id": first["event_id"]},
    )
    assert again["ok"] is True
    assert again["applied"] is False
    assert again["duplicate"] is True


def test_webhook_application_cannot_reopen_a_finished_verification():
    raw, headers = _signed({"session_id": "s1", "status": "In Progress"})
    out = quickpass.apply_webhook(
        raw, headers, "secret", now=int(time.time()),
        current={"status": quickpass.REJECTED, "last_event_id": "older"},
    )
    assert out["ok"] is True
    assert out["applied"] is False
    assert out["stale"] is True
    assert out["status"] == quickpass.REJECTED


def test_simple_signature_requires_a_fresh_decision_fetch():
    body = {"session_id": "s1", "status": "Approved", "webhook_type": "status.updated"}
    raw = _raw(body)
    stamp = str(int(time.time()))
    envelope = stamp + ":s1:Approved:status.updated"
    sig = hmac.new(b"secret", envelope.encode("utf-8"), hashlib.sha256).hexdigest()
    out = quickpass.apply_webhook(
        raw, {"X-Signature-Simple": sig, "X-Timestamp": stamp}, "secret",
        now=int(time.time()))
    assert out["ok"] is True
    assert out["applied"] is False
    assert out["needs_fetch"] is True
