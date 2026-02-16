import json
import os
import time
import paho.mqtt.client as mqtt

def _env(name: str, default: str) -> str:
    v = os.getenv(name)
    return v if v is not None and v != "" else default

class MqttPublisher:
    def __init__(self):
        self.enabled = _env("MQTT_ENABLED", "true").lower() in ("1","true","yes","y")
        if not self.enabled:
            self.client = None
            return

        host = _env("MQTT_HOST", "mosquitto")
        port = int(_env("MQTT_PORT", "1883"))
        self.topic = _env("MQTT_TOPIC_READINGS", "iot/readings")
        self.qos = int(_env("MQTT_QOS", "1"))

        client_id = _env("MQTT_CLIENT_ID", f"datamanager-{int(time.time())}")
        self.client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)

        username = _env("MQTT_USERNAME", "")
        password = _env("MQTT_PASSWORD", "")
        if username:
            self.client.username_pw_set(username, password)

        # ne želimo da DataManager padne ako MQTT nije tu – pokušaj connect, ali fail-safe
        try:
            self.client.connect(host, port, keepalive=60)
            self.client.loop_start()
            print(f"[datamanager] MQTT connected {host}:{port} topic={self.topic}")
        except Exception as e:
            print(f"[datamanager] MQTT connect failed: {e}")
            self.enabled = False

    def publish_reading(self, reading: dict, action: str = "created"):
        if not self.enabled or not self.client:
            return
        msg = {
            "action": action,              # created|updated|deleted
            "emitted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "reading": reading,            # tvoj reading payload
        }
        try:
            self.client.publish(self.topic, json.dumps(msg), qos=self.qos, retain=False)
        except Exception as e:
            print(f"[datamanager] MQTT publish failed: {e}")

    def close(self):
        if self.client:
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except Exception:
                pass