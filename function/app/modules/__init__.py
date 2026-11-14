"""PegPower platform module model — catalog, profiles, business modules,
configuration, and the authorization/event contract layer.

This is the corrected shared layer between modules. Modules publish and consume
platform-validated events and authorization contracts; they do not couple
directly to each other.

Existing QuickPass check_ins work and RoomPower code are preserved and
re-owned under this model — not rewritten.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Module catalogue
# ---------------------------------------------------------------------------

MODULES = {
    "bookings": {
        "name": "Bookings & Inventory",
        "category": "operations",
        "description": "Reservations, rooms, availability, pricing and booking management.",
        "surface": "admin",
        "requires_payment": False,
        "status": "available",
        "nav": {"label": "Bookings", "path": "/bookings", "icon": "calendar", "group": "operations"},
    },
    "quickpass": {
        "name": "QuickPass",
        "category": "guest",
        "description": "Guest identity verification, check-in, digital guest passes and occupant authorization.",
        "surface": "admin",
        "requires_payment": False,
        "status": "available",
        "nav": {"label": "QuickPass", "path": "/quickpass", "icon": "id-badge", "group": "guest"},
    },
    "roompower": {
        "name": "RoomPower",
        "category": "operations",
        "description": "Room controllers, electricity monitoring, commands, telemetry and energy alerts.",
        "surface": "admin",
        "requires_payment": False,
        "status": "available",
        "nav": {"label": "RoomPower", "path": "/roompower", "icon": "bolt", "group": "operations"},
    },
    "guesthub": {
        "name": "Guest Hub",
        "category": "guest",
        "description": "Personalized guest experience, room service, housekeeping requests, concierge and activities.",
        "surface": "both",
        "requires_payment": False,
        "status": "available",
        "nav": {"label": "Guest Hub", "path": "/guesthub", "icon": "sparkles", "group": "guest"},
    },
    "deals": {
        "name": "Deals",
        "category": "commerce",
        "description": "Flash deals, discounts, bundles, promotions, campaigns and rewards.",
        "surface": "both",
        "requires_payment": False,
        "status": "available",
        "nav": {"label": "Deals", "path": "/deals", "icon": "tag", "group": "commerce"},
    },
    "propertyops": {
        "name": "Property Ops",
        "category": "operations",
        "description": "Housekeeping, maintenance, staff tasks and operational workflows.",
        "surface": "admin",
        "requires_payment": False,
        "status": "available",
        "nav": {"label": "Property Ops", "path": "/propertyops", "icon": "tools", "group": "operations"},
    },
    "dining": {
        "name": "Dining",
        "category": "commerce",
        "description": "Menus, table reservations and restaurant operations.",
        "surface": "both",
        "requires_payment": False,
        "status": "planned",
        "nav": {"label": "Dining", "path": "/dining", "icon": "utensils", "group": "commerce"},
    },
    "spa": {
        "name": "Spa & Experiences",
        "category": "guest",
        "description": "Appointments, activities and experience bookings.",
        "surface": "both",
        "requires_payment": False,
        "status": "planned",
        "nav": {"label": "Spa", "path": "/spa", "icon": "flower", "group": "guest"},
    },
    "events": {
        "name": "Events",
        "category": "commerce",
        "description": "Event venue bookings, ticketing and admission.",
        "surface": "both",
        "requires_payment": False,
        "status": "planned",
        "nav": {"label": "Events", "path": "/events", "icon": "ticket", "group": "commerce"},
    },
}

#: Display order for module navigation. Modules not listed sort to the end.
NAV_ORDER = ["bookings", "quickpass", "roompower", "guesthub", "deals", "propertyops"]

# ---------------------------------------------------------------------------
# Business-type default profiles
#
# `requirement` is the profile's tier for the module:
#   required    - the business type cannot operate without it
#   recommended - most businesses of this type want it
#   optional    - available, but not expected
#
# `install` says whether a NEW business of this type gets the module installed.
# `enabled` says whether it starts switched on once installed. RoomPower is
# explicitly not auto-installed for any business type: it needs physical
# controllers, so the operator opts in.
# ---------------------------------------------------------------------------

PROFILE_TIERS = ("required", "recommended", "optional")


def _profile_row(module_id: str, requirement: str, *, install: bool, enabled: bool) -> dict[str, Any]:
    return {
        "module_id": module_id,
        "requirement": requirement,
        "recommended": requirement in ("required", "recommended"),
        "install": install,
        "default_enabled": enabled if install else None,
    }


PROFILES = {
    "hotel": [
        _profile_row("bookings", "required", install=True, enabled=True),
        _profile_row("quickpass", "required", install=True, enabled=True),
        _profile_row("roompower", "recommended", install=False, enabled=False),
        _profile_row("guesthub", "recommended", install=True, enabled=False),
        _profile_row("deals", "optional", install=False, enabled=False),
        _profile_row("propertyops", "recommended", install=True, enabled=True),
    ],
    "short_let": [
        _profile_row("bookings", "required", install=True, enabled=True),
        _profile_row("quickpass", "required", install=True, enabled=True),
        _profile_row("roompower", "recommended", install=False, enabled=False),
        _profile_row("guesthub", "optional", install=False, enabled=False),
        _profile_row("deals", "optional", install=False, enabled=False),
        _profile_row("propertyops", "recommended", install=True, enabled=True),
    ],
    "restaurant": [
        _profile_row("bookings", "required", install=True, enabled=True),
        _profile_row("quickpass", "optional", install=False, enabled=False),
        _profile_row("roompower", "optional", install=False, enabled=False),
        _profile_row("guesthub", "recommended", install=False, enabled=False),
        _profile_row("deals", "recommended", install=False, enabled=False),
        _profile_row("propertyops", "recommended", install=False, enabled=False),
    ],
    "spa": [
        _profile_row("bookings", "required", install=True, enabled=True),
        _profile_row("quickpass", "optional", install=False, enabled=False),
        _profile_row("roompower", "optional", install=False, enabled=False),
        _profile_row("guesthub", "recommended", install=False, enabled=False),
        _profile_row("deals", "recommended", install=False, enabled=False),
        _profile_row("propertyops", "optional", install=False, enabled=False),
    ],
    "event_venue": [
        _profile_row("bookings", "required", install=True, enabled=True),
        _profile_row("quickpass", "recommended", install=False, enabled=False),
        _profile_row("roompower", "optional", install=False, enabled=False),
        _profile_row("guesthub", "optional", install=False, enabled=False),
        _profile_row("deals", "recommended", install=False, enabled=False),
        _profile_row("propertyops", "optional", install=False, enabled=False),
    ],
    "mixed": [
        _profile_row("bookings", "required", install=True, enabled=True),
        _profile_row("quickpass", "recommended", install=False, enabled=False),
        _profile_row("roompower", "optional", install=False, enabled=False),
        _profile_row("guesthub", "optional", install=False, enabled=False),
        _profile_row("deals", "optional", install=False, enabled=False),
        _profile_row("propertyops", "recommended", install=True, enabled=True),
    ],
}

# ---------------------------------------------------------------------------
# Dependencies
#
# `requires` are hard module-to-module dependencies: the module cannot be
# installed enabled, nor enabled later, until each listed module is enabled.
# `recommends` are surfaced to the operator but never block.
# `platform` names a Core capability the module consumes. Core vouches for it
# (see PLATFORM_CAPABILITIES); it is deliberately NOT a dependency on QuickPass,
# so any authorization provider that emits the Core contract satisfies
# RoomPower.
# ---------------------------------------------------------------------------

MODULE_DEPENDENCIES = {
    "bookings": {"requires": [], "recommends": [], "platform": []},
    "quickpass": {"requires": [], "recommends": ["bookings"], "platform": ["bookings_context"]},
    "roompower": {"requires": [], "recommends": ["quickpass"], "platform": ["authorization"]},
    "guesthub": {"requires": ["quickpass"], "recommends": ["bookings"], "platform": ["authorization"]},
    "deals": {"requires": [], "recommends": ["bookings"], "platform": ["visit_context"]},
    "propertyops": {"requires": [], "recommends": ["bookings"], "platform": ["authorization"]},
}

#: Capabilities Core guarantees today. A module declaring anything else is a
#: programming error, not a runtime condition.
PLATFORM_CAPABILITIES = {
    "authorization",
    "bookings_context",
    "visit_context",
    "payment_status",
    "telemetry_ingest",
}

# ---------------------------------------------------------------------------
# In-memory stores (mirror the manifest tables; in a Workpeg deployment these
# are real tables the function reads/writes through the SDK).
# ---------------------------------------------------------------------------

CATALOG: dict[str, dict[str, Any]] = {}
PROFILES_STORE: dict[str, list[dict[str, Any]]] = {}
BUSINESS_MODULES: dict[str, dict[str, Any]] = {}  # keyed by business_id
MODULE_CONFIG: dict[str, dict[str, dict[str, Any]]] = {}  # business -> module -> key -> row
MODULE_EVENTS: list[dict[str, Any]] = []


class ModuleDependencyError(ValueError):
    """A module lifecycle change was refused by the dependency rules."""

    def __init__(self, message: str, *, blocked_by: list[str] | None = None,
                 missing: list[str] | None = None, platform: list[str] | None = None):
        super().__init__(message)
        self.message = message
        self.blocked_by = list(blocked_by or [])
        self.missing = list(missing or [])
        self.platform = list(platform or [])

    def to_payload(self) -> dict[str, Any]:
        return {
            "ok": False,
            "error": self.message,
            "dependency_error": True,
            "blocked_by": self.blocked_by,
            "missing": self.missing,
            "platform": self.platform,
        }


# ---------------------------------------------------------------------------
# Catalog helpers
# ---------------------------------------------------------------------------

def catalog_list() -> list[dict[str, Any]]:
    return [{"module_id": mid, **info} for mid, info in MODULES.items()]


def catalog_get(module_id: str) -> dict[str, Any] | None:
    info = MODULES.get(module_id)
    if not info:
        return None
    return {"module_id": module_id, **info}


def module_dependencies(module_id: str) -> dict[str, list[str]]:
    dep = MODULE_DEPENDENCIES.get(module_id) or {}
    return {
        "requires": list(dep.get("requires") or []),
        "recommends": list(dep.get("recommends") or []),
        "platform": list(dep.get("platform") or []),
    }


def missing_dependencies(business_id: str, module_id: str) -> dict[str, list[str]]:
    """Which of a module's dependencies are not currently satisfied.

    `requires` are unmet when the required module is not installed *and
    enabled* for this business. `platform` are unmet when Core does not
    declare the capability.
    """
    dep = module_dependencies(module_id)
    unmet_modules = [
        required
        for required in dep["requires"]
        if not module_is_enabled_for(business_id, required)
    ]
    unmet_platform = [cap for cap in dep["platform"] if cap not in PLATFORM_CAPABILITIES]
    return {"requires": unmet_modules, "platform": unmet_platform}


def dependents_of(module_id: str) -> list[str]:
    """Modules that hard-require `module_id`."""
    return [
        other
        for other, dep in MODULE_DEPENDENCIES.items()
        if module_id in (dep.get("requires") or [])
    ]


def module_gate(business_id: str, module_id: str) -> dict[str, Any] | None:
    """Gate a module's actions and data for a business.

    Returns None when the module may be used, or an error payload when it may
    not. A disabled module keeps its historical records but its actions and data
    access are unavailable to that business.
    """
    if not business_configured(business_id):
        return None
    if module_is_enabled_for(business_id, module_id):
        return None
    info = MODULES.get(module_id) or {}
    return {
        "ok": False,
        "error": f"{info.get('name', module_id)} is not enabled for this business",
        "module_id": module_id,
        "module_disabled": True,
    }


# ---------------------------------------------------------------------------
# Business-type default profile helpers
# ---------------------------------------------------------------------------

def profile_for(business_type: str) -> list[dict[str, Any]]:
    return [row.copy() for row in PROFILES.get(business_type, [])]


def business_types() -> list[str]:
    return sorted(PROFILES)


def business_configured(business_id: str) -> bool:
    """Has this business had its module configuration written yet?

    A business with no `business_modules` rows is in the legacy/unconfigured
    state that existed before the module model. Those keep working, so the
    migration does not silently switch off an existing business. Once a business
    has any module rows, gating applies: a module that is not enabled is
    unavailable.
    """
    return bool(BUSINESS_MODULES.get(business_id))


# ---------------------------------------------------------------------------
# business_modules helpers
# ---------------------------------------------------------------------------

def get_business_modules(business_id: str) -> dict[str, Any]:
    return BUSINESS_MODULES.get(business_id, {})


def enabled_modules(business_id: str, modules: dict[str, Any] | None = None) -> list[str]:
    modules = modules or get_business_modules(business_id)
    out: list[str] = []
    for module_id, row in modules.items():
        if row.get("enabled"):
            out.append(module_id)
    return out


def module_is_enabled_for(business_id: str, module_id: str, modules: dict[str, Any] | None = None) -> bool:
    modules = modules or get_business_modules(business_id)
    row = modules.get(module_id)
    if not row:
        return False
    return bool(row.get("enabled"))


def _record_event(business_id: str, module_id: str, action: str, *,
                  actor: str = "admin", detail: dict[str, Any] | None = None) -> dict[str, Any]:
    event = {
        "event_id": f"MEV-{len(MODULE_EVENTS) + 1:04d}",
        "business_id": business_id,
        "module_id": module_id,
        "action": action,
        "actor": actor,
        "at": _now(),
        "detail": dict(detail or {}),
    }
    MODULE_EVENTS.append(event)
    return event


def module_events(business_id: str, module_id: str | None = None) -> list[dict[str, Any]]:
    return [
        e for e in MODULE_EVENTS
        if e["business_id"] == business_id and (module_id is None or e["module_id"] == module_id)
    ]


def _assert_can_enable(business_id: str, module_id: str) -> None:
    unmet = missing_dependencies(business_id, module_id)
    if unmet["requires"] or unmet["platform"]:
        names = [catalog_get(m)["name"] if catalog_get(m) else m for m in unmet["requires"]]
        parts = []
        if names:
            parts.append("requires " + ", ".join(names) + " to be installed and enabled first")
        if unmet["platform"]:
            parts.append("requires unavailable platform capability " + ", ".join(unmet["platform"]))
        raise ModuleDependencyError(
            f"{catalog_get(module_id)['name']} " + "; ".join(parts),
            missing=unmet["requires"],
            platform=unmet["platform"],
        )


def install_module(
    business_id: str,
    module_id: str,
    *,
    enabled: bool | None = None,
    source: str = "admin",
    actor: str = "admin",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Install a module for a business.

    Installing disabled is always allowed. Installing enabled enforces the same
    dependency rules as `enable_module`, so a dependent module can never exist
    switched on without what it needs.
    """
    if catalog_get(module_id) is None:
        raise ModuleDependencyError(f"unknown module {module_id}")
    if enabled:
        _assert_can_enable(business_id, module_id)

    modules = BUSINESS_MODULES.setdefault(business_id, {})
    now = _now()
    if module_id in modules:
        row = modules[module_id]
        if enabled is not None:
            row["enabled"] = bool(enabled)
            if enabled:
                row["enabled_at"] = now
                row["disabled_at"] = None
        if source:
            row["source"] = source
        if metadata:
            row.setdefault("metadata", {}).update(metadata)
        row["updated_at"] = now
        _record_event(business_id, module_id, "reinstalled", actor=actor,
                      detail={"enabled": bool(row.get("enabled")), "source": source})
        return row

    row = {
        "business_module_id": f"BM-{len(modules) + 1:04d}",
        "business_id": business_id,
        "module_id": module_id,
        "installed": True,
        "enabled": bool(enabled) if enabled is not None else False,
        "installed_at": now,
        "enabled_at": now if enabled else None,
        "disabled_at": None,
        "source": source,
        "metadata": dict(metadata or {}),
        "updated_at": now,
    }
    modules[module_id] = row
    _record_event(business_id, module_id, "installed", actor=actor,
                  detail={"enabled": row["enabled"], "source": source})
    return row


