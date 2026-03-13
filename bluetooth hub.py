import asyncio
from bleak import BleakScanner, BleakClient
import json
import os

# This must match the Characteristic UUID from your Pico code!
CHAR_UUID = "12345678-1234-5678-1234-56789abcdef1"
PICO_NAME = "Pico_Sensors"

async def fetch_bluetooth_data():
    print("Scanning for Pico W...")
    devices = await BleakScanner.discover(timeout=15.0)
    
    pico_device = None
    for d in devices:
        if d.name == PICO_NAME:
            pico_device = d
            break
            
    if not pico_device:
        print("Could not find the Pico. Is it powered on and in range?")
        return

    print(f"Found {PICO_NAME} at {pico_device.address}. Connecting...")
    
    try:
        # Connect to the Pico
        async with BleakClient(pico_device) as client:
            print("Connected! Reading sensor data...")
            
            # Read the byte data from the characteristic
            byte_data = await client.read_gatt_char(CHAR_UUID)
            
            # Decode the bytes back into a JSON string, then into a dictionary
            json_str = byte_data.decode('utf-8')
            data = json.loads(json_str)
            
            print("\n--- Live Bluetooth Data ---")
            for key, value in data.items():
                print(f"{key.capitalize()}: {value}")
            print("---------------------------\n")
            file_path = os.path.join(os.path.dirname(__file__), 'data.json')
            with open(file_path, 'w') as f:
                data['timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
                json.dump(data, f)
                
            
    except Exception as e:
        print(data)
        print(f"Error connecting or reading data: {e}")

# Bleak is asynchronous, so we use asyncio to run the loop
if __name__ == "__main__":
    while True:
        asyncio.run(fetch_bluetooth_data())
        import time
        time.sleep(30) # Wait 30 seconds before asking for data again