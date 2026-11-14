"""The arrival desk: payment, QuickPass, an explicit approval, then RoomPower.

This page is the receptionist's desk for real reservations. It reads the
platform's own tables and it writes them, so what it shows is the business's
record rather than a demonstration:

* payment and identity status come from `payments` and `verifications`;
* **Approve check-in** appends the Core grant (`authorizations`) and the
  `check_ins` record, then queues a POWER_ON command. The room does not change
  until the controller reports;
* **Check out** appends a revoking authorisation, the check-in's closing
  record, a checkout energy command, and a housekeeping task.

A Didit approval is never a check-in by itself: the identity row only makes the
guest eligible, and the receptionist's click is the approval.
"""
from workpeg.ui import (
    App, State, Padding, Column, Row, Container, Text, Button, Table,
    TableHeader, TableCell, TableRow, Tag, Divider, Icon, Spacer, dates,
    route, biz_url, navigate, set_title, store, workpeg, toast,
)

from components import (
    EmptyState,
    ErrorState,
    LoadingState,
    PageHeader,
    StatCard,
)


class FrontDeskPage(App):
    MODULE = "quickpass"

    loading = State(True)
    error = State("")
    action_error = State("")
    action_note = State("")
    busy = State(False)
    arrivals = State([])
    requests = State([])
    arriving_count = State(0)
    in_house_count = State(0)
    review_count = State(0)
    request_count = State(0)

    async def on_mount(self):
        store.page_title = "Front desk"
        set_title("Front desk")
        await self.load()

    # ── reading ──────────────────────────────────────────────────────────

    async def load(self):
        self.loading = True
        self.error = ""
        try:
            rooms = await self.read_map("rooms", "room_code")
            devices = await self.read_devices()
            payments = await self.read_map("payments", "booking_id")
            verifications = await self.read_map("verifications", "booking_id")
            grants = await self.read_grants()
            table = await self.table("bookings")
            lines = []
            if table is not None:
                for row in await workpeg.get_rows(table["uuid"], limit=200):
                    data = row.get("data") or {}
                    lines.append(self.arrival_line(data, rooms, devices,
                                                   payments, verifications,
                                                   grants))
            lines = lines[::-1]
            self.arrivals = lines
            self.count(lines)
            await self.read_requests(rooms)
        except Exception as e:
            self.error = e.message
        self.loading = False

    def count(self, lines):
        arriving = 0
        in_house = 0
        review = 0
        for line in lines:
            if line["state"] == "Arriving":
                arriving = arriving + 1
            elif line["state"] == "In house":
                in_house = in_house + 1
            if line["review"]:
                review = review + 1
        self.arriving_count = arriving
        self.in_house_count = in_house
        self.review_count = review

    def arrival_line(self, booking, rooms, devices, payments, verifications,
                     grants):
        booking_id = booking.get("booking_id") or ""
        room_code = booking.get("room_code") or ""
        room = rooms.get(room_code) or {}
        payment = payments.get(booking_id) or {}
        verification = verifications.get(booking_id) or {}
        grant = grants.get(room_code) or {}

        payment_status = (payment.get("payment_status") or "").lower()
        verified = (verification.get("status") or "").lower()
        review = verified == "review_required"
        grant_status = (grant.get("status") or "").lower()
        live = grant_status == "granted" and self.is_live(
            grant.get("expires_at"))

        if live:
            state = "In house"
        elif grant_status == "revoked":
            state = "Checked out"
        else:
            state = "Arriving"

        reasons = []
        if payment_status != "confirmed":
            reasons.append("payment is not confirmed")
        if verified == "" or verified == "pending":
            reasons.append("identity check has not finished")
        elif verified == "rejected":
            reasons.append("identity check was declined")
        elif verified == "expired":
            reasons.append("identity check expired")
        elif verified == "error":
            reasons.append("identity check failed")
        elif review:
            reasons.append("identity check needs a human review")
        can_approve = len(reasons) == 0 or (review and payment_status
                                            == "confirmed"
                                            and len(reasons) == 1)

        provider = verification.get("provider") or ""
        if verified == "":
            verification_label = "not started"
        elif provider == "demo":
            verification_label = verified + " (demo)"
        elif provider != "":
            verification_label = verified + " (" + provider + ")"
        else:
            verification_label = verified

        note = ""
        if state == "Arriving" and len(reasons) > 0:
            note = "Blocked: " + ", ".join(reasons) + "."
        elif state == "In house":
            note = "Grant live. RoomPower may switch the room on."
        elif state == "Checked out":
            note = "Grant revoked; checkout energy policy applied."

        return {
            "booking_id": booking_id,
            "room_code": room_code,
            "room_name": room.get("display_name") or room_code,
            "guest": booking.get("guest_label") or "Guest",
            "dates": self.stay_label(booking),
            "end_at": booking.get("end_at") or "",
            "payment": payment_status or "pending",
            "verification": verification_label,
            "grant": grant_status or "none",
            "state": state,
            "note": note,
            "review": review,
            "can_approve": can_approve and state == "Arriving",
            "can_checkout": state == "In house",
            "device_code": devices.get(room_code) or "",
        }

    async def read_requests(self, rooms):
        table = await self.table("service_requests")
        lines = []
        if table is not None:
            rows = await workpeg.get_rows(table["uuid"], limit=200)
            recent = rows[::-1]
            for row in recent:
                data = row.get("data") or {}
                room = rooms.get(data.get("room_code")) or {}
                lines.append({
                    "request_id": data.get("request_id") or "",
                    "room": room.get("display_name")
                    or data.get("room_code") or "—",
                    "guest": data.get("guest_label") or "Guest",
                    "category": data.get("category") or "—",
                    "detail": data.get("detail") or "—",
                    "status": data.get("status") or "requested",
                    "at": self.stamp(data.get("created_at")),
                })
        self.requests = lines
        self.request_count = len(lines)

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

    async def read_devices(self):
        out = {}
        table = await self.table("devices")
        if table is None:
            return out
        for row in await workpeg.get_rows(table["uuid"], limit=200):
            data = row.get("data") or {}
            room_code = data.get("room_code")
            if room_code and data.get("device_code"):
                out[room_code] = data.get("device_code")
        return out

    async def read_grants(self):
        """The newest authorisation event per room, whatever its status."""
        out = {}
        table = await self.table("authorizations")
        if table is None:
            return out
        for row in await workpeg.get_rows(table["uuid"], limit=300):
            data = row.get("data") or {}
            room_code = data.get("room_code") or ""
            current = out.get(room_code)
            if current is None:
                out[room_code] = data
            elif (data.get("issued_at") or "") >= (current.get("issued_at")
                                                   or ""):
                out[room_code] = data
        return out

    def is_live(self, expiry):
        if not expiry:
            return True
        try:
            return dates.to_epoch(expiry) > dates.to_epoch(self.now_iso())
        except Exception:
            return True

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

    def stay_label(self, booking):
        start = booking.get("start_at")
        end = booking.get("end_at")
        if start and end:
            return (self.stamp(start)[0:12] + " to " + self.stamp(end)[0:12])
        elif start:
            return "from " + self.stamp(start)
        else:
            return "no dates recorded"

    async def table(self, name):
        tables = await workpeg.get_tables()
        for candidate in tables:
            if candidate.get("name") == name:
                return candidate
        return None

    # ── writing ──────────────────────────────────────────────────────────

    async def approve(self, booking_id):
        """Explicit approval: grant, check-in record, then a power-on command."""
        self.busy = True
        self.action_error = ""
        self.action_note = ""
        try:
            target = None
            for line in self.arrivals:
                if line["booking_id"] == booking_id:
                    target = line
            if target is None:
                self.action_error = "That reservation is no longer listed."
                self.busy = False
                return
            if not target["can_approve"]:
                self.action_error = ("This arrival is not eligible yet: "
                                     + target["note"])
                self.busy = False
                return
            stamp = self.now_iso()
            expiry = self.grant_expiry(target)
            auth = await self.table("authorizations")
            if auth is not None:
                await workpeg.add_row(auth["uuid"], {
                    "event_id": "AUTH-" + booking_id + "-grant",
                    "business_id": route.business_id,
                    "room_code": target["room_code"],
                    "authorization_type": "room_activation",
                    "status": "granted",
                    "source": "front_desk",
                    "issued_by": "reception",
                    "issued_at": stamp,
                    "expires_at": expiry,
                    "metadata": {
                        "booking_id": booking_id,
                        "guest_label": target["guest"],
                        "review_overridden": target["review"],
                    },
                })
            checkins = await self.table("check_ins")
            if checkins is not None:
                await workpeg.add_row(checkins["uuid"], {
                    "check_in_id": "CI-" + booking_id,
                    "booking_id": booking_id,
                    "room_code": target["room_code"],
                    "guest_label": target["guest"],
                    "arrived_at": stamp,
                    "verified_at": stamp,
                    "approved_at": stamp,
                    "activated_at": "",
                    "check_in_status": "approved",
                })
            queued = ""
            if target["device_code"]:
                queued = await self.queue(target["device_code"],
                                          target["room_code"], "POWER_ON",
                                          "AUTH-" + booking_id + "-grant",
                                          stamp)
            self.action_note = ("Check-in approved for " + target["guest"]
                                + ". The grant is live" + queued + ".")
            toast("Check-in approved")
            await self.reload()
        except Exception as e:
            self.action_error = e.message
        self.busy = False

    async def checkout(self, booking_id):
        """Revoke the grant, apply the checkout energy policy, raise cleaning."""
        self.busy = True
        self.action_error = ""
        self.action_note = ""
        try:
            target = None
            for line in self.arrivals:
                if line["booking_id"] == booking_id:
                    target = line
            if target is None or not target["can_checkout"]:
                self.action_error = "That stay is not in house right now."
                self.busy = False
                return
            stamp = self.now_iso()
            auth = await self.table("authorizations")
            if auth is not None:
                await workpeg.add_row(auth["uuid"], {
                    "event_id": "AUTH-" + booking_id + "-revoke",
                    "business_id": route.business_id,
                    "room_code": target["room_code"],
                    "authorization_type": "room_activation",
                    "status": "revoked",
                    "source": "front_desk",
                    "issued_by": "reception",
                    "issued_at": stamp,
                    "expires_at": None,
                    "metadata": {
                        "booking_id": booking_id,
                        "reason": "guest checked out",
                    },
                })
            checkins = await self.table("check_ins")
            if checkins is not None:
                await workpeg.add_row(checkins["uuid"], {
                    "check_in_id": "CI-" + booking_id + "-out",
                    "booking_id": booking_id,
                    "room_code": target["room_code"],
                    "guest_label": target["guest"],
                    "arrived_at": stamp,
                    "verified_at": "",
                    "approved_at": "",
                    "activated_at": "",
                    "check_in_status": "checked_out",
                })
            queued = ""
            if target["device_code"]:
                queued = await self.queue(
                    target["device_code"], target["room_code"],
                    "CUT_NON_ESSENTIAL",
                    "AUTH-" + booking_id + "-revoke", stamp)
            tasks = await self.table("staff_tasks")
            if tasks is not None:
                await workpeg.add_row(tasks["uuid"], {
                    "task_id": "TASK-" + booking_id + "-housekeeping",
                    "business_id": route.business_id,
                    "kind": "housekeeping",
                    "room_code": target["room_code"],
                    "detail": ("Turn the room after " + target["guest"]
                               + " checked out."),
                    "status": "open",
                    "assigned_to": "",
                    "created_at": stamp,
                })
            self.action_note = ("Checked out " + target["guest"]
                                + ". The grant is revoked and housekeeping has"
                                " the room" + queued + ".")
            toast("Guest checked out")
            await self.reload()
        except Exception as e:
            self.action_error = e.message
        self.busy = False

    async def queue(self, device_code, room_code, command, event_id, stamp):
        """Append one PENDING command; the relay moves only on a report."""
        table = await self.table("commands")
        if table is None:
            return ""
        code = "CMD-" + str(dates.to_epoch(stamp) or 0)
        await workpeg.add_row(table["uuid"], {
            "command_id": code,
            "business_id": route.business_id,
            "room_code": room_code,
            "device_code": device_code,
            "command": command,
            "status": "PENDING",
            "issued_at": stamp,
            "expires_at": "",
            "idempotency_key": code,
            "authorization_event_id": event_id,
            "failure_reason": "",
            "device_reported_state": "",
        })
        return ", and " + command + " is queued for the controller"

    def grant_expiry(self, target):
        """A grant runs to midday after the stay's end date, or 24 hours."""
        end = ""
        for line in self.arrivals:
            if line["booking_id"] == target["booking_id"]:
                end = line.get("end_at") or ""
        if end and len(end) >= 10:
            return end[0:10] + "T12:00:00+01:00"
        return self.now_iso()

    async def reload(self):
        self.loading = True
        try:
            await self.load()
        except Exception as e:
            self.error = e.message
        self.loading = False

    def retry(self):
        self.loading = True
        navigate(biz_url("/front-desk"))

    def open_quickpass(self):
        navigate(biz_url("/quickpass"))

    def open_roompower(self):
        navigate(biz_url("/roompower"))

    # ── rendering ────────────────────────────────────────────────────────

    def build(self):
        return Padding(
            Column(
                PageHeader(
                    "Front desk",
                    "Verify, approve, and check out the guests this business"
                    " has actually booked.",
                    Button("QuickPass", variant="outline-gray",
                           icon="shield-check", on_click=self.open_quickpass),
                ),
                self.body(),
                gap=24,
            ),
            all=24,
        )

    def body(self):
        if self.loading:
            return LoadingState("Reading today's desk...")
        elif self.error != "":
            return ErrorState(
                self.error,
                Button("Reload the page", variant="outline-gray",
                       icon="refresh", on_click=self.retry),
            )
        elif len(self.arrivals) == 0:
            return EmptyState(
                "inbox",
                "No reservations yet",
                "When a guest books a room it appears here for arrival.",
                Button("See the marketplace", variant="outline-gray",
                       icon="arrow-right",
                       on_click=self.open_marketplace),
            )
        else:
            return Column(
                self.stats(),
                self.messages(),
                Column(
                    *[self.arrival_card(line) for line in self.arrivals],
                    gap=12,
                    align="stretch",
                ),
                self.requests_block(),
                gap=20,
                align="stretch",
            )

    def stats(self):
        return Row(
            Container(StatCard("Arriving", str(self.arriving_count),
                               "approved check-ins pending"), variant="card",
                      padding=16),
            Container(StatCard("In house", str(self.in_house_count),
                               "live grants on rooms"), variant="card",
                      padding=16),
            Container(StatCard("Needs review", str(self.review_count),
                               "identity flags to look at"), variant="card",
                      padding=16),
            Container(StatCard("Requests", str(self.request_count),
                               "guest service requests"), variant="card",
                      padding=16),
            gap=12,
            align="stretch",
        )

    def messages(self):
        if self.action_error != "":
            return Container(
                Row(Icon("alert-triangle", size=16),
                    Text(self.action_error, variant="muted"),
                    gap=10, align="start"),
                variant="card", padding=14,
            )
        elif self.action_note != "":
            return Container(
                Row(Icon("check-circle", size=16),
                    Text(self.action_note, variant="muted"),
                    gap=10, align="start"),
                variant="card", padding=14,
            )
        else:
            return Spacer()

    def arrival_card(self, line):
        return Container(
            Column(
                Row(
                    Text(line["guest"], weight="semibold"),
                    Tag(line["state"]),
                    Spacer(),
                    Text(line["room_name"], variant="muted"),
                    align="center", gap=10,
                ),
                Text(line["dates"], variant="caption"),
                Divider(),
                Row(
                    Column(Text("Payment", variant="caption"),
                           Tag(line["payment"]), gap=2, align="start"),
                    Column(Text("Identity", variant="caption"),
                           Tag(line["verification"]), gap=2, align="start"),
                    Column(Text("Core grant", variant="caption"),
                           Tag(line["grant"]), gap=2, align="start"),
                    gap=24, align="start",
                ),
                Text(line["note"], variant="caption"),
                self.actions(line),
                gap=10, align="stretch",
            ),
            variant="card", padding=18,
        )

    def open_guest(self, booking_id):
        navigate(biz_url("/guest/" + booking_id))

    def actions(self, line):
        if line["can_approve"]:
            if line["review"]:
                return Row(
                    Button("Review & approve", variant="primary",
                           icon="shield-check",
                           on_click=lambda: self.approve(line["booking_id"])),
                    Button("Open QuickPass", variant="outline-gray",
                           icon="external-link",
                           on_click=self.open_quickpass),
                    Button("Guest hub", variant="outline-gray", icon="user",
                           on_click=lambda: self.open_guest(
                               line["booking_id"])),
                    gap=10, align="center",
                )
            else:
                return Row(
                    Button("Approve check-in", variant="primary",
                           icon="check", on_click=lambda:
                           self.approve(line["booking_id"])),
                    Button("RoomPower", variant="outline-gray", icon="cpu",
                           on_click=self.open_roompower),
                    Button("Guest hub", variant="outline-gray", icon="user",
                           on_click=lambda: self.open_guest(
                               line["booking_id"])),
                    gap=10, align="center",
                )
        elif line["can_checkout"]:
            return Row(
                Button("Check out", variant="outline-gray", icon="log-out",
                       on_click=lambda: self.checkout(line["booking_id"])),
                Button("RoomPower", variant="outline-gray", icon="cpu",
                       on_click=self.open_roompower),
                Button("Guest hub", variant="outline-gray", icon="user",
                       on_click=lambda: self.open_guest(line["booking_id"])),
                gap=10, align="center",
            )
        else:
            return Row(
                Text("No action available from this desk state.",
                     variant="caption"),
                align="center",
            )

    def requests_block(self):
        if len(self.requests) == 0:
            return Column(
                Text("Guest requests", weight="semibold"),
                Text("No guest has raised a request yet.", variant="caption"),
                gap=8, align="stretch",
            )
        return Column(
            Row(Text("Guest requests", weight="semibold"),
                Text("newest first", variant="caption"),
                align="center", gap=8),
            Table(
                TableHeader(
                    TableCell(title="Room"),
                    TableCell(title="Guest"),
                    TableCell(title="Category"),
                    TableCell(title="Detail"),
                    TableCell(title="Status"),
                    TableCell(title="Raised"),
                ),
                *[TableRow(
                    TableCell(Text(r["room"], weight="medium")),
                    TableCell(Text(r["guest"])),
                    TableCell(Tag(r["category"])),
                    TableCell(Text(r["detail"], variant="muted")),
                    TableCell(Tag(r["status"])),
                    TableCell(Text(r["at"], variant="muted")),
                ) for r in self.requests],
            ),
            gap=10, align="stretch",
        )

    def open_marketplace(self):
        navigate(biz_url("/marketplace"))
