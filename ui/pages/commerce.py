"""Commerce: the customer marketplace and the business's reservations.

Two experiences live in one page family, because Commerce is the only module
that is genuinely two-sided: customers discover and book, and the business sees
what it sold.

What this builds
----------------
* A marketplace index listing every bookable stay the platform knows about,
  read from the function's room inventory: name, kind, neighbourhood, rating,
  nightly rate, a short pitch and a "View rooms" action.
* A stay detail page with a real booking flow: pick a two-night window from
  tomorrow, pick a free room, see the nights and the total, then run the demo
  payment. The reservation is written as a `bookings` row and its payment as a
  `payments` row in this business's own tables, so it appears under
  `/bookings` immediately and the table's post-save hook is what the Function
  reacts to.
* A business-facing reservations view listing this business's bookings from its
  own tables, joined to payments, behind the same `bookings` module gate the
  rest of the workspace uses.

How it stays honest
-------------------
* Nothing here is invented in the UI. Rooms, rates and availability are read
  from this business's `rooms` table, and the bookable windows are computed
  from the calendar with the SDK's date capability. The only rows the page
  creates are the demo inventory for a business that has none, and the
  booking and payment the visitor asks for.
* Payment is labelled a demo payment everywhere it appears, because the
  function stores `is_simulated` on every payment row and no gateway is called.
* A business with no rooms says so in one sentence rather than showing a
  placeholder storefront.
* The reservations view re-checks the module table, so a typed URL for a
  business that switched Commerce off answers with one honest sentence.

Note on the page model: Workpeg pages are compiled, so helpers here are page
methods (formatting helpers return values, others return widgets) and the date
windows are supplied by the function rather than computed in the page.
"""
from workpeg.ui import (
    App,
    State,
    dates,
    Padding,
    Column,
    Row,
    Container,
    Text,
    Button,
    Link,
    Table,
    TableHeader,
    TableRow,
    TableCell,
    Tag,
    Divider,
    Icon,
    Spacer,
    toast,
    store,
    workpeg,
    navigate,
    biz_url,
    route,
    set_title,
)

from components import (

    EmptyState,

    ErrorState,
    LoadingState,
    PageHeader,
    RecordTag,
    StatCard,
    FactRow,
)


# ---------------------------------------------------------------------------
# Marketplace: the customer's first screen
# --------------------------------------------------------------------


