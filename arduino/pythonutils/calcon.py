import serial
import json
import time
import re
import msvcrt
from pynput.mouse import Controller as MouseController
from pynput.keyboard import Controller as KeyboardController

# CONFIG
serial_port = 'COM10'
baud_rate = 115200
calibration_file = 'calibration_data.json'

# Initialize
mouse = MouseController()
keyboard = KeyboardController()
ser = None

# Connect to Serial
def connect_serial():
    global ser
    try:
        ser = serial.Serial(serial_port, baud_rate, timeout=1)
        print(f"Connected to {serial_port}")
    except Exception as e:
        print(f"Failed to connect to serial port: {e}")
        ser = None

# Read Serial Line
def read_joystick_line():
    try:
        line = ser.readline().decode('utf-8', errors='replace').strip()
        x_match = re.search(r'X:\s*(-?\d+)', line)
        y_match = re.search(r'Y:\s*(-?\d+)', line)
        if x_match and y_match:
            x = int(x_match.group(1))
            y = int(y_match.group(1))
            return x, y
    except Exception:
        pass
    return None, None

# Calibration Mode
def calibrate():
    calibration_data = {}
    positions = ['Center', 'Up', 'Down', 'Left', 'Right']
    
    for pos in positions:
        input(f"\nMove the joystick to {pos} position and press ENTER...")
        samples = []
        start_time = time.time()
        while time.time() - start_time < 2:  # Capture for 2 seconds
            x, y = read_joystick_line()
            if x is not None and y is not None:
                samples.append((x, y))
            time.sleep(0.05)
        
        if samples:
            avg_x = sum([s[0] for s in samples]) // len(samples)
            avg_y = sum([s[1] for s in samples]) // len(samples)
            calibration_data[pos.lower()] = {'x': avg_x, 'y': avg_y}
            print(f"{pos} calibrated as X: {avg_x}, Y: {avg_y}")
        else:
            print(f"No data captured for {pos}")

    # Save calibration
    with open(calibration_file, 'w') as f:
        json.dump(calibration_data, f, indent=4)
    print(f"\nCalibration saved to {calibration_file}!")

# Controller Mode
def control():
    # Load calibration
    try:
        with open(calibration_file, 'r') as f:
            calib = json.load(f)
    except Exception as e:
        print(f"Calibration file missing or invalid: {e}")
        return

    center_x = calib['center']['x']
    center_y = calib['center']['y']

    print("\nController started! Press CTRL+C to exit.")

    while True:
        x, y = read_joystick_line()
        if x is None or y is None:
            continue

        # Relative movement from center
        delta_x = x - center_x
        delta_y = y - center_y

        deadzone = 15
        mouse_speed = 0.02
        key_threshold = 50

        # Apply deadzone
        if abs(delta_x) < deadzone:
            delta_x = 0
        if abs(delta_y) < deadzone:
            delta_y = 0

        # Move Mouse
        if delta_x != 0 or delta_y != 0:
            mouse.move(int(delta_x * mouse_speed), int(delta_y * mouse_speed))
#        time.sleep(0.05)

        # Keyboard Emulation
        if delta_y < -key_threshold:
            keyboard.press('w')
            keyboard.release('w')
        elif delta_y > key_threshold:
            keyboard.press('s')
            keyboard.release('s')

        if delta_x > key_threshold:
            keyboard.press('d')
            keyboard.release('d')
        elif delta_x < -key_threshold:
            keyboard.press('a')
            keyboard.release('a')
        time.sleep(0.05)

        
#dddaaaawawawasdsdasassdsdsdsdsdsdsddssddssdwdsdssdsddsdds
# Main
if __name__ == "__main__":
    print("Select Mode:")
    print("1. Calibrate")
    print("2. Controller")
    
    mode = input("Enter 1 or 2: ").strip()

    connect_serial()
    
    if not ser:
        print("Serial connection failed. Exiting.")
        exit()

    if mode == '1':
        calibrate()
    elif mode == '2':
        control()
    else:
        print("Invalid mode selected.")
