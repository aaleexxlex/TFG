import json
import paho.mqtt.client as mqtt

from shared.config import MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE, TOPIC_ALERTS


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[ALERT LISTENER] Conectado al broker MQTT")
        client.subscribe(TOPIC_ALERTS)
        print(f"[ALERT LISTENER] Suscrito a '{TOPIC_ALERTS}'")
    else:
        print(f"[ALERT LISTENER] Error al conectar. Código: {rc}")


def on_message(client, userdata, msg):
    print(f"\n[ALERT LISTENER] Alerta recibida en topic: {msg.topic}")

    try:
        payload = msg.payload.decode("utf-8")
        data = json.loads(payload)

        print("[ALERT LISTENER] Contenido:")
        print(json.dumps(data, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"[ALERT LISTENER] Error procesando mensaje: {e}")
        print("[ALERT LISTENER] Payload crudo:")
        print(msg.payload)


def main():
    client = mqtt.Client()

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)

    print("[ALERT LISTENER] Esperando alertas...\n")

    client.loop_forever()


if __name__ == "__main__":
    main()