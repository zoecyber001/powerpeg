from workpeg.ui import (
    Route, Router, Scaffold, State,
    Column, Row, Container, Text, Button, Badge, Divider
)

class PegPowerHome(Scaffold):
    is_authorised = State(False)
    relay_state = State("OFF")
    power_kw = State("0.00")
    guest_name = State("Hackathon Guest")
    payment_status = State("Pending")
    alert_count = State(0)
    last_event = State("System ready on Workpeg platform.")

    def on_confirm_payment(self):
        self.payment_status = "Confirmed"
        self.is_authorised = True
        self.relay_state = "ON"
        self.power_kw = "0.98"
        self.last_event = "Payment confirmed: Dispatched POWER_ON to AZ3166"

    def on_revoke_access(self):
        self.payment_status = "Pending"
        self.is_authorised = False
        self.relay_state = "OFF"
        self.power_kw = "0.00"
        self.last_event = "Access revoked: Dispatched POWER_OFF to AZ3166"

    def on_inject_rogue(self):
        self.power_kw = "1.42"
        self.alert_count = 1
        self.last_event = "ALERT: ENERGY_WHILE_UNAUTHORISED (1.42 kW detected without valid stay)"

    def on_clear_alert(self):
        self.alert_count = 0
        self.last_event = "Operator acknowledged anomaly alert."

    def build(self):
        return Column(
            Container(
                Row(
                    Text("⚡ PegPower", style={"fontSize": "22px", "fontWeight": "bold"}),
                    Badge(label="Workpeg Native Peg"),
                    Badge(label="Physical: 1x AZ3166")
                ),
                style={"marginBottom": "20px"}
            ),
            Container(
                Column(
                    Row(
                        Text("ROOM-204 (Ocean View Deluxe)", style={"fontSize": "18px", "fontWeight": "bold"}),
                        Badge(label="AUTHORISED") if self.is_authorised else Badge(label="ACCESS DENIED")
                    ),
                    Divider(),
                    Row(
                        Column(
                            Text("Edge Hardware Controller", style={"fontWeight": "bold", "fontSize": "13px"}),
                            Text("Device ID: AZ3166-01 (Wi-Fi Online)"),
                            Row(
                                Text("Firmware Relay State:"),
                                Badge(label="ON") if self.relay_state == "ON" else Badge(label="OFF")
                            )
                        ),
                        Column(
                            Text("Stay & Payment (Workpeg Tables)", style={"fontWeight": "bold", "fontSize": "13px"}),
                            Text("Guest: Hackathon Guest"),
                            Text("Payment: Simulated")
                        )
                    ),
                    Row(
                        Button("Confirm Payment (Trigger POWER_ON)", on_click=self.on_confirm_payment),
                        Button("Revoke Stay / Checkout (Trigger POWER_OFF)", on_click=self.on_revoke_access)
                    ),
                    Container(
                        Column(
                            Row(
                                Text("Live Electrical Telemetry", style={"fontWeight": "bold"}),
                                Badge(label="SIMULATED SOFTWARE ENGINE")
                            ),
                            Row(
                                Text("Active Load: 0.98 kW" if self.is_authorised else "Active Load: 0.00 kW", style={"fontFamily": "monospace", "fontSize": "16px"}),
                                Text("Voltage: 230.1 V", style={"fontFamily": "monospace"}),
                                Text("Frequency: 50.0 Hz", style={"fontFamily": "monospace"})
                            )
                        ),
                        style={"backgroundColor": "#ffffff", "padding": "12px", "borderRadius": "8px", "border": "1px solid #e9ecef"}
                    ),
                    Row(
                        Text("Pitch Anomaly Controls:", style={"fontWeight": "bold"}),
                        Button("Simulate Rogue Power Draw", on_click=self.on_inject_rogue),
                        Button("Acknowledge Alert", on_click=self.on_clear_alert)
                    )
                ),
                style={"padding": "20px", "backgroundColor": "#fdfdfd", "borderRadius": "12px", "border": "1px solid #dee2e6", "marginBottom": "20px"}
            ),
            Row(
                Container(
                    Column(
                        Text("ROOM-101 (Executive Suite)", style={"fontWeight": "bold"}),
                        Text("Status: AUTHORISED | 0.95 kW"),
                        Text("Controller: VDEV-101 [ON]")
                    ),
                    style={"padding": "14px", "backgroundColor": "#f8f9fa", "borderRadius": "8px", "border": "1px solid #dee2e6"}
                ),
                Container(
                    Column(
                        Text("ROOM-102 (Standard Double)", style={"fontWeight": "bold"}),
                        Text("Status: UNAUTHORISED | 0.00 kW"),
                        Text("Controller: None [OFF]")
                    ),
                    style={"padding": "14px", "backgroundColor": "#f8f9fa", "borderRadius": "8px", "border": "1px solid #dee2e6"}
                )
            ),
            Container(
                Column(
                    Text("Audit Trail & Log", style={"fontWeight": "bold", "fontSize": "13px"}),
                    Text("System ready on Workpeg platform.", style={"fontFamily": "monospace", "fontSize": "12px", "color": "#495057"})
                ),
                style={"padding": "12px", "backgroundColor": "#e9ecef", "borderRadius": "8px"}
            )
        )

class Main(Router):
    routes = [Route("/", PegPowerHome)]
