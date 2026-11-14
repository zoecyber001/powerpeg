"""Staff roles: who may do what, as one explicit catalog.

Access control in PegPower is a product feature, not a platform afterthought:
five hospitality roles, eight permissions, and one matrix naming which role
holds which. `main()` consults the matrix before every mutating action it
serves, and refuses under-privileged and unidentified callers loudly.

How the caller's role travels
-----------------------------
An action call states its role in the payload's ``actor_role`` field. The
function cannot know the caller itself (a save hook carries no person), so
identification is declarative and the refusal is on the record: a caller that
names no role is refused, not silently promoted. The workspace UI derives its
own copy of the role from this business's ``staff_members`` table — matched on
the signed-in user — and sends it with every call; a person not on the staff
list has no staff role.

Hooks are the platform's own saves: they carry no actor by design and are not
gated here.
"""
from __future__ import annotations

from typing import Any

#: The permission verbs. Eight is deliberate: broad enough to name every
#: mutating action, small enough to read as one table.
PERMISSIONS: dict[str, str] = {
    "bookings.write": "Create, allocate and cancel reservations",
    "payments.record": "Record and confirm payments",
    "identity.record": "Start and record identity checks",
    "checkin.approve": "Approve a check-in",
    "checkout.run": "Run the checkout and close the stay",
    "devices.command": "Queue device commands and room activation",
    "settings.manage": "Install and configure modules, policies and webhooks",
    "staff.manage": "Manage the staff list and who holds which role",
}

#: The roles, and each one's permission set. The owner holds everything; the
#: manager everything but the staff list; the desk the guest-facing flow;
#: housekeeping and maintenance their own trades.
ROLES: dict[str, dict[str, Any]] = {
    "owner": {
        "label": "Owner",
        "description": "The business's principal: everything, including who"
        " else holds which role.",
        "permissions": sorted(PERMISSIONS),
    },
    "manager": {
        "label": "Manager",
        "description": "Runs the operation day to day; does not manage the"
        " staff list itself.",
        "permissions": sorted(set(PERMISSIONS) - {"staff.manage"}),
    },
    "front_desk": {
        "label": "Front desk",
        "description": "The arrival desk: payments, identity checks,"
        " approving check-ins and running checkouts.",
        "permissions": ["bookings.write", "payments.record", "identity.record",
                        "checkin.approve", "checkout.run"],
    },
    "housekeeping": {
        "label": "Housekeeping",
        "description": "Rooms and tasks: the stay's closing tasks and the"
        " room's readiness.",
        "permissions": ["tasks.manage"],
    },
    "maintenance": {
        "label": "Maintenance",
        "description": "The room's hardware: device commands and room"
        " activation when the desk asks.",
        "permissions": ["devices.command"],
    },
}

#: Which permission each mutating action requires. Actions absent from this
#: map are reads: they change nothing, so any signed-in caller may run them.
ACTION_PERMISSIONS: dict[str, str] = {
    # Reservations and inventory
    "booking_create": "bookings.write",
    "create_booking": "bookings.write",
    "cancel_booking": "bookings.write",
    "allocate_room": "bookings.write",
    "inventory_add": "bookings.write",
    "booking_flow": "bookings.write",
    # Payments
    "confirm_payment": "payments.record",
    # Identity
    "check_in_create": "identity.record",
    "check_in_verify": "identity.record",
    # The desk's approval, and the activation it causes
    "check_in_approve": "checkin.approve",
    "checkin_approve": "checkin.approve",
    "check_in_activate": "checkin.approve",
    "dispatch_activation": "checkin.approve",
    # Checkout
    "check_in_check_out": "checkout.run",
    "checkout_plan": "checkout.run",
    "dispatch_checkout": "checkout.run",
    "revoke_room_activation": "checkout.run",
    # Devices
    "authorize_room_activation": "devices.command",
    "queue_command": "devices.command",
    "command_cancel": "devices.command",
    "command_expire": "devices.command",
    "override_power": "devices.command",
    # Configuration
    "module_install": "settings.manage",
    "module_enable": "settings.manage",
    "module_disable": "settings.manage",
    "checkout_policy_set": "settings.manage",
    "quickpass_webhook_config": "settings.manage",
    "dev_initialize_business": "settings.manage",
    # Staff
    "staff_add": "staff.manage",
    "staff_remove": "staff.manage",
}


def normalize_role(value: Any) -> str:
    """A role name as the catalog spells it, or "" for no role at all."""
    role = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "frontdesk": "front_desk",
        "desk": "front_desk",
        "reception": "front_desk",
        "receptionist": "front_desk",
        "housekeeper": "housekeeping",
        "engineer": "maintenance",
        "admin": "owner",
    }
    return aliases.get(role, role)


def permissions_for(role: Any) -> list[str]:
    """The permission set a role holds; the empty list for no role."""
    entry = ROLES.get(normalize_role(role))
    return list(entry["permissions"]) if entry else []


def role_may(role: Any, permission: str) -> bool:
    """May this role run actions that need this permission?

    An unidentified caller ("") may not: access control that defaults to
    yes is decoration, not a control.
    """
    return permission in permissions_for(role)


def permission_for_action(action: str) -> str | None:
    """The permission an action requires, or None for an open (read) one."""
    return ACTION_PERMISSIONS.get(str(action or ""))


def refuse(action: str, role: Any) -> dict[str, Any]:
    """The loud refusal main() returns for a privileged action."""
    permission = permission_for_action(action) or "unknown"
    named = normalize_role(role)
    if not named:
        reason = ("no role was stated with the call; state one in"
                  " actor_role")
    else:
        reason = (f"the role '{named}' does not hold the"
                  f" '{permission}' permission")
    return {
        "ok": False,
        "refused": True,
        "error": f"access control: {action!r} needs '{permission}'; {reason}",
        "role": named,
        "permission": permission,
        "action": action,
    }


def catalog() -> dict[str, Any]:
    """The whole model in one dict, for the roles action and the tests."""
    return {"roles": ROLES, "permissions": PERMISSIONS,
            "actions": ACTION_PERMISSIONS}
