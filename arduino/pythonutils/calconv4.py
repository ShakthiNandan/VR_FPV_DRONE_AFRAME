import serial
import json
import time
import re
import threading
import asyncio
import websockets
from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key
import ssl
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain(certfile='cert.pem', keyfile='key.pem')

# CONFIG
serial_port       = 'COM10'
baud_rate         = 115200
calibration_file1 = 'calibration_data_joy1.json'
calibration_file2 = 'calibration_data_joy2.json'
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

def read_joystick_lines():
    """Reads lines like 'Joystick 1 -> X: 1909 | Y: 0 | Direction: Up' and returns values for both joysticks."""
    try:
        line1 = ser.readline().decode('utf-8', errors='replace').strip()
        line2 = ser.readline().decode('utf-8', errors='replace').strip()
        
        joy1_x, joy1_y, joy1_dir = None, None, None
        joy2_x, joy2_y, joy2_dir = None, None, None
        
        # Parse joystick 1
        if "Joystick 1" in line1:
            x_m = re.search(r'X:\s*(-?\d+)', line1)
            y_m = re.search(r'Y:\s*(-?\d+)', line1)
            dir_m = re.search(r'Direction:\s*(\w+)', line1)
            if x_m and y_m and dir_m:
                joy1_x = int(x_m.group(1))
                joy1_y = int(y_m.group(1))
                joy1_dir = dir_m.group(1)
        elif "Joystick 1" in line2:
            x_m = re.search(r'X:\s*(-?\d+)', line2)
            y_m = re.search(r'Y:\s*(-?\d+)', line2)
            dir_m = re.search(r'Direction:\s*(\w+)', line2)
            if x_m and y_m and dir_m:
                joy1_x = int(x_m.group(1))
                joy1_y = int(y_m.group(1))
                joy1_dir = dir_m.group(1)
        
        # Parse joystick 2
        if "Joystick 2" in line1:
            x_m = re.search(r'X:\s*(-?\d+)', line1)
            y_m = re.search(r'Y:\s*(-?\d+)', line1)
            dir_m = re.search(r'Direction:\s*(\w+)', line1)
            if x_m and y_m and dir_m:
                joy2_x = int(x_m.group(1))
                joy2_y = int(y_m.group(1))
                joy2_dir = dir_m.group(1)
        elif "Joystick 2" in line2:
            x_m = re.search(r'X:\s*(-?\d+)', line2)
            y_m = re.search(r'Y:\s*(-?\d+)', line2)
            dir_m = re.search(r'Direction:\s*(\w+)', line2)
            if x_m and y_m and dir_m:
                joy2_x = int(x_m.group(1))
                joy2_y = int(y_m.group(1))
                joy2_dir = dir_m.group(1)
                
        return (joy1_x, joy1_y, joy1_dir), (joy2_x, joy2_y, joy2_dir)
    except Exception as e:
        #print(f"Error reading joystick data: {e}")
        pass
    return (None, None, None), (None, None, None)

def calibrate_joystick(joystick_num, calibration_file):
    """Calibrate a specific joystick."""
    calibration_data = {}
    positions = ['Center','Up','Down','Left','Right']
    print(f"\n--- Calibrating Joystick {joystick_num} ---")
    for pos in positions:
        input(f"\nMove Joystick {joystick_num} to {pos}. Press ENTER when ready…")
        samples = []
        start = time.time()
        while time.time() - start < 2:
            (joy1_x, joy1_y, _), (joy2_x, joy2_y, _) = read_joystick_lines()
            
            # Use data from the appropriate joystick
            x, y = None, None
            if joystick_num == 1 and joy1_x is not None and joy1_y is not None:
                x, y = joy1_x, joy1_y
            elif joystick_num == 2 and joy2_x is not None and joy2_y is not None:
                x, y = joy2_x, joy2_y
                
            if x is not None and y is not None:
                samples.append((x, y))
            time.sleep(0.05)
            
        if samples:
            avg_x = sum(s[0] for s in samples)//len(samples)
            avg_y = sum(s[1] for s in samples)//len(samples)
            calibration_data[pos.lower()] = {'x':avg_x,'y':avg_y}
            print(f"{pos} → X={avg_x}, Y={avg_y}")
        else:
            print(f"No data for {pos}")
    
    with open(calibration_file, 'w') as f:
        json.dump(calibration_data, f, indent=4)
    print(f"Calibration saved to {calibration_file}")

