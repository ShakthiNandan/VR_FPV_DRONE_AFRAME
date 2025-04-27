import serial
import json
import time
import re
import threading
import asyncio
import websockets
from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key

# CONFIG
serial_port       = 'COM10'
baud_rate         = 115200
calibration_file  = 'calibration_data.json'
websocket_port    = 8765  # port for WebSocket clients

# Globals for WebSocket
connected_clients = set()
ws_loop          = None  # will hold the asyncio loop

# Initialize serial + controllers
ser    = None
mouse  = MouseController()
keyboard = KeyboardController()

def connect_serial():
    global ser
    try:
        ser = serial.Serial(serial_port, baud_rate, timeout=1)
        print(f"Connected to {serial_port}")
    except Exception as e:
        print(f"Failed to connect to serial port: {e}")
        ser = None

def read_joystick_line():
    """Reads a line like 'X: 1234 | Y: 2345' and returns (x,y)."""
    try:
        line = ser.readline().decode('utf-8', errors='replace').strip()
        x_m = re.search(r'X:\s*(-?\d+)', line)
        y_m = re.search(r'Y:\s*(-?\d+)', line)
        if x_m and y_m:
            return int(x_m.group(1)), int(y_m.group(1))
    except Exception:
        pass
    return None, None

def calibrate():
    calibration_data = {}
    positions = ['Center','Up','Down','Left','Right']
    for pos in positions:
        input(f"\nMove joystick to {pos}. Press ENTER when ready…")
        samples = []
        start = time.time()
        while time.time() - start < 2:
            x,y = read_joystick_line()
            if x is not None:
                samples.append((x,y))
            time.sleep(0.05)
        if samples:
            avg_x = sum(s[0] for s in samples)//len(samples)
            avg_y = sum(s[1] for s in samples)//len(samples)
            calibration_data[pos.lower()] = {'x':avg_x,'y':avg_y}
            print(f"{pos} → X={avg_x}, Y={avg_y}")
        else:
            print(f"No data for {pos}")
    with open(calibration_file,'w') as f:
        json.dump(calibration_data,f,indent=4)
    print(f"Calibration saved to {calibration_file}")

# ————— WebSocket server setup —————

async def websocket_handler(ws, path=None):
    print("WS Client connected")
    connected_clients.add(ws)
    try:
        await ws.wait_closed()
    finally:
        print("WS Client disconnected")
        connected_clients.remove(ws)

def start_ws_server():
    global ws_loop
    # 1) Create a brand-new event loop in this thread
    ws_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(ws_loop)

    # 2) Create an async function to setup and run the server
    async def start_server():
        server = await websockets.serve(websocket_handler, '0.0.0.0', websocket_port)
        print(f"WebSocket server running on ws://0.0.0.0:{websocket_port}")
        # Keep the server running indefinitely
        await asyncio.Future()  # This future never completes, keeping the server alive
    
    # 3) Run the async function in the event loop
    try:
        ws_loop.run_until_complete(start_server())
    except KeyboardInterrupt:
        pass
    finally:
        ws_loop.close()

def broadcast_to_clients(payload: dict):
    """Schedules a broadcast of JSON payload to all WS clients."""
    if not connected_clients:
        return
    msg = json.dumps(payload)
    async def _bcast():
        await asyncio.gather(*(ws.send(msg) for ws in connected_clients))
    asyncio.run_coroutine_threadsafe(_bcast(), ws_loop)

# ————— Controller Modes (now broadcasting over WS instead of local input) —————

def control(mode):
    try:
        with open(calibration_file,'r') as f:
            calib = json.load(f)
    except Exception as e:
        print("Calibration error:", e)
        return

    cx = calib['center']['x']
    cy = calib['center']['y']
    print("\nController started! CTRL+C to exit.")

    last_time = 0
    interval  = 0.2

    while True:
        x,y = read_joystick_line()
        if x is None: 
            continue

        dx = x - cx
        dy = (y - cy)   # invert Y

        # deadzone
        if abs(dx) < 15: dx = 0
        if abs(dy) < 15: dy = 0

        # compute direction label
        direction = 'center'
        if dy < -50: direction = 'up'
        elif dy > 50: direction = 'down'
        if dx < -50:
            direction = 'left' if direction=='center' else direction+'-left'
        elif dx > 50:
            direction = 'right' if direction=='center' else direction+'-right'

        payload = {
            'mode': mode,
            'dx': dx,
            'dy': dy,
            'direction': direction
        }

        # Broadcast every loop
        broadcast_to_clients(payload)

        # Also keep original mouse/keyboard if you want (optional):
        # if mode=='1': mouse.move(int(dx*0.02), int(dy*0.02))
        # elif mode=='2': … etc.  

        time.sleep(0.05)

# ————— Main —————

if __name__=="__main__":
    print("Select Mode:\n1. Calibrate\n2. Controller")
    choice = input("Enter 1 or 2: ").strip()

    connect_serial()
    if not ser:
        print("Serial failed. Exiting.")
        exit(1)

    if choice=='1':
        calibrate()
        exit(0)

    # choice == '2'
    print("\nChoose control type (still sent over WS):")
    print("1. Mouse Control\n2. Keyboard Press/Hold\n3. Mouse Rapid Click\n4. Keyboard Rapid Press")
    ctrl_mode = input("Enter 1–4: ").strip()

    # Start WebSocket server in background
    t = threading.Thread(target=start_ws_server, daemon=True)
    t.start()

    # Enter control loop (broadcasting data)
    control(ctrl_mode)
