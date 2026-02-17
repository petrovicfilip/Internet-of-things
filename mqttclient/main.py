import os
import json
import paho.mqtt.client as mqtt

def env(n, d): 
    v = os.getenv(n); 
    return v if v else d

HOST = env("MQTT_HOST", "localhost")
PORT = int(env("MQTT_PORT", "1883"))
TOPIC = env("MQTT_TOPIC_EVENTS", "iot/events")

def on_connect(client, userdata, flags, rc):
    print(f"[mqttclient] connected rc={rc}, subscribing {TOPIC}")
    client.subscribe(TOPIC, qos=1)

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode("utf-8"))
        print(f"\n=== EVENT ===\n{json.dumps(data, indent=2)}\n")
    except Exception:
        print(msg.payload)

client = mqtt.Client(protocol=mqtt.MQTTv311)
client.on_connect = on_connect
client.on_message = on_message
client.connect(HOST, PORT, 60)
client.loop_forever()