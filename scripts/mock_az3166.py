import sys
import time
import requests

BACKEND_URL = "http://localhost:8000"
DEVICE_CODE = "AZ3166-01"
ROOM_CODE = "ROOM-204"

class AZ3166Emulator:
    def __init__(self, base_url: str = BACKEND_URL):
        self.base_url = base_url
        self.device_id = None
        self.relay_state = "OFF"
        self.rgb_led = "RED"
        self.running = True

    def log_screen(self, status_msg="OK"):
        bar = "═" * 46
        led_indicator = f"\033[92m● GREEN\033[0m" if self.rgb_led == "GREEN" else (
            f"\033[91m● RED\033[0m" if self.rgb_led == "RED" else f"\033[93m● YELLOW\033[0m"
        )
        print(f"\n{bar}")
        print(f"  [AZ3166 OLED DISPLAY (128x64)]  LED: {led_indicator}")
        print(f"  Line 1: PegPower | {ROOM_CODE}")
        print(f"  Line 2: DevID: {DEVICE_CODE} (v1.0.0)")
        print(f"  Line 3: RELAY STATE: [{self.relay_state}]")
        print(f"  Line 4: Status: {status_msg}")
        print(f"{bar}\n")

    def register(self):
        print(f"[*] Booting AZ3166 DevKit. Connecting to backend at {self.base_url}...")
        self.rgb_led = "YELLOW"
        try:
            res = requests.post(
                f"{self.base_url}/api/devices/register",
                json={
                    "device_code": DEVICE_CODE,
                    "device_type": "AZ3166",
                    "firmware_version": "1.0.0"
                },
                timeout=5
            )
            if res.status_code in (200, 201):
                data = res.json()
                self.device_id = data["id"]
                self.relay_state = data.get("reported_relay_state", "OFF")
                self.rgb_led = "GREEN" if self.relay_state == "ON" else "RED"
                self.log_screen(status_msg="Wi-Fi OK | Registered")
                print(f"[+] Device registered with ID: {self.device_id}")
                return True
        except Exception as e:
            print(f"[-] Registration failed: {e}")
            self.rgb_led = "YELLOW"
            return False

    def send_heartbeat(self):
        if not self.device_id:
            return
        try:
            requests.post(
                f"{self.base_url}/api/devices/{self.device_id}/heartbeat",
                json={
                    "device_code": DEVICE_CODE,
                    "reported_relay_state": self.relay_state,
                    "firmware_version": "1.0.0"
                },
                timeout=3
            )
        except Exception:
            pass

    def check_and_execute_commands(self):
        if not self.device_id:
            return
        try:
            res = requests.get(f"{self.base_url}/api/devices/{self.device_id}/commands/next", timeout=3)
            if res.status_code == 200:
                cmd = res.json()
                if cmd:
                    cmd_id = cmd["id"]
                    action = cmd["command"]
                    print(f"\n[⚡ ACTION] Received Command #{cmd_id}: {action}")

                    if action == "POWER_ON":
                        self.relay_state = "ON"
                        self.rgb_led = "GREEN"
                    elif action == "POWER_OFF":
                        self.relay_state = "OFF"
                        self.rgb_led = "RED"

                    self.log_screen(status_msg=f"CMD Executed: {action}")

                    ack_res = requests.post(
                        f"{self.base_url}/api/devices/{self.device_id}/commands/ack",
                        json={
                            "command_id": cmd_id,
                            "status": "ACKNOWLEDGED",
                            "reported_relay_state": self.relay_state,
                            "response_payload": f"Firmware relay switched to {self.relay_state}"
                        },
                        timeout=3
                    )
                    if ack_res.status_code == 200:
                        print(f"[✓ ACK] Command #{cmd_id} acknowledged back to backend.")
        except Exception as e:
            print(f"[-] Error polling commands: {e}")

    def loop(self):
        while not self.register():
            print("[!] Retrying registration in 3 seconds...")
            time.sleep(3)

        heartbeat_timer = 0
        while self.running:
            self.check_and_execute_commands()

            heartbeat_timer += 1
            if heartbeat_timer >= 5:
                self.send_heartbeat()
                heartbeat_timer = 0

            time.sleep(1)

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else BACKEND_URL
    emulator = AZ3166Emulator(url)
    try:
        emulator.loop()
    except KeyboardInterrupt:
        print("\n[!] Stopping AZ3166 emulator.")
