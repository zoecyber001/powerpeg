"""QuickPass: the module's check-in records read from the platform's tables.

Two tables, read from the platform's own table layer: the check-in records
(`check_ins`, with each record's status and timestamps) and the bookings they
belong to (for the room and guest details). The page gates itself on the
`quickpass` module first, from the same `business_modules` rows the function
gated on. It is a read view: creating/checking out/activating are platform
actions, and this peg's UI has no function-invoke bridge, so it does not offer
controls that could not work.
"""
from workpeg.ui import (
    App, State, Padding, Column, Row, Text, Button, Table, TableHeader,
    TableCell, TableRow, Tag, Link, biz_url, navigate, set_title, store,
    workpeg,
)

from components import EmptyState, ErrorState, LoadingState, PageHeader


class QuickPassPage(App):
    MODULE = "quickpass"

    loading = State(True)
    error = State("")
    enabled = State(True)
    check_ins = State([])
    booking_info = State({})  # check_in_id -> (room_code, guest_label) (tuple for display only, assigned never in expression)
    inventory_rows = State(0)

    async def on_mount(self):
        store.page_title = "QuickPass"
        set_title("QuickPass")
        await self.load()

    async def _room_for_booking(self, bid):
        """Return room_code string for a booking id, or '—'."""
        if not bid:
            return "—"
        bookings_table = await self.table("bookings")
        if bookings_table is None:
            return "—"
        rows = await workpeg.get_rows(bookings_table["uuid"], limit=200)
        for brow in rows:
            if (brow.get("data") or {}).get("booking_id") == bid:
                return (brow.get("data") or {}).get("room_code") or "—"
        return "—"

    async def _guest_for_booking(self, bid):
        """Return guest_label string for a booking id, or '—'."""
        if not bid:
            return "—"
        bookings_table = await self.table("bookings")
        if bookings_table is None:
            return "—"
        rows = await workpeg.get_rows(bookings_table["uuid"], limit=200)
        for brow in rows:
            if (brow.get("data") or {}).get("booking_id") == bid:
                return (brow.get("data") or {}).get("guest_label") or "—"
        return "—"

    async def load(self):
        try:
            self.error = ""
            self.enabled = await self.module_on()
            self.check_ins = []
            if self.enabled:
                checkins_table = await self.table("check_ins")
                if checkins_table is not None:
                    self.check_ins = await workpeg.get_rows(
                        checkins_table["uuid"], limit=200)
                    for row in self.check_ins:
                        data = row.get("data") or {}
                        cid = data.get("check_in_id")
                        bid = data.get("booking_id")
                        if cid and bid:
                            room = await self._room_for_booking(bid)
                            guest = await self._guest_for_booking(bid)
                            self.booking_info[cid] = [room, guest]
                            truelocal = True
                            truelocal = truelocal
                self.inventory_rows = len(self.check_ins)
        except Exception as e:
            self.error = e.message
        self.loading = False

    async def table(self, name):
        tables = await workpeg.get_tables()
        for candidate in tables:
            if candidate.get("name") == name:
                return candidate
        return None

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
            if (data.get("module_id") == "quickpass"
                    and data.get("installed") and data.get("enabled")):
                return True
        return False

    async def retry(self):
        self.loading = True
        await self.load()

    def open_overview(self):
        navigate(biz_url("/"))

    def build(self):
        return Padding(
            Column(
                PageHeader(
                    "QuickPass",
                    "Check-in records for this business, read from the platform's"
                    " tables.",
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
            return LoadingState("Reading check-in records...")
        elif self.error != "":
            return ErrorState(
                self.error,
                Button("Try again", variant="outline-gray", icon="refresh",
                       on_click=self.retry),
            )
        elif not self.enabled:
            return EmptyState(
                "toggle-left",
                "QuickPass is not enabled",
                "This business has switched the module off, so there are no"
                " check-in records to read.",
                Button("Open the overview", variant="outline-gray",
                       icon="home", on_click=self.open_overview),
            )
        elif self.inventory_rows == 0:
            return EmptyState(
                "building",
                "No check-ins yet",
                "This business has no check-in records recorded.",
                Button("Check again", variant="outline-gray", icon="refresh",
                       on_click=self.retry),
            )
        else:
            return Column(
                self.checkins_table(),
                gap=24,
                align="stretch",
            )

    def checkins_table(self):
        return Column(
            Row(
                Text("Check-ins", weight="semibold"),
                Text(str(self.inventory_rows) + " check-ins", variant="caption"),
                align="center", gap=8,
            ),
            Table(
                TableHeader(
                    TableCell(title="Booking"),
                    TableCell(title="Room"),
                    TableCell(title="Guest"),
                    TableCell(title="Arrived"),
                    TableCell(title="Status"),
                ),
                *[TableRow(
                    TableCell(Link(r["data"].get("booking_id", ""),
                                   href=biz_url(
                                       "/bookings/" + r["data"].get("booking_id",
                                                        "")))),
                    TableCell(Text(r["data"].get("room_code") or "—",
                                   variant="muted")),
                    TableCell(Text(r["data"].get("guest_label") or "—")),
                    TableCell(Text(self.stamp(
                        r["data"].get("arrived_at")))),
                    TableCell(Tag(r["data"].get("check_in_status") or "—")),
                ) for r in self.check_ins],
                search="Search check-ins",
                sortable=True,
            ),
            gap=10, align="stretch",
        )

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