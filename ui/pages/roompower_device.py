"""One controller: what it is, what it last reported, and its commands.

The device block is the `devices` row, the room block is the `rooms` row for
the same room, and the command table is every `commands` row for this device,
newest first. Gating matches the module list page, so a typed URL cannot read a
switched-off module's tables.
"""
from workpeg.ui import (
    App, State, Padding, Column, Row, Text, Button, Table, TableHeader,
    TableCell, TableRow, Tag, Link, route, biz_url, navigate, set_title,
    store, workpeg,
)

from components import EmptyState, ErrorState, LoadingState, PageHeader


class RoomPowerDevicePage(App):
    MODULE = "roompower"

    loading = State(True)
    error = State("")
    enabled = State(True)
    found = State(False)
    device = State({})
    room = State({})
    command_rows = State([])
    command_count = State(0)
    command_summary = State("")

    async def on_mount(self):
        store.page_title = "Device"
        set_title("Device")
        await self.load()

    async def load(self):
        try:
            self.error = ""
            self.enabled = await self.module_on()
            self.found = False
            self.device = {}
            self.room = {}
            self.command_rows = []
            self.command_count = 0
            if self.enabled:
                await self.read_device()
                await self.read_commands()
            self.command_count = len(self.command_rows)
            if self.command_count == 1:
                self.command_summary = "1 command"
            else:
                self.command_summary = (str(self.command_count)
                                        + " commands")
        except Exception as e:
            self.error = e.message
        self.loading = False

    async def read_device(self):
        table = await self.table("devices")
        if table is None:
            return
        rows = await workpeg.get_rows(table["uuid"], limit=200)
        for row in rows:
            data = row.get("data") or {}
            if data.get("device_code") == route.device_code:
                data["last_seen_display"] = self.stamp(
                    data.get("last_seen_at"))
                self.device = data
                self.found = True
        room_code = self.device.get("room_code")
        if not room_code:
            return
        rooms_table = await self.table("rooms")
        if rooms_table is None:
            return
        for row in await workpeg.get_rows(rooms_table["uuid"], limit=200):
            data = row.get("data") or {}
            if data.get("room_code") == room_code:
                self.room = data

    async def read_commands(self):
        table = await self.table("commands")
        if table is None:
            return
        rows = await workpeg.get_rows(table["uuid"], limit=200)
        mine = []
        for row in rows:
            data = row.get("data") or {}
            if data.get("device_code") == route.device_code:
                data["issued_display"] = self.stamp(data.get("issued_at"))
                data["acknowledged_display"] = self.stamp(
                    data.get("acknowledged_at"))
                mine.append(row)
        mine = mine[::-1]
        self.command_rows = mine

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

    def open_roompower(self):
        navigate(biz_url("/roompower"))

    def build(self):
        return Padding(
            Column(
                PageHeader(
                    "Device",
                    "One controller, its own reported state and its command"
                    " history.",
                    Button("All devices", variant="outline-gray",
                           icon="arrow-left", on_click=self.open_roompower),
                ),
                self.body(),
                gap=24,
            ),
            all=24,
        )

    def body(self):
        if self.loading:
            return LoadingState("Reading this device...")
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
                "This business has switched the module off, so this device is"
                " not shown here.",
                Button("Open the overview", variant="outline-gray",
                       icon="home", on_click=self.open_overview),
            )
        elif not self.found:
            return EmptyState(
                "bolt",
                "No device with that code",
                "This business has no controller recorded under this code.",
                Button("All devices", variant="outline-gray",
                       icon="arrow-left", on_click=self.open_roompower),
            )
        else:
            return Column(
                self.device_block(),
                self.room_block(),
                self.commands_table(),
                gap=24,
                align="stretch",
            )

    def device_block(self):
        return Column(
            Text("Device", weight="semibold"),
            Column(
                Row(
                    Text("Code", variant="caption"),
                    Text(self.device.get("device_code") or "—"),
                    align="center", gap=8,
                ),
                Row(
                    Text("Type", variant="caption"),
                    Text(self.device.get("device_type") or "—"),
                    align="center", gap=8,
                ),
                Row(
                    Text("Connection", variant="caption"),
                    Tag(self.device.get("connection_status") or "unknown"),
                    align="center", gap=8,
                ),
                Row(
                    Text("Reported relay", variant="caption"),
                    Tag(self.device.get("reported_relay_state") or "—"),
                    align="center", gap=8,
                ),
                Row(
                    Text("Last seen", variant="caption"),
                    Text(self.device.get("last_seen_display") or "—"),
                    align="center", gap=8,
                ),
                gap=8, align="start",
            ),
            gap=10, align="stretch",
        )

    def room_block(self):
        if not self.room:
            return Column(
                Text("Room", weight="semibold"),
                Text("This device is not assigned to a room.",
                     variant="caption"),
                gap=10, align="stretch",
            )
        return Column(
            Text("Room", weight="semibold"),
            Column(
                Row(
                    Text("Room", variant="caption"),
                    Text(self.room.get("display_name") or "—"),
                    align="center", gap=8,
                ),
                Row(
                    Text("Status", variant="caption"),
                    Tag(self.room.get("status") or "unknown"),
                    align="center", gap=8,
                ),
                Row(
                    Text("Authorised", variant="caption"),
                    Tag("authorised" if self.room.get("authorised")
                        else "not authorised"),
                    align="center", gap=8,
                ),
                Row(
                    Text("Controller", variant="caption"),
                    Text(self.room.get("assigned_device_id") or "—"),
                    align="center", gap=8,
                ),
                gap=8, align="start",
            ),
            gap=10, align="stretch",
        )

    def commands_table(self):
        if self.command_count == 0:
            return Column(
                Text("Commands", weight="semibold"),
                Text("No commands have been sent to this device.",
                     variant="caption"),
                gap=10, align="stretch",
            )
        return Column(
            Row(
                Text("Commands", weight="semibold"),
                Text(self.command_summary, variant="caption"),
                align="center", gap=8,
            ),
            Table(
                TableHeader(
                    TableCell(title="Command"),
                    TableCell(title="Action"),
                    TableCell(title="Status"),
                    TableCell(title="Issued"),
                    TableCell(title="Delivered"),
                    TableCell(title="Acknowledged"),
                ),
                *[TableRow(
                    TableCell(Text(r["data"].get("command_id", ""),
                                   weight="medium")),
                    TableCell(Tag(r["data"].get("command") or "—")),
                    TableCell(Tag(r["data"].get("status") or "unknown")),
                    TableCell(Text(r["data"].get("issued_display") or "—",
                                   variant="muted")),
                    TableCell(Text(self.stamp(r["data"].get("delivered_at")),
                                   variant="muted")),
                    TableCell(Text(r["data"].get("acknowledged_display")
                                   or "—", variant="muted")),
                ) for r in self.command_rows],
                sortable=True,
            ),
            gap=10, align="stretch",
        )
