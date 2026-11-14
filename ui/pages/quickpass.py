"""QuickPass: identity sessions and the check-ins they made possible.

The page reads two tables from the platform: `verifications`, which is one row
per identity session and names its provider, and `check_ins`, which is what the
desk approved afterwards. It never calls a provider itself; only the function
holds the Didit key, and a Didit approval does not create a check-in.

The provider column is deliberate: a demo session says demo, and a real Didit
session says didit, because a receptionist must never mistake one for the
other. The session link opens the hosted verification page for that guest.
"""
from workpeg.ui import (
    App, State, Padding, Column, Row, Container, Text, Button, Table,
    TableHeader, TableCell, TableRow, Tag, Link, Spacer, biz_url, navigate,
    set_title, store, workpeg,
)

from components import EmptyState, ErrorState, LoadingState, PageHeader, StatCard




class QuickPassPage(App):
    MODULE = "quickpass"

    loading = State(True)
    error = State("")
    enabled = State(True)
    sessions = State([])
    check_ins = State([])
    verified_count = State(0)
    review_count = State(0)
    pending_count = State(0)
    check_in_count = State(0)

    async def on_mount(self):
        store.page_title = "QuickPass"
        set_title("QuickPass")
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
        defs["check_ins"] = [
            {"name": "check_in_id", "type": "string", "required": True},
            {"name": "booking_id", "type": "string", "required": True},
            {"name": "room_code", "type": "string", "required": True},
            {"name": "guest_label", "type": "string", "required": True},
            {"name": "arrived_at", "type": "datetime"},
            {"name": "verified_at", "type": "datetime"},
            {"name": "approved_at", "type": "datetime"},
            {"name": "activated_at", "type": "datetime"},
            {"name": "check_in_status", "type": "string"},
        ]
        defs["verifications"] = [
            {"name": "verification_id", "type": "string", "required": True},
            {"name": "booking_id", "type": "string", "required": True},
            {"name": "guest_label", "type": "string"},
            {"name": "room_code", "type": "string"},
            {"name": "provider", "type": "string"},
            {"name": "session_id", "type": "string"},
            {"name": "verification_url", "type": "string"},
            {"name": "provider_status", "type": "string"},
            {"name": "status", "type": "string"},
            {"name": "decision", "type": "string"},
            {"name": "reviewed_by", "type": "string"},
            {"name": "created_at", "type": "datetime"},
            {"name": "updated_at", "type": "datetime"},
            {"name": "last_event_id", "type": "string"},
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
        self.loading = True
        self.error = ""
        try:
            self.enabled = await self.module_on()
            if self.enabled:
                self.read_sessions()
                self.read_check_ins()
        except Exception as e:
            self.error = e.message
        self.loading = False

    async def read_sessions(self):
        """Sessions newest first, with the counts a receptionist acts on."""
        lines = []
        verified = 0
        review = 0
        pending = 0
        table = await self.table("verifications")
        if table is not None:
            rows = await workpeg.get_rows(table["uuid"], limit=300)
            for row in rows[::-1]:
                data = row.get("data") or {}
                status = (data.get("status") or "pending").lower()
                provider = data.get("provider") or "unknown"
                lines.append({
                    "verification_id": data.get("verification_id") or "—",
                    "booking_id": data.get("booking_id") or "",
                    "guest": data.get("guest_label") or "Guest",
                    "room": data.get("room_code") or "—",
                    "provider": provider,
                    "provider_status": data.get("provider_status") or "—",
                    "status": status,
                    "url": data.get("verification_url") or "",
                    "updated": self.stamp(data.get("updated_at")),
                })
                if status == "verified":
                    verified = verified + 1
                elif status == "review_required":
                    review = review + 1
                elif status == "pending":
                    pending = pending + 1
        self.sessions = lines
        self.verified_count = verified
        self.review_count = review
        self.pending_count = pending

    async def read_check_ins(self):
        lines = []
        table = await self.table("check_ins")
        if table is not None:
            rows = await workpeg.get_rows(table["uuid"], limit=200)
            for row in rows[::-1]:
                data = row.get("data") or {}
                lines.append({
                    "booking_id": data.get("booking_id") or "",
                    "guest": data.get("guest_label") or "Guest",
                    "room": data.get("room_code") or "—",
                    "approved": self.stamp(data.get("approved_at")),
                    "status": data.get("check_in_status") or "—",
                })
        self.check_ins = lines
        self.check_in_count = len(lines)


    async def module_on(self):
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

    async def retry(self):
        await self.load()

    def open_overview(self):
        navigate(biz_url("/"))

    def open_front_desk(self):
        navigate(biz_url("/front-desk"))

    def build(self):
        return Padding(
            Column(
                PageHeader(
                    "QuickPass",
                    "Identity sessions for this business, and the check-ins"
                    " the desk approved from them.",
                    Button("Front desk", variant="outline-gray",
                           icon="arrow-left", on_click=self.open_front_desk),
                ),
                self.body(),
                gap=24,
            ),
            all=24,
        )

    def body(self):
        if self.loading:
            return LoadingState("Reading identity sessions...")
        elif self.error != "":
            return ErrorState(
                self.error,
                Button("Reload the page", variant="outline-gray",
                       icon="refresh", on_click=self.retry),
            )
        elif not self.enabled:
            return EmptyState(
                "toggle-left",
                "QuickPass is not enabled",
                "This business has switched the module off, so no identity"
                " sessions are read here.",
                Button("Open the overview", variant="outline-gray",
                       icon="home", on_click=self.open_overview),
            )
        elif len(self.sessions) == 0:
            return EmptyState(
                "shield",
                "No identity sessions yet",
                "Sessions appear here once a guest starts a QuickPass check.",
                Button("Front desk", variant="outline-gray", icon="arrow-left",
                       on_click=self.open_front_desk),
            )
        else:
            return Column(
                Row(
                    Container(StatCard("Sessions", str(len(self.sessions)),
                                       "identity checks requested"),
                              variant="card", padding=16),
                    Container(StatCard("Verified", str(self.verified_count),
                                       "eligible for check-in"),
                              variant="card", padding=16),
                    Container(StatCard("Needs review", str(self.review_count),
                                       "flagged by the provider"),
                              variant="card", padding=16),
                    Container(StatCard("Pending", str(self.pending_count),
                                       "guest has not finished"),
                              variant="card", padding=16),
                    gap=12, align="stretch",
                ),
                self.sessions_block(),
                self.checkins_block(),
                gap=20, align="stretch",
            )

    def sessions_block(self):
        return Column(
            Row(Text("Identity sessions", weight="semibold"),
                Spacer(),
                Text("provider is named on every row", variant="caption"),
                align="center", gap=8),
            Table(
                TableHeader(
                    TableCell(title="Guest"),
                    TableCell(title="Room"),
                    TableCell(title="Provider"),
                    TableCell(title="Provider status"),
                    TableCell(title="QuickPass status"),
                    TableCell(title="Updated"),
                    TableCell(title="Session"),
                ),
                *[TableRow(
                    TableCell(Text(s["guest"], weight="medium")),
                    TableCell(Text(s["room"], variant="muted")),
                    TableCell(Tag(s["provider"])),
                    TableCell(Text(s["provider_status"], variant="muted")),
                    TableCell(Tag(s["status"])),
                    TableCell(Text(s["updated"], variant="muted")),
                    TableCell(self.session_link(s)),
                ) for s in self.sessions],
                search="Search sessions",
            ),
            gap=10, align="stretch",
        )

    def session_link(self, session):
        if session["url"]:
            return Link("Open session", href=session["url"])
        else:
            return Text("no hosted link", variant="caption")

    def checkins_block(self):
        if len(self.check_ins) == 0:
            return Column(
                Text("Check-ins", weight="semibold"),
                Text("The desk has not approved a check-in yet.",
                     variant="caption"),
                gap=8, align="stretch",
            )
        return Column(
            Row(Text("Check-ins", weight="semibold"),
                Text(str(self.check_in_count) + " recorded", variant="caption"),
                align="center", gap=8),
            Table(
                TableHeader(
                    TableCell(title="Guest"),
                    TableCell(title="Room"),
                    TableCell(title="Approved"),
                    TableCell(title="Status"),
                    TableCell(title="Booking"),
                ),
                *[TableRow(
                    TableCell(Text(c["guest"], weight="medium")),
                    TableCell(Text(c["room"], variant="muted")),
                    TableCell(Text(c["approved"], variant="muted")),
                    TableCell(Tag(c["status"])),
                    TableCell(Text(c["booking_id"], variant="caption")),
                ) for c in self.check_ins],
            ),
            gap=10, align="stretch",
        )