def install_for_profile(business_id: str, business_type: str, *, source: str = "profile",
                        actor: str = "system") -> dict[str, Any]:
    """Apply a business type's profile to a new business.

    Only modules the profile installs are installed, and only those whose
    dependencies are met are switched on. RoomPower is not installed by any
    profile: it requires physical controllers, so the operator opts in.
    """
    installed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for entry in profile_for(business_type):
        module_id = entry["module_id"]
        if not entry.get("install"):
            skipped.append({"module_id": module_id, "reason": "not_installed_by_profile",
                            "requirement": entry["requirement"]})
            continue
        try:
            row = install_module(
                business_id,
                module_id,
                enabled=bool(entry.get("default_enabled")),
                source=source,
                actor=actor,
            )
        except ModuleDependencyError as exc:
            skipped.append({"module_id": module_id, "reason": exc.message,
                            "requirement": entry["requirement"]})
            continue
        installed.append(row)
    return {
        "business_id": business_id,
        "business_type": business_type,
        "installed": installed,
        "skipped": skipped,
        "surface": business_surface(business_id),
    }


def enable_module(business_id: str, module_id: str, *, source: str = "admin",
                  actor: str = "admin") -> dict[str, Any] | None:
    """Enable an installed module, enforcing hard dependencies."""
    row = _require_business_module(business_id, module_id)
    if row is None:
        return None
    _assert_can_enable(business_id, module_id)
    now = _now()
    was_disabled = row.get("enabled") is False
    row["enabled"] = True
    row["enabled_at"] = now
    row["disabled_at"] = None
    if source:
        row["source"] = source
    row["updated_at"] = now
    _record_event(business_id, module_id, "reactivated" if was_disabled else "enabled",
                  actor=actor, detail={"source": source})
    return row


