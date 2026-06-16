import json
import paho.mqtt.client as mqtt

from shared.config import MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE


def publish_message(topic: str, payload: dict) -> None:
    """
    Publica un mensaje JSON en el topic MQTT indicado.
    """
    client = mqtt.Client()

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
        message = json.dumps(payload, ensure_ascii=False)
        result = client.publish(topic, message)

        status = result.rc
        if status == 0:
            print(f"[MQTT] Mensaje publicado en '{topic}'")
        else:
            print(f"[MQTT] Error al publicar en '{topic}', código: {status}")

    except Exception as e:
        print(f"[MQTT] Error de conexión/publicación: {e}")

    finally:
        client.disconnect()