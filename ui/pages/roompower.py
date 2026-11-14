"""RoomPower: the module's real devices and its command queue.

Two tables, read from the platform's own table layer: the controllers this
business has (`devices`, with each device's own reported relay state) and the
commands sent to them (`commands`), joined to `rooms` for the room's name.

A command's status is *not* the device's state. `ACKNOWLEDGED` means the device
confirmed the command; the relay column is what the device last reported about
itself. The page shows them apart for that reason.

The page gates itself on the `roompower` module first, from the same
`business_modules` rows the function gated on. It is a read view: issuing a
command is a platform action, and this peg's UI has no function-invoke bridge,
so it does not offer controls that could not work.
"""
from workpeg.ui import (
    App, State, Padding, Column, Row, Text, Button, Table, TableHeader,
    TableCell, TableRow, Tag, Link, Container, Icon, Spacer, dates,
    biz_url, navigate, set_title, store, workpeg, toast,
)

from components import EmptyState, ErrorState, LoadingState, PageHeader




class RoomPowerPage(App):
    MODULE = "roompower"

    loading = State(True)
    error = State("")
    enabled = State(True)
    busy = State(False)
    seed_error = State("")
    seed_note = State("")
    devices = State([])
    command_rows = State([])
    rooms = State([])
    device_count = State(0)
    command_count = State(0)
    command_summary = State("")
    online_count = State(0)
    awaiting_count = State(0)
    room_count = State(0)

    async def on_mount(self):
        store.page_title = "RoomPower"
        set_title("RoomPower")
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
        defs["commands"] = [
            {"id": "command_id", "name": "command_id", "type": "text", "position": 1000, "required": True},
            {"id": "device_code", "name": "device_code", "type": "text", "position": 2000, "required": True},
            {"id": "command", "name": "command", "type": "text", "position": 3000, "required": True},
            {"id": "status", "name": "status", "type": "text", "position": 4000},
            {"id": "room_code", "name": "room_code", "type": "text", "position": 5000},
            {"id": "issued_at", "name": "issued_at", "type": "datetime", "position": 6000},
            {"id": "sent_at", "name": "sent_at", "type": "datetime", "position": 7000},
            {"id": "expires_at", "name": "expires_at", "type": "datetime", "position": 8000},
            {"id": "acknowledged_at", "name": "acknowledged_at", "type": "datetime", "position": 9000},
            {"id": "authorization_event_id", "name": "authorization_event_id", "type": "text", "position": 10000},
            {"id": "idempotency_key", "name": "idempotency_key", "type": "text", "position": 11000},
            {"id": "failure_reason", "name": "failure_reason", "type": "text", "position": 12000},
            {"id": "device_reported_state", "name": "device_reported_state", "type": "text", "position": 13000},
        ]
        defs["devices"] = [
            {"id": "device_code", "name": "device_code", "type": "text", "position": 1000, "required": True},
            {"id": "room_code", "name": "room_code", "type": "text", "position": 2000},
            {"id": "device_type", "name": "device_type", "type": "text", "position": 3000},
            {"id": "connection_status", "name": "connection_status", "type": "text", "position": 4000},
            {"id": "reported_relay_state", "name": "reported_relay_state", "type": "text", "position": 5000},
            {"id": "last_seen_at", "name": "last_seen_at", "type": "datetime", "position": 6000},
            {"id": "firmware", "name": "firmware", "type": "text", "position": 7000},
        ]
        defs["rooms"] = [
            {"id": "room_code", "name": "room_code", "type": "text", "position": 1000, "required": True},
            {"id": "display_name", "name": "display_name", "type": "text", "position": 2000, "required": True},
            {"id": "status", "name": "status", "type": "text", "position": 3000},
            {"id": "room_type", "name": "room_type", "type": "text", "position": 4000},
            {"id": "rate", "name": "rate", "type": "number", "position": 5000},
            {"id": "area", "name": "area", "type": "text", "position": 6000},
            {"id": "star_rating", "name": "star_rating", "type": "number", "position": 7000},
            {"id": "pitch", "name": "pitch", "type": "text", "position": 8000},
            {"id": "assigned_device_id", "name": "assigned_device_id", "type": "text", "position": 9000},
            {"id": "authorised", "name": "authorised", "type": "boolean", "position": 10000},
            {"id": "authorised_reason", "name": "authorised_reason", "type": "text", "position": 11000},
            {"id": "updated_at", "name": "updated_at", "type": "datetime", "position": 12000},
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
            self.enabled = await self.module_on()
            self.devices = []
            self.command_rows = []
            if self.enabled:
                devices_table = await self.table("devices")
                if devices_table is not None:
                    rows = await workpeg.get_rows(devices_table["uuid"],
                                                  limit=200)
                    on = 0
                    for row in rows:
                        data = row.get("data") or {}
                        if (data.get("connection_status") or "") == "online":
                            on = on + 1
                        data["last_seen_display"] = self.stamp(
                            data.get("last_seen_at"))
                    self.devices = rows
                    self.online_count = on
                commands_table = await self.table("commands")
                if commands_table is not None:
                    rows = await workpeg.get_rows(commands_table["uuid"],
                                                  limit=200)
                    awaiting = 0
                    for row in rows:
                        data = row.get("data") or {}
                        status = data.get("status") or ""
                        if status == "PENDING" or status == "SENT":
                            awaiting = awaiting + 1
                        data["issued_display"] = self.stamp(
                            data.get("issued_at"))
                        data["acknowledged_display"] = self.stamp(
                            data.get("acknowledged_at"))
                        data["device_url"] = biz_url(
                            "/roompower/" + (data.get("device_code") or ""))
                    # Rows come back in table order, oldest first.
                    rows = rows[::-1]
                    self.command_rows = rows
                    self.awaiting_count = awaiting
                rooms_table = await self.table("rooms")
                if rooms_table is not None:
                    found = []
                    for row in await workpeg.get_rows(rooms_table["uuid"],
                                                      limit=100):
                        data = row.get("data") or {}
                        if data.get("room_code"):
                            data["view_url"] = biz_url(
                                "/roompower/room/"
                                + data.get("room_code"))
                            found.append(data)
                    self.rooms = found
                    self.room_count = len(found)
            self.device_count = len(self.devices)
            self.command_count = len(self.command_rows)
            if self.command_count == 1:
                self.command_summary = "1 command"
            else:
                self.command_summary = (str(self.command_count)
                                        + " commands")
        except Exception as e:
            self.error = e.message
        self.loading = False


    def now_iso(self):
        return str(dates.now("Africa/Lagos", True) or "") + "+01:00"

    # ── demo seed ────────────────────────────────────────────────────────

    async def register_demo_controller(self):
        """Register one demo AZ3166 controller so the twin console has a
        device to talk to. This page and the twin console both say the
        twin is not physical hardware, wherever it could be mistaken."""
        self.busy = True
        self.seed_error = ""
        self.seed_note = ""
        try:
            table = await self.table("devices")
            if table is None:
                self.seed_error = "This business has no devices table."
                self.busy = False
                return
            existing = await workpeg.get_rows(table["uuid"], limit=200)
            if len(existing) > 0:
                self.seed_error = "A controller is already registered."
                self.busy = False
                return
            room_code = ""
            rooms = await self.table("rooms")
            if rooms is not None:
                for row in await workpeg.get_rows(rooms["uuid"], limit=50):
                    candidate = (row.get("data") or {}).get("room_code") or ""
                    if room_code == "" and candidate:
                        room_code = candidate
            code = "AZ-" + (room_code or "3166")
            stamp = self.now_iso()
            await workpeg.add_row(table["uuid"], {
                "data": {
                    "device_code": code,
                    "room_code": room_code,
                    "device_type": "AZ3166 (demo twin)",
                    "connection_status": "online",
                    "reported_relay_state": "OFF",
                    "last_seen_at": stamp,
                    "firmware": "demo-twin",
                },
                "position": dates.to_epoch(stamp),
            })
            self.seed_note = ("Registered " + code + " as the demo twin"
                              " for room " + (room_code or "—")
                              + ". It is not physical hardware; the twin"
                              " console says so too.")
            toast("Demo controller registered")
            await self.load()
        except Exception as e:
            self.seed_error = e.message
        self.busy = False

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
            if (data.get("module_id") == "roompower"
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
                    "RoomPower",
                    "The controllers in this building and the commands sent to"
                    " them, read from the platform's tables.",
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
            return LoadingState("Reading devices and commands...")
        elif self.error != "":
            return ErrorState(
                self.error,
                Button("Try again", variant="outline-gray", icon="refresh",
                       on_click=self.retry),
            )
        elif not self.enabled:
            return EmptyState(
                "toggle-left",
                "RoomPower is not enabled",
                "This business has switched the module off, so there are no"
                " devices or commands to read.",
                Button("Open the overview", variant="outline-gray",
                       icon="home", on_click=self.open_overview),
            )
        elif self.device_count == 0:
            return Column(
                EmptyState(
                    "bolt",
                    "No devices yet",
                    "This business has no controllers registered, so there is"
                    " nothing to power on or off.",
                    Column(
                        Button("Register the demo AZ3166 controller",
                               variant="outline-gray", icon="cpu",
                               on_click=self.register_demo_controller),
                        Text("Writes one devices row labelled as a demo"
                             " twin, so the twin console has something to"
                             " command and report.", variant="caption"),
                        gap=8, align="center",
                    ),
                ),
                self.seed_messages(),
                gap=12, align="stretch",
            )
        else:
            return Column(
                self.seed_messages(),
                self.rooms_section(),
                self.devices_table(),
                self.commands_table(),
                gap=24,
                align="stretch",
            )

    def rooms_section(self):
        """The rooms this business keeps, each opening its room view."""
        if self.room_count == 0:
            return Spacer()
        return Column(
            Row(
                Text("Rooms", weight="semibold"),
                Text("Click a room to see its appliances and power",
                     variant="caption"),
                align="center", gap=8,
            ),
            Row(*[Expanded(self.room_card(r)) for r in self.rooms],
                gap=12, align="stretch"),
            gap=10, align="stretch",
        )

    def room_card(self, room):
        return Container(
            Column(
                Row(
                    Icon("photo", size=16),
                    Text("Room photo placeholder", variant="caption"),
                    gap=6, align="center",
                ),
                Text(room.get("display_name") or "Room", weight="medium"),
                Text(room.get("room_code") or "", variant="muted"),
                Row(
                    Tag(room.get("status") or "unknown"),
                    Spacer(),
                    Link("Open room view", href=room.get("view_url")),
                    gap=8, align="center",
                ),
                gap=6, align="start",
            ),
            variant="card", padding=16,
        )

    def seed_messages(self):
        """The demo-seed result, shown until the next reload clears it."""
        if self.seed_error != "":
            return Container(
                Row(Icon("alert-triangle", size=16),
                    Text(self.seed_error, variant="muted"),
                    gap=10, align="start"),
                variant="card", padding=14,
            )
        elif self.seed_note != "":
            return Container(
                Row(Icon("circle-check", size=16),
                    Text(self.seed_note, variant="muted"),
                    gap=10, align="start"),
                variant="card", padding=14,
            )
        else:
            return Spacer()

    def devices_table(self):
        return Column(
            Row(
                Text("Devices", weight="semibold"),
                Text(str(self.device_count) + " devices · "
                     + str(self.online_count) + " online", variant="caption"),
                align="center", gap=8,
            ),
            Table(
                TableHeader(
                    TableCell(title="Device"),
                    TableCell(title="Room"),
                    TableCell(title="Type"),
                    TableCell(title="Connection"),
                    TableCell(title="Relay"),
                    TableCell(title="Last seen"),
                    TableCell(title="Open"),
                ),
                *[TableRow(
                    TableCell(Text(r["data"].get("device_code", ""),
                                   weight="medium")),
                    TableCell(Text(r["data"].get("room_code") or "—",
                                   variant="muted")),
                    TableCell(Text(r["data"].get("device_type") or "—",
                                   variant="muted")),
                    TableCell(Tag(r["data"].get("connection_status") or "unknown")),
                    TableCell(Tag(r["data"].get("reported_relay_state") or "—")),
                    TableCell(Text(r["data"].get("last_seen_display") or "—",
                                   variant="muted")),
                    TableCell(Link("View", href=biz_url(
                        "/roompower/" + r["data"].get("device_code", "")))),
                ) for r in self.devices],
                search="Search devices",
                sortable=True,
            ),
            gap=10, align="stretch",
        )

    def commands_table(self):
        return Column(
            Row(
                Text("Commands", weight="semibold"),
                Text(self.command_summary + " · "
                     + str(self.awaiting_count) + " awaiting acknowledgement",
                     variant="caption"),
                align="center", gap=8,
            ),
            Table(
                TableHeader(
                    TableCell(title="Command"),
                    TableCell(title="Device"),
                    TableCell(title="Action"),
                    TableCell(title="Status"),
                    TableCell(title="Issued"),
                    TableCell(title="Acknowledged"),
                ),
                *[TableRow(
                    TableCell(Text(r["data"].get("command_id", ""),
                                   weight="medium")),
                    TableCell(Link(r["data"].get("device_code", ""),
                                   href=r["data"].get("device_url"))),
                    TableCell(Tag(r["data"].get("command") or "—")),
                    TableCell(Tag(r["data"].get("status") or "unknown")),
                    TableCell(Text(r["data"].get("issued_display") or "—",
                                   variant="muted")),
                    TableCell(Text(r["data"].get("acknowledged_display") or "—",
                                   variant="muted")),
                ) for r in self.command_rows],
                search="Search commands",
                sortable=True,
            ),
            gap=10, align="stretch",
        )
