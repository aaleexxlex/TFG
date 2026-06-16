import json
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_KEEPALIVE = 60
TOPIC = "telemetry/dgt"


def publish_message():
    payload = {
        "source": "dgt",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "location": "madrid_road_network",
        "variables": {
            "incident_count": 135,
            "severity_low_count": 5,
            "severity_medium_count": 18,
            "severity_high_count": 22,
            "severity_highest_count": 2,
            "severity_unknown_count": 88,
            "validity_active_count": 135,
            "probability_certain_count": 130,
            "missing_location_info_count": 0,
            "skipped_outside_madrid_count": 520,
            "affected_municipality_count": 54,
            "affected_road_count": 68,
            "type_sit_RoadOrCarriagewayOrLaneManagement_count": 70,
            "type_sit_SpeedManagement_count": 8,
            "type_sit_GenericSituationRecord_count": 42,
            "type_sit_AbnormalTraffic_count": 15
        }
    }

    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)

    client.publish(TOPIC, json.dumps(payload), qos=1)
    print(f"[TEST DGT] Publicado en {TOPIC}")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    client.disconnect()


if __name__ == "__main__":
    publish_message()