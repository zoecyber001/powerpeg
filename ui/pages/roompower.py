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
    TableCell, TableRow, Tag, Link, biz_url, navigate, set_title, store,
    workpeg,
)

from components import EmptyState, ErrorState, LoadingState, PageHeader


class RoomPowerPage(App):
    MODULE = "roompower"

    loading = State(True)
    error = State("")
    enabled = State(True)
    devices = State([])
    command_rows = State([])
    device_count = State(0)
    command_count = State(0)
    command_summary = State("")
    online_count = State(0)
    awaiting_count = State(0)

    async def on_mount(self):
        store.page_title = "RoomPower"
        set_title("RoomPower")
        await self.load()

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
            return EmptyState(
                "bolt",
                "No devices yet",
                "This business has no controllers registered, so there is"
                " nothing to power on or off.",
                Button("Check again", variant="outline-gray", icon="refresh",
                       on_click=self.retry),
            )
        else:
            return Column(
                self.devices_table(),
                self.commands_table(),
                gap=24,
                align="stretch",
            )

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
