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

        Found by the table's own namespace label (get_tables filters
        on it); a table the business has never used is created here
        on first use, in the shape the Tables API expects: display
        name, namespace label, permission, and columns with ids,
        types and positions. Column ids are the manifest's column
        names, so every row write and read keeps its keys."""
        defs = {}
        defs["business_modules"] = [
            {"id": "business_module_id", "name": "business_module_id", "type": "text", "position": 1000, "required": True},
            {"id": "business_id", "name": "business_id", "type": "text", "position": 2000, "required": True},
            {"id": "module_id", "name": "module_id", "type": "text", "position": 3000, "required": True},
            {"id": "installed", "name": "installed", "type": "boolean", "position": 4000},
            {"id": "enabled", "name": "enabled", "type": "boolean", "position": 5000},
            {"id": "installed_at", "name": "installed_at", "type": "datetime", "position": 6000},
            {"id": "enabled_at", "name": "enabled_at", "type": "datetime", "position": 7000},
            {"id": "disabled_at", "name": "disabled_at", "type": "datetime", "position": 8000},
            {"id": "source", "name": "source", "type": "text", "position": 9000},
            {"id": "metadata", "name": "metadata", "type": "text", "position": 10000},
        ]
        tables = await workpeg.get_tables(name)
        if len(tables) > 0:
            return tables[0]
        definition = defs.get(name)
        if definition is None:
            return None
        return await workpeg.create_table({
            "name": name,
            "namespace": name,
            "permission": "760",
            "columns": definition,
        })
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
