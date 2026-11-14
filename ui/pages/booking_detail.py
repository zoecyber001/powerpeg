"""One reservation: the booking row, its payment and its check-in record.

Read from the platform's tables by booking id. This is state, not a pipeline
the UI invents: each fact shown is a stored field on a real row.
"""
from workpeg.ui import (
    App, State, Padding, Column, Row, Text, Button, Divider, Tag, biz_url,
    navigate, route, set_title, store, workpeg,
)

from components import EmptyState, ErrorState, LoadingState, PageHeader




class BookingDetailPage(App):
    loading = State(True)
    error = State("")
    found = State(False)
    enabled = State(True)
    booking = State({})
    payment = State({})
    check_in = State({})

    async def on_mount(self):
        store.page_title = "Booking"
        set_title("Booking")
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
            booking_id = route.booking_id
            self.booking = {}
            self.payment = {}
            self.check_in = {}
            self.enabled = await self.module_on()
            if not booking_id:
                self.found = False
            else:
                rows = await self.read("bookings")
                for row in rows:
                    data = row.get("data") or {}
                    if data.get("booking_id") == booking_id:
                        data["start_display"] = self.stamp(
                            data.get("start_at"))
                        data["end_display"] = self.stamp(data.get("end_at"))
                        self.booking = data
                        self.found = True
                payment_rows = await self.read("payments")
                for row in payment_rows:
                    data = row.get("data") or {}
                    if data.get("booking_id") == booking_id:
                        self.payment = data
                check_in_rows = await self.read("check_ins")
                for row in check_in_rows:
                    data = row.get("data") or {}
                    if data.get("booking_id") == booking_id:
                        data["verified_display"] = self.stamp(
                            data.get("verified_at"))
                        data["approved_display"] = self.stamp(
                            data.get("approved_at"))
                        data["activated_display"] = self.stamp(
                            data.get("activated_at"))
                        self.check_in = data
        except Exception as e:
            self.error = e.message
        self.loading = False

    async def module_on(self):
        """The bookings module must be on to read this business's bookings."""
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

    async def read(self, name):
        table = await self.table(name)
        if table is None:
            return []
        return await workpeg.get_rows(table["uuid"], limit=500)

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

    def open_bookings(self):
        navigate(biz_url("/bookings"))

    def open_guest_hub(self):
        booking_id = self.booking.get("booking_id") or route.booking_id or ""
        if booking_id:
            navigate(biz_url("/guest/" + booking_id))

    def build(self):
        return Padding(
            Column(
                PageHeader(
                    "Booking",
                    "The stored record for this reservation.",
                    Row(
                        Button("Guest hub", variant="primary", icon="user",
                               on_click=self.open_guest_hub),
                        Button("All bookings", variant="outline-gray",
                               icon="arrow-left", on_click=self.open_bookings),
                        gap=10, align="center",
                    ),
                ),
                self.body(),
                gap=24,
            ),
            all=24,
        )

    def body(self):
        if self.loading:
            return LoadingState("Reading this booking...")
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
                "This business has switched the module off, so this"
                " reservation is not shown here.",
                Button("Open the overview", variant="outline-gray",
                       icon="home", on_click=self.open_overview),
            )
        elif not self.found:
            return EmptyState(
                "calendar",
                "Booking not found",
                "No booking with that id exists in this business's bookings"
                " table.",
                Button("All bookings", variant="outline-gray",
                       icon="arrow-left", on_click=self.open_bookings),
            )
        else:
            return Column(
                Column(
                    Text("Reservation", weight="semibold"),
                    Row(
                        Text("Booking id", variant="muted"),
                        Tag(self.booking.get("booking_id", "")),
                        align="center", gap=10,
                    ),
                    Row(
                        Text("Guest", variant="muted"),
                        Tag(self.booking.get("guest_label", "")),
                        align="center", gap=10,
                    ),
                    Row(
                        Text("Room", variant="muted"),
                        Tag(self.booking.get("room_code", "")),
                        align="center", gap=10,
                    ),
                    Row(
                        Text("Start", variant="muted"),
                        Tag(self.booking.get("start_display", "")),
                        align="center", gap=10,
                    ),
                    Row(
                        Text("End", variant="muted"),
                        Tag(self.booking.get("end_display", "")),
                        align="center", gap=10,
                    ),
                    Row(
                        Text("Status", variant="muted"),
                        Tag(self.booking.get("booking_status", "")),
                        align="center", gap=10,
                    ),
                    gap=8, align="stretch",
                ),
                Divider(),
                Column(
                    Text("Payment", weight="semibold"),
                    Row(
                        Text("Payment id", variant="muted"),
                        Tag(self.payment.get("payment_id") or "—"),
                        align="center", gap=10,
                    ),
                    Row(
                        Text("Status", variant="muted"),
                        Tag(self.payment.get("payment_status") or "none"),
                        align="center", gap=10,
                    ),
                    Row(
                        Text("Amount", variant="muted"),
                        Tag(str(self.payment.get("amount") or "—")),
                        align="center", gap=10,
                    ),
                    gap=8, align="stretch",
                ),
                Divider(),
                Column(
                    Text("Check-in", weight="semibold"),
                    Row(
                        Text("Check-in id", variant="muted"),
                        Tag(self.check_in.get("check_in_id") or "—"),
                        align="center", gap=10,
                    ),
                    Row(
                        Text("Verified", variant="muted"),
                        Tag(self.check_in.get("verified_display") or "not yet"),
                        align="center", gap=10,
                    ),
                    Row(
                        Text("Approved", variant="muted"),
                        Tag(self.check_in.get("approved_display") or "not yet"),
                        align="center", gap=10,
                    ),
                    Row(
                        Text("Activated", variant="muted"),
                        Tag(self.check_in.get("activated_display") or "not yet"),
                        align="center", gap=10,
                    ),
                    Row(
                        Text("State", variant="muted"),
                        Tag(self.check_in.get("check_in_status") or "—"),
                        align="center", gap=10,
                    ),
                    gap=8, align="stretch",
                ),
                gap=20, align="stretch",
            )
