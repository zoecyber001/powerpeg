"""QuickPass/PegPower consolidated function package.

This package is the runtime surface of the one peg (pegpower). It contains:

* app.main — the Workpeg function entrypoint and the legacy in-memory
  room/booking/payment/device/command/telemetry/alert model.
* app.platform — the QuickPass module model: MODULES catalogue,
  module_profile table shape, profile helpers, and build_surface with the
  check_ins room-activation coil.
* app.checkins — the check_ins-driven room activation module: create,
  verify, approve, activate, check_out, list, plus an in-memory store and
  audit trail for offline validation.
"""

from . import authorization
from . import checkins
from . import modules
from . import platform

# Re-export the platform module model and authorization layer for other
# module code to use without importing internals.
from .modules import (
    MODULE_DEPENDENCIES,
    PROFILES,
    business_configured,
    business_types,
    catalog_get,
    catalog_list,
    describe_module,
    disable_module,
    enable_module,
    enabled_modules,
    get_business_modules,
    get_module_config,
    install_module,
    module_gate,
    module_is_enabled_for,
    profile_for,
    set_module_config,
)
from .authorization import (
    authorize_room_activation,
    ensure_module_enabled,
    is_module_installed_and_enabled,
    last_authorized_room_activation,
    revoke_room_activation,
)
from .checkins import (
    activate_room,
    approve_check_in,
    check_out,
    create_check_in,
    get_check_in,
    list_check_ins,
    verify_check_in,
)
from .platform import (
    MODULES,
    build_surface,
    business_table_columns,
    default_module_profile,
    inventory_table_columns,
    module_is_live,
    module_profile_table_columns,
)

__all__ = [
    "MODULES",
    "MODULE_DEPENDENCIES",
    "PROFILES",
    "activate_room",
    "approve_check_in",
    "authorize_room_activation",
    "build_surface",
    "business_configured",
    "business_table_columns",
    "business_types",
    "catalog_get",
    "catalog_list",
    "check_out",
    "create_check_in",
    "default_module_profile",
    "describe_module",
    "disable_module",
    "enable_module",
    "enabled_modules",
    "ensure_module_enabled",
    "get_business_modules",
    "get_check_in",
    "get_module_config",
    "install_module",
    "inventory_table_columns",
    "is_module_installed_and_enabled",
    "last_authorized_room_activation",
    "list_check_ins",
    "module_gate",
    "module_is_enabled_for",
    "module_is_live",
    "module_profile_table_columns",
    "profile_for",
    "revoke_room_activation",
    "set_module_config",
    "verify_check_in",
]
