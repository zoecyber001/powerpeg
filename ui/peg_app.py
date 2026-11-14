"""The shared page base: every page reads and writes the business's own
tables through `self.table(name)`, which creates a missing table from
the manifest's definition on first use. A business that has never
opened a page gets its tables then, instead of a refusal to read.

The compiler compiles page methods, not free functions, so the ensure
logic lives on the base class the pages share."""

from workpeg.ui import App, workpeg

TABLES = {
    "rooms": [
        {"name": "room_code", "type": "string", "required": True},
        {"name": "display_name", "type": "string", "required": True},
        {"name": "status", "type": "string"},
        {"name": "room_type", "type": "string"},
        {"name": "rate", "type": "number"},
        {"name": "area", "type": "string"},
        {"name": "star_rating", "type": "number"},
        {"name": "pitch", "type": "string"},
        {"name": "assigned_device_id", "type": "string"},
        {"name": "authorised", "type": "boolean"},
        {"name": "authorised_reason", "type": "string"},
        {"name": "updated_at", "type": "datetime"},
    ],
    "bookings": [
        {"name": "booking_id", "type": "string", "required": True},
        {"name": "room_code", "type": "string", "required": True},
        {"name": "guest_label", "type": "string", "required": True},
        {"name": "start_at", "type": "datetime", "required": True},
        {"name": "end_at", "type": "datetime", "required": True},
        {"name": "booking_status", "type": "string"},
    ],
    "payments": [
        {"name": "payment_id", "type": "string", "required": True},
        {"name": "booking_id", "type": "string", "required": True},
        {"name": "payment_status", "type": "string", "required": True},
        {"name": "amount", "type": "number"},
        {"name": "is_simulated", "type": "boolean"},
        {"name": "updated_at", "type": "datetime"},
    ],
    "devices": [
        {"name": "device_code", "type": "string", "required": True},
        {"name": "room_code", "type": "string"},
        {"name": "device_type", "type": "string"},
        {"name": "connection_status", "type": "string"},
        {"name": "reported_relay_state", "type": "string"},
        {"name": "last_seen_at", "type": "datetime"},
        {"name": "firmware", "type": "string"},
    ],
    "commands": [
        {"name": "command_id", "type": "string", "required": True},
        {"name": "device_code", "type": "string", "required": True},
        {"name": "command", "type": "string", "required": True},
        {"name": "status", "type": "string"},
        {"name": "room_code", "type": "string"},
        {"name": "issued_at", "type": "datetime"},
        {"name": "sent_at", "type": "datetime"},
        {"name": "expires_at", "type": "datetime"},
        {"name": "acknowledged_at", "type": "datetime"},
        {"name": "authorization_event_id", "type": "string"},
        {"name": "idempotency_key", "type": "string"},
        {"name": "failure_reason", "type": "string"},
        {"name": "device_reported_state", "type": "json"},
    ],
    "device_reports": [
        {"name": "report_id", "type": "text"},
        {"name": "device_code", "type": "text"},
        {"name": "room_code", "type": "text"},
        {"name": "command_id", "type": "text"},
        {"name": "relay_state", "type": "text"},
        {"name": "source", "type": "text"},
        {"name": "reported_at", "type": "text"},
        {"name": "note", "type": "text"},
    ],
    "telemetry": [
        {"name": "room_code", "type": "string", "required": True},
        {"name": "voltage", "type": "number"},
        {"name": "current", "type": "number"},
        {"name": "power", "type": "number"},
        {"name": "energy", "type": "number"},
        {"name": "is_simulated", "type": "boolean"},
        {"name": "observed_at", "type": "datetime"},
    ],
    "alerts": [
        {"name": "alert_id", "type": "string", "required": True},
        {"name": "room_code", "type": "string", "required": True},
        {"name": "alert_type", "type": "string", "required": True},
        {"name": "severity", "type": "string"},
        {"name": "description", "type": "string", "required": True},
        {"name": "status", "type": "string"},
    ],
    "check_ins": [
        {"name": "check_in_id", "type": "string", "required": True},
        {"name": "booking_id", "type": "string", "required": True},
        {"name": "room_code", "type": "string", "required": True},
        {"name": "guest_label", "type": "string", "required": True},
        {"name": "arrived_at", "type": "datetime"},
        {"name": "verified_at", "type": "datetime"},
        {"name": "approved_at", "type": "datetime"},
        {"name": "activated_at", "type": "datetime"},
        {"name": "check_in_status", "type": "string"},
    ],
    "authorizations": [
        {"name": "event_id", "type": "string", "required": True},
        {"name": "business_id", "type": "string", "required": True},
        {"name": "room_code", "type": "string", "required": True},
        {"name": "authorization_type", "type": "string"},
        {"name": "status", "type": "string", "required": True},
        {"name": "source", "type": "string"},
        {"name": "issued_by", "type": "string"},
        {"name": "issued_at", "type": "datetime"},
        {"name": "expires_at", "type": "datetime"},
        {"name": "metadata", "type": "json"},
    ],
    "verifications": [
        {"name": "verification_id", "type": "string", "required": True},
        {"name": "booking_id", "type": "string", "required": True},
        {"name": "guest_label", "type": "string"},
        {"name": "room_code", "type": "string"},
        {"name": "provider", "type": "string"},
        {"name": "session_id", "type": "string"},
        {"name": "verification_url", "type": "string"},
        {"name": "provider_status", "type": "string"},
        {"name": "status", "type": "string"},
        {"name": "decision", "type": "string"},
        {"name": "reviewed_by", "type": "string"},
        {"name": "created_at", "type": "datetime"},
        {"name": "updated_at", "type": "datetime"},
        {"name": "last_event_id", "type": "string"},
    ],
    "service_requests": [
        {"name": "request_id", "type": "string", "required": True},
        {"name": "booking_id", "type": "string", "required": True},
        {"name": "room_code", "type": "string"},
        {"name": "guest_label", "type": "string"},
        {"name": "category", "type": "string", "required": True},
        {"name": "detail", "type": "string"},
        {"name": "status", "type": "string"},
        {"name": "assigned_to", "type": "string"},
        {"name": "created_at", "type": "datetime"},
        {"name": "updated_at", "type": "datetime"},
    ],
    "staff_tasks": [
        {"name": "task_id", "type": "string", "required": True},
        {"name": "business_id", "type": "string"},
        {"name": "kind", "type": "string", "required": True},
        {"name": "room_code", "type": "string"},
        {"name": "detail", "type": "string"},
        {"name": "status", "type": "string"},
        {"name": "assigned_to", "type": "string"},
        {"name": "created_at", "type": "datetime"},
    ],
    "business_module_settings": [
        {"name": "business_id", "type": "string", "required": True},
        {"name": "enabled_modules", "type": "json"},
        {"name": "module_config", "type": "json"},
        {"name": "updated_at", "type": "datetime"},
    ],
    "module_catalog": [
        {"name": "module_id", "type": "string", "required": True},
        {"name": "name", "type": "string", "required": True},
        {"name": "description", "type": "string"},
        {"name": "category", "type": "string"},
        {"name": "version", "type": "string"},
        {"name": "status", "type": "string"},
        {"name": "surface", "type": "string"},
        {"name": "requires_payment", "type": "boolean"},
        {"name": "metadata", "type": "json"},
    ],
    "module_profile": [
        {"name": "profile_id", "type": "string", "required": True},
        {"name": "business_type", "type": "string", "required": True},
        {"name": "module_id", "type": "string", "required": True},
        {"name": "recommended", "type": "boolean"},
        {"name": "default_enabled", "type": "boolean"},
        {"name": "sort_order", "type": "number"},
        {"name": "metadata", "type": "json"},
    ],
    "business_modules": [
        {"name": "business_module_id", "type": "string", "required": True},
        {"name": "business_id", "type": "string", "required": True},
        {"name": "module_id", "type": "string", "required": True},
        {"name": "installed", "type": "boolean"},
        {"name": "enabled", "type": "boolean"},
        {"name": "installed_at", "type": "datetime"},
        {"name": "enabled_at", "type": "datetime"},
        {"name": "disabled_at", "type": "datetime"},
        {"name": "source", "type": "string"},
        {"name": "metadata", "type": "json"},
    ],
    "module_config": [
        {"name": "business_config_id", "type": "string", "required": True},
        {"name": "business_id", "type": "string", "required": True},
        {"name": "module_id", "type": "string", "required": True},
        {"name": "key", "type": "string", "required": True},
        {"name": "value", "type": "json"},
        {"name": "updated_at", "type": "datetime"},
    ],
    "staff_members": [
        {"name": "staff_member_id", "type": "string", "required": True},
        {"name": "name", "type": "string", "required": True},
        {"name": "email", "type": "string"},
        {"name": "role", "type": "string"},
        {"name": "status", "type": "string"},
        {"name": "created_at", "type": "datetime"},
        {"name": "updated_at", "type": "datetime"},
    ],
}


class PegPage(App):
    """The pages' common base: platform-table access that provisions."""

    async def table(self, name):
        """This business's table with that name, created if absent.

        Reading a table the business has never used would answer "no such
        table"; the definition comes from the peg manifest's own shape.
        Returns the table (with its uuid) or None for an unknown name."""
        tables = await workpeg.get_tables()
        for candidate in tables:
            if candidate.get("name") == name:
                return candidate
        definition = TABLES.get(name)
        if definition is None:
            return None
        return await workpeg.create_table({"name": name,
                                            "columns": definition})
