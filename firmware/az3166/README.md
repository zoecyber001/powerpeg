# PegPower - MXChip AZ3166 DevKit Firmware

## Overview
This firmware runs on the single physical **MXChip AZ3166 IoT DevKit** serving as the **PegPower Control Unit (PCU)** prototype.

### Hardware Responsibilities (PRD Section 8.2)
1. **Device Identity:** Identifies as `AZ3166-01`, assigned to `ROOM-204`.
2. **Wi-Fi Connectivity:** Connects to local Wi-Fi and communicates with the FastAPI backend over HTTP REST.
3. **Heartbeat:** Periodically sends heartbeats (`POST /api/devices/{id}/heartbeat`) every 5 seconds.
4. **Command Execution & Acknowledgment:**
   - Polls `GET /api/devices/{id}/commands/next`.
   - Executes `POWER_ON` and `POWER_OFF` at the firmware level.
   - Posts acknowledgment to `POST /api/devices/{id}/commands/ack`.
5. **Onboard OLED (128x64):**
   - Displays PegPower identity, Room Code, Wi-Fi status, and live simulated relay state.
6. **Onboard RGB LED:**
   - **Green:** Power Authorized (`RELAY: ON`)
   - **Red:** Power Revoked / Denied (`RELAY: OFF`)
   - **Yellow:** Connecting / Syncing

> **Safety Note (PRD Section 8.4):** The AZ3166 maintains a firmware-level simulated relay state. It is NOT connected to mains electricity and does NOT measure physical current or power.

---

## Flashing Instructions

### Method 1: Arduino IDE
1. Install Arduino IDE (v2.x or v1.8.x).
2. Add MXChip AZ3166 board support via Board Manager URL:
   `https://raw.githubusercontent.com/VSChina/azureiotdevkit_tools/master/package_azureboard_index.json`
3. Install **AZ3166** board package under `Tools > Board > Boards Manager`.
4. Open `PegPower_AZ3166.ino`.
5. Configure your Wi-Fi credentials and backend IP in the configuration section:
   ```cpp
   const char* WIFI_SSID = "YOUR_WIFI_SSID";
   const char* WIFI_PASS = "YOUR_WIFI_PASSWORD";
   const char* BACKEND_BASE_URL = "http://<YOUR_LAPTOP_IP>:8000";
   ```
6. Select Board: `MXCHIP AZ3166` and the corresponding serial COM port.
7. Click **Upload**.

### Method 2: Software Emulator (When physical board is not plugged in)
If presenting or testing without physical hardware plugged in:
```bash
python scripts/mock_az3166.py http://localhost:8000
```
This emulator implements the identical REST contract, logs OLED and RGB LED state in the terminal, and acknowledges commands instantly.
