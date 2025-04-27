
// Pin Definitions
const int VRx = 32; // Joystick X-axis
const int VRy = 33; // Joystick Y-axis

void setup() {
  Serial.begin(115200);
  delay(1000);
  pinMode(VRx, INPUT);
  pinMode(VRy, INPUT);
}

void loop() {
  int xValue = analogRead(VRx);
  int yValue = analogRead(VRy);

  // Calculate Direction
  String direction = "Center";
  if (yValue < 1200) direction = "Up";
  else if (yValue > 2800) direction = "Down";

  if (xValue < 1200) {
    if (yValue < 1200) direction = "Up-Left";
    else if (yValue > 2800) direction = "Down-Left";
    else direction = "Left";
  }
  else if (xValue > 2800) {
    if (yValue < 1200) direction = "Up-Right";
    else if (yValue > 2800) direction = "Down-Right";
    else direction = "Right";
  }

  // Print to Serial
  Serial.print("X: ");
  Serial.print(xValue);
  Serial.print(" | Y: ");
  Serial.print(yValue);
  Serial.print(" | Direction: ");
  Serial.println(direction);

  delay(100);
}
