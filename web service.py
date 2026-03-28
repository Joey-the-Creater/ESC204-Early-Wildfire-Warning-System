from flask import Flask, request, Response, render_template_string, redirect, url_for
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from pyngrok import ngrok, conf 
import smtplib
import json
import os
import time
from collections import deque
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file
app = Flask(__name__)

TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# File to store our registered users
SUBSCRIBERS_FILE = os.path.join(os.path.dirname(__file__), 'subscribers.json')

# --- STATEFUL WILDFIRE MONITOR CLASS ---
class WildfireMonitor:
    def __init__(self, window_size=5):
        self.history = deque(maxlen=window_size)
        
        # --- NEW: Track the last processed file and the last result ---
        self.last_timestamp = None
        self.last_result = {
            "level": "UNKNOWN", 
            "color": "#777", 
            "message": "Waiting for initial sensor data..."
        }

    def assess_risk(self, data):
        if "error" in data:
            return {"level": "UNKNOWN", "color": "#777", "message": "Cannot assess risk. Sensor data unavailable."}

        # --- NEW: The Staleness Gate ---
        current_timestamp = data.get("timestamp")
        
        # If the timestamp exists and matches the last one we saw, the file hasn't updated.
        # Just return the cached result without polluting the history deque.
        if current_timestamp and current_timestamp == self.last_timestamp:
            return self.last_result

        try:
            current_temp = float(data.get("temperature_c", 0) or 0)
            current_hum = float(data.get("humidity_pct", 100) or 100)
            current_smoke = float(data.get("smoke", 0) or 0)
            current_methane = float(data.get("methane", 0) or 0)
            current_hydrogen = float(data.get("hydrogen", 0) or 0)
        except ValueError:
            return {"level": "ERROR", "color": "#777", "message": "Invalid data format."}

        # Update our tracker to the new file's timestamp
        self.last_timestamp = current_timestamp

        # Save current reading to history
        current_reading = {
            "time": time.time(), # We still use system time here to gauge real-world elapsed time
            "temp": current_temp,
            "hum": current_hum,
            "smoke": current_smoke
        }
        self.history.append(current_reading)
        environmental_score = 0
        chemical_score = 0
        reasons = []

        # 1. ENVIRONMENTAL METRICS
        if current_temp > 50:
            environmental_score += 2
            reasons.append("extreme heat")
        elif current_temp > 45:
            environmental_score += 1
            reasons.append("elevated temperature")
        elif current_temp > 55:
            environmental_score += 4
            reasons.append("dangerous heat levels")
        elif current_temp > 60:
            environmental_score += 7
            reasons.append("critical heat levels")

        if current_hum < 15:
            environmental_score += 2
            reasons.append("critically dry")
        elif current_hum < 25:
            environmental_score += 1
            reasons.append("very low humidity")

        # 2. CHEMICAL METRICS
        if current_smoke > 400:
            chemical_score += 2
            reasons.append("severe smoke detected")
        elif current_smoke > 200:
            chemical_score += 1
            reasons.append("elevated smoke")
        elif current_smoke > 600:
            chemical_score += 4
            reasons.append("dangerous smoke levels")

        # 3. RATE OF CHANGE (RoC)
        if len(self.history) > 1:
            oldest = self.history[0]
            time_diff_mins = (current_reading["time"] - oldest["time"]) / 60.0
            
            if time_diff_mins > 0:
                if (current_temp - oldest["temp"]) / time_diff_mins > 2.0:
                    environmental_score += 2
                    reasons.append("rapid temperature spike")
                
                if (current_hum - oldest["hum"]) / time_diff_mins < -5.0:
                    environmental_score += 1
                    reasons.append("rapid humidity drop")

                if (current_smoke - oldest["smoke"]) / time_diff_mins > 50.0:
                    chemical_score += 1
                    reasons.append("rapid smoke accumulation")

        # 4. GATING & SCORING
        total_score = environmental_score + chemical_score

        if chemical_score < 2:
            total_score = min(total_score, 3)

        # 5. ALERT ROUTING
        if total_score >= 7:
            level = "CRITICAL"
            color = "#d9534f"
            message = "Extreme danger! " + ", ".join(reasons) + ". Evacuate immediately."
            send_fire_alerts()  # Trigger alerts
        elif total_score >= 4:
            level = "MODERATE"
            color = "#f0ad4e"
            message = "Warning: " + ", ".join(reasons) + ". Increase monitoring."
        else:
            level = "LOW"
            color = "#5cb85c"
            message = "Conditions are normal." if total_score == 0 else "Elevated metrics: " + ", ".join(reasons)

        self.last_result = {"level": level, "color": color, "message": message}
        return self.last_result