def calibrate():
    """Calibrate both joysticks."""
    print("Which joystick(s) would you like to calibrate?")
    print("1. Joystick 1 only")
    print("2. Joystick 2 only")
    print("3. Both joysticks")
    choice = input("Enter 1, 2, or 3: ").strip()
    
    if choice == '1' or choice == '3':
        calibrate_joystick(1, calibration_file1)
    
    if choice == '2' or choice == '3':
        calibrate_joystick(2, calibration_file2)

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
        server = await websockets.serve(websocket_handler, '0.0.0.0', websocket_port,ssl=ssl_context)
        print(f"WebSocket server running on wss://0.0.0.0:{websocket_port}")
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

def control():
    """Control using both joysticks with keyboard press as default mode."""
    try:
        with open(calibration_file1, 'r') as f:
            calib1 = json.load(f)
        with open(calibration_file2, 'r') as f:
            calib2 = json.load(f)
    except Exception as e:
        print(f"Calibration error: {e}")
        print("Please run calibration first.")
        return

    # Use the calibration data for joystick centering
    cx1 = calib1['center']['x']
    cy1 = calib1['center']['y']
    cx2 = calib2['center']['x']
    cy2 = calib2['center']['y']
    
    print("\nController started with keyboard press mode! CTRL+C to exit.")
    
    while True:
        (joy1_x, joy1_y, joy1_dir), (joy2_x, joy2_y, joy2_dir) = read_joystick_lines()
        
        # Skip if either joystick data is missing
        if joy1_x is None or joy2_x is None:
            continue

        # Calculate displacement from center for joystick 1
        dx1 = joy1_x - cx1
        dy1 = joy1_y - cy1
        
        # Calculate displacement from center for joystick 2
        dx2 = joy2_x - cx2
        dy2 = joy2_y - cy2

        # Apply deadzone
        if abs(dx1) < 15: dx1 = 0
        if abs(dy1) < 15: dy1 = 0
        if abs(dx2) < 15: dx2 = 0
        if abs(dy2) < 15: dy2 = 0
        
        # Compute directions if not provided in the input
        if joy1_dir is None:
            joy1_dir = 'center'
            if dy1 < -50: joy1_dir = 'up'
            elif dy1 > 50: joy1_dir = 'down'
            if dx1 < -50:
                joy1_dir = 'left' if joy1_dir == 'center' else joy1_dir + '-left'
            elif dx1 > 50:
                joy1_dir = 'right' if joy1_dir == 'center' else joy1_dir + '-right'
        
        if joy2_dir is None:
            joy2_dir = 'center'
            if dy2 < -50: joy2_dir = 'up'
            elif dy2 > 50: joy2_dir = 'down'
            if dx2 < -50:
                joy2_dir = 'left' if joy2_dir == 'center' else joy2_dir + '-left'
            elif dx2 > 50:
                joy2_dir = 'right' if joy2_dir == 'center' else joy2_dir + '-right'

        # Create payload with both joysticks data
        payload = {
            'mode': '2',  # Keyboard Press/Hold mode by default
            'joystick1': {
                'dx': dx1,
                'dy': dy1,
                'direction': joy1_dir
            },
            'joystick2': {
                'dx': dx2,
                'dy': dy2,
                'direction': joy2_dir
            }
        }

        # Broadcast data to WebSocket clients
        broadcast_to_clients(payload)
        
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

    # If choice is 2 or anything else, proceed with controller mode
    # Start WebSocket server in background
    t = threading.Thread(target=start_ws_server, daemon=True)
    t.start()

    # Enter control loop (broadcasting data) with keyboard press as default
    control()
