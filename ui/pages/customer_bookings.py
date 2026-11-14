"""My bookings: the customer's own list of the stays they reserved.

Reads the same `bookings` table the workspace uses, joined with `rooms` for
the room's name and `payments` for what has been settled. It is a read view:
the guest hub opens per stay, where the guest sees the stay and can raise
service requests.
"""
from workpeg.ui import (
    App, State, Padding, Column, Row, Text, Button, Table, TableHeader,
    TableCell, TableRow, Tag, Link, biz_url, navigate, set_title, store,
    workpeg,
)

from components import EmptyState, ErrorState, LoadingState, PageHeader




class CustomerBookingsPage(App):
    loading = State(True)
    error = State("")
    stays = State([])

    async def on_mount(self):
        store.page_title = "My bookings"
        set_title("My bookings")
        await self.load()

    # ── reading ──────────────────────────────────────────────────────────

    async def table(self, name):
        """This business's table with that name, created if absent.

        Found by the table's own namespace label (get_tables filters
        on it); a table the business has never used is created here
        on first use, in the shape the Tables API expects: display
        name, namespace label, permission, and columns with ids,
        types and positions. Column ids are the manifest's column
        names, so every row write and read keeps its keys."""
        defs = {}
        defs["bookings"] = [
            {"id": "booking_id", "name": "booking_id", "type": "text", "position": 1000, "required": True},
            {"id": "room_code", "name": "room_code", "type": "text", "position": 2000, "required": True},
            {"id": "guest_label", "name": "guest_label", "type": "text", "position": 3000, "required": True},
            {"id": "start_at", "name": "start_at", "type": "datetime", "position": 4000, "required": True},
            {"id": "end_at", "name": "end_at", "type": "datetime", "position": 5000, "required": True},
            {"id": "booking_status", "name": "booking_status", "type": "text", "position": 6000},
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
        self.loading = True
        self.error = ""
        try:
            rooms = await self.read_map("rooms", "room_code")
            payments = await self.read_map("payments", "booking_id")
            lines = []
            table = await self.table("bookings")
            if table is not None:
                rows = await workpeg.get_rows(table["uuid"], limit=200)
                for row in rows[::-1]:
                    data = row.get("data") or {}
                    room = rooms.get(data.get("room_code") or "") or {}
                    payment = payments.get(data.get("booking_id")) or {}
                    lines.append({
                        "booking_id": data.get("booking_id") or "",
                        "room": room.get("display_name")
                        or data.get("room_code") or "—",
                        "guest": data.get("guest_label") or "Guest",
                        "dates": self.stay_label(data),
                        "booking_status": data.get("booking_status")
                        or "reserved",
                        "payment": (payment.get("payment_status")
                                    or "pending").lower(),
                    })
            self.stays = lines
        except Exception as e:
            self.error = e.message
        self.loading = False

    async def read_map(self, name, key):
        out = {}
        table = await self.table(name)
        if table is None:
            return out
        for row in await workpeg.get_rows(table["uuid"], limit=300):
            data = row.get("data") or {}
            value = data.get(key)
            if value:
                out[value] = data
        return out


    # ── helpers ──────────────────────────────────────────────────────────

    def stamp(self, value):
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

    def stay_label(self, booking):
        start = booking.get("start_at")
        end = booking.get("end_at")
        if start and end:
            return (self.stamp(start)[0:12] + " to " + self.stamp(end)[0:12])
        elif start:
            return "from " + self.stamp(start)
        else:
            return "no dates recorded"

    async def retry(self):
        self.loading = True
        await self.load()

    def open_marketplace(self):
        navigate(biz_url("/marketplace"))

    # ── rendering ────────────────────────────────────────────────────────

    def build(self):
        return Padding(
            Column(
                PageHeader(
                    "My bookings",
                    "The stays reserved in this business. Open a stay's hub"
                    " to see it the way the guest does.",
                    Button("Marketplace", variant="outline-gray",
                           icon="tag", on_click=self.open_marketplace),
                ),
                self.body(),
                gap=24,
            ),
            all=24,
        )

    def body(self):
        if self.loading:
            return LoadingState("Reading your stays...")
        elif self.error != "":
            return ErrorState(
                self.error,
                Button("Reload the page", variant="outline-gray",
                       icon="refresh", on_click=self.retry),
            )
        elif len(self.stays) == 0:
            return EmptyState(
                "calendar",
                "No stays yet",
                "When a stay is reserved at the marketplace it appears here.",
                Button("Open the marketplace", variant="outline-gray",
                       icon="tag", on_click=self.open_marketplace),
            )
        else:
            return Column(
                Row(Text("Stays", weight="semibold"),
                    Text(str(len(self.stays)) + " reserved",
                         variant="caption"),
                    align="center", gap=8),
                Table(
                    TableHeader(
                        TableCell(title="Room"),
                        TableCell(title="Stay"),
                        TableCell(title="Guest"),
                        TableCell(title="Reservation"),
                        TableCell(title="Payment"),
                        TableCell(title="Guest hub"),
                    ),
                    *[TableRow(
                        TableCell(Text(s["room"], weight="medium")),
                        TableCell(Text(s["dates"], variant="muted")),
                        TableCell(Text(s["guest"])),
                        TableCell(Tag(s["booking_status"])),
                        TableCell(Tag(s["payment"])),
                        TableCell(Link("Open", href=biz_url(
                            "/guest/" + s["booking_id"]))),
                    ) for s in self.stays],
                    search="Search stays",
                ),
                Text("The guest hub shows one stay: its payment, its"
                     " identity status, the room's last reported power"
                     " state, and where the guest raises service requests.",
                     variant="caption"),
                gap=10, align="stretch",
            )
