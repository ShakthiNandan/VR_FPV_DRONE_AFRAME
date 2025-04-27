#include <WiFi.h>
#include <WebServer.h>

// Pin Definitions (for right-side pins on ESP32)
const int VRx = 32; // Joystick X-axis (GPIO34)
const int VRy = 33; // Joystick Y-axis (GPIO35)

// Wi-Fi credentials
const char* ssid = "qwertyuiop";     // Wi-Fi SSID
const char* password = "asdfghjkl";  // Wi-Fi password

WebServer server(80);

// Variables to store joystick readings
int xValue = 0;
int yValue = 0;

// HTML Page to render on ESP32
const char htmlPage[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <title>ESP32 Joystick Monitor</title>
  <style>
    body { font-family: Arial; text-align: center; margin-top: 30px; }
    #joystickBox {
      margin: 20px auto;
      width: 200px; height: 200px;
      border: 2px solid #000;
      position: relative;
      background: #f0f0f0;
    }
    #joystickDot {
      width: 20px; height: 20px;
      background: red;
      border-radius: 50%;
      position: absolute;
      top: 90px; left: 90px;
      transition: all 0.1s linear;
    }
    #values {
      font-size: 20px;
      margin-top: 20px;
    }
    #direction {
      font-size: 24px;
      font-weight: bold;
      color: blue;
      margin-top: 10px;
    }
  </style>
</head>
<body>
  <h1>ESP32 Joystick Live Monitor</h1>

  <div id="joystickBox">
    <div id="joystickDot"></div>
  </div>

  <div id="values">
    X: <span id="xVal">0</span> |
    Y: <span id="yVal">0</span>
  </div>

  <div id="direction">
    Direction: <span id="dir">Center</span>
  </div>

  <script>
    function fetchData() {
      fetch('/read')
        .then(response => response.json())
        .then(data => {
          let x = data.x;
          let y = data.y;
          document.getElementById('xVal').innerText = x;
          document.getElementById('yVal').innerText = y;

          // Normalize joystick values (assuming ADC 0-4095)
          let normX = (x / 4095) * 160; // 160px move in 200px box (centered 20px dot)
          let normY = (y / 4095) * 160;

          document.getElementById('joystickDot').style.left = normX + "px";
          document.getElementById('joystickDot').style.top = normY + "px";

          // Calculate Direction
          let direction = "Center";
          if (y < 1200) direction = "Up";
          else if (y > 2800) direction = "Down";

          if (x < 1200) {
            if (y < 1200) direction = "Up-Left";
            else if (y > 2800) direction = "Down-Left";
            else direction = "Left";
          }
          else if (x > 2800) {
            if (y < 1200) direction = "Up-Right";
            else if (y > 2800) direction = "Down-Right";
            else direction = "Right";
          }

          document.getElementById('dir').innerText = direction;
        })
        .catch(error => console.error('Error:', error));
    }

    setInterval(fetchData, 100); // Fetch data every 100ms
  </script>
</body>
</html>
)rawliteral";

// Handle root URL to send HTML page
void handleRoot() {
  server.send_P(200, "text/html", htmlPage);
}

// Handle "/read" URL to send joystick values as JSON
void handleRead() {
  xValue = analogRead(VRx);
  yValue = analogRead(VRy);
  
  Serial.print(xValue,yValue);
  String json = "{\"x\":" + String(xValue) + ",\"y\":" + String(yValue) + "}";
  server.send(200, "application/json", json);
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  pinMode(VRx, INPUT);
  pinMode(VRy, INPUT);

  // Connect to Wi-Fi
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("Connected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());

  server.on("/", handleRoot);
  server.on("/read", handleRead);
  server.begin();
  Serial.println("HTTP server started");
}

void loop() {
  server.handleClient();
}
