"""The QuickPass/PegPower module model for the consolidated peg.

One peg (pegpower), multiple modules. A business opts into modules; a module
that is off is invisible to that business and the UI renders one honest
sentence when a module is off.

Design notes
------------

* This module is the source of truth for the module-gated surface the UI renders
  and for the check_ins room-activation coil.
* The room-activation coil is the consolidation's key idea: PegPower room-power
  control becomes the QuickPass smart-room activation layer, and it is driven by
  an authorized check-in record, not by reservation approval.
* Identity & Trust is a separate layer from physical room activation. Identity
  verification does not, by itself, turn power on. Physical activation is owned
  by smart_room and is driven by the check_ins coil: a check-in must be verified
  AND approved before the room is activated.
* A module that is disabled in module_config is treated as off even if it is in
  enabled_modules. This lets an admin turn a module off without editing the
  enabled list.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Module catalogue
# ---------------------------------------------------------------------------

MODULES = {
    "accommodation": {
        "name": "Accommodation",
        "description": "Rooms, stays, check-in/out and room-level operations.",
    },
    "dining": {
        "name": "Dining",
        "description": "Tables, reservations, menus and dining offers.",
    },
    "spa": {
        "name": "Spa & Wellness",
        "description": "Appointments, sessions and wellness packages.",
    },
    "events": {
        "name": "Events & Venue",
        "description": "Tickets, timed entries and venue bookings.",
    },
    "guest_hub": {
        "name": "Guest Hub",
        "description": "The personalized post-booking customer experience.",
    },
    "qr": {
        "name": "QR",
        "description": "Storefront, walk-in, guest check-in and room/service QR.",
    },
    "smart_room": {
        "name": "Smart Room & Energy",
        "description": "Device control, telemetry, anomalies and overrides. In the consolidation this module owns physical room activation via the check_ins coil.",
    },
    "promotions": {
        "name": "Promotions",
        "description": "Flash deals, bundles, campaigns and deal management.",
    },
    "identity": {
        "name": "Identity & Trust",
        "description": "Verification, guest passes and trust credentials. In the consolidation this module is the face-verification and guest-authorisation layer; it does not, by itself, authorise a room. Physical room activation is owned by the smart_room module and is driven by the check_ins coil.",
    },
    "staff": {
        "name": "Staff & Roles",
        "description": "Teams, roles and permissions.",
    },
}


# ---------------------------------------------------------------------------
# Tenant / business
# ---------------------------------------------------------------------------

def business_table_columns() -> list[dict[str, Any]]:
    """The columns that describe a hospitality business / tenant."""
    return [
        {"name": "business_id", "type": "text", "primary": True},
        {"name": "name", "type": "text"},
        {"name": "category", "type": "text"},
        {"name": "status", "type": "text"},
        {"name": "contact_email", "type": "text"},
        {"name": "contact_phone", "type": "text"},
        {"name": "address", "type": "text"},
        {"name": "time_zone", "type": "text"},
        {"name": "currency", "type": "text"},
        {"name": "locale", "type": "text"},
        {"name": "owner_id", "type": "text"},
        {"name": "created_at", "type": "timestamp"},
        {"name": "updated_at", "type": "timestamp"},
    ]


# ---------------------------------------------------------------------------
# Module profile
# ---------------------------------------------------------------------------

def module_profile_table_columns() -> list[dict[str, Any]]:
    """DEPRECATED: shape of the legacy per-business aggregate, now the
    `business_module_settings` table in the manifest.

    Superseded by the platform module model in app.modules:
    `module_catalog` (available modules), `module_profile` (business-type
    defaults), `business_modules` (per-business install/enable state) and
    `module_config` (per business/module settings). Kept so existing rows and
    callers keep working; nothing deletes historical data on disable.
    """
    return [
        {"name": "business_id", "type": "text", "primary": True},
        {"name": "enabled_modules", "type": "json"},
        {"name": "module_config", "type": "json"},
        {"name": "updated_at", "type": "datetime"},
    ]


def default_module_profile() -> dict[str, Any]:
    """A fresh business has no enabled modules until an owner opts in."""
    return {
        "business_id": None,
        "enabled_modules": [],
        "module_config": {},
        "updated_at": None,
    }


def module_is_live(profile: dict[str, Any], module: str) -> bool:
    """A module is live for a business when it is in enabled_modules and not
    disabled in module_config."""
    if module not in profile.get("enabled_modules", []):
        return False
    config = profile.get("module_config", {})
    if module in config and isinstance(config[module], dict):
        if config[module].get("enabled") is False:
            return False
    return True


# ---------------------------------------------------------------------------
# Inventory / resources
# ---------------------------------------------------------------------------

INVENTORY_KINDS = {
    "room": "Accommodation room or unit.",
    "table": "Dining table.",
    "slot": "Bookable appointment or session slot.",
    "ticket": "Event or venue ticket / timed entry.",
    "day_use": "Day-use access pass.",
    "package": "Bundled hospitality package.",
}


def inventory_table_columns() -> list[dict[str, Any]]:
    """Flexible inventory: one row per bookable resource."""
    return [
        {"name": "inventory_id", "type": "text", "primary": True},
        {"name": "business_id", "type": "text"},
        {"name": "module", "type": "text"},
        {"name": "kind", "type": "text"},
        {"name": "name", "type": "text"},
        {"name": "description", "type": "text"},
        {"name": "capacity", "type": "integer"},
        {"name": "price", "type": "decimal"},
        {"name": "currency", "type": "text"},
        {"name": "status", "type": "text"},
        {"name": "metadata", "type": "json"},
        {"name": "created_at", "type": "timestamp"},
        {"name": "updated_at", "type": "timestamp"},
    ]


def availability_table_columns() -> list[dict[str, Any]]:
    """Availability windows and blackout dates per resource."""
    return [
        {"name": "availability_id", "type": "text", "primary": True},
        {"name": "inventory_id", "type": "text"},
        {"name": "business_id", "type": "text"},
        {"name": "starts_at", "type": "timestamp"},
        {"name": "ends_at", "type": "timestamp"},
        {"name": "capacity", "type": "integer"},
        {"name": "status", "type": "text"},
        {"name": "created_at", "type": "timestamp"},
    ]


# ---------------------------------------------------------------------------
# Bookings
# ---------------------------------------------------------------------------

def booking_table_columns() -> list[dict[str, Any]]:
    """Shared booking core. The shape adapts to the business's enabled modules."""
    return [
        {"name": "booking_id", "type": "text", "primary": True},
        {"name": "business_id", "type": "text"},
        {"name": "customer_id", "type": "text"},
        {"name": "module", "type": "text"},
        {"name": "inventory_id", "type": "text"},
        {"name": "status", "type": "text"},
        {"name": "starts_at", "type": "timestamp"},
        {"name": "ends_at", "type": "timestamp"},
        {"name": "guests", "type": "integer"},
        {"name": "price", "type": "decimal"},
        {"name": "currency", "type": "text"},
        {"name": "payment_id", "type": "text"},
        {"name": "metadata", "type": "json"},
        {"name": "created_at", "type": "timestamp"},
        {"name": "updated_at", "type": "timestamp"},
    ]


