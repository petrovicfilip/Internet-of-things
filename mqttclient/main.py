import os
import json
import asyncio
import threading
import paho.mqtt.client as mqtt
from nats.aio.client import Client as NATS

def env(n, d):
    v = os.getenv(n)
    return v if v else d

# ---- MQTT (events) ----
MQTT_HOST = env("MQTT_HOST", "localhost")
MQTT_PORT = int(env("MQTT_PORT", "1883"))
MQTT_TOPIC_EVENTS = env("MQTT_TOPIC_EVENTS", "iot/events")

# ---- NATS (predictions) ----
NATS_URL = env("NATS_URL", "nats://localhost:4222")
NATS_SUBJECT = env("NATS_SUBJECT", "iot.predictions")

def run_mqtt():
    def on_connect(client, userdata, flags, rc):
        print(f"[mqttnats] mqtt connected rc={rc}, subscribing {MQTT_TOPIC_EVENTS}")
        client.subscribe(MQTT_TOPIC_EVENTS, qos=1)

    def on_message(client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode("utf-8"))
            print(f"\n=== MQTT EVENT ===\n{json.dumps(data, indent=2)}\n")
        except Exception:
            print(msg.payload)

    client = mqtt.Client(protocol=mqtt.MQTTv311)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_forever()

async def run_nats():
    nc = NATS()
    await nc.connect(servers=[NATS_URL])
    print(f"[mqttnats] nats connected, subscribing {NATS_SUBJECT} on {NATS_URL}")

    async def cb(msg):
        try:
            data = json.loads(msg.data.decode("utf-8"))
            print(f"\n=== NATS PREDICTION ===\n{json.dumps(data, indent=2)}\n")
        except Exception:
            print(msg.data)

    await nc.subscribe(NATS_SUBJECT, cb=cb)
    await asyncio.Event().wait()  # radi zauvek

def main():
    # MQTT radi u svom thread-u (blocking loop_forever)
    t = threading.Thread(target=run_mqtt, daemon=True)
    t.start()

    # NATS radi u asyncio loop-u (main thread)
    asyncio.run(run_nats())

if __name__ == "__main__":
    main()