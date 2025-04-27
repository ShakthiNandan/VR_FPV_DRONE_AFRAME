import serial
from pynput.mouse import Controller
from pynput.keyboard import Controller as KeyboardController
import time
import re
import msvcrt  # For keyboard input detection on Windows

# Define your serial port (adjust based on your system: COMx on Windows, /dev/ttyUSBx on Linux/macOS)
serial_port = 'COM10'#hange this to the correct serial port
baud_rate = 115200  # Baud rate of ESP32

# Initialize variables for error tolerance
last_valid_x = 2048  # Initial middle position
last_valid_y = 2048  # Initial middle position
error_tolerance_count = 0
max_error_tolerance = 5  # Maximum number of errors before reconnecting
reconnect_attempts = 0
max_reconnect_attempts = 3

# Calibration values based on observed output
# Center position calibration (offsets)
x_center_offset = -10  # The X value when joystick is at center
y_center_offset = -16  # The Y value when joystick is at center

# Initialize calibration mode variables
calibration_samples = []
is_calibrating = False
calibration_start_time = 0
calibration_duration = 5  # seconds to collect calibration data

# Initialize serial communication
try:
    ser = serial.Serial(serial_port, baud_rate, timeout=1)
except Exception as e:
    print(f"Error opening serial port: {e}")
    print("Please check if the device is connected and the port is correct.")
    ser = None

# Initialize mouse and keyboard controllers
mouse = Controller()
keyboard = KeyboardController()

# Function to map joystick value to a specific range with bounds checking and calibration
def map_joystick_value(value, min_value, max_value, offset=0):
    try:
        # Apply calibration (subtract offset to center around 0)
        calibrated_value = value - offset
        
        # Ensure value is within expected range
        calibrated_value = max(-200, min(200, calibrated_value))
        
        # Apply non-linear scaling for better control (optional)
        if abs(calibrated_value) < 20:
            # Reduce sensitivity near center for finer control
            return int(calibrated_value * 0.5)
        else:
            # Normal or increased sensitivity away from center
            return int(calibrated_value)
    except Exception:
        # If any error occurs, return 0 (neutral position)
        return 0

# Function to safely parse integer values
def safe_parse_int(value_str, default_value=0):
    try:
        return int(value_str)
    except (ValueError, TypeError):
        return default_value

# Function to attempt reconnection to serial port
def try_reconnect():
    global ser, reconnect_attempts
    if ser:
        try:
            ser.close()
        except:
            pass
    
    print(f"Attempting to reconnect to {serial_port} (Attempt {reconnect_attempts+1}/{max_reconnect_attempts})")
    try:
        ser = serial.Serial(serial_port, baud_rate, timeout=1)
        print("Successfully reconnected!")
        reconnect_attempts = 0
        return True
    except Exception as e:
        print(f"Reconnection failed: {e}")
        reconnect_attempts += 1
        time.sleep(2)  # Wait before trying again
        return False

# Function to perform auto-calibration
def start_calibration():
    global is_calibrating, calibration_samples, calibration_start_time
    print("Starting joystick calibration...")
    print("Please leave the joystick in the center position for 5 seconds.")
    calibration_samples = []
    is_calibrating = True
    calibration_start_time = time.time()

# Function to finish calibration and set offsets
def finish_calibration():
    global is_calibrating, x_center_offset, y_center_offset, calibration_samples
    
    if len(calibration_samples) > 0:
        # Calculate average center position
        x_values = [sample[0] for sample in calibration_samples]
        y_values = [sample[1] for sample in calibration_samples]
        
        x_center_offset = sum(x_values) // len(x_values)
        y_center_offset = sum(y_values) // len(y_values)
        
        print(f"Calibration complete!")
        print(f"New center offsets - X: {x_center_offset}, Y: {y_center_offset}")
    else:
        print("Calibration failed - no samples collected")
    
    is_calibrating = False

# Optionally start with calibration
print("Press 'c' in the terminal to calibrate the joystick at any time.")
print("Using default calibration values: X offset = {}, Y offset = {}".format(x_center_offset, y_center_offset))

