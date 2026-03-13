from mq2 import MQ2
from machine import Pin, I2C
import bme680
import time
import json
import bluetooth
import struct

# --- Initialize Onboard LED ---
led = Pin('LED', Pin.OUT)
led.value(0)

# --- Sensor Initialization ---
i2c = I2C(0, scl=Pin(5), sda=Pin(4))
bme = bme680.BME680_I2C(i2c=i2c, address=0x76)

pin = 26
sensor = MQ2(pinData=pin, baseVoltage=3.3)
print("Calibrating MQ2...")
sensor.calibrate()
print("Calibration completed.")

# --- BLE Setup ---
ble = bluetooth.BLE()
ble.active(True)

# Define Custom UUIDs for our Sensor Service
SERVICE_UUID = bluetooth.UUID('12345678-1234-5678-1234-56789abcdef0')
CHAR_UUID = bluetooth.UUID('12345678-1234-5678-1234-56789abcdef1')

# Register the service and characteristic (Make it READable)
sensor_service = (SERVICE_UUID, ((CHAR_UUID, bluetooth.FLAG_READ),))
services = (sensor_service,)
((char_handle,),) = ble.gatts_register_services(services)

# Helper function to format the BLE advertisement name
def advertise(name="Pico_Sensors"):
    name_bytes = bytes(name, 'utf-8')
    payload = struct.pack("BB", len(name_bytes) + 1, 0x09) + name_bytes
    ble.gap_advertise(100000, adv_data=payload)
    print(f"Advertising as {name}...")

advertise()

# Blink 6 times to show BLE is ready
for _ in range(6):
    led.value(1)
    time.sleep(0.3)
    led.value(0)
    time.sleep(0.3)

# --- Main Loop ---
print("Waiting for computer to read data...")
while True:
    # 1. Read the sensors
    data_payload = {
        "smoke": round(sensor.readSmoke(), 1),
        "lpg": round(sensor.readLPG(), 1),
        "methane": round(sensor.readMethane(), 1),
        "hydrogen": round(sensor.readHydrogen(), 1),
        "temperature_c": round(bme.temperature, 1),
        "humidity_pct": round(bme.humidity, 1),
        "pressure_hpa": round(bme.pressure, 1),
        "gas_res_ohms": bme.gas
    }
    
    # 2. Convert to JSON string and encode to bytes
    # (Kept keys short to save byte space over Bluetooth)
    json_bytes = json.dumps(data_payload).encode('utf-8')
    
    # 3. Update the BLE characteristic with the fresh data
    ble.gatts_write(char_handle, json_bytes)
    
    # Quick blink to show data was updated internally
    led.value(1)
    time.sleep(0.3)
    led.value(0)
    
    # Wait a bit before taking the next reading
    time.sleep(5)