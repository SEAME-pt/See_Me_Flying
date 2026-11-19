// pi_bridge - turns a Wemos D1 Mini (ESP8266) into a "Wi-Fi cable" between the
// Pi's USB port and the drone's esp-link.
//
//   Pi --USB serial--> D1 Mini --Wi-Fi, TCP--> esp-link (192.168.4.1:23) --UART--> FC
//
// It joins esp-link's access point, connects to the serial bridge port, and
// copies bytes both ways. It never prints anything on the serial port: that
// port carries MSP only. Status is shown on the blue LED:
//   fast blink  joining the Wi-Fi
//   slow blink  Wi-Fi OK, connecting to esp-link
//   solid on    bridging
//
// On the Pi:  ./build/msp_gateway --serial /dev/ttyUSB0 --baud 115200

#include <ESP8266WiFi.h>

// ---------- settings ----------
const char* WIFI_SSID = "ESP_XXXXXX";          // esp-link's AP name (see esp-link's Wi-Fi page)
const char* WIFI_PASS = "";                    // empty if the AP is open
const IPAddress ESP_LINK_IP(192, 168, 4, 1);   // esp-link's address on its own AP
const uint16_t ESP_LINK_PORT = 23;             // esp-link's serial bridge port
const uint32_t USB_BAUD = 115200;              // must match msp_gateway --baud
// ------------------------------

const int LED = LED_BUILTIN;   // GPIO2 on the D1 Mini, lit when LOW

WiFiClient link;
unsigned long lastConnectAttempt = 0;

void setLed(bool on) { digitalWrite(LED, on ? LOW : HIGH); }

void blink(unsigned long periodMs) { setLed((millis() / periodMs) % 2 == 0); }

// While there's nowhere to send it, throw away what the Pi sends so old
// requests don't arrive at the FC in a burst once the link is back.
void discardSerial() {
    while (Serial.available()) Serial.read();
}

void setup() {
    Serial.setRxBufferSize(1024);
    Serial.begin(USB_BAUD);
    Serial.setDebugOutput(false);   // no Wi-Fi debug text mixed into the MSP stream

    pinMode(LED, OUTPUT);
    setLed(false);

    WiFi.persistent(false);              // don't wear the flash with Wi-Fi settings
    WiFi.mode(WIFI_STA);
    WiFi.setSleepMode(WIFI_NONE_SLEEP);  // modem sleep adds tens of ms of latency
    WiFi.setAutoReconnect(true);
    WiFi.begin(WIFI_SSID, WIFI_PASS);
}

void loop() {
    if (WiFi.status() != WL_CONNECTED) {
        if (link.connected()) link.stop();
        blink(100);
        discardSerial();
        return;
    }

    if (!link.connected()) {
        blink(500);
        discardSerial();
        if (millis() - lastConnectAttempt > 1000) {
            lastConnectAttempt = millis();
            if (link.connect(ESP_LINK_IP, ESP_LINK_PORT)) {
                link.setNoDelay(true);   // send small MSP frames immediately
                while (link.available()) link.read();
            }
        }
        return;
    }

    setLed(true);
    uint8_t buf[256];

    // Pi -> drone
    size_t n = Serial.available();
    if (n > 0) {
        n = Serial.readBytes(buf, n < sizeof buf ? n : sizeof buf);
        link.write(buf, n);
    }

    // drone -> Pi
    n = link.available();
    if (n > 0) {
        const int got = link.read(buf, n < sizeof buf ? n : sizeof buf);
        if (got > 0) Serial.write(buf, static_cast<size_t>(got));
    }
}
