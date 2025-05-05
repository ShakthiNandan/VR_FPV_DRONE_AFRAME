import serial
import json
import time
import re
from pynput.keyboard import Key, Controller as KeyboardController

# CONFIG
serial_port       = 'COM10'
baud_rate         = 115200
calibration_file1 = 'calibration_data_joy1.json'
calibration_file2 = 'calibration_data_joy2.json'

# Globals
ser       = None
keyboard  = KeyboardController()
last_keys = set()

# Key mappings (customize if you like)
KEY_MAP_1 = {
    'up': 'w', 'down': 's', 'left': 'a', 'right': 'd',
    'up-left': 'w', 'up-right': 'w',
    'down-left': 's', 'down-right': 's'
}
KEY_MAP_2 = {
    'up': Key.up, 'down': Key.down, 'left': Key.left, 'right': Key.right,
    'up-left': Key.up, 'up-right': Key.up,
    'down-left': Key.down, 'down-right': Key.down
}

def connect_serial():
    global ser
    try:
        ser = serial.Serial(serial_port, baud_rate, timeout=1)
        print(f"[+] Connected to {serial_port}")
    except Exception as e:
        print(f"[!] Serial connection failed: {e}")
        ser = None

def read_joystick_lines():
    """Read two lines and parse Joystick 1 & 2."""
    try:
        l1 = ser.readline().decode(errors='replace').strip()
        l2 = ser.readline().decode(errors='replace').strip()
    except:
        return (None,)*3, (None,)*3

    joy1 = joy2 = (None, None, None)
    for line in (l1, l2):
        if line.startswith("Joystick 1"):
            m = re.match(r'.*X:\s*(-?\d+).*Y:\s*(-?\d+).*Direction:\s*(\w+)', line)
            if m: joy1 = (int(m[1]), int(m[2]), m[3])
        elif line.startswith("Joystick 2"):
            m = re.match(r'.*X:\s*(-?\d+).*Y:\s*(-?\d+).*Direction:\s*(\w+)', line)
            if m: joy2 = (int(m[1]), int(m[2]), m[3])
    return joy1, joy2

def calibrate_joystick(num, filename):
    data = {}
    for pos in ['Center','Up','Down','Left','Right']:
        input(f"Move joystick {num} to {pos}. Press ENTER when steady.")
        samples, t0 = [], time.time()
        while time.time() - t0 < 2:
            (x1,y1,_),(x2,y2,_) = read_joystick_lines()
            x,y = (x1,y1) if num==1 else (x2,y2)
            if x is not None:
                samples.append((x,y))
            time.sleep(0.05)
        if samples:
            xs = [s[0] for s in samples]
            ys = [s[1] for s in samples]
            data[pos.lower()] = {
                'x': sum(xs)//len(xs),
                'y': sum(ys)//len(ys),
                'err_x': (max(xs)-min(xs))//2,
                'err_y': (max(ys)-min(ys))//2
            }
            print(f"  {pos}: X={data[pos.lower()]['x']}±{data[pos.lower()]['err_x']}, "
                  f"Y={data[pos.lower()]['y']}±{data[pos.lower()]['err_y']}")
        else:
            print(f"[!] No samples for {pos}")
    with open(filename,'w') as f:
        json.dump(data, f, indent=4)
    print(f"[+] Saved → {filename}\n")

def calibrate():
    print("Calibration Menu:\n 1) Joystick 1\n 2) Joystick 2\n 3) Both")
    choice = input("Choose: ").strip()
    if choice in ('1','3'):
        calibrate_joystick(1, calibration_file1)
    if choice in ('2','3'):
        calibrate_joystick(2, calibration_file2)

def compute_thresholds(cal):
    """From center and direction data compute dx/dy thresholds."""
    cx, cy = cal['center']['x'], cal['center']['y']
    # horizontal thresholds
    left_thresh  = (cx - cal['left']['x']) // 2
    right_thresh = (cal['right']['x'] - cx) // 2
    # vertical thresholds
    up_thresh    = (cy - cal['up']['y']) // 2
    down_thresh  = (cal['down']['y'] - cy) // 2
    # also incorporate measurement error
    ex = cal['center']['err_x']
    ey = cal['center']['err_y']
    return {
        'left':  left_thresh  - ex,
        'right': right_thresh - ex,
        'up':    up_thresh    - ey,
        'down':  down_thresh  - ey
    }

def resolve_direction(dx, dy, thr):
    dir_ = 'center'
    if dy < -thr['up']:    dir_ = 'up'
    elif dy >  thr['down']: dir_ = 'down'
    if dx < -thr['left']:
        dir_ += '-left' if dir_!='center' else 'left'
    elif dx >  thr['right']:
        dir_ += '-right' if dir_!='center' else 'right'
    return dir_

def press_keys(keys):
    global last_keys
    # release old keys
    for k in last_keys - keys:
        keyboard.release(k)
    # press new keys
    for k in keys - last_keys:
        keyboard.press(k)
    last_keys = keys

def controller_mode():
    # load calibration
    try:
        c1 = json.load(open(calibration_file1))
        c2 = json.load(open(calibration_file2))
    except:
        print("[!] Missing calibration files. Run mode 1 first.")
        return

    thr1 = compute_thresholds(c1)
    thr2 = compute_thresholds(c2)
    cx1, cy1 = c1['center']['x'], c1['center']['y']
    cx2, cy2 = c2['center']['x'], c2['center']['y']

    print("→ Controller mode active. Move joysticks to send keys. (CTRL+C to exit)\n")
    while True:
        (x1,y1,_),(x2,y2,_) = read_joystick_lines()
        if x1 is None or x2 is None:
            continue

        dx1, dy1 = x1-cx1, y1-cy1
        dx2, dy2 = x2-cx2, y2-cy2

        d1 = resolve_direction(dx1, dy1, thr1)
        d2 = resolve_direction(dx2, dy2, thr2)

        keys = set()
        if d1 in KEY_MAP_1: keys.add(KEY_MAP_1[d1])
        if d2 in KEY_MAP_2: keys.add(KEY_MAP_2[d2])

        press_keys(keys)
        time.sleep(0.05)

if __name__ == "__main__":
    print("Mode:\n 1) Calibrate\n 2) Controller")
    mode = input("Enter 1 or 2: ").strip()
    connect_serial()
    if not ser:
        print("[!] Cannot open serial port. Exiting.")
        exit(1)

    if mode == '1':
        calibrate()
    else:
        controller_mode()
