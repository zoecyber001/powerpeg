"""The original single-room front-desk demo.

Kept as-is: it runs on in-page state, not on the platform's tables, so it is a
demonstration of the RoomPower idea, not a record of a real room. The real
front-desk flow lives in the function's booking flow.
"""
from workpeg.ui import (
    Scaffold, State, Column, Row, Container, Text, Button, Badge, Divider,
)


class FrontDeskPage(Scaffold):
    is_authorised = State(False)
    guest_name = State("Alice Johnson")
    payment_status = State("Pending Payment")
    room_status = State("Power Off")

    def on_check_in(self):
        self.guest_name = "Alice Johnson"
        self.payment_status = "Pending Payment"
        self.is_authorised = False
        self.room_status = "Power Off"

    def on_confirm_payment(self):
        self.payment_status = "Paid"
        self.is_authorised = True
        self.room_status = "Power Active (230V)"

    def on_check_out(self):
        self.guest_name = "Vacant"
        self.payment_status = "No Charge"
        self.is_authorised = False
        self.room_status = "Power Off"

    def build(self):
        return Column(
            Container(
                Row(
                    Text("PegPower Front Desk (demo)",
                         style={"fontSize": "20px", "fontWeight": "bold"}),
                    Badge(label="Demo data"),
                ),
                style={"marginBottom": "20px"},
            ),
            Container(
                Column(
                    Row(
                        Text("Room 204 • Ocean Suite",
                             style={"fontSize": "16px", "fontWeight": "bold"}),
                        Badge(label="Power Active") if self.is_authorised
                        else Badge(label="Power Off"),
                    ),
                    Divider(),
                    Row(
                        Column(
                            Text("Guest:",
                                 style={"color": "#6c757d", "fontSize": "12px"}),
                            Text(self.guest_name,
                                 style={"fontWeight": "bold",
                                        "fontSize": "15px"}),
                        ),
                        Column(
                            Text("Payment Status:",
                                 style={"color": "#6c757d", "fontSize": "12px"}),
                            Text(self.payment_status,
                                 style={"fontWeight": "bold",
                                        "fontSize": "15px"}),
                        ),
                    ),
                    Divider(),
                    Row(
                        Button("Verify Payment & Enable Power",
                               on_click=self.on_confirm_payment),
                        Button("Check Out & Cut Power",
                               on_click=self.on_check_out),
                        Button("Check In New Guest",
                               on_click=self.on_check_in),
                    ),
                ),
                style={"padding": "20px", "backgroundColor": "#ffffff",
                       "borderRadius": "12px", "border": "1px solid #dee2e6",
                       "marginBottom": "20px"},
            ),
            Row(
                Container(
                    Column(
                        Text("Room 101 • Executive Suite",
                             style={"fontWeight": "bold"}),
                        Text("Guest: Marcus Vance (Paid)"),
                        Text("Power: Active (230V)",
                             style={"color": "#198754"}),
                    ),
                    style={"padding": "15px", "backgroundColor": "#f8f9fa",
                           "borderRadius": "10px",
                           "border": "1px solid #dee2e6", "flex": "1"},
                ),
                Container(
                    Column(
                        Text("Room 102 • Standard Room",
                             style={"fontWeight": "bold"}),
                        Text("Guest: Vacant"),
                        Text("Power: Cut (0V)",
                             style={"color": "#6c757d"}),
                    ),
                    style={"padding": "15px", "backgroundColor": "#f8f9fa",
                           "borderRadius": "10px",
                           "border": "1px solid #dee2e6", "flex": "1"},
                ),
            ),
        )
