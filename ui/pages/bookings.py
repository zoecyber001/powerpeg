"""Bookings & Inventory: the module's real rooms and reservations.

Two tables, both read from the platform's own table layer: the inventory the
business sells (`rooms`) and the reservations against it (`bookings`), with each
booking's payment status joined from `payments`.

The page gates itself on the `bookings` module first, from the same
`business_modules` rows the function gated on. It is a read view: creating,
allocating and cancelling are platform actions, and this peg's UI has no
function-invoke bridge, so it does not pretend to write.
"""
from workpeg.ui import (
    App, State, Padding, Column, Row, Text, Button, Table, TableHeader,
    TableCell, TableRow, Tag, Link, biz_url, navigate, set_title, store,
    workpeg,
)

from components import EmptyState, ErrorState, LoadingState, PageHeader




class BookingsPage(App):
    MODULE = "bookings"

    loading = State(True)
    error = State("")
    enabled = State(True)
    rooms = State([])
    bookings = State([])
    payments = State({})
    inventory_rows = State(0)
    booking_rows = State(0)

    async def on_mount(self):
        store.page_title = "Bookings"
        set_title("Bookings")
        await self.load()

    async def table(self, name):
        """This business's table with that name, created if absent.

        The definitions mirror the manifest, so a table the business
        has never used is created here on first use instead of
        answering "no such table"."""
        defs = {}
        defs["bookings"] = [
            {"name": "booking_id", "type": "string", "required": True},
            {"name": "room_code", "type": "string", "required": True},
            {"name": "guest_label", "type": "string", "required": True},
            {"name": "start_at", "type": "datetime", "required": True},
            {"name": "end_at", "type": "datetime", "required": True},
            {"name": "booking_status", "type": "string"},
        ]
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
        defs["payments"] = [
            {"name": "payment_id", "type": "string", "required": True},
            {"name": "booking_id", "type": "string", "required": True},
            {"name": "payment_status", "type": "string", "required": True},
            {"name": "amount", "type": "number"},
            {"name": "is_simulated", "type": "boolean"},
            {"name": "updated_at", "type": "datetime"},
        ]
        defs["rooms"] = [
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
            self.enabled = await self.module_on()
            self.rooms = []
            self.bookings = []
            self.payments = {}
            if self.enabled:
                rooms_table = await self.table("rooms")
                if rooms_table is not None:
                    self.rooms = await workpeg.get_rows(
                        rooms_table["uuid"], limit=200)
                bookings_table = await self.table("bookings")
                if bookings_table is not None:
                    self.bookings = await workpeg.get_rows(
                        bookings_table["uuid"], limit=200)
                    for row in self.bookings:
                        data = row.get("data") or {}
                        data["start_display"] = self.stamp(
                            data.get("start_at"))
                        data["end_display"] = self.stamp(data.get("end_at"))
                payments_table = await self.table("payments")
                if payments_table is not None:
                    paid = await workpeg.get_rows(payments_table["uuid"],
                                                  limit=500)
                    by_booking = {}
                    for row in paid:
                        data = row.get("data") or {}
                        by_booking[data.get("booking_id")] = data.get(
                            "payment_status")
                    self.payments = by_booking
            self.inventory_rows = len(self.rooms)
            self.booking_rows = len(self.bookings)
        except Exception as e:
            self.error = e.message
        self.loading = False


    async def module_on(self):
        """Read the business's module rows; no rows means unconfigured."""
        table = await self.table("business_modules")
        if table is None:
            return True
        rows = await workpeg.get_rows(table["uuid"], limit=100)
        if len(rows) == 0:
            return True
        for row in rows:
            data = row.get("data") or {}
            if (data.get("module_id") == "bookings"
                    and data.get("installed") and data.get("enabled")):
                return True
        return False

    def stamp(self, value):
        """A stored ISO timestamp as the desk reads it: 13 Nov 2026, 15:00."""
        if not value:
            return "—"
        text = str(value)
        if len(text) < 16:
            return text
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug",
                  "Sep", "Oct", "Nov", "Dec"]
        month = months[int(text[5:7]) - 1]
        return (str(int(text[8:10])) + " " + month + " " + text[0:4] + ", "
                + text[11:16])

    async def retry(self):
        self.loading = True
        await self.load()

    def open_overview(self):
        navigate(biz_url("/"))

    def build(self):
        return Padding(
            Column(
                PageHeader(
                    "Bookings & Inventory",
                    "The rooms this business sells and the reservations"
                    " against them, read from the platform's tables.",
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
            return LoadingState("Reading inventory and bookings...")
        elif self.error != "":
            return ErrorState(
                self.error,
                Button("Try again", variant="outline-gray", icon="refresh",
                       on_click=self.retry),
            )
        elif not self.enabled:
            return EmptyState(
                "toggle-left",
                "Bookings & Inventory is not enabled",
                "This business has switched the module off, so there is no"
                " inventory or booking list to read.",
                Button("Open the overview", variant="outline-gray",
                       icon="home", on_click=self.open_overview),
            )
        elif self.inventory_rows == 0 and self.booking_rows == 0:
            return EmptyState(
                "building",
                "No inventory yet",
                "This business has no rooms and no bookings recorded.",
                Button("Check again", variant="outline-gray", icon="refresh",
                       on_click=self.retry),
            )
        else:
            return Column(
                self.inventory(),
                self.bookings_table(),
                gap=24,
                align="stretch",
            )

    def inventory(self):
        return Column(
            Row(
                Text("Inventory", weight="semibold"),
                Text(str(self.inventory_rows) + " rooms", variant="caption"),
                align="center", gap=8,
            ),
            Table(
                TableHeader(
                    TableCell(title="Room"),
                    TableCell(title="Name"),
                    TableCell(title="Status"),
                    TableCell(title="Controller"),
                    TableCell(title="Authorised"),
                ),
                *[TableRow(
                    TableCell(Text(r["data"].get("room_code", ""),
                                   weight="medium")),
                    TableCell(Text(r["data"].get("display_name", ""),
                                   variant="muted")),
                    TableCell(Tag(r["data"].get("status", ""))),
                    TableCell(Text(r["data"].get("assigned_device_id") or "—",
                                   variant="muted")),
                    TableCell(Text("Yes" if r["data"].get("authorised")
                                   else "No", variant="muted")),
                ) for r in self.rooms],
                search="Search rooms",
                sortable=True,
            ),
            gap=10, align="stretch",
        )

    def bookings_table(self):
        return Column(
            Row(
                Text("Reservations", weight="semibold"),
                Text(str(self.booking_rows) + " bookings", variant="caption"),
                align="center", gap=8,
            ),
            Table(
                TableHeader(
                    TableCell(title="Booking"),
                    TableCell(title="Guest"),
                    TableCell(title="Room"),
                    TableCell(title="Start"),
                    TableCell(title="End"),
                    TableCell(title="Status"),
                    TableCell(title="Payment"),
                    TableCell(title="Open"),
                ),
                *[TableRow(
                    TableCell(Text(r["data"].get("booking_id", ""),
                                   weight="medium")),
                    TableCell(Text(r["data"].get("guest_label", ""))),
                    TableCell(Text(r["data"].get("room_code", ""),
                                   variant="muted")),
                    TableCell(Text(r["data"].get("start_display", ""),
                                   variant="muted")),
                    TableCell(Text(r["data"].get("end_display", ""),
                                   variant="muted")),
                    TableCell(Tag(r["data"].get("booking_status", ""))),
                    TableCell(Tag(self.payments.get(
                        r["data"].get("booking_id")) or "unpaid")),
                    TableCell(Link("View", href=biz_url(
                        "/bookings/" + r["data"].get("booking_id", "")))),
                ) for r in self.bookings],
                search="Search bookings",
                sortable=True,
            ),
            gap=10, align="stretch",
        )
