import serial
from pynput.mouse import Controller as MouseController
from pynput.keyboard import Controller as KBController
import time
import re
import msvcrt  # Windows‐only

# ————— CONFIG —————
SERIAL_PORT        = 'COM10'      # change as needed
BAUD_RATE          = 115200
MAX_ERROR_TOLERANCE = 5
MAX_RECONNECTS      = 3

# initial “center” raw values (you’ll overwrite via calibration)
x_center_offset = -10
y_center_offset = -16

# ————— STATE —————
ser = None
reconnect_attempts = 0
error_tolerance_count = 0

last_valid_x = 2048
last_valid_y = 2048

calibration_samples = []
is_calibrating = False
calibration_start_time = 0
CALIBRATION_DURATION = 5  # seconds

mouse = MouseController()
keyboard = KBController()

# ————— HELPERS —————
def open_serial():
    global ser, reconnect_attempts
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        reconnect_attempts = 0
        print(f"[+] Opened {SERIAL_PORT}")
    except Exception as e:
        reconnect_attempts += 1
        print(f"[!] Couldn’t open {SERIAL_PORT}: {e} "
              f"(Attempt {reconnect_attempts}/{MAX_RECONNECTS})")
        ser = None

def map_joystick_value(val, offset):
    """Apply offset, clamp to ±200, then apply a small dead‐zone scaling."""
    v = val - offset
    v = max(-200, min(200, v))
    if abs(v) < 20:
        return int(v * 0.5)
    return int(v)

def start_calibration():
    global is_calibrating, calibration_samples, calibration_start_time
    print("[*] Calibration start — keep joystick centered…")
    calibration_samples = []
    is_calibrating = True
    calibration_start_time = time.time()

def finish_calibration():
    global is_calibrating, x_center_offset, y_center_offset
    if calibration_samples:
        xs, ys = zip(*calibration_samples)
        x_center_offset = sum(xs) // len(xs)
        y_center_offset = sum(ys) // len(ys)
        print(f"[+] Calibration done. Offsets: X={x_center_offset}, Y={y_center_offset}")
    else:
        print("[!] Calibration failed — no samples.")
    is_calibrating = False

def parse_line(line):
    """Expect lines like: 'Raw X: 1954, Y: 1887 | … Direction: Center'"""
    m = re.search(r'X:\s*(-?\d+),\s*Y:\s*(-?\d+).*Direction:\s*(\w+)', line)
    if not m:
        return None
    x_raw = int(m.group(1))
    y_raw = int(m.group(2))
    direction = m.group(3)
    return x_raw, y_raw, direction

# ————— MAIN LOOP —————
print("Press 'c' to calibrate. Ctrl-C to quit.")
open_serial()

while True:
    # (Re)open serial if needed
    if ser is None or not ser.is_open:
        if reconnect_attempts < MAX_RECONNECTS:
            open_serial()
            time.sleep(1)
            continue
        else:
            print("[!] Max reconnects reached. Check hardware.")
            time.sleep(5)
            reconnect_attempts = 0
            continue

    # Read one line
    raw = ser.readline().decode('utf-8', errors='ignore').strip()
    if raw:
        parsed = parse_line(raw)
        if parsed:
            # reset error counter
            error_tolerance_count = 0
            x_raw, y_raw, direction = parsed

            # during calibration, collect samples
            if is_calibrating:
                calibration_samples.append((x_raw, y_raw))
                if time.time() - calibration_start_time >= CALIBRATION_DURATION:
                    finish_calibration()
                # skip control actions while calibrating
                continue

            # map & deadzone
            x_m = map_joystick_value(x_raw, x_center_offset)
            y_m = map_joystick_value(y_raw, y_center_offset)
            dead = 10
            if abs(x_m) < dead: x_m = 0
            if abs(y_m) < dead: y_m = 0

            # feedback
            print(f"Raw X:{x_raw:4d} Y:{y_raw:4d} → Cal X:{x_m:4d} Y:{y_m:4d} Dir:{direction}")

            # mouse move
            if x_m or y_m:
                scale = 0.2
                mouse.move(int(x_m * scale), int(y_m * scale))

            # WASD on threshold
            thr = 50
            if y_m >  thr: keyboard.press('s'); keyboard.release('s')
            if y_m < -thr: keyboard.press('w'); keyboard.release('w')
            if x_m >  thr: keyboard.press('d'); keyboard.release('d')
            if x_m < -thr: keyboard.press('a'); keyboard.release('a')

        else:
            # parse error
            error_tolerance_count += 1
            if error_tolerance_count > MAX_ERROR_TOLERANCE:
                print(f"[!] {error_tolerance_count} invalid lines — flushing buffer.")
                ser.reset_input_buffer()
                error_tolerance_count = 0

    # check for ‘c’ to calibrate
    if msvcrt.kbhit():
        key = msvcrt.getch().decode('utf-8', errors='ignore').lower()
        if key == 'c' and not is_calibrating:
            start_calibration()

    time.sleep(0.05)
