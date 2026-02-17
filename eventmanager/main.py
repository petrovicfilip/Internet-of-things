import json
import os
import time
import uuid
import paho.mqtt.client as mqtt

def env(name: str, default: str) -> str:
    v = os.getenv(name)
    return v if v is not None and v != "" else default

MQTT_HOST = env("MQTT_HOST", "mosquitto")
MQTT_PORT = int(env("MQTT_PORT", "1883"))

TOPIC_IN  = env("MQTT_TOPIC_READINGS", "iot/readings")
TOPIC_OUT = env("MQTT_TOPIC_EVENTS", "iot/events")
QOS = int(env("MQTT_QOS", "1"))

# pragovi (proizvoljni, ali smisleni)
TEMP_MAX = float(env("TEMP_MAX", "0.0"))
CO2_MAX  = float(env("CO2_MAX", "0"))
HUM_MIN  = float(env("HUM_MIN", "0.0"))
LIGHT_MAX = float(env("LIGHT_MAX", "0"))

def detect_events(reading: dict):
    events = []
    temp = reading.get("temperature_c", 0) or 0
    co2  = reading.get("co2_ppm", 0) or 0
    hum  = reading.get("humidity_percent", 0) or 0
    lux  = reading.get("light_lux", 0) or 0

    if temp > TEMP_MAX:
        events.append(("HIGH_TEMPERATURE", {"temperature_c": temp, "threshold": TEMP_MAX}))
    if co2 > CO2_MAX:
        events.append(("HIGH_CO2", {"co2_ppm": co2, "threshold": CO2_MAX}))
    if hum < HUM_MIN:
        events.append(("LOW_HUMIDITY", {"humidity_percent": hum, "threshold": HUM_MIN}))
    if lux > LIGHT_MAX:
        events.append(("HIGH_LIGHT", {"light_lux": lux, "threshold": LIGHT_MAX}))

    return events

def on_connect(client, userdata, flags, rc):
    print(f"[eventmanager] connected rc={rc}, subscribing {TOPIC_IN}")
    client.subscribe(TOPIC_IN, qos=QOS)

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        reading = payload.get("reading", payload)   # podrži i format sa wrapper-om
        action = payload.get("action", "created")

        if action not in ("created", "updated"):
            return

        detected = detect_events(reading)
        for event_type, values in detected:
            event_msg = {
                "event_id": str(uuid.uuid4()),
                "event_type": event_type,
                "detected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "reading_id": reading.get("id"),
                "source_id": reading.get("source_id"),
                "ts": reading.get("ts"),
                "values": values,
                "location": reading.get("location", None),
            }
            client.publish(TOPIC_OUT, json.dumps(event_msg), qos=QOS, retain=False)
            print(f"[eventmanager] published {event_type} for reading={reading.get('id')}")
    except Exception as e:
        print(f"[eventmanager] bad message: {e}")

def main():
    client_id = env("MQTT_CLIENT_ID", f"eventmanager-{int(time.time())}")
    client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)

    username = env("MQTT_USERNAME", "")
    password = env("MQTT_PASSWORD", "")
    if username:
        client.username_pw_set(username, password)

    client.on_connect = on_connect
    client.on_message = on_message

    print(f"[eventmanager] connecting to {MQTT_HOST}:{MQTT_PORT}")
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_forever()

if __name__ == "__main__":
    main()