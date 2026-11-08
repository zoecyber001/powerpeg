# PegPower

> **Smart electricity access control and monitoring platform linking room booking and payment authorisation to physical power supply, correlating device state and simulated electrical telemetry with an immutable audit trail.**

Built for the **PegPower Hackathon Prototype Specification (v1.0)**.

---

## ⚡ Executive Architecture & Prototype Boundaries

PegPower continuously reconciles three independent state vectors:
1. **Authorisation State:** Evaluated by the core engine based on room booking, simulated payment status, and the stay access window.
2. **Device State:** Reported by the **MXChip AZ3166 IoT DevKit** (the sole physical controller in scope) over Wi-Fi, reporting connection heartbeats and firmware-level simulated relay status (`ON` / `OFF`).
3. **Telemetry State:** Generated independently by the software electrical simulation service (voltage, current, active power, and accumulated kWh).

```
                          ┌────────────────────────────────────────┐
                          │         React + Vite Dashboard         │
                          │   (Tailwind, Lucide, Recharts, WS)     │
                          └───────────────────▲────────────────────┘
                                              │ REST + WebSocket
                                              ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 FastAPI Core Engine                                    │
│                                                                                        │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────────────┐  │
│  │ Authorisation Engine │  │ Command Dispatcher   │  │ Conflict & Anomaly Detector  │  │
│  │ (Rules & Lifecycle)  │  │ (Queue & ACK Tracker)│  │ (Vector Cross-Reconciliation)│  │
│  └──────────┬───────────┘  └──────────┬───────────┘  └──────────────▲───────────────┘  │
│             │                         │                             │                  │
│  ┌──────────▼─────────────────────────▼─────────────────────────────┴───────────────┐  │
│  │                    Database Layer (SQLite Async / PostgreSQL)                    │  │
│  │       Rooms | Bookings | Devices | Commands | Telemetry | Alerts | Audit Log     │  │
│  └────────────────────────────────────▲─────────────────────────────▲───────────────┘  │
└───────────────────────────────────────┼─────────────────────────────┼──────────────────┘
                                        │                             │
                     HTTP REST (Poll/Heartbeat/ACK)            Internal Telemetry Ingest
                                        │                             │
             ┌──────────────────────────┴────────┐         ┌──────────┴──────────────────┐
             │       MXChip AZ3166 DevKit        │         │ Virtual Electrical Engine   │
             │   - Wi-Fi Station (HTTP Client)   │         │ - Configurable Loads        │
             │   - OLED Status Display           │         │ - Telemetry (V, I, P, kWh)  │
             │   - RGB LED Indicator             │         │ - Injection: Bypass/Anomaly │
             │   - Firmware Simulated Relay      │         │ - Multi-Room Simulation     │
             └───────────────────────────────────┘         └─────────────────────────────┘
```

> **Hardware Truth & Safety Rule (PRD Section 8.4):** The AZ3166 maintains an internal firmware-level relay state and does **not** switch live mains electricity or measure room current. All electrical telemetry is produced by the independent simulation service and is explicitly labelled as `[SIMULATED]` across the API and UI.

---

## 📁 Repository Structure

