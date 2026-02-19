import os, json, asyncio
from collections import deque
from datetime import datetime, timezone

import httpx
import paho.mqtt.client as mqtt
from nats.aio.client import Client as NATS

MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC_READINGS", "iot/readings")

MLAAS_URL = os.getenv("MLAAS_URL", "http://mlaas:8000/predict")
NATS_URL = os.getenv("NATS_URL", "nats://nats:4222")
NATS_SUBJECT = os.getenv("NATS_SUBJECT", "iot.predictions")

WINDOW = int(os.getenv("WINDOW_SIZE", "20"))  # poslednjih N reading-a po source_id

def iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

def compute_features(window):
    # window: list[reading]
    def arr(key):
        return [float(x.get(key) or 0.0) for x in window]

    import statistics as st

    def mean_std(vals):
        if len(vals) < 2:
            return (vals[-1] if vals else 0.0, 0.0)
        return (st.mean(vals), st.pstdev(vals))

    t = arr("temperature_c")
    h = arr("humidity_percent")
    l = arr("light_lux")
    c = arr("co2_ppm")

    t_mean, t_std = mean_std(t)
    h_mean, h_std = mean_std(h)
    l_mean, l_std = mean_std(l)
    c_mean, c_std = mean_std(c)

    last = window[-1]
    return {
        "temp_mean": t_mean, "temp_std": t_std,
        "hum_mean": h_mean, "hum_std": h_std,
        "light_mean": l_mean, "light_std": l_std,
        "co2_mean": c_mean, "co2_std": c_std,
        "temp_last": float(last.get("temperature_c") or 0.0),
        "hum_last": float(last.get("humidity_percent") or 0.0),
        "light_last": float(last.get("light_lux") or 0.0),
        "co2_last": float(last.get("co2_ppm") or 0.0),
    }

async def main():
    loop = asyncio.get_running_loop()
    q: asyncio.Queue[bytes] = asyncio.Queue()

    # NATS connect
    nc = NATS()
    await nc.connect(servers=[NATS_URL])

    # HTTP client
    http = httpx.AsyncClient(timeout=10.0)

    # global sliding window (poslednjih WINDOW reading-a ukupno)
    window = deque(maxlen=WINDOW)

    # MQTT callbacks (paho radi u svom thread-u)
    def on_connect(client, userdata, flags, rc):
        print(f"[analytics] mqtt connected rc={rc}, subscribing {MQTT_TOPIC}")
        client.subscribe(MQTT_TOPIC)

    def on_message(client, userdata, msg):
        loop.call_soon_threadsafe(q.put_nowait, msg.payload)

    m = mqtt.Client()
    m.on_connect = on_connect
    m.on_message = on_message
    m.connect(MQTT_HOST, MQTT_PORT, 60)
    m.loop_start()

    print(f"[analytics] nats connected {NATS_URL}, subject={NATS_SUBJECT}")
    print(f"[analytics] mlaas url={MLAAS_URL}, window={WINDOW}")

    try:
        while True:
            payload = await q.get()
            env = json.loads(payload.decode("utf-8"))

            action = env.get("action")
            if action not in ("created", "updated"):
                continue

            r = env.get("reading") or {}
            source_id = int(r.get("source_id", 0))
            rid = r.get("id")
            ts = r.get("ts")

            window.append(r)

            if len(window) < WINDOW:
                continue  # još nema dovoljno za prozor

            feats = compute_features(list(window))

            req = {
                "reading_id": rid,
                "source_id": source_id,
                "ts": ts,
                "features": feats,
            }

            try:
                resp = await http.post(MLAAS_URL, json=req)
                resp.raise_for_status()
                pred = resp.json()
            except Exception as e:
                print(f"[analytics] mlaas error: {e}")
                continue

            out = {
                "emitted_at": iso_z(datetime.now(timezone.utc)),
                "reading_id": pred["reading_id"],
                "source_id": pred["source_id"],
                "ts": pred["ts"],
                "prediction": pred["prediction"],
                "probability": pred["probability"],
                "model_version": pred["model_version"],
                "window_size": WINDOW,
            }

            await nc.publish(NATS_SUBJECT, json.dumps(out).encode("utf-8"))
            await nc.flush()
            print(f"[analytics] published prediction rid={rid} p={out['probability']:.3f}")

    finally:
        m.loop_stop()
        await http.aclose()
        await nc.close()

if __name__ == "__main__":
    asyncio.run(main())