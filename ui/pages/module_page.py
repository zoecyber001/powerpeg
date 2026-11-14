"""One guarded page for every module route: ``/m/[module_id]``.

The platform has no UI-to-function bridge, so a page cannot ask the function
"is this module on?" — it reads the same ``business_modules`` table the
function gated on. The guard matters because a URL can be typed directly: a
module the business has not enabled answers with one honest sentence instead
of rendering an empty imitation of itself.

A business with no ``business_modules`` rows is *unconfigured* — an existing
business that predates modules — so nothing is hidden from it.
"""
from workpeg.ui import (
    App, State, Padding, Column, Text, Button, biz_url, navigate, route,
    set_title, workpeg,
)

from components import EmptyState, ErrorState, LoadingState, PageHeader




class ModulePage(App):
    loading = State(True)
    error = State("")
    legacy = State(False)
    #: module id -> "enabled" | "disabled" | "not installed"
    states = State({})
    #: module id -> the name the platform catalogue uses
    titles = State({
        "bookings": "Bookings",
        "quickpass": "QuickPass",
        "roompower": "RoomPower",
        "guesthub": "Guest Hub",
        "deals": "Deals",
        "propertyops": "Property Ops",
    })

    async def on_mount(self):
        set_title("Module")
        await self.load()

    async def table(self, name):
        """This business's table with that name, created if absent.

        The definitions mirror the manifest, so a table the business
        has never used is created here on first use instead of
        answering "no such table"."""
        defs = {}
        defs["business_modules"] = [
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
        ]
        tables = await workpeg.get_tables()
        for candidate in tables:
            if candidate.get("name") == name:
                return candidate
        definition = defs.get(name)
        if definition is None:
            return None
        return await workpeg.create_table({"name": name,
                                            "columns": definition})
    async def load(self):
        try:
            self.error = ""
            table = await self.table("business_modules")
            found = {}
            if table is not None:
                rows = await workpeg.get_rows(table["uuid"], limit=100)
                for row in rows:
                    data = row.get("data") or {}
                    module_id = data.get("module_id")
                    state = "not installed"
                    if data.get("installed") and data.get("enabled"):
                        state = "enabled"
                    elif data.get("installed"):
                        state = "disabled"
                    if module_id:
                        found[module_id] = state
            self.legacy = len(found) == 0
            self.states = found
        except Exception as e:
            self.error = e.message
        self.loading = False

    async def retry(self):
        self.loading = True
        await self.load()

    def open_overview(self):
        navigate(biz_url("/"))

    def module_label(self):
        name = self.titles.get(route.module_id)
        if name:
            return name
        return "This module"

    def module_state(self):
        if self.legacy:
            return "enabled"
        state = self.states.get(route.module_id)
        if state:
            return state
        return "not installed"

    def build(self):
        return Padding(
            Column(
                PageHeader(
                    self.module_label(),
                    "A module of PegPower Core.",
                    Button("Refresh", variant="outline-gray", icon="refresh",
                           on_click=self.retry),
                ),
                self.body(),
                gap=24,
            ),
            all=24,
        )

    def body(self):
        if self.loading:
            return LoadingState("Reading this business's modules...")
        elif self.error != "":
            return ErrorState(
                self.error,
                Button("Try again", variant="outline-gray", icon="refresh",
                       on_click=self.retry),
            )
        elif self.module_state() == "not installed":
            return EmptyState(
                "layout",
                self.module_label() + " is not installed",
                self.module_label() + " is not installed for this business,"
                " so there is nothing here to open. An owner can install it"
                " from the platform.",
                Button("Open the overview", variant="outline-gray",
                       icon="home", on_click=self.open_overview),
            )
        elif self.module_state() == "disabled":
            return EmptyState(
                "toggle-left",
                self.module_label() + " is not enabled",
                self.module_label() + " is switched off in this business's"
                " module settings, so this page has nothing to show. An owner"
                " can enable it from the platform.",
                Button("Open the overview", variant="outline-gray",
                       icon="home", on_click=self.open_overview),
            )
        else:
            return EmptyState(
                "layout",
                self.module_label() + " is enabled",
                "This module is installed and enabled for the business, but"
                " its own screens are not built in this peg yet. The module's"
                " actions and tables are available to the platform.",
                Button("Open the overview", variant="outline-gray",
                       icon="home", on_click=self.open_overview),
            )