def disable_module(business_id: str, module_id: str, *, actor: str = "admin",
                   force: bool = False) -> dict[str, Any] | None:
    """Disable a module without deleting its records or its configuration.

    Refused while another enabled module hard-requires it. `force` exists for
    deliberate operator escapes (e.g. decommissioning a business) and is
    recorded in the module event log.
    """
    row = _require_business_module(business_id, module_id)
    if row is None:
        return None

    blocking = [d for d in dependents_of(module_id) if module_is_enabled_for(business_id, d)]
    if blocking and not force:
        names = [catalog_get(m)["name"] if catalog_get(m) else m for m in blocking]
        raise ModuleDependencyError(
            f"{catalog_get(module_id)['name']} is required by "
            + ", ".join(names)
            + "; disable or remove those first",
            blocked_by=blocking,
        )

    now = _now()
    row["enabled"] = False
    row["disabled_at"] = now
    row["updated_at"] = now
    _record_event(business_id, module_id, "disabled", actor=actor,
                  detail={"forced": bool(force and blocking), "blocked_by": blocking})
    return row


def _require_business_module(business_id: str, module_id: str) -> dict[str, Any] | None:
    modules = BUSINESS_MODULES.get(business_id, {})
    return modules.get(module_id)


def business_surface(business_id: str) -> dict[str, Any]:
    """Everything the UI needs to render this business's module surface.

    This is the authoritative description of which modules exist for the
    business. The UI uses it to build navigation and to refuse a direct route
    to a module that is not enabled; the function gates the same modules again
    on every action, so the UI is convenience, not the security boundary.
    """
    modules = get_business_modules(business_id)
    configured = business_configured(business_id)
    rows: list[dict[str, Any]] = []
    for module_id, info in MODULES.items():
        row = modules.get(module_id) or {}
        enabled = bool(row.get("enabled")) if configured else False
        dep = module_dependencies(module_id)
        rows.append({
            "module_id": module_id,
            "name": info["name"],
            "category": info["category"],
            "surface": info["surface"],
            "status": info["status"],
            "nav": dict(info["nav"]),
            "installed": bool(row.get("installed")),
            "enabled": enabled,
            "missing_dependencies": missing_dependencies(business_id, module_id)["requires"],
            "requires": dep["requires"],
            "recommends": dep["recommends"],
        })

    def _order(item: dict[str, Any]) -> tuple[int, str]:
        mid = item["module_id"]
        return (NAV_ORDER.index(mid) if mid in NAV_ORDER else len(NAV_ORDER), mid)

    nav = [
        {"module_id": r["module_id"], **r["nav"]}
        for r in sorted(rows, key=_order)
        if r["enabled"] and r["status"] == "available"
    ]
    return {
        "business_id": business_id,
        "configured": configured,
        "enabled": enabled_modules(business_id),
        "disabled": [m for m, r in modules.items() if not r.get("enabled")],
        "modules": sorted(rows, key=_order),
        "nav": nav,
    }


