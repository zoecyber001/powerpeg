#include "AZ3166WiFi.h"
#include "OledDisplay.h"
#include "RGB_LED.h"
#include "http_client.h"

const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASS = "YOUR_WIFI_PASSWORD";
const char* BACKEND_BASE_URL = "http://192.168.1.150:8000";

const char* DEVICE_CODE = "AZ3166-01";
const char* ROOM_CODE = "ROOM-204";
const char* FIRMWARE_VERSION = "1.0.0";

RGB_LED rgbLed;
static bool hasWifi = false;
static int deviceId = 1;
static String reportedRelayState = "OFF";
static unsigned long lastHeartbeatMillis = 0;
static const unsigned long HEARTBEAT_INTERVAL_MS = 5000;
static const unsigned long POLL_INTERVAL_MS = 1500;
static unsigned long lastPollMillis = 0;

void updateOled(const char* line1, const char* line2, const char* line3, const char* line4) {
    Screen.clean();
    Screen.print(0, line1);
    Screen.print(1, line2);
    Screen.print(2, line3);
    Screen.print(3, line4);
}

void setRgbState(const String& state) {
    if (state == "ON") {
        rgbLed.setColor(0, 255, 0);
    } else if (state == "OFF") {
        rgbLed.setColor(255, 0, 0);
    } else {
        rgbLed.setColor(255, 200, 0);
    }
}

void setupWifi() {
    updateOled("PegPower Booting", "Connecting Wi-Fi", WIFI_SSID, "Please wait...");
    setRgbState("SYNCING");

    if (WiFi.begin(WIFI_SSID, WIFI_PASS) == WL_CONNECTED) {
        hasWifi = true;
        IPAddress ip = WiFi.localIP();
        char ipStr[32];
        sprintf(ipStr, "IP: %s", ip.get_address());
        updateOled("PegPower | RM-204", "Wi-Fi: Connected", ipStr, "RELAY: [OFF]");
        setRgbState("OFF");
        Serial.println("[Wi-Fi] Connected successfully.");
    } else {
        hasWifi = false;
        updateOled("PegPower Error", "Wi-Fi Failed", "Check SSID/Pass", "Retrying...");
        setRgbState("OFF");
        Serial.println("[Wi-Fi] Failed to connect.");
    }
}

void registerDevice() {
    if (!hasWifi) return;

    char url[128];
    sprintf(url, "%s/api/devices/register", BACKEND_BASE_URL);

    char body[192];
    sprintf(body, "{\"device_code\":\"%s\",\"device_type\":\"AZ3166\",\"firmware_version\":\"%s\"}", DEVICE_CODE, FIRMWARE_VERSION);

    HTTPClient client = HTTPClient(HTTP_POST, url);
    client.set_header("Content-Type", "application/json");
    const Http_Response* response = client.send(body, strlen(body));

    if (response != NULL && (response->status_code == 200 || response->status_code == 201)) {
        Serial.println("[Registration] Success.");
    } else {
        Serial.println("[Registration] Failed or server unreachable.");
    }
}

void sendHeartbeat() {
    if (!hasWifi) return;

    char url[128];
    sprintf(url, "%s/api/devices/%d/heartbeat", BACKEND_BASE_URL, deviceId);

    char body[192];
    sprintf(body, "{\"device_code\":\"%s\",\"reported_relay_state\":\"%s\",\"firmware_version\":\"%s\"}", DEVICE_CODE, reportedRelayState.c_str(), FIRMWARE_VERSION);

    HTTPClient client = HTTPClient(HTTP_POST, url);
    client.set_header("Content-Type", "application/json");
    client.send(body, strlen(body));
}

void sendAck(int commandId, const char* state) {
    if (!hasWifi) return;

    char url[128];
    sprintf(url, "%s/api/devices/%d/commands/ack", BACKEND_BASE_URL, deviceId);

    char body[192];
    sprintf(body, "{\"command_id\":%d,\"status\":\"ACKNOWLEDGED\",\"reported_relay_state\":\"%s\",\"response_payload\":\"Firmware relay updated\"}", commandId, state);

    HTTPClient client = HTTPClient(HTTP_POST, url);
    client.set_header("Content-Type", "application/json");
    client.send(body, strlen(body));
    Serial.printf("[Command] ACK sent for Command ID %d\n", commandId);
}

void pollCommands() {
    if (!hasWifi) return;

    char url[128];
    sprintf(url, "%s/api/devices/%d/commands/next", BACKEND_BASE_URL, deviceId);

    HTTPClient client = HTTPClient(HTTP_GET, url);
    const Http_Response* response = client.send();

    if (response != NULL && response->status_code == 200 && response->body_length > 4) {
        String respBody = response->body;
        Serial.printf("[Command Received] %s\n", respBody.c_str());

        int idIdx = respBody.indexOf("\"id\":");
        int cmdIdx = respBody.indexOf("\"command\":\"");

        if (cmdIdx != -1) {
            int cmdStart = cmdIdx + 11;
            int cmdEnd = respBody.indexOf("\"", cmdStart);
            String command = respBody.substring(cmdStart, cmdEnd);

            int commaIdx = respBody.indexOf(",", idIdx);
            int commandId = respBody.substring(idIdx + 5, commaIdx).toInt();

            if (command == "POWER_ON") {
                reportedRelayState = "ON";
                setRgbState("ON");
                updateOled("PegPower | RM-204", "Auth: ACTIVE", "RELAY: [ON]", "Power Available");
            } else if (command == "POWER_OFF") {
                reportedRelayState = "OFF";
                setRgbState("OFF");
                updateOled("PegPower | RM-204", "Auth: REVOKED", "RELAY: [OFF]", "Power Cut");
            }

            sendAck(commandId, reportedRelayState.c_str());
        }
    }
}

void setup() {
    Serial.begin(115200);
    Screen.init();
    updateOled("PegPower AZ3166", "Initializing...", "Device: AZ3166-01", "v1.0.0");
    setRgbState("SYNCING");
    delay(1000);

    setupWifi();
    registerDevice();
}

void loop() {
    unsigned long currentMillis = millis();

    if (currentMillis - lastPollMillis >= POLL_INTERVAL_MS) {
        lastPollMillis = currentMillis;
        pollCommands();
    }

    if (currentMillis - lastHeartbeatMillis >= HEARTBEAT_INTERVAL_MS) {
        lastHeartbeatMillis = currentMillis;
        sendHeartbeat();
    }
}
