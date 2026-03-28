import requests
import time
import json
import os

# Replace this with the IP address your Pico printed to the console!
PICO_IP = "http://192.168.2.111" 

def fetch_sensor_data():
    try:
        print(f"Sending request to {PICO_IP}...")
        
        # Send the GET request to the Pico
        response = requests.get(PICO_IP, timeout=15)
        
        # If the request was successful (HTTP 200)
        if response.status_code == 200:

            data = response.json()
            file_path = os.path.join(os.path.dirname(__file__), 'data.json')
            # Add the timestamp immediately so it is included in the printout
            data['timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
            with open(file_path, 'w') as f:
                json.dump(data, f)
            print("\n--- Sensor Data Received ---")
            print(f"Temperature: {data['temperature_c']} C")
            print(f"Humidity:    {data['humidity_pct']} %")
            print(f"Pressure:    {data['pressure_hpa']} hPa")
            print(f"VOC Gas Res: {data['gas_res_ohms']} Ohms")
            print(f"Smoke:       {data['smoke']}")
            print(f"LPG:         {data['lpg']}")
            print(f"Methane:     {data['methane']}")
            print(f"Hydrogen:    {data['hydrogen']}")
            print("----------------------------\n")
        else:
            print(f"Failed to get data. Status code: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Pico: {e}")

# Example usage: Request data every 10 seconds from the computer side
if __name__ == "__main__":
    while True:
        fetch_sensor_data()
        time.sleep(10) # Control the polling rate from the master!