# ---------------------------------------------------------------------------
# module_config helpers
# ---------------------------------------------------------------------------

def get_module_config(
    business_id: str, module_id: str, key: str | None = None
) -> dict[str, Any] | list[dict[str, Any]] | None:
    by_key = MODULE_CONFIG.setdefault(business_id, {}).setdefault(module_id, {})
    if key:
        return by_key.get(key)
    return list(by_key.values())


def set_module_config(
    business_id: str, module_id: str, key: str, value: Any
) -> dict[str, Any]:
    by_key = MODULE_CONFIG.setdefault(business_id, {}).setdefault(module_id, {})
    now = _now()
    existing = by_key.get(key)
    if existing:
        existing["value"] = value
        existing["updated_at"] = now
        return existing
    row: dict[str, Any] = {
        "business_config_id": f"BC-{len(by_key) + 1:04d}",
        "business_id": business_id,
        "module_id": module_id,
        "key": key,
        "value": value,
        "updated_at": now,
    }
    by_key[key] = row
    return row


def config_value(business_id: str, module_id: str, key: str, default: Any = None) -> Any:
    row = get_module_config(business_id, module_id, key)
    if isinstance(row, dict):
        return row.get("value", default)
    return default


# ---------------------------------------------------------------------------
# Authorization / event contract helpers
# ---------------------------------------------------------------------------