# Instantiate our monitor globally so it remembers history across requests
fire_monitor = WildfireMonitor(window_size=5)

# --- HTML TEMPLATE ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Fire Detection System</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #f4f4f9; color: #333; padding: 30px; }
        .container { display: flex; gap: 20px; justify-content: center; flex-wrap: wrap; align-items: flex-start; }
        .card { background: white; width: 350px; padding: 30px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        h2 { color: #d9534f; border-bottom: 2px solid #eee; padding-bottom: 10px;}
        input[type="text"], input[type="email"] { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 5px; box-sizing: border-box;}
        button { background-color: #d9534f; color: white; padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; width: 100%; font-size: 1.1em;}
        button:hover { background-color: #c9302c; }
        .risk-card { display: flex; width: 350px; flex-direction: column; justify-content: space-between; }
    </style>
</head>
<body>
    <h1 style="text-align: center; color: #333;">🔥 ESC204 Fire Alert System</h1>
    
    <div class="container">

        <div class="card">
            <h2>Live Sensor Data</h2>
            {% if data.error %}
                <p style="color: red;">{{ data.error }}</p>
            {% else %}
                {% for key, value in data.items() %}
                    {% if key != 'timestamp' %}
                        <p><strong>{{ key | replace('_', ' ') | title }}:</strong> <span style="float: right;">{{ value }}</span></p>
                    {% endif %}
                {% endfor %}
                <p style="font-size: 0.8em; color: #777; text-align: center; margin-top: 20px;">Last updated: {{ data.get('timestamp', 'Unknown') }}</p>
            {% endif %}
        </div>

        <div class="card">
            <h2>Get Alerts</h2>
            <p style="font-size: 0.9em; color: #555;">Register to receive SMS and Email alerts if fire or smoke is detected.</p>
            
            {% if message %}
                <div style="background-color: #dff0d8; color: #3c763d; padding: 10px; border-radius: 5px; margin-bottom: 15px;">
                    {{ message }}
                </div>
            {% endif %}

            <form action="/register" method="POST">
                <label>Name:</label>
                <input type="text" name="name" required placeholder="John Doe">
                
                <label>Phone Number:</label>
                <input type="text" name="phone" required placeholder="+16475071400">
                
                <label>Email Address:</label>
                <input type="email" name="email" required placeholder="john@example.com">
                
                <button type="submit">Subscribe to Alerts</button>
            </form>
        </div>
        <div class="card risk-card" style="border-top: 6px solid {{ risk.color }}; text-align: center;">
            <h2 style="color: {{ risk.color }}; border-bottom: none;">Current Risk Level</h2>
            <h1 style="font-size: 2em; margin: 10px 0; color: {{ risk.color }};">{{ risk.level }}</h1>
            <p style="font-size: 1.1em; color: #555;">{{ risk.message }}</p>
        </div>
    </div>
</body>
</html>
"""

# --- HELPER FUNCTIONS ---
def get_sensor_data():
    file_path = os.path.join(os.path.dirname(__file__), 'data.json')
    try:
        with open(file_path, 'r') as f: return json.load(f)
    except:
        return {"error": "Data file not found."}

def get_subscribers():
    if not os.path.exists(SUBSCRIBERS_FILE):
        return []
    try:
        with open(SUBSCRIBERS_FILE, 'r') as f: 
            return json.load(f)
    except: return []

def save_subscriber(name, phone, email):
    subs = get_subscribers()
    subs.append({"name": name, "phone": phone, "email": email})
    with open(SUBSCRIBERS_FILE, 'w') as f:
        json.dump(subs, f, indent=4)

def send_fire_alerts():
    """Reads the subscriber list and sends SMS and Emails to everyone."""
    subs = get_subscribers()
    if not subs:
        print("No subscribers to alert.")
        return

    print(f"Triggering alerts for {len(subs)} subscribers...")
    
    # 1. Setup Twilio
    twilio_client = Client(TWILIO_SID, TWILIO_AUTH)
    
    # 2. Setup Email
    try:
        email_server = smtplib.SMTP('smtp.gmail.com', 587)
        email_server.starttls()
        email_server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    except Exception as e:
        print(f"Failed to connect to email server: {e}")
        return

    subject = "EMERGENCY: Fire Detected!"
    body = "This is an automated alert from the ESC204 system. High levels of smoke/heat have been detected. Please evacuate immediately."

    for sub in subs:
        # Send SMS
        try:
            twilio_client.messages.create(
                body=body,
                from_=TWILIO_PHONE,
                to=sub['phone']
            )
            print(f"SMS sent to {sub['phone']}")
        except Exception as e: print(f"Failed to send SMS to {sub['phone']}: {e}")

        # Send Email
        try:
            msg = f"Subject: {subject}\n\n{body}"
            email_server.sendmail(EMAIL_ADDRESS, sub['email'], msg)
            print(f"Email sent to {sub['email']}")
        except Exception as e: print(f"Failed to send Email to {sub['email']}: {e}")

    email_server.quit()
    print("All alerts processed.")

# --- ROUTES ---
@app.route("/", methods=['GET'])
def web_dashboard():
    # We look for a 'msg' URL parameter to show a success message after registering
    success_msg = request.args.get('msg')
    data = get_sensor_data()
    
    # Assess the risk based on current data using our stateful monitor
    current_risk = fire_monitor.assess_risk(data)
    
    return render_template_string(HTML_TEMPLATE, data=data, message=success_msg, risk=current_risk)

@app.route("/register", methods=['POST'])
def register_user():
    name = request.form.get('name')
    phone = request.form.get('phone')
    email = request.form.get('email')
    
    save_subscriber(name, phone, email)
    return redirect(url_for('web_dashboard', msg="Successfully registered for alerts!"))

@app.route("/reply_sms", methods=['POST'])
def reply_sms():
    """Respond to incoming SMS with a simple text message."""
    resp = MessagingResponse()
    data = get_sensor_data()
    
    if "error" in data:
        resp.message("Error: Could not read sensor data at this time.")
        return Response(str(resp), mimetype='text/xml')

    time = data.get('timestamp', 'Unknown time')
    data_points = [{'name': k, 'value': v} for k, v in data.items() if k != 'timestamp']
    
    data_str = '\n'.join([f"{dp['name']}: {dp['value']}" for dp in data_points])
    resp.message(f"Current time: {time}\nData points:\n{data_str}")

    return Response(str(resp), mimetype='text/xml')

# --- TEST ROUTE ---
@app.route("/test_fire", methods=['GET'])
def test_fire():
    """Visit http://localhost:3000/test_fire to test your notifications"""
    send_fire_alerts()
    return "Alerts triggered! Check your terminal and phone."

if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        conf.get_default().ngrok_path = os.getenv("NGROK")
        public_url = ngrok.connect(3000)
        
        print("*" * 60)
        print(f"🌐 VIEW DASHBOARD & REGISTER: {public_url.public_url}")
        print(f"🚨 TRIGGER A TEST ALERT:      {public_url.public_url}/test_fire")
        print("*" * 60)

    app.run(port=3000, debug=True)