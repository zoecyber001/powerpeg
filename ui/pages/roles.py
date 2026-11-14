"""Roles: who holds which role, and what each role may do.

Access control here is explicit and ordinary: this business's `staff_members`
rows name a role per person, and the role catalog says what each role may do.
The signed-in user's own row — matched on the session's email, then name —
is the banner at the top, so the page never leaves you guessing whose
permissions you are looking through.

A person not on the staff list has no staff role. The page says so and offers
the one honest way onto the list at a desk: a clearly-labelled demo row, with
the demo label travelling with it. Managing the list itself needs the owner
or manager role.
"""
from workpeg.ui import (
    App, State, Padding, Column, Row, Text, Button, Table, TableHeader,
    TableCell, TableRow, Tag, TextInput, Input, Container, Divider, Icon,
    Spacer, set_title, store, workpeg, user, toast, dates,
)

from components import EmptyState, ErrorState, LoadingState, PageHeader


class RolesPage(App):
    loading = State(True)
    error = State("")
    busy = State(False)
    action_error = State("")
    action_note = State("")
    my_role = State("")
    my_name = State("")
    on_staff = State(False)
    staff = State([])
    roles = State([])
    new_name = State("")
    new_email = State("")

    async def on_mount(self):
        store.page_title = "Roles"
        set_title("Roles")
        await self.load()

    async def load(self):
        self.loading = True
        self.error = ""
        try:
            self.roles = self.catalog()
            table = await self.table("staff_members")
            rows = []
            if table is not None:
                rows = await workpeg.get_rows(table["uuid"], limit=200)
            lines = []
            email = str(user.email or "").lower()
            name = str(user.name or "")
            role = ""
            for row in rows[::-1]:
                data = row.get("data") or {}
                line = {
                    "staff_member_id": data.get("staff_member_id") or "",
                    "name": data.get("name") or "—",
                    "email": data.get("email") or "—",
                    "role": data.get("role") or "",
                    "status": data.get("status") or "active",
                    "demo": str(data.get("staff_member_id") or "")[0:10]
                    == "STAFF-DEMO",
                }
                lines.append(line)
                row_email = str(data.get("email") or "").lower()
                row_name = str(data.get("name") or "")
                if role == "":
                    if email and row_email and email == row_email:
                        role = line["role"]
                    elif name and row_name and name == row_name:
                        role = line["role"]
            self.staff = lines
            self.my_name = name
            self.my_role = role
            self.on_staff = role != ""
        except Exception as e:
            self.error = e.message
        self.loading = False

    def catalog(self):
        """The role catalog, as the function's matrix spells it.

        Inlined here because the browser cannot call the function: this
        page's catalog and the function's must agree, and the tests check
        the function's side.
        """
        return [
            {"role": "owner", "label": "Owner",
             "description": "The business's principal: everything, including"
             " who else holds which role.",
             "permissions": ["bookings.write", "payments.record",
                             "identity.record", "checkin.approve",
                             "checkout.run", "devices.command",
                             "settings.manage", "staff.manage"]},
            {"role": "manager", "label": "Manager",
             "description": "Runs the operation day to day; does not manage"
             " the staff list itself.",
             "permissions": ["bookings.write", "payments.record",
                             "identity.record", "checkin.approve",
                             "checkout.run", "devices.command",
                             "settings.manage"]},
            {"role": "front_desk", "label": "Front desk",
             "description": "The arrival desk: payments, identity checks,"
             " approving check-ins and running checkouts.",
             "permissions": ["bookings.write", "payments.record",
                             "identity.record", "checkin.approve",
                             "checkout.run"]},
            {"role": "housekeeping", "label": "Housekeeping",
             "description": "Rooms and tasks: the stay's closing tasks and"
             " the room's readiness.",
             "permissions": ["tasks.manage"]},
            {"role": "maintenance", "label": "Maintenance",
             "description": "The room's hardware: device commands and room"
             " activation when the desk asks.",
             "permissions": ["devices.command"]},
        ]

    async def table(self, name):
        """This business's table with that name, created if absent.

        Found by the table's own namespace label (get_tables filters
        on it); a table the business has never used is created here
        on first use, in the shape the Tables API expects: display
        name, namespace label, permission, and columns with ids,
        types and positions. Column ids are the manifest's column
        names, so every row write and read keeps its keys."""
        defs = {}
        defs["staff_members"] = [
            {"id": "staff_member_id", "name": "staff_member_id", "type": "text", "position": 1000, "required": True},
            {"id": "name", "name": "name", "type": "text", "position": 2000, "required": True},
            {"id": "email", "name": "email", "type": "text", "position": 3000},
            {"id": "role", "name": "role", "type": "text", "position": 4000},
            {"id": "status", "name": "status", "type": "text", "position": 5000},
            {"id": "created_at", "name": "created_at", "type": "datetime", "position": 6000},
            {"id": "updated_at", "name": "updated_at", "type": "datetime", "position": 7000},
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

    def now_iso(self):
        return str(dates.now("Africa/Lagos", True) or "") + "+01:00"

    def set_new_name(self, value):
        self.new_name = value

    def set_new_email(self, value):
        self.new_email = value

    async def add_me_demo(self):
        """Put the signed-in user on the list as owner, labelled demo.

        A person not on the staff list is locked out of everything, and the
        desk needs an owner to break the deadlock — so the seed writes one
        clearly-labelled demo row for the signed-in user rather than
        pretending they were already the owner.
        """
        self.busy = True
        self.action_error = ""
        self.action_note = ""
        name = str(user.name or "")
        email = str(user.email or "")
        if not name:
            self.action_error = ("The signed-in user's name is not on the"
                                 " session, so there is nobody to add.")
            self.busy = False
            return
        try:
            table = await self.table("staff_members")
            if table is None:
                self.action_error = "The staff table could not be provisioned."
                self.busy = False
                return
            await workpeg.add_row(table["uuid"], {
                "data": {
                    "staff_member_id": "STAFF-DEMO-me",
                    "name": name,
                    "email": email,
                    "role": "owner",
                    "status": "active",
                    "created_at": self.now_iso(),
                    "updated_at": self.now_iso(),
                },
                "position": dates.to_epoch(self.now_iso()),
            })
            self.action_note = (name + " is on the staff list as Owner, by"
                                " a demo row — the row is labelled demo in"
                                " the register.")
            toast("Demo owner row added")
            await self.load()
        except Exception as e:
            self.action_error = e.message
        self.busy = False

    async def add_member(self, role):
        self.busy = True
        self.action_error = ""
        self.action_note = ""
        if self.my_role not in ["owner", "manager"]:
            self.action_error = ("Managing the staff list needs the owner"
                                 " or manager role; your role is"
                                 " '" + (self.my_role or "none") + "'.")
            self.busy = False
            return
        name = str(self.new_name or "").strip()
        email = str(self.new_email or "").strip()
        if not name:
            self.action_error = "Add the person's name first."
            self.busy = False
            return
        try:
            table = await self.table("staff_members")
            if table is None:
                self.action_error = "The staff table could not be provisioned."
                self.busy = False
                return
            marker = ("STAFF-" + name.lower().strip())[0:40]
            await workpeg.add_row(table["uuid"], {
                "data": {
                    "staff_member_id": marker,
                    "name": name,
                    "email": email,
                    "role": role,
                    "status": "active",
                    "created_at": self.now_iso(),
                    "updated_at": self.now_iso(),
                },
                "position": dates.to_epoch(self.now_iso()),
            })
            self.action_note = (name + " is on the staff list as " + role
                                + ".")
            toast("Staff member added")
            self.new_name = ""
            self.new_email = ""
            await self.load()
        except Exception as e:
            self.action_error = e.message
        self.busy = False

    async def retry(self):
        self.loading = True
        await self.load()

    # ── rendering ────────────────────────────────────────────────────────

    def build(self):
        return Padding(
            Column(
                PageHeader(
                    "Roles",
                    "Who holds which role, and what each role may do.",
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
            return LoadingState("Reading the staff list...")
        elif self.error != "":
            return ErrorState(
                self.error,
                Button("Try again", variant="outline-gray", icon="refresh",
                       on_click=self.retry),
            )
        else:
            return Column(
                self.viewer_banner(),
                self.action_banner(),
                self.roles_catalog(),
                self.staff_section(),
                gap=20, align="stretch",
            )

    def viewer_banner(self):
        if self.on_staff:
            return Container(
                Row(
                    Icon("shield-check", size=18),
                    Column(
                        Row(Text("You are signed in as " + self.my_name,
                                 weight="medium"),
                            Tag(self.my_role, tone="success", dot=True),
                            gap=8, align="center"),
                        Text("Your permissions are the ones this role holds"
                             " below; the desk's actions check the same"
                             " list.", variant="muted"),
                        gap=4, align="start",
                    ),
                    gap=12, align="start",
                ),
                variant="card", padding=18,
            )
        return Container(
            Row(
                Icon("shield", size=18),
                Column(
                    Text("You are not on the staff list", weight="medium"),
                    Text("The signed-in user is " + (self.my_name or "known"
                         " to the platform") + ", but no staff row matches,"
                         " so you hold no role and the desk's gated actions"
                         " are closed to you.", variant="muted"),
                    gap=4, align="start",
                ),
                gap=12, align="start",
            ),
            variant="card", padding=18,
        )

    def action_banner(self):
        if self.action_error != "":
            return Container(
                Row(Icon("alert-triangle", size=16),
                    Text(self.action_error, variant="muted"),
                    gap=10, align="start"),
                variant="card", padding=14,
            )
        elif self.action_note != "":
            return Container(
                Row(Icon("circle-check", size=16),
                    Text(self.action_note, variant="muted"),
                    gap=10, align="start"),
                variant="card", padding=14,
            )
        else:
            return Spacer()

    def roles_catalog(self):
        return Column(
            Text("The five roles", weight="semibold"),
            Column(
                *[
                    Container(
                        Column(
                            Row(Text(entry["label"], weight="semibold"),
                                gap=8, align="center"),
                            Text(entry["description"], variant="muted"),
                            Row(
                                *[
                                    Tag(permission, tone="info", size="sm")
                                    for permission in entry["permissions"]
                                ],
                                gap=6, align="start",
                            ),
                            gap=8, align="start",
                        ),
                        variant="card", padding=18,
                    )
                    for entry in self.roles
                ],
                gap=12, align="stretch",
            ),
            gap=10, align="stretch",
        )

    def staff_section(self):
        if len(self.staff) == 0:
            return Column(
                Container(
                    Column(
                        Row(Icon("shield-lock", size=18, weight="thin"),
                            Text("No staff on the list yet", weight="medium"),
                            gap=8, align="center"),
                        Text("This business has no staff rows, so nobody"
                             " holds a role and the desk's gated actions"
                             " are closed.", variant="muted"),
                        self.seed_actions(),
                        gap=10, align="start",
                    ),
                    variant="card", padding=24,
                ),
                gap=12, align="stretch",
            )
        return Column(
            Row(Text("Staff list", weight="semibold"),
                Text(str(len(self.staff)) + " on the list",
                     variant="caption"),
                gap=8, align="center"),
            Table(
                TableHeader(
                    TableCell(title="Name"),
                    TableCell(title="Email"),
                    TableCell(title="Role"),
                    TableCell(title="Status"),
                ),
                *[TableRow(
                    TableCell(Text(s["name"], weight="medium")),
                    TableCell(Text(s["email"], variant="muted")),
                    TableCell(self.role_cell(s)),
                    TableCell(Tag(s["status"], dot=True)),
                ) for s in self.staff],
                search="Search staff",
            ),
            self.manage_form(),
            gap=10, align="stretch",
        )

    def can_manage(self):
        return self.my_role in ["owner", "manager"]

    def seed_actions(self):
        """The way onto an empty staff list: add someone properly (owner or
        manager only), or the labelled demo row for the signed-in user."""
        if self.can_manage():
            return Column(
                Row(Input(TextInput(value=self.new_name,
                          on_change=self.set_new_name,
                          placeholder="Full name"),
                label="Full name"),
                    Input(TextInput(value=self.new_email,
                          on_change=self.set_new_email,
                          placeholder="Work email"),
                label="Work email"),
                    Button("Add as Owner", variant="primary",
                           on_click=lambda: self.add_member("owner")),
                    gap=10, align="center"),
                self.demo_seed_row(),
                gap=10, align="center",
            )
        return self.demo_seed_row()

    def role_cell(self, s):
        if s["demo"]:
            return Row(Tag(s["role"] or "none", tone="warning", dot=True),
                       Tag("demo", size="sm"), gap=6, align="center")
        return Tag(s["role"] or "none")

    def demo_seed_row(self):
        if self.on_staff:
            return Spacer()
        return Row(
            Button("Add me as Owner (demo)", variant="outline-gray",
                   icon="shield-check", on_click=self.add_me_demo),
            Text("writes a staff row labelled demo for the signed-in user;"
                 " a real owner adds everyone else", variant="caption"),
            gap=10, align="center",
        )

    def manage_form(self):
        if not self.can_manage():
            return Text("Managing the staff list needs the owner or manager"
                        " role.", variant="caption")
        return Container(
            Column(
                Text("Add a staff member", weight="semibold"),
                Row(Input(TextInput(value=self.new_name,
                          on_change=self.set_new_name,
                          placeholder="Full name"),
                label="Full name"),
                    Input(TextInput(value=self.new_email,
                          on_change=self.set_new_email,
                          placeholder="Work email"),
                label="Work email"),
                    Button("Add as Owner", variant="outline-color", size="sm",
                           on_click=lambda: self.add_member("owner")),
                    Button("Add as Manager", variant="outline-color",
                           size="sm",
                           on_click=lambda: self.add_member("manager")),
                    gap=10, align="center"),
                Row(Button("Add as Front desk", variant="outline-gray",
                           size="sm",
                           on_click=lambda: self.add_member("front_desk")),
                    Button("Add as Housekeeping", variant="outline-gray",
                           size="sm",
                           on_click=lambda: self.add_member("housekeeping")),
                    Button("Add as Maintenance", variant="outline-gray",
                           size="sm",
                           on_click=lambda: self.add_member("maintenance")),
                    gap=10, align="center"),
                Text("The role decides what the person may do; the desk's"
                     " gated actions check this list.", variant="caption"),
                gap=10, align="start",
            ),
            variant="card", padding=18,
        )