# Read joystick values and emulate control
while True:
    try:
        # Check if serial connection is valid
        if ser is None or not ser.is_open:
            if reconnect_attempts < max_reconnect_attempts:
                if try_reconnect():
                    continue
            else:
                print("Max reconnection attempts reached. Please check your hardware and restart the script.")
                time.sleep(5)
                reconnect_attempts = 0
                continue
        
        # Read the serial data from ESP32
        line = ser.readline().decode('utf-8', errors='replace').strip()
        
        if line:
            # Parse the format: "Joystick X: xValue, Y: yValue, Direction: direction"
            x_match = re.search(r'X:\s*(-?\d+)', line)
            y_match = re.search(r'Y:\s*(-?\d+)', line)
            direction_match = re.search(r'Direction:\s*(\w+)', line)
            
            # Check if we got valid data
            if x_match and y_match:
                # Reset error counter on successful read
                error_tolerance_count = 0
                
                # Extract and validate values
                x_raw = safe_parse_int(x_match.group(1), 0)
                y_raw = safe_parse_int(y_match.group(1), 0)
                
                # Store last valid values
                last_valid_x = x_raw
                last_valid_y = y_raw
                
                direction = direction_match.group(1) if direction_match else "None"
                
                # If we're calibrating, collect samples
                if is_calibrating:
                    calibration_samples.append((x_raw, y_raw))
                    elapsed_time = time.time() - calibration_start_time
                    if elapsed_time >= calibration_duration:
                        finish_calibration()
                    continue  # Skip control actions during calibration
                
                # Apply calibration and mapping
                x_mapped = map_joystick_value(x_raw, -100, 100, x_center_offset)
                y_mapped = map_joystick_value(y_raw, -100, 100, y_center_offset)
                
                # Apply a dead zone - ignore small movements near center
                dead_zone = 10
                if abs(x_mapped) < dead_zone:
                    x_mapped = 0
                if abs(y_mapped) < dead_zone:
                    y_mapped = 0

                print(f"Raw X: {x_raw}, Y: {y_raw} | Calibrated X: {x_mapped}, Y: {y_mapped}, Direction: {direction}")

                # Only move the mouse if values are outside the dead zone
                if x_mapped != 0 or y_mapped != 0:
                    # Scale down values for smoother mouse movement
                    mouse_scale = 0.2
                    mouse.move(int(x_mapped * mouse_scale), int(y_mapped * mouse_scale))

                # Emulate keyboard controls with thresholds
                key_threshold = 50  # Threshold for key presses
                
                if y_mapped > key_threshold:  # Move down
                    keyboard.press('s')
                    keyboard.release('s')
                elif y_mapped < -key_threshold:  # Move up
                    keyboard.press('w')
                    keyboard.release('w')

                if x_mapped > key_threshold:  # Move right
                    keyboard.press('d')
                    keyboard.release('d')
                elif x_mapped < -key_threshold:  # Move left
                    keyboard.press('a')
                    keyboard.release('a')
            else:
                # Increment error counter when invalid data is received
                error_tolerance_count += 1
                if error_tolerance_count > max_error_tolerance:
                    print(f"Too many invalid readings. Last line: {line}")
                    error_tolerance_count = 0  # Reset counter
                    
                    # Use the last valid values as a fallback
                    x_mapped = map_joystick_value(last_valid_x, -100, 100, x_center_offset)
                    y_mapped = map_joystick_value(last_valid_y, -100, 100, y_center_offset)
                    
                    if error_tolerance_count % (max_error_tolerance * 2) == 0:
                        # Attempt to flush the buffer if we keep getting errors
                        ser.reset_input_buffer()

            # Add a small delay for responsiveness
            time.sleep(0.05)  # Reduced delay for better responsiveness

        # Check for keyboard input to start calibration (requires terminal focus)
        if not is_calibrating and msvcrt.kbhit():
            key = msvcrt.getch().decode('utf-8', errors='ignore').lower()
            if key == 'c':
                start_calibration()
                
    except serial.SerialException as se:
        print(f"Serial connection error: {se}")
        if ser:
            try:
                ser.close()
            except:
                pass
            ser = None
        time.sleep(1)
    except Exception as e:
        print(f"Error: {e}")
        error_tolerance_count += 1
        time.sleep(0.5)  # Longer delay on error
