import json
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_KEEPALIVE = 60
TOPIC = "telemetry/renfe"


def publish_message():
    payload = {
        "source": "renfe",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "location": "madrid_rail_network",
        "variables": {
            "incident_count": 48,
            "affected_route_count": 260,
            "affected_line_count": 9,
            "accessibility_alert_count": 12,
            "bus_service_alert_count": 8,
            "infrastructure_alert_count": 35,
            "service_cut_alert_count": 10,
            "trip_update_count": 20,
            "delayed_trip_count": 14,
            "cancelled_trip_count": 6,
            "added_trip_count": 0,
            "affected_stop_count": 25,
            "mean_delay_seconds": 720.0,
            "max_delay_seconds": 1800,
            "skipped_non_madrid_alerts": 15,
            "skipped_non_madrid_trip_updates": 180,
            "matched_lines_alerts": [
                "C1", "C2", "C3", "C4", "C5", "C7", "C8", "C9", "C10"
            ],
            "matched_lines_trip_updates": [
                "C2", "C3", "C4", "C5", "C7", "C8"
            ]
        }
    }

    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)

    client.publish(TOPIC, json.dumps(payload), qos=1)
    print(f"[TEST RENFE] Publicado en {TOPIC}")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    client.disconnect()


if __name__ == "__main__":
    publish_message()