```
powerpeg/
├── backend/
│   ├── app/
│   │   ├── api/                   # REST & WebSocket Endpoints (Rooms, Bookings, Devices, Telemetry, Alerts, Audit)
│   │   ├── models/                # SQLAlchemy 2.0 Async Entity Definitions
│   │   ├── schemas/               # Pydantic v2 Contract Validation
│   │   ├── services/
│   │   │   ├── auth_engine.py     # Authorisation Logic & State Transitions
│   │   │   ├── device_service.py  # Device Registration, Heartbeat, Command Queue & ACK
│   │   │   ├── simulator_service.py # Independent Virtual Telemetry Generator
│   │   │   ├── anomaly_service.py # Vector Cross-Reconciliation & Alert Generator
│   │   │   └── websocket_manager.py # Real-time Event Streaming
│   │   ├── config.py              # Application Configuration
│   │   ├── database.py            # Async Database Engine & Sessionmaker
│   │   └── main.py                # FastAPI Application & Static UI Server
│   ├── tests/
│   │   └── test_api.py            # Comprehensive Async End-to-End Test Suite
│   └── requirements.txt
├── frontend/                      # React 18 + Vite + Tailwind CSS + Recharts
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.jsx         # Live Bus Monitor & System KPIs
│   │   │   ├── RoomHero.jsx       # Primary Hardware Showcase (ROOM-204) + OLED Simulation
│   │   │   ├── MultiRoomGrid.jsx  # Scaling Fleet (ROOM-101, ROOM-102)
│   │   │   ├── AlertsPanel.jsx    # Real-Time Anomaly Ticker with Acknowledgment
│   │   │   └── AuditTimeline.jsx  # Timestamped Chronological Event Trail
│   │   └── api.js                 # Centralized Client API Service
│   └── package.json
├── firmware/
│   └── az3166/
│       ├── PegPower_AZ3166.ino    # Arduino C++ Firmware Sketch for MXChip AZ3166
│       └── README.md              # Flashing and Setup Guide
├── scripts/
│   ├── seed_demo.py               # 1-Click Database Demo Reset & Seeder
│   └── mock_az3166.py             # Python AZ3166 DevKit Emulator (Console OLED/RGB LED)
├── PegPower_Hackathon_PRD.docx     # Original Product Requirements Document
├── start.sh                       # Single-Command Unified Launcher
└── README.md
```

---

## 🚀 Quick Start

### 1. Launch Backend & Dashboard
```bash
./start.sh
```
* **Mission Control Dashboard:** [http://localhost:8000](http://localhost:8000)
* **Interactive API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Live WebSocket Bus:** `ws://localhost:8000/api/ws`

### 2. Connect the Edge Hardware
* **Option A: Physical MXChip AZ3166 DevKit**
  Follow the [Firmware Guide](file:///home/zoecyber/powerpeg/firmware/az3166/README.md) to flash `PegPower_AZ3166.ino`.
* **Option B: Run the Console Hardware Emulator**
  ```bash
  source .venv/bin/activate
  python scripts/mock_az3166.py http://localhost:8000
  ```

---

## 🧪 Running Automated Tests

Run the full end-to-end test suite (authorization state machine, device command queueing, telemetry ingestion, anomaly detection, and audit logging):

```bash
PYTHONPATH=backend .venv/bin/pytest -v backend/tests/test_api.py
```

---

## 🎬 Suggested Live Hackathon Presentation Demo (PRD Section 13.2)

1. **Overview & Initial State:** Open [http://localhost:8000](http://localhost:8000). Show `ROOM-204` assigned to `AZ3166-01`. Point out that the room is `UNAUTHORISED`, the physical controller relay reports `OFF` (Red LED), and telemetry shows 0 kW.
2. **Booking Creation:** Click **Check In Demo Guest**. A new stay is booked with simulated payment `PENDING`. Show that authorization remains `DENIED` because payment is not verified.
3. **Simulated Payment Confirmation:** Click **Confirm Simulated Payment**. The Authorisation Engine approves the room (`AUTHORISED`), instantly queues `POWER_ON`, and dispatches it to the AZ3166.
4. **Physical Controller Response:** Show the AZ3166 OLED updating to `RELAY: [ON]` with the RGB LED turning **Green**.
5. **Electrical Simulator Telemetry:** The independent virtual electrical simulator activates, streaming realistic voltage (~230V) and active load (~0.95 kW) to the Recharts waveform. Point out the `[SIMULATED TELEMETRY]` banner.
6. **Triggering Anomaly (The "Pitch Hero"):** Click **Simulate Rogue Power Draw**. The simulator generates a 1.4 kW load while unpermitted, immediately triggering a `CRITICAL` alert: `ENERGY_WHILE_UNAUTHORISED`.
7. **Operator Acknowledgment:** Click **Acknowledge** on the alert card. Show the resolution logged to the audit trail.
8. **Checkout / Revocation:** Click **Revoke Stay / Checkout**. The backend revokes authorization, dispatches `POWER_OFF`, the AZ3166 relay turns `OFF` (Red LED), and load drops to 0 kW.
9. **Audit Log Inspection:** Scroll through the Audit Trail showing timestamped proof of every booking, payment change, command dispatch, device acknowledgment, and anomaly alert.
