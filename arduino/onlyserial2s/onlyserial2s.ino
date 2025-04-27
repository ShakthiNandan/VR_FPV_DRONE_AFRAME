// Pin Definitions
const int VRx1 = 36; // Joystick 1 X-axis
const int VRy1 = 39; // Joystick 1 Y-axis
const int VRx2 = 25; // Joystick 2 X-axis
const int VRy2 = 26; // Joystick 2 Y-axis

void setup() {
  Serial.begin(115200);
  delay(1000);

  pinMode(VRx1, INPUT);
  pinMode(VRy1, INPUT);
  pinMode(VRx2, INPUT);
  pinMode(VRy2, INPUT);
}

void loop() {
  int xValue1 = analogRead(VRx1);
  int yValue1 = analogRead(VRy1);
  int xValue2 = analogRead(VRx2);
  int yValue2 = analogRead(VRy2);

  // Calculate Direction for Joystick 1
  String direction1 = "Center";
  if (yValue1 < 1200) direction1 = "Up";
  else if (yValue1 > 2800) direction1 = "Down";

  if (xValue1 < 1200) {
    if (yValue1 < 1200) direction1 = "Up-Left";
    else if (yValue1 > 2800) direction1 = "Down-Left";
    else direction1 = "Left";
  }
  else if (xValue1 > 2800) {
    if (yValue1 < 1200) direction1 = "Up-Right";
    else if (yValue1 > 2800) direction1 = "Down-Right";
    else direction1 = "Right";
  }

  // Calculate Direction for Joystick 2
  String direction2 = "Center";
  if (yValue2 < 1200) direction2 = "Up";
  else if (yValue2 > 2800) direction2 = "Down";

  if (xValue2 < 1200) {
    if (yValue2 < 1200) direction2 = "Up-Left";
    else if (yValue2 > 2800) direction2 = "Down-Left";
    else direction2 = "Left";
  }
  else if (xValue2 > 2800) {
    if (yValue2 < 1200) direction2 = "Up-Right";
    else if (yValue2 > 2800) direction2 = "Down-Right";
    else direction2 = "Right";
  }

  // Print Joystick 1
  Serial.print("Joystick 1 -> X: ");
  Serial.print(xValue1);
  Serial.print(" | Y: ");
  Serial.print(yValue1);
  Serial.print(" | Direction: ");
  Serial.println(direction1);

  // Print Joystick 2
  Serial.print("Joystick 2 -> X: ");
  Serial.print(xValue2);
  Serial.print(" | Y: ");
  Serial.print(yValue2);
  Serial.print(" | Direction: ");
  Serial.println(direction2);

  delay(100);
}
