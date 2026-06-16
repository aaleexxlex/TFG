import json
from pathlib import Path
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from shared.config import (
    MQTT_BROKER,
    MQTT_PORT,
    MQTT_KEEPALIVE,
    TOPIC_FUSED_OBSERVATIONS,
    TOPIC_FINAL_ALERTS,
)

from fog.services.inference import FogMLInference
from fog.services.decision_fusion import fuse_rule_and_ml
from fog.services.influx_writer import InfluxWriter

from shared.critical_infra import compute_graph_risk


ml_inference = FogMLInference()
influx_writer = InfluxWriter()

# Ruta absoluta al directorio raíz del proyecto.
# Si fog/main.py está en /proyecto/fog/main.py, parents[1] apunta a /proyecto
PROJECT_ROOT = Path(__file__).resolve().parents[1]
LATEST_GRAPH_STATE_PATH = PROJECT_ROOT / "data" / "latest_graph_state.json"


def _extract_base_scores(graph_result: dict) -> dict:
    """
    Extrae los scores iniciales por nodo a partir de node_scores.
    Es robusto por si node_scores guarda floats directamente o diccionarios.
    """
    node_scores = graph_result.get("node_scores", {}) or {}
    base_scores = {}

    for node_name, value in node_scores.items():
        if isinstance(value, dict):
            base_scores[node_name] = float(
                value.get(
                    "state_score",
                    value.get(
                        "base_score",
                        value.get(
                            "score",
                            value.get("final_score", 0.0),
                        ),
                    ),
                )
            )
        else:
            base_scores[node_name] = float(value)

    return base_scores


def save_latest_graph_state(observation: dict, features: dict, graph_result: dict, final_payload: dict) -> None:
    """
    Guarda el último estado del grafo para que la aplicación de Streamlit
    pueda visualizar la propagación en modo tiempo real.
    """
    try:
        LATEST_GRAPH_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

        dominant_node = graph_result.get("dominant_node", {})
        if isinstance(dominant_node, dict):
            dominant_node_name = dominant_node.get("name", final_payload.get("dominant_node"))
        else:
            dominant_node_name = dominant_node or final_payload.get("dominant_node")

        payload = {
            "source": "fog",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "timestamp": observation.get("timestamp"),

            "target_area": observation.get("target_area"),
            "location": observation.get("location"),

            "base_scores": _extract_base_scores(graph_result),
            "node_scores": graph_result.get("node_scores", {}),

            "graph_score": final_payload.get("graph_score", 0.0),
            "global_graph_score": final_payload.get("graph_score", 0.0),
            "criticality_score": final_payload.get("criticality_score", 0.0),
            "dominant_node": dominant_node_name,

            "rule_score": final_payload.get("rule_score", 0.0),
            "ml_score": final_payload.get("ml_score", 0.0),
            "final_score": final_payload.get("final_score", 0.0),
            "final_severity": final_payload.get("final_severity"),
            "final_anomaly": final_payload.get("final_anomaly"),
            "decision_mode": final_payload.get("decision_mode"),

            "features": features,
        }

        LATEST_GRAPH_STATE_PATH.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

        print(f"[FOG] Estado del grafo guardado en {LATEST_GRAPH_STATE_PATH}")

    except Exception as e:
        print(f"[FOG] Error guardando latest_graph_state.json: {e}")


def publish_final_observation(client, payload: dict) -> bool:
    message = json.dumps(payload, ensure_ascii=False, default=str)
    result = client.publish(TOPIC_FINAL_ALERTS, message, qos=1, retain=False)

    if result.rc == 0:
        print(f"[FOG] Observación final publicada en '{TOPIC_FINAL_ALERTS}'")
        return True

    print(f"[FOG] Error publicando observación final. Código: {result.rc}")
    return False


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[FOG] Conectado al broker MQTT")
        client.subscribe(TOPIC_FUSED_OBSERVATIONS)
        print(f"[FOG] Suscrito a '{TOPIC_FUSED_OBSERVATIONS}'")
    else:
        print(f"[FOG] Error al conectar. Código: {rc}")


def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode("utf-8")
        observation = json.loads(payload)

        print("\n[FOG] Observación recibida desde Edge")
        print(f"[FOG] timestamp={observation.get('timestamp')}")
        print(f"[FOG] rule_score={observation.get('score')}")
        print(f"[FOG] rule_severity={observation.get('severity')}")
        print(f"[FOG] dominant_node_incoming={observation.get('dominant_node')}")

        rule_score = float(observation.get("score", 0.0))
        ml_score = ml_inference.predict_score(observation)

        features = observation.get("features", {}) or {}
        graph_result = compute_graph_risk(features)

        fusion = fuse_rule_and_ml(rule_score, ml_score)

        final_payload = {
            "source": "fog",
            "timestamp": observation.get("timestamp"),
            "target_area": observation.get("target_area"),
            "location": observation.get("location"),
            "fusion_quality": observation.get("fusion_quality"),

            "rule_score": rule_score,
            "rule_severity": observation.get("severity"),
            "rule_anomaly": observation.get("anomaly_detected"),

            "ml_score": ml_score,

            "final_score": fusion["final_score"],
            "final_severity": fusion["final_severity"],
            "final_anomaly": fusion["final_anomaly"],
            "decision_mode": fusion["decision_mode"],

            "dominant_node": graph_result.get("dominant_node", {}).get(
                "name",
                observation.get("dominant_node"),
            ),
            "graph_score": graph_result.get("global_graph_score", 0.0),
            "criticality_score": graph_result.get("criticality_score", 0.0),
            "node_scores": graph_result.get("node_scores", {}),

            "aemet_included": observation.get("aemet_included"),
            "ree_included": observation.get("ree_included"),
            "aemet_age_seconds": observation.get("aemet_age_seconds"),
            "ree_age_seconds": observation.get("ree_age_seconds"),
            "delta_dgt_renfe_seconds": observation.get("delta_dgt_renfe_seconds"),

            "message": observation.get("alert_message"),
            "features": features,
        }

        print(
            f"[FOG] decision_mode={final_payload['decision_mode']} | "
            f"ml_score={ml_score} | "
            f"final_score={final_payload['final_score']:.3f} | "
            f"final_severity={final_payload['final_severity']} | "
            f"final_anomaly={final_payload['final_anomaly']}"
        )

        print(f"[FOG] graph_score={final_payload['graph_score']}")
        print(f"[FOG] criticality_score={final_payload['criticality_score']}")
        print(f"[FOG] dominant_node={final_payload['dominant_node']}")

        # Guardado para la app de Streamlit
        save_latest_graph_state(observation, features, graph_result, final_payload)

        publish_final_observation(client, final_payload)

        influx_writer.write_observation(final_payload)

    except Exception as e:
        print(f"[FOG] Error procesando observación: {e}")


def main():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
    client.loop_forever()


if __name__ == "__main__":
    main()