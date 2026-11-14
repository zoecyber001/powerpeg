"""One controller: the AZ3166 demo twin and its request / command / report trail.

Three things are kept apart here, as RoomPower requires:

* **Requested** — what the desk wants (power on, cut non-essential, power off).
  A request only queues a command row; nothing is assumed about the room.
* **Command** — the queued instruction and its lifecycle
  (PENDING, SENT, ACKNOWLEDGED, FAILED, EXPIRED, CANCELLED).
* **Reported** — what the controller itself claims. Reports are append-only
  `device_reports` rows, so this page derives ACKNOWLEDGED by matching a
  report's `command_id` against a queued command instead of editing rows.

The buttons below stand in for a physical board: this is a demo twin running in
the browser, and the page says so wherever it could be mistaken for hardware.
"""
from workpeg.ui import (
    App, State, Padding, Column, Row, Container, Text, Button, Table,
    TableHeader, TableCell, TableRow, Tag, Divider, Icon, Spacer, Link,
    dates, route, biz_url, navigate, set_title, store, workpeg, toast,
)

from components import (

    FactRow,

    EmptyState,
    ErrorState,
    LoadingState,
    PageHeader,
)


class RoomPowerDevicePage(App):
    MODULE = "roompower"

    loading = State(True)
    error = State("")
    enabled = State(True)
    found = State(False)
    busy = State(False)
    action_error = State("")
    action_note = State("")
    device = State({})
    room = State({})
    commands = State([])
    reports = State([])
    requested = State("")
    reported = State("")
    report_age = State("No report yet")
    report_tone = State("neutral")
    state_label = State("")
    state_tone = State("")
    state_note = State("")
    grant_label = State("")
    grant_live = State(False)
    pending_id = State("")

    async def on_mount(self):
        store.page_title = "AZ3166 twin"
        set_title("AZ3166 twin")
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
        defs["authorizations"] = [
            {"id": "event_id", "name": "event_id", "type": "text", "position": 1000, "required": True},
            {"id": "business_id", "name": "business_id", "type": "text", "position": 2000, "required": True},
            {"id": "room_code", "name": "room_code", "type": "text", "position": 3000, "required": True},
            {"id": "authorization_type", "name": "authorization_type", "type": "text", "position": 4000},
            {"id": "status", "name": "status", "type": "text", "position": 5000, "required": True},
            {"id": "source", "name": "source", "type": "text", "position": 6000},
            {"id": "issued_by", "name": "issued_by", "type": "text", "position": 7000},
            {"id": "issued_at", "name": "issued_at", "type": "datetime", "position": 8000},
            {"id": "expires_at", "name": "expires_at", "type": "datetime", "position": 9000},
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
        self.device = {}
        self.room = {}
        self.commands = []
        self.reports = []
        self.pending_id = ""
        try:
            await self.read_device()
            if self.found:
                await self.read_commands()
                await self.read_reports()
                await self.read_grant()
            self.judge()
        except Exception as e:
            self.error = e.message
        self.loading = False

    async def read_device(self):
        table = await self.table("devices")
        if table is None:
            return
        for row in await workpeg.get_rows(table["uuid"], limit=200):
            data = row.get("data") or {}
            if data.get("device_code") == route.device_code:
                self.device = data
                self.found = True
        if not self.found:
            return
        room_code = self.device.get("room_code") or ""
        if not room_code:
            return
        rooms = await self.table("rooms")
        if rooms is None:
            return
        for row in await workpeg.get_rows(rooms["uuid"], limit=200):
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
                mine.append(data)
        mine = mine[::-1]
        lines = []
        for data in mine:
            lines.append({
                "command_id": data.get("command_id") or "",
                "command": data.get("command") or "",
                "status": data.get("status") or "unknown",
                "issued": self.stamp(data.get("issued_at")),
                "reason": data.get("failure_reason") or "",
                "acked": "",
            })
        self.commands = lines

    async def read_reports(self):
        table = await self.table("device_reports")
        if table is None:
            return
        rows = await workpeg.get_rows(table["uuid"], limit=200)
        mine = []
        for row in rows:
            data = row.get("data") or {}
            if data.get("device_code") == route.device_code:
                mine.append(data)
        mine = mine[::-1]
        lines = []
        for data in mine:
            lines.append({
                "report_id": data.get("report_id") or "",
                "relay": (data.get("relay_state") or "").upper(),
                "source": data.get("source") or "",
                "command_id": data.get("command_id") or "",
                "at": self.stamp(data.get("reported_at")),
                "raw": data.get("reported_at") or "",
                "note": data.get("note") or "",
            })
        self.reports = lines
        self.link_reports()

    def link_reports(self):
        """Mark a queued command acknowledged when a report names it."""
        seen = []
        for report in self.reports:
            if report["command_id"]:
                seen.append(report["command_id"])
        updated = []
        for command in self.commands:
            status = command["status"]
            acked = command["acked"]
            if command["command_id"] in seen and (status == "PENDING" or status == "SENT"):
                status = "ACKNOWLEDGED"
                acked = "by twin report"
            updated.append({
                "command_id": command["command_id"],
                "command": command["command"],
                "status": status,
                "issued": command["issued"],
                "reason": command["reason"],
                "acked": acked,
            })
        self.commands = updated

    async def read_grant(self):
        """A live Core grant for this room, if there is one."""
        room_code = self.device.get("room_code") or ""
        self.grant_live = False
        self.grant_label = "No grant for this room"
        table = await self.table("authorizations")
        if table is None or not room_code:
            return
        rows = await workpeg.get_rows(table["uuid"], limit=200)
        latest = None
        for row in rows:
            data = row.get("data") or {}
            if (data.get("room_code") == room_code
                    and (data.get("status") or "") == "granted"):
                if latest is None:
                    latest = data
                elif (data.get("granted_at") or "") >= (
                        latest.get("granted_at") or ""):
                    latest = data
        if latest is None:
            return
        expiry = str(latest.get("expires_at") or "")
        if expiry and dates.to_epoch(expiry) and dates.to_epoch(self.now_iso()) \
                and dates.to_epoch(expiry) < dates.to_epoch(self.now_iso()):
            self.grant_label = "Grant expired " + self.stamp(expiry)
            return
        self.grant_live = True
        guest = latest.get("guest_name") or latest.get("booking_id") or "guest"
        self.grant_label = "Granted to " + str(guest)
        if expiry:
            self.grant_label = (self.grant_label + ", until "
                                + self.stamp(expiry))

    def judge(self):
        """Requested vs reported, stated in one sentence a receptionist reads."""
        self.requested = ""
        self.pending_id = ""
        for command in self.commands:
            if (command["status"] == "PENDING" or command["status"] == "SENT"):
                if self.pending_id == "":
                    self.requested = command["command"]
                    self.pending_id = command["command_id"]
        self.reported = ""
        self.report_age = "No report yet"
        self.report_tone = "neutral"
        if len(self.reports) > 0:
            self.reported = self.reports[0]["relay"]
            self.report_age = self.age_label(self.reports[0]["raw"])
            self.report_tone = self.age_tone(self.reports[0]["raw"])

        if self.reported == "":
            self.state_label = "No report yet"
            self.state_tone = "neutral"
            self.state_note = ("This controller has never reported a relay"
                               " state, so the room's power is unknown.")
            return

        if self.reported == "ON" and not self.grant_live:
            self.state_label = "Unauthorized load"
            self.state_tone = "danger"
            self.state_note = ("The relay is on with no live grant for this"
                               " room. That is a load the desk did not"
                               " authorise.")
            return

        wanted = ""
        if self.requested == "POWER_ON":
            wanted = "ON"
        elif self.requested == "CUT_NON_ESSENTIAL":
            wanted = "OFF"
        elif self.requested == "POWER_OFF":
            wanted = "OFF"

        if wanted and wanted != self.reported:
            self.state_label = "Awaiting acknowledgement"
            self.state_tone = "warning"
            self.state_note = ("Requested " + self.requested + ", controller"
                               " still reports " + self.reported + ".")
            return

        if self.reported == "ON":
            self.state_label = "Live"
            self.state_tone = "success"
            self.state_note = ("The relay is on and reported by the"
                               " controller itself.")
        else:
            self.state_label = "Power off"
            self.state_tone = "neutral"
            self.state_note = ("The relay is off and reported by the"
                               " controller itself.")

    # ── writing ──────────────────────────────────────────────────────────

    async def dispatch(self, command):
        """Queue one command row. Nothing is assumed until the twin reports."""
        self.busy = True
        self.action_error = ""
        self.action_note = ""
        try:
            if command == "POWER_ON" and not self.grant_live:
                self.action_error = ("RoomPower will not switch a room on"
                                     " without a live Core grant. Approve the"
                                     " check-in at the front desk first.")
                self.busy = False
                return
            table = await self.table("commands")
            if table is None:
                self.action_error = "This business has no commands table."
                self.busy = False
                return
            stamp = self.now_iso()
            millis = str(dates.to_epoch(stamp) or 0)
            code = "CMD-" + millis
            row = {
                "command_id": code,
                "business_id": route.business_id,
                "room_code": self.device.get("room_code") or "",
                "device_code": route.device_code,
                "command": command,
                "status": "PENDING",
                "issued_at": stamp,
                "expires_at": "",
                "idempotency_key": code,
                "authorization_event_id": "",
                "failure_reason": "",
                "device_reported_state": "",
            }
            await workpeg.add_row(table["uuid"], {
                "data": row,
                "position": dates.to_epoch(stamp),
            })
            self.action_note = ("Queued " + command + " as " + code
                                + ". The room stays as it is until the twin"
                                " reports back.")
            toast(command + " queued")
            await self.reload()
        except Exception as e:
            self.action_error = e.message
        self.busy = False

    async def power_on(self):
        await self.dispatch("POWER_ON")

    async def cut_essential(self):
        await self.dispatch("CUT_NON_ESSENTIAL")

    async def power_off(self):
        await self.dispatch("POWER_OFF")

    async def report(self, relay):
        """The twin's own claim, appended as a `device_reports` row."""
        self.busy = True
        self.action_error = ""
        self.action_note = ""
        try:
            table = await self.table("device_reports")
            if table is None:
                self.action_error = "This business has no device reports table."
                self.busy = False
                return
            stamp = self.now_iso()
            millis = str(dates.to_epoch(stamp) or 0)
            note = "Demo twin in the browser; not physical hardware."
            if self.pending_id:
                note = (note + " Acknowledges " + self.pending_id + ".")
            row = {
                "report_id": "RPT-" + millis,
                "device_code": route.device_code,
                "room_code": self.device.get("room_code") or "",
                "command_id": self.pending_id,
                "relay_state": relay.lower(),
                "source": "az3166-twin",
                "reported_at": stamp,
                "note": note,
            }
            await workpeg.add_row(table["uuid"], {
                "data": row,
                "position": dates.to_epoch(stamp),
            })
            self.action_note = "The twin reported relay " + relay + "."
            toast("Twin reported " + relay)
            await self.reload()
        except Exception as e:
            self.action_error = e.message
        self.busy = False

    async def report_on(self):
        await self.report("ON")

    async def report_off(self):
        await self.report("OFF")

    async def reload(self):
        self.loading = True
        self.error = ""
        self.found = False
        try:
            await self.read_device()
            if self.found:
                await self.read_commands()
                await self.read_reports()
                await self.read_grant()
            self.judge()
        except Exception as e:
            self.error = e.message
        self.loading = False

    def retry(self):
        self.loading = True
        navigate(biz_url("/roompower/" + route.device_code))

    # ── helpers ──────────────────────────────────────────────────────────


    def now_iso(self):
        return str(dates.now("Africa/Lagos", True) or "") + "+01:00"

    def freshness_tag(self):
        """The report's age, coloured: green fresh, red once it has gone cold."""
        if self.report_tone == "success":
            return Tag(self.report_age, tone="success")
        elif self.report_tone == "critical":
            return Tag(self.report_age, tone="critical")
        elif self.report_tone == "warning":
            return Tag(self.report_age, tone="warning")
        else:
            return Tag(self.report_age)

    def age_seconds(self, raw):
        """Seconds since the controller's own report, or -1 if unreadable."""
        if not raw:
            return -1
        then = dates.to_epoch(raw)
        now = dates.to_epoch(self.now_iso())
        if not then or not now:
            return -1
        return int(now) - int(then)

    def age_label(self, raw):
        seconds = self.age_seconds(raw)
        if seconds < 0:
            return "Report time unknown"
        elif seconds < 120:
            return "Fresh, just reported"
        elif seconds < 1800:
            return "Fresh, " + str(int(seconds / 60)) + " min old"
        else:
            return "Stale, " + self.age_long(seconds)

    def age_long(self, seconds):
        hours = int(seconds / 3600)
        minutes = int((seconds - hours * 3600) / 60)
        if hours == 0:
            return str(minutes) + " min old"
        elif minutes == 0:
            return str(hours) + " h old"
        else:
            return str(hours) + " h " + str(minutes) + " min old"

    def age_tone(self, raw):
        seconds = self.age_seconds(raw)
        if seconds < 0:
            return "warning"
        elif seconds < 1800:
            return "success"
        else:
            return "critical"

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

    def open_roompower(self):
        navigate(biz_url("/roompower"))

    def open_front_desk(self):
        navigate(biz_url("/front-desk"))

    # ── rendering ────────────────────────────────────────────────────────

    def build(self):
        return Padding(
            Column(
                PageHeader(
                    "AZ3166 twin",
                    "Dispatch a command, let the demo controller report back,"
                    " and watch requested, command and reported state stay"
                    " separate.",
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
            return LoadingState("Reading this controller...")
        elif self.error != "":
            return ErrorState(
                self.error,
                Button("Reload the page", variant="outline-gray",
                       icon="refresh", on_click=self.retry),
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
                self.status_card(),
                Row(self.room_card(), self.report_card(), gap=16,
                    align="stretch"),
                self.controls_card(),
                self.messages(),
                self.command_table(),
                self.report_table(),
                gap=20,
                align="stretch",
            )

    def status_card(self):
        return Container(
            Column(
                Row(
                    Icon("cpu", size=18),
                    Text(self.state_label or "Unknown", variant="title",
                         weight="medium"),
                    Spacer(),
                    self.freshness_tag(),
                    Tag(self.device.get("device_code") or "—"),
                    align="center",
                    gap=10,
                ),
                Text(self.state_note or "", variant="muted"),
                Row(
                    FactRow("Requested", self.requested or "nothing pending"),
                    FactRow("Reported", self.reported or "nothing yet"),
                    FactRow("Grant", self.grant_label or "—"),
                    gap=24,
                    align="start",
                ),
                gap=12,
                align="stretch",
            ),
            variant="card",
            padding=20,
        )

    def room_card(self):
        return Column(
            Row(
                Text("Room", weight="semibold"),
                Spacer(),
                self.room_link(),
                gap=8, align="center",
            ),
            Column(
                FactRow("Room", self.room.get("display_name") or "—"),
                FactRow("Room code", self.room.get("room_code") or "—"),
                FactRow("Status", self.room.get("status") or "unknown"),
                FactRow("Controller", self.device.get("device_code") or "—"),
                FactRow("Connection",
                        self.device.get("connection_status") or "unknown",
                        ruled=False),
                gap=2,
            ),
            gap=8,
            align="stretch",
        )

    def room_link(self):
        if self.room.get("room_code"):
            return Link("Open room view",
                        href=biz_url("/roompower/room/"
                                     + self.room.get("room_code")))
        return Spacer()

    def report_card(self):
        return Column(
            Text("Controller", weight="semibold"),
            Column(
                FactRow("Type", self.device.get("device_type") or "AZ3166"),
                FactRow("Last seen",
                        self.stamp(self.device.get("last_seen_at"))),
                FactRow("Reports", str(len(self.reports)) + " recorded"),
                FactRow("Commands", str(len(self.commands)) + " queued"),
                gap=2,
            ),
            gap=8,
            align="stretch",
        )

    def controls_card(self):
        return Container(
            Column(
                Row(Text("Dispatch a command", weight="semibold"),
                    Spacer(),
                    Tag("requested state"), align="center", gap=8),
                Text(
                    "A command is queued with status PENDING. The room's power"
                    " does not change until the controller reports, and no"
                    " grant is implied by a command.",
                    variant="muted",
                ),
                Row(
                    Button("Request power on", variant="primary",
                           icon="power", on_click=self.power_on),
                    Button("Cut non-essential", variant="outline-gray",
                           icon="minus", on_click=self.cut_essential),
                    Button("Request power off", variant="outline-gray",
                           icon="hand-stop", on_click=self.power_off),
                    gap=10,
                    align="center",
                ),
                Divider(),
                Row(Text("Demo twin", weight="semibold"),
                    Spacer(),
                    Tag("not physical hardware"), align="center", gap=8),
                Text(
                    "These buttons stand in for the AZ3166 board. Each press"
                    " appends a report of what the controller claims; it never"
                    " edits a command row.",
                    variant="muted",
                ),
                Row(
                    Button("Twin reports relay ON", variant="outline-gray",
                           icon="toggle-right", on_click=self.report_on),
                    Button("Twin reports relay OFF", variant="outline-gray",
                           icon="toggle-left", on_click=self.report_off),
                    gap=10,
                    align="center",
                ),
                gap=12,
                align="stretch",
            ),
            variant="card",
            padding=20,
        )

    def messages(self):
        if self.action_error != "":
            return Container(
                Row(Icon("alert-triangle", size=16),
                    Text(self.action_error, variant="muted"),
                    gap=10, align="start"),
                variant="card",
                padding=14,
            )
        elif self.action_note != "":
            return Container(
                Row(Icon("circle-check", size=16),
                    Text(self.action_note, variant="muted"),
                    gap=10, align="start"),
                variant="card",
                padding=14,
            )
        else:
            return Spacer()

    def command_table(self):
        if len(self.commands) == 0:
            return Column(
                Text("Commands", weight="semibold"),
                Text("No command has ever been sent to this controller.",
                     variant="caption"),
                gap=8,
                align="stretch",
            )
        return Column(
            Row(Text("Commands", weight="semibold"),
                Text("newest first", variant="caption"),
                align="center", gap=8),
            Table(
                TableHeader(
                    TableCell(title="Command"),
                    TableCell(title="Requested"),
                    TableCell(title="Status"),
                    TableCell(title="Issued"),
                    TableCell(title="Note"),
                ),
                *[TableRow(
                    TableCell(Text(c["command_id"], weight="medium")),
                    TableCell(Tag(c["command"] or "—")),
                    TableCell(Tag(c["status"] or "unknown")),
                    TableCell(Text(c["issued"] or "—", variant="muted")),
                    TableCell(Text(c["acked"] or c["reason"] or "—",
                                   variant="muted")),
                ) for c in self.commands],
            ),
            Text(
                "ACKNOWLEDGED appears here when a controller report names the"
                " command; the command row itself is never rewritten by this"
                " page.",
                variant="caption",
            ),
            gap=10,
            align="stretch",
        )

    def report_table(self):
        if len(self.reports) == 0:
            return Column(
                Text("Reported state", weight="semibold"),
                Text("The controller has not reported yet.", variant="caption"),
                gap=8,
                align="stretch",
            )
        return Column(
            Row(Text("Reported state", weight="semibold"),
                Text(str(len(self.reports)) + " reports", variant="caption"),
                align="center", gap=8),
            Table(
                TableHeader(
                    TableCell(title="Reported"),
                    TableCell(title="Relay"),
                    TableCell(title="Source"),
                    TableCell(title="Acknowledges"),
                    TableCell(title="Note"),
                ),
                *[TableRow(
                    TableCell(Text(r["at"] or "—", variant="muted")),
                    TableCell(Tag(r["relay"] or "—")),
                    TableCell(Text(r["source"] or "—")),
                    TableCell(Text(r["command_id"] or "—", variant="muted")),
                    TableCell(Text(r["note"] or "—", variant="caption")),
                ) for r in self.reports],
            ),
            gap=10,
            align="stretch",
        )
