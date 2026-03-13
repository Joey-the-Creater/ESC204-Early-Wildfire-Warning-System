# ESC204-Early-Wildfire-Warning-System 


This project is a comprehensive Internet of Things (IoT) Fire Detection and Alert System. It uses a Raspberry Pi Pico W connected to environmental and gas sensors to monitor local conditions. The data is transmitted to a host computer (via Bluetooth Low Energy or Wi-Fi), which then runs a Flask web dashboard. If hazardous conditions (high heat, low humidity, smoke, or combustible gases) are detected, the system assesses the risk and automatically sends emergency SMS and Email alerts to subscribed users.

---

## ✨ Features

* **Multi-Sensor Environmental Monitoring:** Tracks Temperature, Humidity, Pressure, Air Quality (BME680), and specific gases like Smoke, LPG, Methane, and Hydrogen (MQ2).
* **Dual Connectivity Modes:** The Pico W can transmit data to the host hub via Bluetooth Low Energy (BLE) or a local Wi-Fi HTTP server.
* **Intelligent Risk Assessment:** Evaluates sensor data using a scoring system to determine the fire/leak risk level (LOW, MODERATE, CRITICAL).
* **Live Web Dashboard:** A user-friendly Flask interface to view real-time sensor data and the current risk level.
* **Emergency Alert System:** Uses Twilio and SMTP to blast SMS and Email warnings to registered users if the risk becomes CRITICAL.
* **Public Access via Ngrok:** The local Flask server is exposed to the internet via Ngrok, allowing remote users to register for alerts and view the dashboard.
* **Two-Way SMS:** Subscribers can text the Twilio number to instantly receive the latest sensor readings.

---

## 🛠️ Hardware Requirements

1. **Raspberry Pi Pico W** (Microcontroller)
2. **BME680 Sensor** (Temperature, Humidity, Pressure, Gas Resistance)
3. **MQ2 Gas Sensor** (Smoke, LPG, Methane, Hydrogen)
4. Jumper wires & Breadboard
5. Host Computer (Windows, macOS, or Linux) to run the web server and data hub.

---

## 📁 Project Structure

### MicroPython Files (Upload to Pico W)
* `wifi.py`: Main scipt for the Pico in Wifi. Must change wifi setting SSID and Password.
```ini
SSID = YOUR_WIFI_NAME
PASSWORD = YOUR_WIFI_PASSWORD
```
* `bluetooth peripheral.py`: Main script for the Pico in Bluetooth.
* `bme680.py`: Driver library for the BME680 sensor.
* `basemq.py` & `mq2.py`: Driver libraries for the MQ2 gas sensor to calculate specific gas concentrations.

### Python Files (Run on Host Computer)

* `web service.py`: The Flask web application. It reads `data.json`, serves the HTML dashboard, evaluates risk, manages subscribers, and handles Twilio/Email alerts.
* `bluetooth hub.py`: Connects to the Pico W via BLE, reads the sensor data, and updates `data.json`.
* `wifi server.py`: An alternative to the BLE hub. Fetches data directly from the Pico W over Wi-Fi and updates `data.json`.
* `data.json`: Local storage file updated by the hub/server with the latest sensor readings.
* `subscribers.json`: Stores the names, emails, and phone numbers of registered users.
* `.env`: Stores sensitive environment variables (API keys, passwords, paths).

---

## 🚀 Setup & Installation
### 0. Registration

Ensure you install NGrok on your computer. You need to register for a number from Twilio.

### 1. Host Computer Environment

Ensure you have Python 3.8+ installed. Install the required dependencies or from `requirements.py`:

```bash
pip install Flask twilio pyngrok python-dotenv bleak requests

```

### 2. Configure Environment Variables

Create a `.env` file in the same directory as your host scripts (or use the provided one) and update it with your credentials:

```ini
TWILIO_SID=your_twilio_account_sid
TWILIO_AUTH=your_twilio_auth_token
TWILIO_PHONE=your_twilio_phone_number

EMAIL_ADDRESS=your_sender_email@gmail.com
EMAIL_PASSWORD=your_app_specific_password

NGROK=C:\path\to\your\ngrok.exe
```

*Note: For Gmail, you will need to generate an "App Password" in your Google Account security settings.*

### 3. Pico W Setup

1. Flash your Raspberry Pi Pico W with the latest MicroPython firmware.
2. Using Thonny (or your preferred IDE), upload `wifi.py`, `bluetooth peripheral.py`, `bme680.py`, `basemq.py`, and `mq2.py` to the Pico.
3. Rename `bluetooth peripheral.py` to `main.py` on the Pico if you want it to run automatically on boot.
4. Wire your sensors:
* **BME680:** I2C0 (SCL -> Pin 5, SDA -> Pin 4)
* **MQ2:** Analog Output -> Pin 26 (ADC)



---

## 💻 Usage Instructions

You will need to run two scripts concurrently on your host computer: the Data Hub and the Web Service.

### Step 1: Start the Data Hub

Choose either Bluetooth (`bluetooth peripheral.py`) or Wi-Fi (`wifi.py`) to receive data from your Pico.

**Option A (Bluetooth):** Ensure your Pico is powered on and advertising.

```bash
python "bluetooth hub.py"

```

**Option B (Wi-Fi):** If using Wi-Fi, ensure your Pico is running a corresponding web server script (not fully detailed in the uploaded BLE peripheral file, but supported by the host).

```bash
python "wifi server.py"

```

*This script will continuously poll the Pico and update `data.json`.*

### Step 2: Start the Web Service

In a new terminal window, start the Flask dashboard and alert system:

```bash
python "web service.py"

```

When this runs, Ngrok will generate a public URL. Look for the following output in your terminal:

```text
************************************************************
🌐 VIEW DASHBOARD & REGISTER: https://<random-string>.ngrok.app
🚨 TRIGGER A TEST ALERT:      https://<random-string>.ngrok.app/test_fire
************************************************************

```

### Step 3: Monitor & Alert

1. Open the Ngrok URL in your browser to view the live dashboard.
2. Register yourself in the "Get Alerts" section.
3. If the risk level hits "CRITICAL" (Score >= 5 based on high temps, low humidity, or elevated gases), the system will automatically dispatch emails and texts to everyone in `subscribers.json`.
4. You can manually test the alerts by visiting the `/test_fire` endpoint.