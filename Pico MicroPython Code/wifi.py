from mq2 import MQ2
import utime
from machine import Pin, I2C
import bme680
import time
import network
import socket
import json

led = Pin('LED', Pin.OUT)
led.value(0)

# --- 1. Wi-Fi Setup ---
SSID = 'BELL585'
PASSWORD = 'AA567C96F397'

#SSID = "Joey's iPhone"
#PASSWORD = 'kbnpass123'

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASSWORD)

print("Connecting to Wi-Fi...")
while not wlan.isconnected():
    time.sleep(1)
    print(".", end="")
    
# Get and print the IP address (You'll need this for your computer script!)
ip_address = wlan.ifconfig()[0]
print("\nConnected! Pico W IP Address:", ip_address)

print("Wi-Fi connected: Lighting LED for 2 seconds...")
# Blink 6 times to show BLE is ready
for _ in range(6):
    led.value(1)
    time.sleep(0.2)
    led.value(0)
    time.sleep(0.2)

# --- 2. Sensor Initialization ---
# Initialize I2C0 
i2c = I2C(1, scl=Pin(15), sda=Pin(14))
bme = bme680.BME680_I2C(i2c=i2c, address=0x76)

# Initialize MQ2
pin = 26
sensor = MQ2(pinData=pin, baseVoltage=3.3)

print("Calibrating MQ2...")
sensor.calibrate()
print("Calibration completed. Base resistance: {0}".format(sensor._ro))

# --- 3. Set up the Socket Server ---
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(addr)
s.listen(1)
print('Listening for computer requests on port 80...')

# --- 4. Main Server Loop ---
while True:
    try:
        # Wait for a connection from the computer
        cl, addr = s.accept()
        print('Request received from:', addr)
        
        # Read the incoming request (we can ignore the contents for a simple trigger)
        request = cl.recv(1024)
        
        # Read all sensor data ON DEMAND
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
        
        # Convert dictionary to a JSON string
        json_data = json.dumps(data_payload)
        
        # Build the HTTP response
        response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n" + json_data
        
        # Send data and close connection
        cl.sendall(response.encode('utf-8'))
        cl.close()
        print("Data sent successfully.\n")
        led.value(1)
        time.sleep(0.2) # 200 milliseconds is a good, snappy blink
        led.value(0)
        time.sleep(0.2)
        
    except OSError as e:
        cl.close()
        print('Connection closed due to error:', e)
