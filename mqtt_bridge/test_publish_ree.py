import json
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_KEEPALIVE = 60
TOPIC = "telemetry/ree"


def publish_message():
    payload = {
        "source": "ree",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "location": "spain_power_system",
        "variables": {
            "wind_generation": 36000.0,
            "solar_generation": 118000.0
        }
    }

    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)

    client.publish(TOPIC, json.dumps(payload), qos=1)
    print(f"[TEST REE] Publicado en {TOPIC}")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    client.disconnect()


if __name__ == "__main__":
    publish_message()