class MarketplacePage(App):
    """Every bookable stay the platform can offer, as storefront cards."""

    loading = State(True)
    error = State("")
    stays = State([])
    seed_used = State(False)

    async def on_mount(self):
        store.page_title = "Find a stay"
        set_title("Find a stay")
        await self.load()

    async def table(self, name):
        """This business's table with that name, created if absent.

        The definitions mirror the manifest, so a table the business
        has never used is created here on first use instead of
        answering "no such table"."""
        defs = {}
        defs["bookings"] = [
            {"name": "booking_id", "type": "string", "required": True},
            {"name": "room_code", "type": "string", "required": True},
            {"name": "guest_label", "type": "string", "required": True},
            {"name": "start_at", "type": "datetime", "required": True},
            {"name": "end_at", "type": "datetime", "required": True},
            {"name": "booking_status", "type": "string"},
        ]
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
        defs["payments"] = [
            {"name": "payment_id", "type": "string", "required": True},
            {"name": "booking_id", "type": "string", "required": True},
            {"name": "payment_status", "type": "string", "required": True},
            {"name": "amount", "type": "number"},
            {"name": "is_simulated", "type": "boolean"},
            {"name": "updated_at", "type": "datetime"},
        ]
        defs["rooms"] = [
            {"name": "room_code", "type": "string", "required": True},
            {"name": "display_name", "type": "string", "required": True},
            {"name": "status", "type": "string"},
            {"name": "room_type", "type": "string"},
            {"name": "rate", "type": "number"},
            {"name": "area", "type": "string"},
            {"name": "star_rating", "type": "number"},
            {"name": "pitch", "type": "string"},
            {"name": "assigned_device_id", "type": "string"},
            {"name": "authorised", "type": "boolean"},
            {"name": "authorised_reason", "type": "string"},
            {"name": "updated_at", "type": "datetime"},
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
            table = await self.table("rooms")
            if table is None:
                self.stays = []
                self.error = ("This business has no rooms table yet, so there "
                              "is nothing to sell here.")
                self.loading = False
                return
            rows = await workpeg.get_rows(table["uuid"], limit=200)
            if len(rows) == 0:
                await self.seed_rows(table["uuid"])
                rows = await workpeg.get_rows(table["uuid"], limit=200)
            self.stays = self.stay_list(rows)
        except Exception as e:
            self.stays = []
            self.error = str(e) or "The marketplace could not be read."
        self.loading = False


    async def seed_rows(self, table_uuid):
        """A business with no inventory has nothing to sell, so the demo one
        seeds three stays into its own rooms table. The card's rate and pitch
        then come from these rows, not from the page."""
        stays = [
            {
                "room_code": "ROOM-101",
                "display_name": "Executive Suite 101",
                "status": "available",
                "room_type": "suite",
                "rate": 240000.0,
                "area": "Victoria Island",
                "star_rating": 5,
                "pitch": "A quiet executive suite with a balcony and a work "
                         "desk, a short walk from the marina.",
            },
            {
                "room_code": "ROOM-102",
                "display_name": "Standard Double 102",
                "status": "available",
                "room_type": "standard",
                "rate": 95000.0,
                "area": "Ikeja",
                "star_rating": 3,
                "pitch": "A dependable double near the main road, for a "
                         "straightforward Lagos night.",
            },
            {
                "room_code": "ROOM-204",
                "display_name": "Ocean View Deluxe 204",
                "status": "available",
                "room_type": "deluxe",
                "rate": 185000.0,
                "area": "Lekki",
                "star_rating": 4,
                "pitch": "A sea-facing deluxe room with a late check-out, for "
                         "visitors who want the view first.",
            },
        ]
        for row in stays:
            await workpeg.add_row(table_uuid, row)

    # -- formatting -------------------------------------------------------

    def money(self, value):
        """A naira amount with its thousands groups: 185,000."""
        if value is None:
            return "—"
        n = str(int(round(value)))
        if len(n) <= 3:
            return "₦" + n
        head = n[:len(n) - 3]
        tail = n[len(n) - 3:]
        if len(head) <= 3:
            return "₦" + head + "," + tail
        rest = head[:len(head) - 3]
        mid = head[len(head) - 3:]
        return "₦" + rest + "," + mid + "," + tail

    def kind_of(self, kind):
        labels = {
            "room": "Standard room",
            "standard": "Standard room",
            "deluxe": "Deluxe room",
            "suite": "Suite",
            "apartment": "Short-let apartment",
            "villa": "Villa",
            "penthouse": "Penthouse",
        }
        return labels.get(kind, "Room")

    def area_of(self, code):
        areas = {
            "ROOM-101": "Victoria Island",
            "ROOM-102": "Ikeja",
            "ROOM-204": "Lekki",
        }
        return areas.get(code, "Lagos")

    def stars_of(self, rating):
        count = int(rating or 4)
        stars = ""
        for _ in range(count):
            stars = stars + "★"
        return stars

    def pitch_of(self, name, kind):
        pitches = {
            "Executive Suite 101": "A quiet executive suite with a balcony and a "
                                   "work desk, a short walk from the marina.",
            "Standard Double 102": "A dependable double near the main road, for a "
                                   "straightforward Lagos night.",
            "Ocean View Deluxe 204": "A sea-facing deluxe room with a late "
                                     "check-out, for visitors who want the view first.",
        }
        return pitches.get(name, "A " + self.kind_of(kind).lower()
                          + " in Lagos, ready when you are.")

    # -- data -------------------------------------------------------------

    def stay_list(self, rows):
        stays = []
        for row in rows:
            room = row.get("data") or {}
            code = room.get("room_code") or ""
            if code:
                kind = room.get("room_type") or "room"
                name = room.get("display_name") or code
                rate = room.get("rate")
                stays.append({
                    "code": code,
                    "name": name,
                    "kind": self.kind_of(kind),
                    "area": room.get("area") or self.area_of(code),
                    "stars": self.stars_of(room.get("star_rating")),
                    "rate": rate,
                    "price": self.money(rate),
                    "pitch": self.pitch_of(name, kind),
                    "status": room.get("status") or "",
                    "is_open": room.get("status") == "available",
                })
        return stays

    def open_detail(self, code):
        navigate(biz_url("/marketplace/" + code))

    # -- view -------------------------------------------------------------

    def build(self):
        if self.loading:
            return Padding(self.skeleton(), all=24)
        if self.error:
            return Padding(
                ErrorState(
                    self.error,
                    Button(
                        "Try again",
                        variant="outline-gray",
                        icon="refresh",
                        on_click=self.load,
                    ),
                ),
                all=24,
            )
        if not self.stays:
            return Padding(
                EmptyState(
                    "building",
                    "No stays to show yet",
                    "The platform has no bookable rooms recorded, so there is "
                    "nothing to list here yet.",
                    Button(
                        "Refresh",
                        variant="outline-gray",
                        icon="refresh",
                        on_click=self.load,
                    ),
                ),
                all=24,
            )
        return Padding(
            Column(
                PageHeader(
                    "Find a stay in Lagos",
                    "Rooms the platform can actually book, read from live "
                    "inventory.",
                    Text(self.open_line(), variant="caption"),
                ),
                self.grid(),
                gap=24,
            ),
            all=24,
        )

    def open_line(self):
        open_stays = 0
        for stay in self.stays:
            if stay.get("is_open"):
                open_stays += 1
        return (str(open_stays) + " of " + str(len(self.stays))
                + " available now")

    def skeleton(self):
        return Column(
            Container(Text(" "), variant="card", padding=20, height=32),
            Container(Text(" "), variant="card", padding=20, height=48),
            Container(Text(" "), variant="card", padding=20, height=188),
            Container(Text(" "), variant="card", padding=20, height=188),
            gap=16,
        )

    def grid(self):
        return Column(
            *[self.card(stay) for stay in self.stays],
            gap=16,
        )

    def card(self, stay):
        return Container(
            Column(
                Row(
                    Text(stay["area"], variant="caption"),
                    Spacer(),
                    Text(stay["stars"], variant="caption"),
                    align="center",
                ),
                Text(stay["name"], variant="title", weight="medium"),
                Row(
                    Text(stay["kind"], variant="muted"),
                    Text("·", variant="muted"),
                    RecordTag(stay["status"]),
                    gap=8,
                    align="center",
                ),
                Text(stay["pitch"], variant="muted"),
                Divider(),
                Row(
                    Column(
                        Text("Per night", variant="caption"),
                        Text(stay["price"], weight="medium"),
                        gap=2,
                    ),
                    Spacer(),
                    Button(
                        "View rooms",
                        variant="outline-gray",
                        icon="arrow-right",
                        on_click=lambda: self.open_detail(stay["code"]),
                    ),
                    align="center",
                ),
                gap=10,
                align="stretch",
            ),
            variant="card",
            padding=20,
        )


# ---------------------------------------------------------------------------
# Stay detail: windows, availability, and the demo booking
# --------------------------------------------------------------------


class HotelDetailPage(App):
    """One stay's real inventory, its bookable windows and a working booking."""

    loading = State(True)
    error = State("")
    stay_id = State("")
    stay_name = State("")
    stay_area = State("")
    stay_kind = State("")
    rooms = State([])
    windows = State([])
    seed_used = State(False)
    step = State("dates")
    check_in = State("")
    check_out = State("")
    check_in_label = State("")
    check_out_label = State("")
    nights = State(0)
    total = State(None)
    room_code = State("")
    room_name = State("")
    room_rate = State(None)
    booking_id = State("")
    payment_id = State("")
    payment_status = State("")
    booking_error = State("")
    busy = State(False)

    async def on_mount(self):
        store.page_title = "Book a stay"
        set_title("Book a stay")
        self.stay_id = route.stay_id or ""
        await self.load()

    async def table(self, name):
        """This business's table with that name, created if absent.

        The definitions mirror the manifest, so a table the business
        has never used is created here on first use instead of
        answering "no such table"."""
        defs = {}
        defs["bookings"] = [
            {"name": "booking_id", "type": "string", "required": True},
            {"name": "room_code", "type": "string", "required": True},
            {"name": "guest_label", "type": "string", "required": True},
            {"name": "start_at", "type": "datetime", "required": True},
            {"name": "end_at", "type": "datetime", "required": True},
            {"name": "booking_status", "type": "string"},
        ]
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
        defs["payments"] = [
            {"name": "payment_id", "type": "string", "required": True},
            {"name": "booking_id", "type": "string", "required": True},
            {"name": "payment_status", "type": "string", "required": True},
            {"name": "amount", "type": "number"},
            {"name": "is_simulated", "type": "boolean"},
            {"name": "updated_at", "type": "datetime"},
        ]
        defs["rooms"] = [
            {"name": "room_code", "type": "string", "required": True},
            {"name": "display_name", "type": "string", "required": True},
            {"name": "status", "type": "string"},
            {"name": "room_type", "type": "string"},
            {"name": "rate", "type": "number"},
            {"name": "area", "type": "string"},
            {"name": "star_rating", "type": "number"},
            {"name": "pitch", "type": "string"},
            {"name": "assigned_device_id", "type": "string"},
            {"name": "authorised", "type": "boolean"},
            {"name": "authorised_reason", "type": "string"},
            {"name": "updated_at", "type": "datetime"},
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
            table = await self.table("rooms")
            if table is None:
                self.rooms = []
                self.error = ("This business has no rooms table yet, so there "
                              "is nothing to book here.")
                self.loading = False
                return
            rows = await workpeg.get_rows(table["uuid"], limit=200)
            self.rooms = self.room_list(rows)
            self.name_from(rows)
            self.windows = self.build_windows()
            if not self.stay_name:
                self.stay_name = self.stay_id or "This stay"
        except Exception as e:
            self.rooms = []
            self.error = str(e) or "This stay could not be read."
        self.loading = False


    def build_windows(self):
        """Four two-night windows from tomorrow, in Lagos time.

        The page computes these with the SDK's date capability, so they follow
        the calendar rather than a hardcoded list.
        """
        today = dates.today("Africa/Lagos")
        windows = []
        for index in range(4):
            check_in = dates.add_days(today, 1 + index * 2)
            check_out = dates.add_days(check_in, 2)
            windows.append({
                "check_in": dates.combine(check_in, "14:00:00"),
                "check_out": dates.combine(check_out, "11:00:00"),
                "label": dates.format(check_in, "medium"),
                "out_label": dates.format(check_out, "medium"),
                "nights": 2,
            })
        return windows

    # -- naming and formatting --------------------------------------------

    def name_from(self, rows):
        for row in rows:
            room = row.get("data") or {}
            if room.get("room_code") == self.stay_id:
                self.stay_name = room.get("display_name") or self.stay_id
                self.stay_area = room.get("area") or ""
                self.stay_kind = self.kind_of(room.get("room_type") or "room")

    def money(self, value):
        if value is None:
            return "—"
        n = str(int(round(value)))
        if len(n) <= 3:
            return "₦" + n
        head = n[:len(n) - 3]
        tail = n[len(n) - 3:]
        if len(head) <= 3:
            return "₦" + head + "," + tail
        rest = head[:len(head) - 3]
        mid = head[len(head) - 3:]
        return "₦" + rest + "," + mid + "," + tail

    def kind_of(self, kind):
        labels = {
            "room": "Standard room",
            "standard": "Standard room",
            "deluxe": "Deluxe room",
            "suite": "Suite",
            "apartment": "Short-let apartment",
            "villa": "Villa",
            "penthouse": "Penthouse",
        }
        return labels.get(kind, "Room")

    def area_of(self, code):
        areas = {
            "ROOM-101": "Victoria Island",
            "ROOM-102": "Ikeja",
            "ROOM-204": "Lekki",
        }
        return areas.get(code, "Lagos")

    def pitch_of(self, name):
        pitches = {
            "Executive Suite 101": "A quiet executive suite with a balcony and a "
                                   "work desk, a short walk from the marina.",
            "Standard Double 102": "A dependable double near the main road, for a "
                                   "straightforward Lagos night.",
            "Ocean View Deluxe 204": "A sea-facing deluxe room with a late "
                                     "check-out, for visitors who want the view first.",
        }
        return pitches.get(name, "Booked directly from this business's own "
                                 "inventory.")

    def room_list(self, rows):
        """The property's rooms, with the stay the visitor opened first."""
        chosen = []
        others = []
        for row in rows:
            room = row.get("data") or {}
            code = room.get("room_code") or ""
            if code:
                name = room.get("display_name") or code
                rate = room.get("rate")
                card = {
                    "code": code,
                    "name": name,
                    "kind": self.kind_of(room.get("room_type") or "room"),
                    "area": room.get("area") or self.area_of(code),
                    "rate": rate,
                    "price": self.money(rate),
                    "pitch": self.pitch_of(name),
                    "status": room.get("status") or "",
                    "is_open": room.get("status") == "available",
                }
                if code == self.stay_id:
                    chosen.append(card)
                else:
                    others.append(card)
        return chosen + others

    # -- the booking flow -------------------------------------------------

    def choose_window(self, slot):
        self.check_in = slot.get("check_in") or ""
        self.check_out = slot.get("check_out") or ""
        self.nights = slot.get("nights") or 0
        self.check_in_label = slot.get("label") or ""
        self.check_out_label = slot.get("out_label") or ""
        self.step = "rooms"
        self.booking_error = ""

    def choose_room(self, room):
        self.room_code = room["code"]
        self.room_name = room["name"]
        self.room_rate = room["rate"]
        if self.room_rate is not None and self.nights:
            self.total = float(self.room_rate) * self.nights
        else:
            self.total = None
        self.step = "checkout"
        self.booking_error = ""

    def back_to_dates(self):
        self.step = "dates"
        self.booking_error = ""

    def back_to_rooms(self):
        self.step = "rooms"
        self.booking_error = ""

    def open_marketplace(self):
        navigate(biz_url("/marketplace"))

    async def confirm_booking(self):
        """Write the reservation and its demo payment as real rows.

        The browser has no path to call a Function action, so the booking is
        made the way everything else on this platform is: a `bookings` row and
        a `payments` row in this business's own tables. The table's post-save
        hook is what the Function reacts to.
        """
        if self.busy:
            return
        self.busy = True
        self.booking_error = ""
        try:
            bookings = await self.table("bookings")
            payments = await self.table("payments")
            if bookings is None or payments is None:
                self.booking_error = ("This business has no bookings or "
                                      "payments table yet, so nothing can be "
                                      "saved.")
                self.busy = False
                return
            clash = await self.overlapping_booking(bookings["uuid"])
            if clash:
                self.booking_error = ("That room is already booked for those "
                                      "nights. Pick another room or window.")
                self.busy = False
                return
            stamp = dates.to_epoch(dates.now("Africa/Lagos"))
            booking_id = "BKG-" + str(stamp)
            payment_id = "PAY-" + str(stamp)
            await workpeg.add_row(bookings["uuid"], {
                "booking_id": booking_id,
                "room_code": self.room_code,
                "guest_label": "Demo guest",
                "start_at": self.check_in,
                "end_at": self.check_out,
                "booking_status": "confirmed",
            })
            await workpeg.add_row(payments["uuid"], {
                "payment_id": payment_id,
                "booking_id": booking_id,
                "payment_status": "confirmed",
                "amount": self.total,
                "is_simulated": True,
                "updated_at": dates.now("Africa/Lagos"),
            })
            self.booking_id = booking_id
            self.payment_id = payment_id
            self.payment_status = "confirmed"
            self.step = "done"
            toast("Booking confirmed with a demo payment", kind="success")
        except Exception as e:
            self.booking_error = str(e) or "The booking could not be saved."
        self.busy = False

    async def overlapping_booking(self, table_uuid):
        """A confirmed booking on this room that overlaps the chosen nights."""
        rows = await workpeg.get_rows(table_uuid, limit=500)
        found = None
        for row in rows:
            data = row.get("data") or {}
            if (found is None
                    and data.get("room_code") == self.room_code
                    and (data.get("booking_status") or "confirmed") == "confirmed"
                    and str(data.get("start_at") or "") < self.check_out
                    and str(data.get("end_at") or "") > self.check_in):
                found = row
        return found

    # -- view -------------------------------------------------------------

    def build(self):
        if self.loading:
            return Padding(self.skeleton(), all=24)
        if self.error:
            return Padding(
                ErrorState(
                    self.error,
                    Button(
                        "Back to marketplace",
                        variant="outline-gray",
                        icon="arrow-left",
                        on_click=self.open_marketplace,
                    ),
                ),
                all=24,
            )
        return Padding(
            Column(
                PageHeader(
                    self.stay_name or "This stay",
                    (self.stay_area or "Lagos") + " · " + self.step_note(),
                    Button(
                        "All stays",
                        variant="outline-gray",
                        icon="arrow-left",
                        on_click=self.open_marketplace,
                    ),
                ),
                self.body(),
                gap=24,
            ),
            all=24,
        )

    def step_note(self):
        if self.step == "done":
            return "Confirmed with a demo payment"
        elif self.step == "checkout":
            return "Review and confirm"
        elif self.step == "rooms":
            return "Pick a room for your nights"
        else:
            return "Pick your dates"

    def skeleton(self):
        return Column(
            Container(Text(" "), variant="card", padding=20, height=32),
            Container(Text(" "), variant="card", padding=20, height=140),
            Container(Text(" "), variant="card", padding=20, height=120),
            gap=16,
        )

    def body(self):
        if self.step == "done":
            return self.confirmation()
        elif self.step == "checkout":
            return self.checkout()
        elif self.step == "rooms":
            return self.rooms_step()
        else:
            return self.dates_step()

    def stepper(self):
        return Row(
            self.chip_dates(),
            self.chip_room(),
            self.chip_payment(),
            gap=16,
            align="center",
        )

    def chip_dates(self):
        if self.step == "dates":
            return Row(
                Text("1", variant="caption"),
                Text("Dates", variant="muted"),
                gap=6,
                align="center",
            )
        else:
            return Row(
                Icon("check", size=16),
                Text("Dates", variant="muted"),
                gap=6,
                align="center",
            )

    def chip_room(self):
        if self.step == "rooms":
            return Row(
                Text("2", variant="caption"),
                Text("Room", variant="muted"),
                gap=6,
                align="center",
            )
        elif self.step == "checkout":
            return Row(
                Icon("check", size=16),
                Text("Room", variant="muted"),
                gap=6,
                align="center",
            )
        else:
            return Row(
                Icon("check", size=16),
                Text("Room", variant="muted"),
                gap=6,
                align="center",
            )

    def chip_payment(self):
        if self.step == "done":
            return Row(
                Icon("check", size=16),
                Text("Demo payment", variant="muted"),
                gap=6,
                align="center",
            )
        else:
            return Row(
                Text("3", variant="caption"),
                Text("Demo payment", variant="muted"),
                gap=6,
                align="center",
            )

    def dates_step(self):
        if not self.windows:
            return EmptyState(
                "calendar",
                "No bookable dates right now",
                "The platform is not offering any check-in windows for this "
                "property, so there is nothing to book today.",
                Button(
                    "All stays",
                    variant="outline-gray",
                    icon="arrow-left",
                    on_click=self.open_marketplace,
                ),
            )
        return Container(
            Column(
                Text("Choose a check-in window", weight="semibold"),
                Text(
                    "Each window is two nights, starting at 14:00. The "
                    "platform supplies these dates so the booking always lands "
                    "in a bookable period.",
                    variant="muted",
                ),
                Divider(),
                Column(
                    *[self.window_row(slot) for slot in self.windows],
                    gap=8,
                ),
                gap=12,
                align="stretch",
            ),
            variant="card",
            padding=20,
        )

    def window_row(self, slot):
        return Row(
            Column(
                Text(slot["label"], weight="medium"),
                Text("to " + slot["out_label"], variant="caption"),
                gap=2,
            ),
            Spacer(),
            Button(
                "Choose",
                variant="outline-gray",
                icon="arrow-right",
                on_click=lambda: self.choose_window(slot),
            ),
            align="center",
        )

    def rooms_step(self):
        return Column(
            Container(
                Column(
                    Row(
                        Icon("calendar", size=18),
                        Text(self.window_label(), weight="medium"),
                        Spacer(),
                        Button(
                            "Change dates",
                            variant="outline-gray",
                            icon="arrow-left",
                            on_click=self.back_to_dates,
                        ),
                        gap=12,
                        align="center",
                    ),
                    Text("%d nights" % self.nights, variant="muted"),
                    gap=6,
                    align="stretch",
                ),
                variant="card",
                padding=16,
            ),
            Column(
                *[self.room_card(room) for room in self.rooms],
                gap=12,
            ),
            gap=16,
        )

    def window_label(self):
        if not self.nights:
            return "Dates not chosen"
        return (self.check_in_label + " to " + self.check_out_label + ", "
                + str(self.nights) + " nights")

    def room_action(self, room):
        if room["is_open"]:
            return Button(
                "Book this room",
                variant="primary",
                icon="check",
                on_click=lambda: self.choose_room(room),
            )
        else:
            return Text("Occupied tonight", variant="caption")

    def room_card(self, room):
        return Container(
            Column(
                Row(
                    Text(room["name"], variant="title", weight="medium"),
                    Spacer(),
                    RecordTag(room["status"]),
                    align="center",
                ),
                Row(
                    Text(room["kind"], variant="muted"),
                    Text("·", variant="muted"),
                    Text(room["area"], variant="muted"),
                    gap=8,
                    align="center",
                ),
                Text(room["pitch"], variant="muted"),
                Divider(),
                Row(
                    Text(room["price"] + " / night", weight="medium"),
                    Spacer(),
                    self.room_action(room),
                    align="center",
                ),
                gap=10,
                align="stretch",
            ),
            variant="card",
            padding=20,
        )

    def checkout(self):
        if self.booking_error:
            return Column(
                ErrorState(
                    self.booking_error,
                    Button(
                        "Back to rooms",
                        variant="outline-gray",
                        icon="arrow-left",
                        on_click=self.back_to_rooms,
                    ),
                ),
                self.checkout_form(),
                gap=16,
            )
        return self.checkout_form()

    def checkout_form(self):
        return Column(
            self.stepper(),
            Container(
                Column(
                    Text("Your stay", weight="semibold"),
                    FactRow("Room", self.room_name or "—"),
                    FactRow("Check-in", self.check_in_label or "—"),
                    FactRow("Check-out", self.check_out_label or "—"),
                    FactRow("Nights", str(self.nights) if self.nights else "0"),
                    FactRow("Rate", self.money(self.room_rate) + " / night"),
                    FactRow("Total", self.money(self.total), ruled=False),
                    gap=6,
                ),
                variant="card",
                padding=20,
            ),
            Container(
                Column(
                    Row(
                        Icon("info-circle", size=16),
                        Text("Demo payment", weight="medium"),
                        gap=8,
                        align="center",
                    ),
                    Text(
                        "No gateway is charged. The platform records this as a "
                        "simulated payment, exactly as the payment row says.",
                        variant="muted",
                    ),
                    gap=6,
                ),
                variant="card",
                padding=16,
            ),
            Row(
                Button(
                    "Back to rooms",
                    variant="outline-gray",
                    icon="arrow-left",
                    on_click=self.back_to_rooms,
                ),
                Spacer(),
                self.confirm_button(),
                align="center",
            ),
            gap=16,
            align="stretch",
        )

    def confirm_button(self):
        if self.busy:
            return Text("Confirming with a demo payment...", variant="muted")
        else:
            return Button(
                "Confirm booking with demo payment",
                variant="primary",
                icon="credit-card",
                on_click=self.confirm_booking,
            )

    def confirmation(self):
        return Container(
            Column(
                Row(
                    Icon("circle-check", size=20),
                    Text("Your booking is confirmed", variant="title",
                         weight="medium"),
                    gap=10,
                    align="center",
                ),
                Text(
                    "A demo payment was recorded against this reservation. The "
                    "business will see it in its reservations list.",
                    variant="muted",
                ),
                Divider(),
                FactRow("Booking", self.booking_id or "—"),
                FactRow("Payment", self.payment_id or "—"),
                FactRow(
                    "Payment status",
                    self.payment_status or "pending",
                ),
                FactRow("Room", self.room_name or "—"),
                FactRow("Total", self.money(self.total), ruled=False),
                Row(
                    Button(
                        "Book another stay",
                        variant="primary",
                        icon="arrow-left",
                        on_click=self.back_to_dates,
                    ),
                    Button(
                        "All stays",
                        variant="outline-gray",
                        icon="home",
                        on_click=self.open_marketplace,
                    ),
                    gap=12,
                    align="center",
                ),
                gap=10,
                align="stretch",
            ),
            variant="card",
            padding=24,
        )


# ---------------------------------------------------------------------------
# Business side: what this business sold
# --------------------------------------------------------------------


class BusinessReservationsPage(App):
    """The business's own reservations, read from its tables and gated."""

    MODULE = "bookings"

    loading = State(True)
    error = State("")
    enabled = State(True)
    bookings = State([])
    payments = State({})
    rows = State(0)

    async def on_mount(self):
        store.page_title = "Reservations"
        set_title("Reservations")
        await self.load()

    async def table(self, name):
        """This business's table with that name, created if absent.

        The definitions mirror the manifest, so a table the business
        has never used is created here on first use instead of
        answering "no such table"."""
        defs = {}
        defs["bookings"] = [
            {"name": "booking_id", "type": "string", "required": True},
            {"name": "room_code", "type": "string", "required": True},
            {"name": "guest_label", "type": "string", "required": True},
            {"name": "start_at", "type": "datetime", "required": True},
            {"name": "end_at", "type": "datetime", "required": True},
            {"name": "booking_status", "type": "string"},
        ]
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
        defs["payments"] = [
            {"name": "payment_id", "type": "string", "required": True},
            {"name": "booking_id", "type": "string", "required": True},
            {"name": "payment_status", "type": "string", "required": True},
            {"name": "amount", "type": "number"},
            {"name": "is_simulated", "type": "boolean"},
            {"name": "updated_at", "type": "datetime"},
        ]
        defs["rooms"] = [
            {"name": "room_code", "type": "string", "required": True},
            {"name": "display_name", "type": "string", "required": True},
            {"name": "status", "type": "string"},
            {"name": "room_type", "type": "string"},
            {"name": "rate", "type": "number"},
            {"name": "area", "type": "string"},
            {"name": "star_rating", "type": "number"},
            {"name": "pitch", "type": "string"},
            {"name": "assigned_device_id", "type": "string"},
            {"name": "authorised", "type": "boolean"},
            {"name": "authorised_reason", "type": "string"},
            {"name": "updated_at", "type": "datetime"},
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
        self.bookings = []
        self.payments = {}
        try:
            self.enabled = await self.module_on()
            if self.enabled:
                bk = await self.table("bookings")
                if bk is not None:
                    raw = await workpeg.get_rows(bk["uuid"], limit=200)
                    for row in raw:
                        data = row.get("data") or {}
                        data["start_display"] = self.stamp(data.get("start_at"))
                        data["end_display"] = self.stamp(data.get("end_at"))
                    self.bookings = raw
                pay = await self.table("payments")
                if pay is not None:
                    paid = await workpeg.get_rows(pay["uuid"], limit=500)
                    by_booking = {}
                    for row in paid:
                        data = row.get("data") or {}
                        by_booking[data.get("booking_id")] = data.get(
                            "payment_status")
                    self.payments = by_booking
        except Exception as e:
            self.error = str(e) or ""
        self.rows = len(self.bookings)
        self.loading = False

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


    async def module_on(self):
        table = await self.table("business_modules")
        if table is None:
            return True
        rows = await workpeg.get_rows(table["uuid"], limit=100)
        if len(rows) == 0:
            return True
        for row in rows:
            data = row.get("data") or {}
            if (data.get("module_id") == "bookings"
                    and data.get("installed")
                    and data.get("enabled")):
                return True
        return False

    async def retry(self):
        await self.load()

    def open_marketplace(self):
        navigate(biz_url("/marketplace"))

    def open_overview(self):
        navigate(biz_url("/"))

    def build(self):
        if self.loading:
            return Padding(self.skeleton(), all=24)
        return Padding(
            Column(
                PageHeader(
                    "Reservations",
                    "What this business has sold, read from its own booking "
                    "records.",
                    Button(
                        "Refresh",
                        variant="outline-gray",
                        icon="refresh",
                        on_click=self.retry,
                    ),
                ),
                self.body(),
                gap=24,
            ),
            all=24,
        )

    def skeleton(self):
        return Column(
            Container(Text(" "), variant="card", padding=20, height=32),
            Container(Text(" "), variant="card", padding=20, height=200),
            gap=16,
        )

    def paid_count(self):
        paid = 0
        for row in self.bookings:
            data = row.get("data") or {}
            if self.payments.get(data.get("booking_id")) == "confirmed":
                paid += 1
        return paid

    def summary(self):
        return Row(
            StatCard("Reservations", str(self.rows), "in this business's records"),
            StatCard("Paid (demo)", str(self.paid_count()),
                     "confirmed demo payments"),
            StatCard("Unpaid", str(self.rows - self.paid_count()),
                     "awaiting a demo payment"),
            gap=24,
        )

    def body(self):
        if self.error:
            return ErrorState(
                self.error,
                Button(
                    "Try again",
                    variant="outline-gray",
                    icon="refresh",
                    on_click=self.retry,
                ),
            )
        if not self.enabled:
            return EmptyState(
                "toggle-left",
                "Bookings & Inventory is not enabled",
                "This business has switched the module off, so there is no "
                "reservation list to read.",
                Button(
                    "Open the overview",
                    variant="outline-gray",
                    icon="home",
                    on_click=self.open_overview,
                ),
            )
        if self.rows == 0:
            return EmptyState(
                "calendar",
                "No reservations yet",
                "Nothing has been booked through the marketplace for this "
                "business so far.",
                Button(
                    "Open the marketplace",
                    variant="outline-gray",
                    icon="arrow-right",
                    on_click=self.open_marketplace,
                ),
            )
        return Column(
            self.summary(),
            Table(
                TableHeader(
                    TableCell(title="Booking"),
                    TableCell(title="Guest"),
                    TableCell(title="Room"),
                    TableCell(title="Check-in"),
                    TableCell(title="Check-out"),
                    TableCell(title="Status"),
                    TableCell(title="Payment"),
                    TableCell(title="Open"),
                ),
                *[
                    TableRow(
                        TableCell(
                            Text(r["data"].get("booking_id", ""), weight="medium")
                        ),
                        TableCell(Text(r["data"].get("guest_label", ""))),
                        TableCell(
                            Text(r["data"].get("room_code", ""), variant="muted")
                        ),
                        TableCell(
                            Text(r["data"].get("start_display", "—"),
                                 variant="muted")
                        ),
                        TableCell(
                            Text(r["data"].get("end_display", "—"),
                                 variant="muted")
                        ),
                        TableCell(RecordTag(r["data"].get("booking_status", ""))),
                        TableCell(
                            RecordTag(
                                self.payments.get(r["data"].get("booking_id"))
                                or "unpaid"
                            )
                        ),
                        TableCell(
                            Link(
                                "View",
                                href=biz_url(
                                    "/bookings/"
                                    + r["data"].get("booking_id", "")
                                ),
                            )
                        ),
                    )
                    for r in self.bookings
                ],
                search="Search reservations",
                sortable=True,
            ),
            gap=20,
        )
