#include <WiFi.h>
#include <WebServer.h>

// Pin Definitions
const int VRx = 32; // Joystick X-axis (connected to GPIO32)
const int VRy = 33; // Joystick Y-axis (connected to GPIO33)

// SoftAP credentials
const char* ssid = "ESP32_Joystick";
const char* password = "12345678"; // Minimum 8 characters

WebServer server(80);

// Variables to store joystick readings
int xValue = 0;
int yValue = 0;

// Timer variables for serial printing
unsigned long lastSerialPrint = 0;
const unsigned long serialInterval = 100; // Print every 500 milliseconds

// Handle the main webpage
void handleRoot() {
  String html = "<!DOCTYPE html><html><head><title>Joystick Monitor</title>"
                "<meta http-equiv='refresh' content='1'/>"
                "<style>body{font-family:Arial;text-align:center;margin-top:50px;}</style>"
                "</head><body>"
                "<h1>ESP32 Joystick Monitor</h1>"
                "<p><b>X-axis:</b> " + String(xValue) + "</p>"
                "<p><b>Y-axis:</b> " + String(yValue) + "</p>"
                "</body></html>";
  server.send(200, "text/html", html);
}

void setup() {
  // Start Serial Monitor
  Serial.begin(115200);
  delay(1000);

  // Setup joystick pins
  pinMode(VRx, INPUT);
  pinMode(VRy, INPUT);

  // Start Wi-Fi in AP mode
  WiFi.softAP(ssid, password);
  Serial.println("Access Point Started");
  Serial.print("IP Address: ");
  Serial.println(WiFi.softAPIP());

  // Setup HTTP Server
  server.on("/", handleRoot);
  server.begin();
  Serial.println("HTTP server started");
}

void loop() {
  // Read Joystick Values
  xValue = analogRead(VRx);
  yValue = analogRead(VRy);

  // Only print to Serial every 500ms
  unsigned long currentMillis = millis();
  if (currentMillis - lastSerialPrint >= serialInterval) {
    lastSerialPrint = currentMillis;

    // Serial.print("X: ");
    // Serial.print(xValue);
    // Serial.print(" | Y: ");
    // Serial.println(yValue);
  }

  server.handleClient();
}
