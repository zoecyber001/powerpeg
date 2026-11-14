"""Room view: one room, its appliances, and what the controller reports.

The guest-facing window into RoomPower. A room's photo, its facts, and the
appliances a guest would actually look at — air conditioning, television,
lights — each shown as on or off, derived from the latest relay report the
controller sent (falling back to the device's own record when it has never
reported).

The appliance states are a simulation: the AZ3166 twin reports one relay, and
this page plays the room from it, honestly labelled as such. The air
conditioner's temperature is the one live number — a simulated read of the
room air that drifts toward 22°C while the relay is on and toward the warm
30°C of a Lagos afternoon when it is not, re-drawn every second and a half.
A real photo goes where the placeholders sit; until then every image slot
says so in plain words.
"""
from workpeg.ui import (
    App, State, Padding, Column, Row, Container, Text, Button, Tag, Link,
    Icon, Divider, Spacer, Expanded, dates, route, biz_url, navigate,
    set_title, store, workpeg, set_interval,
)

from components import (
    FactRow,
    EmptyState,
    ErrorState,
    LoadingState,
    PageHeader,
)


class RoomViewPage(App):
    MODULE = "roompower"

    loading = State(True)
    error = State("")
    enabled = State(True)
    found = State(False)
    room_code = State("")
    room = State({})
    device = State({})
    device_code = State("")
    reports_count = State(0)
    last_report = State("")
    relay = State("")
    relay_source = State("")
    ac_temp = State(294)       # simulated room air, in tenths of a degree
    ticks = State(0)

    async def on_mount(self):
        store.page_title = "Room view"
        set_title("Room view")
        set_interval(self.tick, 1500)
        self.room_code = str(route.room_code or "")
        await self.load()

    # ── reading ──────────────────────────────────────────────────────────

    async def table(self, name):
        """This business's table with that name, created if absent.

        Found by the table's own namespace label (get_tables filters
        on it); a table the business has never used is created here
        on first use, in the shape the Tables API expects. Column ids
        are the manifest's column names, so every row write and read
        keeps its keys."""
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
        defs["device_reports"] = [
            {"id": "report_id", "name": "report_id", "type": "text", "position": 1000},
            {"id": "device_code", "name": "device_code", "type": "text", "position": 2000},
            {"id": "room_code", "name": "room_code", "type": "text", "position": 3000},
            {"id": "command_id", "name": "command_id", "type": "text", "position": 4000},
            {"id": "relay_state", "name": "relay_state", "type": "text", "position": 5000},
            {"id": "source", "name": "source", "type": "text", "position": 6000},
            {"id": "reported_at", "name": "reported_at", "type": "text", "position": 7000},
            {"id": "note", "name": "note", "type": "text", "position": 8000},
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
        self.loading = True
        self.error = ""
        self.enabled = True
        self.found = False
        try:
            self.enabled = await self.module_on()
            if self.enabled:
                await self.read_room()
        except Exception as e:
            self.error = e.message
        self.loading = False

    async def read_room(self):
        """The room, its controller, and the latest relay report for it."""
        code = self.room_code
        rooms = await self.table("rooms")
        if rooms is None:
            return
        for row in await workpeg.get_rows(rooms["uuid"], limit=200):
            data = row.get("data") or {}
            if data.get("room_code") == code:
                self.room = data
                self.found = True
        if not self.found:
            return
        devices = await self.table("devices")
        if devices is not None:
            for row in await workpeg.get_rows(devices["uuid"], limit=200):
                data = row.get("data") or {}
                if data.get("room_code") == code:
                    self.device = data
                    self.device_code = data.get("device_code") or ""
        self.relay = ""
        self.relay_source = ""
        latest = None
        latest_at = 0
        reports = await self.table("device_reports")
        if reports is not None and self.device_code:
            mine = []
            for row in await workpeg.get_rows(reports["uuid"], limit=200):
                data = row.get("data") or {}
                if data.get("device_code") == self.device_code:
                    mine.append(data)
            self.reports_count = len(mine)
            for data in mine:
                at = dates.to_epoch(data.get("reported_at") or "") or 0
                if at >= latest_at:
                    latest_at = at
                    latest = data
        if latest is not None:
            self.relay = (latest.get("relay_state") or "").upper()
            self.relay_source = "the controller's own report"
            self.last_report = self.stamp(latest.get("reported_at"))
        elif self.device_code:
            fallback = (self.device.get("reported_relay_state") or "").upper()
            if fallback:
                self.relay = fallback
                self.relay_source = "the device record (no report yet)"
        if self.ac_temp == 0:
            if self.relay == "ON":
                self.ac_temp = 262
            else:
                self.ac_temp = 294

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

    # ── the simulated room air ───────────────────────────────────────────

    def tick(self):
        """Drift the simulated air toward the set point the relay implies.

        On with a grant, the air conditioning pulls the room to 22°C; off,
        the room drifts to the warm 30°C outside. A small wobble keeps the
        read alive without pretending the sensor is more than a simulation.
        """
        if not self.found:
            return
        target = 300
        if self.relay == "ON":
            target = 220
        diff = target - self.ac_temp
        move = 0
        if diff > 0:
            move = 2
        elif diff < 0:
            move = -2
        if diff > 80:
            move = 5
        elif diff < -80:
            move = -5
        wobble = 0
        phase = self.ticks % 3
        if phase == 0:
            wobble = 1
        elif phase == 1:
            wobble = 0
        else:
            wobble = -1
        self.ac_temp = self.ac_temp + move + wobble
        if self.ac_temp < 180:
            self.ac_temp = 180
        elif self.ac_temp > 320:
            self.ac_temp = 320
        self.ticks = self.ticks + 1

    # ── helpers ──────────────────────────────────────────────────────────

    def temp_display(self):
        return str(self.ac_temp // 10) + "." + str(self.ac_temp % 10) + "°C"

    def ac_tag(self):
        if self.relay == "ON":
            return Tag("Running", tone="success", dot=True)
        elif self.relay == "":
            return Tag("Unknown", tone="warning", dot=True)
        else:
            return Tag("Off", tone="neutral", dot=True)

    def ac_note(self):
        if self.relay == "":
            return ("No report yet, so the air is assumed warm and drifts"
                    " toward 30.0°C.")
        elif self.relay == "ON":
            diff = self.ac_temp - 220
            if diff > 5:
                return "Cooling toward the 22.0°C set point."
            elif diff < -5:
                return "A touch under the set point, easing back up."
            else:
                return "Holding the 22.0°C set point."
        else:
            if self.ac_temp >= 298:
                return "The room sits at the warm 30.0°C of the day."
            return "The relay is off, so the air drifts toward 30.0°C."

    def tv_tag(self):
        if self.relay == "ON":
            return Tag("On", tone="success", dot=True)
        elif self.relay == "":
            return Tag("Unknown", tone="warning", dot=True)
        else:
            return Tag("Standby", tone="neutral", dot=True)

    def lights_tag(self):
        if self.relay == "ON":
            return Tag("On", tone="success", dot=True)
        elif self.relay == "":
            return Tag("Unknown", tone="warning", dot=True)
        else:
            return Tag("Off", tone="neutral", dot=True)

    def relay_tag(self):
        if self.relay == "ON":
            return Tag("Relay ON", tone="success", dot=True)
        elif self.relay == "OFF":
            return Tag("Relay OFF", tone="neutral", dot=True)
        else:
            return Tag("No report yet", tone="warning", dot=True)

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

    def console_link(self):
        if self.device_code:
            return Link("Open the twin console",
                        href=biz_url("/roompower/" + self.device_code))
        return Spacer()

    def relay_sentence(self):
        if self.relay_source == "":
            return "Nothing has reported a relay state for this room yet."
        return ("The relay comes from " + self.relay_source + ".")

    def open_roompower(self):
        navigate(biz_url("/roompower"))

    # ── rendering ────────────────────────────────────────────────────────

    def build(self):
        return Padding(
            Column(
                PageHeader(
                    "Room view",
                    "One room, its appliances, and what the controller"
                    " reports — simulated from the relay, and labelled as"
                    " such.",
                    Button("RoomPower", variant="outline-gray",
                           icon="arrow-left", on_click=self.open_roompower),
                ),
                self.body(),
                gap=24,
            ),
            all=24,
        )

    def body(self):
        if self.loading:
            return LoadingState("Reading this room...")
        elif self.error != "":
            return ErrorState(
                self.error,
                Button("Reload the page", variant="outline-gray",
                       icon="refresh", on_click=self.open_roompower),
            )
        elif not self.enabled:
            return EmptyState(
                "toggle-left",
                "RoomPower is not enabled",
                "This business has switched the module off, so the rooms"
                " have no appliance view.",
                Button("Open the overview", variant="outline-gray",
                       icon="home", on_click=self.open_roompower),
            )
        elif not self.found:
            return EmptyState(
                "photo",
                "No room with that code",
                "This business has no room recorded under this code.",
                Button("All rooms and devices", variant="outline-gray",
                       icon="arrow-left", on_click=self.open_roompower),
            )
        else:
            return Column(
                Row(Expanded(self.photo_hero()), self.facts_card(),
                    gap=16, align="stretch"),
                Row(Expanded(self.ac_card()), Expanded(self.tv_card()),
                    Expanded(self.lights_card()), gap=12, align="stretch"),
                self.trail_card(),
                gap=20,
                align="stretch",
            )

    def photo_hero(self):
        """Where the room's photograph goes; a placeholder until it does."""
        return Container(
            Column(
                Icon("photo", size=28, weight="thin"),
                Text("Room photo", weight="medium"),
                Text("Placeholder — the room's photograph goes here.",
                     variant="caption"),
                gap=8, align="center",
            ),
            variant="card", padding=32,
        )

    def facts_card(self):
        return Container(
            Column(
                Row(
                    Text(self.room.get("display_name") or "Room",
                         variant="title", weight="medium"),
                    self.relay_tag(),
                    align="center", gap=10,
                ),
                Text(self.room.get("pitch") or "", variant="muted"),
                FactRow("Room code", self.room.get("room_code") or "—"),
                FactRow("Room type", self.room.get("room_type") or "—"),
                FactRow("Status", self.room.get("status") or "unknown"),
                FactRow("Area", self.room.get("area") or "—"),
                FactRow("Controller", self.device_code or "none yet"),
                FactRow("Connection",
                        self.device.get("connection_status") or "unknown",
                        ruled=False),
                gap=4, align="stretch",
            ),
            variant="card", padding=20,
        )

    def ac_card(self):
        return Container(
            Column(
                Row(
                    Icon("adjustments", size=16),
                    Text("Air conditioning", weight="semibold"),
                    Spacer(),
                    self.ac_tag(),
                    align="center", gap=8,
                ),
                Row(
                    Text(self.temp_display(), variant="title"),
                    Text("simulated air", variant="caption"),
                    gap=10, align="end",
                ),
                Text(self.ac_note(), variant="muted"),
                Row(
                    Icon("photo", size=14),
                    Text("AC photo placeholder", variant="caption"),
                    gap=6, align="center",
                ),
                gap=8, align="start",
            ),
            variant="card", padding=20,
        )

    def tv_card(self):
        return Container(
            Column(
                Row(
                    Icon("video", size=16),
                    Text("Television", weight="semibold"),
                    Spacer(),
                    self.tv_tag(),
                    align="center", gap=8,
                ),
                Text("Follows the controller relay: on while the room is"
                     " powered, standby when it is not.", variant="muted"),
                Row(
                    Icon("photo", size=14),
                    Text("TV photo placeholder", variant="caption"),
                    gap=6, align="center",
                ),
                gap=8, align="start",
            ),
            variant="card", padding=20,
        )

    def lights_card(self):
        return Container(
            Column(
                Row(
                    Icon("sun", size=16),
                    Text("Lights", weight="semibold"),
                    Spacer(),
                    self.lights_tag(),
                    align="center", gap=8,
                ),
                Text("Follows the controller relay: lit while the room is"
                     " powered, dark when it is not.", variant="muted"),
                Row(
                    Icon("photo", size=14),
                    Text("Lights photo placeholder", variant="caption"),
                    gap=6, align="center",
                ),
                gap=8, align="start",
            ),
            variant="card", padding=20,
        )

    def trail_card(self):
        return Container(
            Column(
                Row(
                    Text("Where this state comes from", weight="semibold"),
                    Spacer(),
                    self.console_link(),
                    align="center", gap=8,
                ),
                Text(
                    "The appliance states above are simulated from the"
                    " relay the AZ3166 demo twin reports — not physical"
                    " hardware. " + self.relay_sentence(),
                    variant="muted",
                ),
                FactRow("Relay", self.relay or "no report yet"),
                FactRow("Latest report", self.last_report),
                FactRow("Reports recorded", str(self.reports_count)),
                FactRow("Device type",
                        self.device.get("device_type") or "—",
                        ruled=False),
                gap=6, align="stretch",
            ),
            variant="card", padding=20,
        )
