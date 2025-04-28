import serial
import json
import time
import re
import threading
import asyncio
import websockets
from pynput.mouse import Controller as MouseController
from pynput.keyboard import Controller as KeyboardController

# CONFIG
serial_port       = 'COM10'
baud_rate         = 115200
calibration_file1 = 'calibration_data_joy1.json'
calibration_file2 = 'calibration_data_joy2.json'
websocket_port    = 8765

# Globals
ser               = None
mouse             = MouseController()
keyboard          = KeyboardController()
connected_clients = set()
ws_loop           = None

def connect_serial():
    global ser
    try:
        ser = serial.Serial(serial_port, baud_rate, timeout=1)
        print(f"Connected to {serial_port}")
    except Exception as e:
        print(f"Serial connection failed: {e}")
        ser = None

def read_joystick_lines():
    try:
        line1 = ser.readline().decode(errors='replace').strip()
        line2 = ser.readline().decode(errors='replace').strip()
    except:
        return (None, None, None), (None, None, None)

    joy1 = joy2 = (None, None, None)
    for line in (line1, line2):
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
        input(f"Move joystick {num} to {pos}. Press ENTER.")
        samples, t0 = [], time.time()
        while time.time() - t0 < 2:
            (x1,y1,_),(x2,y2,_) = read_joystick_lines()
            x,y = (x1,y1) if num==1 else (x2,y2)
            if x is not None: samples.append((x,y))
            time.sleep(0.05)
        if samples:
            avg_x = sum(s[0] for s in samples)//len(samples)
            avg_y = sum(s[1] for s in samples)//len(samples)
            data[pos.lower()] = {'x':avg_x,'y':avg_y}
            print(f"{pos}: X={avg_x}, Y={avg_y}")
        else:
            print(f"No samples for {pos}")
    with open(filename,'w') as f:
        json.dump(data, f, indent=4)
    print(f"Saved calibration → {filename}")

def calibrate():
    print("1) Joystick 1\n2) Joystick 2\n3) Both")
    c = input("Choose: ").strip()
    if c in ('1','3'): calibrate_joystick(1, calibration_file1)
    if c in ('2','3'): calibrate_joystick(2, calibration_file2)

async def websocket_handler(ws):
    print("WS client connected")
    connected_clients.add(ws)
    try:
        await ws.wait_closed()
    finally:
        connected_clients.remove(ws)
        print("WS client disconnected")

def start_ws_server():
    global ws_loop
    ws_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(ws_loop)

    async def runner():
        await websockets.serve(
            websocket_handler,
            '0.0.0.0', websocket_port,
            origins=None     # disable origin checks in dev
        )
        print(f"WS server listening on ws://0.0.0.0:{websocket_port}")
        await asyncio.Future()  # run forever

    ws_loop.run_until_complete(runner())
    ws_loop.run_forever()

def broadcast_to_clients(msg_obj):
    if not connected_clients:
        return
    msg = json.dumps(msg_obj)
    async def _bcast():
        await asyncio.gather(*(ws.send(msg) for ws in connected_clients))
    asyncio.run_coroutine_threadsafe(_bcast(), ws_loop)

def control():
    try:
        c1 = json.load(open(calibration_file1))
        c2 = json.load(open(calibration_file2))
    except:
        print("Missing calibration. Run mode 1 first.")
        return

    cx1, cy1 = c1['center']['x'], c1['center']['y']
    cx2, cy2 = c2['center']['x'], c2['center']['y']
    print("Controller started (CTRL+C to exit)")

    while True:
        (x1,y1,d1),(x2,y2,d2) = read_joystick_lines()
        if x1 is None or x2 is None:
            continue

        dx1, dy1 = x1-cx1, y1-cy1
        dx2, dy2 = x2-cx2, y2-cy2
        for v in (dx1,dy1,dx2,dy2):
            if abs(v) < 15: v = 0

        def resolve(d, dx, dy):
            if d: return d
            dir_ = 'center'
            if dy < -50: dir_ = 'up'
            elif dy > 50: dir_ = 'down'
            if dx < -50: dir_ += '-left' if dir_!='center' else 'left'
            elif dx > 50: dir_ += '-right' if dir_!='center' else 'right'
            return dir_

        d1 = resolve(d1, dx1, dy1)
        d2 = resolve(d2, dx2, dy2)

        payload = {
            'mode': '2',
            'joystick1': {'dx':dx1,'dy':dy1,'direction':d1},
            'joystick2': {'dx':dx2,'dy':dy2,'direction':d2},
        }
        broadcast_to_clients(payload)
        time.sleep(0.05)

if __name__ == "__main__":
    print("Mode:\n1) Calibrate\n2) Controller")
    choice = input("Enter 1 or 2: ").strip()
    connect_serial()
    if not ser:
        print("Cannot open serial port. Exiting.")
        exit(1)

    if choice == '1':
        calibrate()
        exit(0)

    threading.Thread(target=start_ws_server, daemon=True).start()
    control()
