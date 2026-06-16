import json
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_KEEPALIVE = 60
TOPIC = "telemetry/aemet"


def publish_message():
    payload = {
        "source": "aemet",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "location": "madrid_retiro",
        "variables": {
            "temperature": 31.8,
            "humidity": 28.0,
            "pressure": 939.2,
            "precipitation": 0.0,
            "wind_speed": 2.4
        }
    }

    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)

    client.publish(TOPIC, json.dumps(payload), qos=1)
    print(f"[TEST AEMET] Publicado en {TOPIC}")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    client.disconnect()


if __name__ == "__main__":
    publish_message()