def build_authorization_event(
    *,
    event_id: str | None = None,
    business_id: str,
    room_code: str,
    authorization_type: str = "room_activation",
    status: str = "granted",
    source: str = "quickpass",
    issued_by: str = "system",
    expires_at: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a platform authorization event. This is the contract QuickPass and
    future compatible systems produce; RoomPower and other consumers consume it
    after Core validates tenant context and module activation state."""
    return {
        "event_id": event_id or f"EV-{_counter('events'):04d}",
        "business_id": business_id,
        "room_code": room_code,
        "authorization_type": authorization_type,
        "status": status,
        "source": source,
        "issued_by": issued_by,
        "issued_at": _now(),
        "expires_at": expires_at,
        "metadata": dict(metadata or {}),
    }


def revoke_authorization_event(
    *,
    event_id: str | None = None,
    business_id: str,
    room_code: str,
    authorization_type: str = "room_activation",
    source: str = "quickpass",
    issued_by: str = "system",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Emit an authorization revocation event (e.g. checkout)."""
    return build_authorization_event(
        event_id=event_id,
        business_id=business_id,
        room_code=room_code,
        authorization_type=authorization_type,
        status="revoked",
        source=source,
        issued_by=issued_by,
        metadata=metadata,
    )


def validate_authorization_event(event: dict[str, Any], business_id: str) -> dict[str, Any]:
    """Validate an authorization event at the platform layer: tenant context and
    basic shape. This is not a full policy engine yet; it is the seam where Core
    vouches for an event before modules act on it."""
    if not isinstance(event, dict):
        raise ValueError("authorization event must be a dict")
    if event.get("business_id") != business_id:
        raise ValueError("authorization event business_id does not match tenant")
    if not event.get("room_code"):
        raise ValueError("authorization event must include room_code")
    if not event.get("authorization_type"):
        raise ValueError("authorization event must include authorization_type")
    if not event.get("source"):
        raise ValueError("authorization event must include source")
    if not event.get("issued_at"):
        raise ValueError("authorization event must include issued_at")
    if event.get("status") not in ("granted", "revoked"):
        raise ValueError("authorization event status must be granted or revoked")
    return event


# ---------------------------------------------------------------------------
# tiny helpers
# ---------------------------------------------------------------------------

_counter_state: dict[str, int] = {}


def _counter(bucket: str) -> int:
    _counter_state[bucket] = _counter_state.get(bucket, 0) + 1
    return _counter_state[bucket]


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def describe_module(module_id: str) -> dict[str, Any] | None:
    """Public description of a module for the Peg Marketplace catalog UI."""
    info = MODULES.get(module_id)
    if not info:
        return None
    return {
        "module_id": module_id,
        "name": info.get("name"),
        "category": info.get("category"),
        "description": info.get("description"),
        "surface": info.get("surface"),
        "requires_payment": info.get("requires_payment", False),
        "status": info.get("status", "available"),
        "nav": dict(info.get("nav") or {}),
        "requirements": module_dependencies(module_id),
    }