def booking_status_options() -> list[str]:
    return [
        "pending",
        "confirmed",
        "approved",
        "checked_in",
        "in_progress",
        "completed",
        "cancelled",
        "no_show",
    ]


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------

def payment_table_columns() -> list[dict[str, Any]]:
    """Payments are platform events, not card storage."""
    return [
        {"name": "payment_id", "type": "text", "primary": True},
        {"name": "business_id", "type": "text"},
        {"name": "customer_id", "type": "text"},
        {"name": "booking_id", "type": "text"},
        {"name": "amount", "type": "decimal"},
        {"name": "currency", "type": "text"},
        {"name": "status", "type": "text"},
        {"name": "provider_reference", "type": "text"},
        {"name": "metadata", "type": "json"},
        {"name": "created_at", "type": "timestamp"},
        {"name": "updated_at", "type": "timestamp"},
    ]


def payment_status_options() -> list[str]:
    return [
        "pending",
        "authorized",
        "captured",
        "failed",
        "refunded",
        "disputed",
    ]


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

def notification_table_columns() -> list[dict[str, Any]]:
    """Out-of-band customer and staff notifications."""
    return [
        {"name": "notification_id", "type": "text", "primary": True},
        {"name": "business_id", "type": "text"},
        {"name": "customer_id", "type": "text"},
        {"name": "staff_id", "type": "text"},
        {"name": "type", "type": "text"},
        {"name": "subject", "type": "text"},
        {"name": "body", "type": "text"},
        {"name": "status", "type": "text"},
        {"name": "channel", "type": "text"},
        {"name": "created_at", "type": "timestamp"},
        {"name": "updated_at", "type": "timestamp"},
    ]


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

def audit_table_columns() -> list[dict[str, Any]]:
    """Administrative and operational actions on the platform."""
    return [
        {"name": "audit_id", "type": "text", "primary": True},
        {"name": "business_id", "type": "text"},
        {"name": "actor_id", "type": "text"},
        {"name": "actor_type", "type": "text"},
        {"name": "action", "type": "text"},
        {"name": "resource_type", "type": "text"},
        {"name": "resource_id", "type": "text"},
        {"name": "before", "type": "json"},
        {"name": "after", "type": "json"},
        {"name": "metadata", "type": "json"},
        {"name": "created_at", "type": "timestamp"},
    ]


# ---------------------------------------------------------------------------
# Derived surface
# ---------------------------------------------------------------------------

def build_surface(profile: dict[str, Any]) -> dict[str, Any]:
    """Turn a module profile into the module-aware surface the UI renders.

    This is where the consolidation's room-activation coil is expressed: the
    peg only drives physical room activation when BOTH smart_room and identity
    are enabled for the business. If either is off, the peg still tracks
    check-ins and authorisation, but it does not claim to activate a room.
    """
    enabled = profile.get("enabled_modules", [])
    config = profile.get("module_config", {})

    smart_room_enabled = module_is_live(profile, "smart_room")
    identity_enabled = module_is_live(profile, "identity")

    room_activation_coil = None
    if smart_room_enabled and identity_enabled:
        room_activation_coil = {
            "source": "check_ins",
            "requires_verified": True,
            "requires_approved": True,
            "activates_device": True,
        }

    return {
        "enabled": enabled,
        "smart_room_enabled": smart_room_enabled,
        "identity_enabled": identity_enabled,
        "qr_enabled": "qr" in enabled,
        "guest_hub_enabled": "guest_hub" in enabled,
        "promotions_enabled": "promotions" in enabled,
        "staff_enabled": "staff" in enabled,
        "room_activation_coil": room_activation_coil,
    }
