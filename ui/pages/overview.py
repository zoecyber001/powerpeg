"""The business root: what this business actually has switched on.

Reads the ``business_modules`` table — the same rows the function's module
gate uses — and lists each module with its real state. No demo inventory, no
invented metrics: if the business has no module rows yet, the page says so and
means it.
"""
from workpeg.ui import (
    App, State, Padding, Column, Row, Text, Button, Tag, ListTile, Divider,
    set_title, store, workpeg,
)

from components import EmptyState, ErrorState, LoadingState, PageHeader




class OverviewPage(App):
    loading = State(True)
    error = State("")
    configured = State(False)
    bookings = State("unconfigured")
    quickpass = State("unconfigured")
    roompower = State("unconfigured")
    guesthub = State("unconfigured")
    deals = State("unconfigured")
    propertyops = State("unconfigured")

    async def on_mount(self):
        store.page_title = "Overview"
        set_title("Overview")
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
            rows = []
            if table is not None:
                rows = await workpeg.get_rows(table["uuid"], limit=100)
            self.configured = len(rows) > 0
            if self.configured:
                self.bookings = "not installed"
                self.quickpass = "not installed"
                self.roompower = "not installed"
                self.guesthub = "not installed"
                self.deals = "not installed"
                self.propertyops = "not installed"
                for row in rows:
                    data = row.get("data") or {}
                    module_id = data.get("module_id")
                    state = "not installed"
                    if data.get("installed") and data.get("enabled"):
                        state = "enabled"
                    elif data.get("installed"):
                        state = "disabled"
                    if module_id == "bookings":
                        self.bookings = state
                    elif module_id == "quickpass":
                        self.quickpass = state
                    elif module_id == "roompower":
                        self.roompower = state
                    elif module_id == "guesthub":
                        self.guesthub = state
                    elif module_id == "deals":
                        self.deals = state
                    elif module_id == "propertyops":
                        self.propertyops = state
        except Exception as e:
            self.error = e.message
        self.loading = False

    async def retry(self):
        self.loading = True
        await self.load()

    def build(self):
        return Padding(
            Column(
                PageHeader(
                    "Modules",
                    "What this business can do depends on the modules"
                    " switched on for it.",
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
        elif not self.configured:
            return EmptyState(
                "toggle-left",
                "No module settings yet",
                "This business has no module settings, so it is treated as an"
                " existing business: nothing is gated. An owner can enable"
                " modules from the platform to make this page exact.",
                Button("Check again", variant="outline-gray", icon="refresh",
                       on_click=self.retry),
            )
        else:
            return Column(
                self.module_row("Bookings", self.bookings,
                                "Rooms, inventory and reservations"),
                Divider(),
                self.module_row("QuickPass", self.quickpass,
                                "Guest check-in and verification"),
                Divider(),
                self.module_row("RoomPower", self.roompower,
                                "Room power and device commands"),
                Divider(),
                self.module_row("Guest Hub", self.guesthub,
                                "The guest's own view of their stay"),
                Divider(),
                self.module_row("Deals", self.deals,
                                "Offers and packages for guests"),
                Divider(),
                self.module_row("Property Ops", self.propertyops,
                                "Housekeeping and maintenance"),
                gap=0,
            )

    def module_row(self, label, state, note):
        return ListTile(
            title=label,
            subtitle=note,
            trailing=Tag(state, dot=True),
        )
