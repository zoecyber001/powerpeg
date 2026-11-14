"""The guest hub: one stay, as the guest sees it.

The page reads the platform's tables for a single booking and shows the four
things a guest asks about at the door and during the stay:

* the stay itself, from `bookings` and `payments`;
* the identity check, from `verifications`, naming the provider;
* the room's power, from the controller's own `device_reports` rows — the page
  shows the last state the device reported, never the state we requested;
* service requests, and a form that appends a new one to `service_requests`.

Nothing here grants access or changes a room: requests are queued for staff,
and the function validates each row when it lands.
"""
from workpeg.ui import (
    App, State, Padding, Column, Row, Container, Text, Button, Input, TextInput,
    Select, Table, TableHeader, TableCell, TableRow, Tag, Divider, Icon,
    Spacer, dates, route, biz_url, navigate, set_title, store, workpeg, toast,
)

from components import (


    EmptyState,
    ErrorState,
    FactRow,
    LoadingState,
    PageHeader,
    StatCard,
)


class GuestHubPage(App):
    MODULE = "quickpass"

    loading = State(True)
    error = State("")
    found = State(False)
    booking = State({})
    payment = State({})
    verification = State({})
    power = State({})
    requests = State([])
    category = State("Housekeeping")
    detail = State("")
    sending = State(False)

    async def on_mount(self):
        store.page_title = "Guest hub"
        set_title("Guest hub")
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
        defs["service_requests"] = [
            {"id": "request_id", "name": "request_id", "type": "text", "position": 1000, "required": True},
            {"id": "booking_id", "name": "booking_id", "type": "text", "position": 2000, "required": True},
            {"id": "room_code", "name": "room_code", "type": "text", "position": 3000},
            {"id": "guest_label", "name": "guest_label", "type": "text", "position": 4000},
            {"id": "category", "name": "category", "type": "text", "position": 5000, "required": True},
            {"id": "detail", "name": "detail", "type": "text", "position": 6000},
            {"id": "status", "name": "status", "type": "text", "position": 7000},
            {"id": "assigned_to", "name": "assigned_to", "type": "text", "position": 8000},
            {"id": "created_at", "name": "created_at", "type": "datetime", "position": 9000},
            {"id": "updated_at", "name": "updated_at", "type": "datetime", "position": 10000},
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
            booking_id = route.booking_id
            self.found = False
            self.booking = {}
            self.payment = {}
            self.verification = {}
            self.power = {}
            self.requests = []
            if booking_id:
                await self.read_stay(booking_id)
                if self.found:
                    await self.read_power()
                    await self.read_requests(booking_id)
        except Exception as e:
            self.error = e.message
        self.loading = False

    async def read_stay(self, booking_id):
        rows = await self.read("bookings")
        for row in rows:
            data = row.get("data") or {}
            if data.get("booking_id") == booking_id:
                data["start_display"] = self.stamp(data.get("start_at"))
                data["end_display"] = self.stamp(data.get("end_at"))
                self.booking = data
                self.found = True
        payments = await self.read("payments")
        for row in payments:
            data = row.get("data") or {}
            if data.get("booking_id") == booking_id:
                self.payment = data
        verifications = await self.read("verifications")
        for row in verifications:
            data = row.get("data") or {}
            if data.get("booking_id") == booking_id:
                self.verification = data

    async def read_power(self):
        """The last state the controller reported for this room, if any."""
        room = self.booking.get("room_code") or ""
        device_code = ""
        devices = await self.read("devices")
        for row in devices:
            data = row.get("data") or {}
            if data.get("room_code") == room:
                device_code = data.get("device_code") or ""
        self.power = {"device": device_code, "room": room, "relay": "",
                      "reported": "", "source": ""}
        if device_code == "":
            return
        reports = await self.read("device_reports")
        for row in reports:
            data = row.get("data") or {}
            if data.get("device_code") == device_code:
                self.power = {
                    "device": device_code,
                    "room": room,
                    "relay": data.get("relay_state") or "",
                    "reported": self.stamp(data.get("reported_at")),
                    "source": data.get("source") or "controller",
                }

    async def read_requests(self, booking_id):
        lines = []
        rows = await self.read("service_requests")
        for row in rows[::-1]:
            data = row.get("data") or {}
            if data.get("booking_id") == booking_id:
                lines.append({
                    "request_id": data.get("request_id") or "—",
                    "category": data.get("category") or "Request",
                    "detail": data.get("detail") or "",
                    "status": data.get("status") or "requested",
                    "created": self.stamp(data.get("created_at")),
                })
        self.requests = lines

    async def read(self, name):
        table = await self.table(name)
        if table is None:
            return []
        return await workpeg.get_rows(table["uuid"], limit=500)

    def now_iso(self):
        return str(dates.now("Africa/Lagos", True) or "") + "+01:00"

    def stamp(self, value):
        if not value:
            return "—"
        text = str(value)
        if len(text) < 16:
            return text
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
                  "Oct", "Nov", "Dec"]
        month = months[int(text[5:7]) - 1]
        return (str(int(text[8:10])) + " " + month + " " + text[0:4] + ", "
                + text[11:16])

    def set_category(self, value):
        self.category = value

    def set_detail(self, value):
        self.detail = value

    async def send_request(self):
        if self.sending:
            return
        text = (self.detail or "").strip()
        if len(text) < 3:
            toast("Add a line about what you need", kind="danger")
            return
        self.sending = True
        now = self.now_iso()
        try:
            table = await self.table("service_requests")
            if table is None:
                toast("Service requests are not available here", kind="danger")
            else:
                await workpeg.add_row(table["uuid"], {
                    "data": {
                        "request_id": "SR-" + str(dates.to_epoch(now)),
                        "booking_id": self.booking.get("booking_id") or "",
                        "room_code": self.booking.get("room_code") or "",
                        "guest_label": self.booking.get("guest_label")
                        or "Guest",
                        "category": self.category,
                        "detail": text,
                        "status": "requested",
                        "created_at": now,
                        "updated_at": now,
                    },
                    "position": dates.to_epoch(now),
                })
                self.detail = ""
                toast("Request sent to the front desk", kind="success")
                await self.load()
        except Exception as e:
            toast(e.message, kind="danger")
        self.sending = False

    async def retry(self):
        await self.load()

    def open_bookings(self):
        navigate(biz_url("/bookings"))

    def open_front_desk(self):
        navigate(biz_url("/front-desk"))

    def build(self):
        return Padding(
            Column(
                PageHeader(
                    "Guest hub",
                    "Your stay, your identity check, and the room as the"
                    " controller last reported it.",
                    Button("Bookings", variant="outline-gray",
                           icon="arrow-left", on_click=self.open_bookings),
                ),
                self.body(),
                gap=24,
            ),
            all=24,
        )

    def body(self):
        if self.loading:
            return LoadingState("Opening your stay...")
        elif self.error != "":
            return ErrorState(
                self.error,
                Button("Reload the page", variant="outline-gray",
                       icon="refresh", on_click=self.retry),
            )
        elif not self.found:
            return EmptyState(
                "search",
                "No stay at this address",
                "This booking does not exist for this business.",
                Button("Back to bookings", variant="outline-gray",
                       icon="arrow-left", on_click=self.open_bookings),
            )
        else:
            return Column(
                Row(
                    Container(self.stay_card(), variant="card", padding=20),
                    Container(self.power_card(), variant="card", padding=20),
                    gap=16, align="stretch",
                ),
                self.requests_block(),
                gap=20, align="stretch",
            )

    def stay_card(self):
        return Column(
            Row(Icon("calendar-event"), Text("Your stay", weight="semibold"),
                align="center", gap=8),
            Text(self.booking.get("guest_label") or "Guest", variant="h3"),
            FactRow("Room", Text(self.booking.get("room_code") or "—")),
            FactRow("Arrive", Text(self.booking.get("start_display") or "—")),
            FactRow("Leave", Text(self.booking.get("end_display") or "—")),
            FactRow("Booking", Tag(self.booking.get("booking_status") or "—")),
            FactRow("Payment", Tag(self.payment.get("payment_status") or "unpaid")),
            Divider(),
            Row(Icon("shield-check"), Text("Identity check", weight="semibold"),
                align="center", gap=8),
            FactRow("Status", Tag(self.verification.get("status") or "not started")),
            FactRow("Provider", Text(self.verification.get("provider") or "—",
                                     variant="muted")),
            FactRow("Provider says",
                    Text(self.verification.get("provider_status") or "—",
                         variant="muted")),
            Text("The front desk approves the check-in; an identity check on"
                 " its own does not open a room.", variant="caption"),
            gap=12, align="stretch",
        )

    def power_card(self):
        return Column(
            Row(Icon("bolt"), Text("Room power", weight="semibold"),
                align="center", gap=8),
            Text(self.power_label(), variant="h3"),
            FactRow("Controller", Text(self.power.get("device") or "unassigned")),
            FactRow("Reported", Text(self.power.get("reported") or "—",
                                     variant="muted")),
            FactRow("Source", Text(self.power.get("source") or "no report yet",
                                   variant="muted")),
            Text("This is the last state the room controller reported, not the"
                 " state we asked for.", variant="caption"),
            gap=12, align="stretch",
        )

    def power_label(self):
        relay = self.power.get("relay") or ""
        if relay == "on":
            return "Power on"
        elif relay == "off":
            return "Power off"
        else:
            return "No report yet"

    def requests_block(self):
        return Column(
            Row(Text("Service requests", weight="semibold"), Spacer(),
                Text("queued for the front desk", variant="caption"),
                align="center", gap=8),
            Container(
                Column(
                    Text("Ask for something", weight="semibold"),
                    Select(
                        options=["Housekeeping", "Maintenance", "Food and drink",
                                 "Front desk"],
                        value=self.category,
                        on_change=self.set_category,
                    ),
                    Input(
                        TextInput(value=self.detail, on_change=self.set_detail,
                                  placeholder="Extra towels, please"),
                        label="What do you need?",
                    ),
                    Row(
                        Button("Send request", variant="primary", icon="send",
                               on_click=self.send_request),
                        align="center",
                    ),
                    gap=12, align="stretch",
                ),
                variant="card", padding=20,
            ),
            self.requests_table(),
            gap=12, align="stretch",
        )

    def requests_table(self):
        if len(self.requests) == 0:
            return Text("No requests yet for this stay.", variant="caption")
        return Table(
            TableHeader(
                TableCell(title="Request"),
                TableCell(title="Category"),
                TableCell(title="Detail"),
                TableCell(title="Raised"),
                TableCell(title="Status"),
            ),
            *[TableRow(
                TableCell(Text(r["request_id"], variant="caption")),
                TableCell(Text(r["category"], weight="medium")),
                TableCell(Text(r["detail"], variant="muted")),
                TableCell(Text(r["created"], variant="muted")),
                TableCell(Tag(r["status"])),
            ) for r in self.requests],
        )
