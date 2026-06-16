import json
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from edge.fused_storage import FusedObservationStorage
from shared.config import (
    MQTT_BROKER,
    MQTT_PORT,
    MQTT_KEEPALIVE,
    TOPIC_REE,
    TOPIC_AEMET,
    TOPIC_DGT,
    TOPIC_RENFE,
    TOPIC_ALERTS,
    TOPIC_FUSED_OBSERVATIONS,
    FUSION_MAX_DELTA_SECONDS,
)
from shared.schemas import AlertMessage, TelemetryMessage
from edge.detector import detect_anomaly_dummy
from edge.telemetry_fusion import TelemetryFusionBuffer


fusion_buffer = TelemetryFusionBuffer(max_delta_seconds=FUSION_MAX_DELTA_SECONDS)
fusion_storage = FusedObservationStorage()

last_alert_signature = None
last_storage_signature = None
last_storage_datetime = None

MIN_STORAGE_INTERVAL_SECONDS = 300


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[EDGE] Conectado al broker MQTT")

        client.subscribe(TOPIC_REE)
        client.subscribe(TOPIC_AEMET)
        client.subscribe(TOPIC_DGT)
        client.subscribe(TOPIC_RENFE)

        print(f"[EDGE] Suscrito a '{TOPIC_REE}'")
        print(f"[EDGE] Suscrito a '{TOPIC_AEMET}'")
        print(f"[EDGE] Suscrito a '{TOPIC_DGT}'")
        print(f"[EDGE] Suscrito a '{TOPIC_RENFE}'")
    else:
        print(f"[EDGE] Error al conectar. Código: {rc}")


def publish_alert(client, alert_payload: dict) -> bool:
    try:
        message = json.dumps(alert_payload, ensure_ascii=False, default=str)
        result = client.publish(TOPIC_ALERTS, message, qos=1, retain=False)

        if result.rc == 0:
            print(f"[EDGE] Alerta publicada en '{TOPIC_ALERTS}'")
            return True

        print(f"[EDGE] Error publicando alerta. Código: {result.rc}")
        return False

    except Exception as e:
        print(f"[EDGE] Error al publicar alerta: {e}")
        return False


def publish_fused_observation(client, observation: dict) -> bool:
    try:
        message = json.dumps(observation, ensure_ascii=False, default=str)
        result = client.publish(TOPIC_FUSED_OBSERVATIONS, message, qos=1, retain=False)

        if result.rc == 0:
            print(f"[EDGE] Observación fusionada publicada en '{TOPIC_FUSED_OBSERVATIONS}'")
            return True

        print(f"[EDGE] Error publicando observación fusionada. Código: {result.rc}")
        return False

    except Exception as e:
        print(f"[EDGE] Error al publicar observación fusionada: {e}")
        return False


def compute_fusion_quality(observation: dict) -> str:
    dgt_included = observation.get("dgt_timestamp") is not None
    renfe_included = observation.get("renfe_timestamp") is not None
    aemet_included = observation.get("aemet_included", False)
    ree_included = observation.get("ree_included", False)

    if dgt_included and renfe_included and aemet_included and ree_included:
        return "complete"

    if dgt_included and renfe_included:
        return "transport_context"

    return "partial"


def normalize_severity_from_score(score: float) -> str:
    if score >= 0.90:
        return "critical"
    if score >= 0.75:
        return "high"
    if score >= 0.60:
        return "medium"
    return "low"


def parse_datetime(value):
    if value is None:
        return None

    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt


def build_storage_signature(observation: dict) -> tuple:
    features = observation.get("features", {}) or {}

    return (
        observation.get("fusion_quality"),
        observation.get("severity"),
        round(float(observation.get("score", 0.0)), 3),

        features.get("dgt_incident_count"),
        features.get("dgt_severity_medium_count"),
        features.get("dgt_severity_high_count"),
        features.get("dgt_severity_highest_count"),
        features.get("dgt_affected_municipality_count"),
        features.get("dgt_affected_road_count"),
        features.get("dgt_type_sit_AbnormalTraffic_count"),

        features.get("renfe_incident_count"),
        features.get("renfe_affected_line_count"),
        features.get("renfe_infrastructure_alert_count"),
        features.get("renfe_service_cut_alert_count"),
        features.get("renfe_delayed_trip_count"),
        features.get("renfe_cancelled_trip_count"),
        features.get("renfe_max_delay_seconds"),

        features.get("aemet_temperature"),
        features.get("aemet_precipitation"),
        features.get("aemet_wind_speed"),

        features.get("ree_wind_generation"),
        features.get("ree_solar_generation"),
    )


def should_store_observation(observation: dict) -> bool:
    global last_storage_signature
    global last_storage_datetime

    current_signature = build_storage_signature(observation)
    current_datetime = parse_datetime(observation.get("timestamp"))

    if last_storage_signature is None:
        last_storage_signature = current_signature
        last_storage_datetime = current_datetime
        return True

    if current_signature != last_storage_signature:
        last_storage_signature = current_signature
        last_storage_datetime = current_datetime
        return True

    if current_datetime is None or last_storage_datetime is None:
        return False

    elapsed_seconds = abs((current_datetime - last_storage_datetime).total_seconds())

    if elapsed_seconds >= MIN_STORAGE_INTERVAL_SECONDS:
        last_storage_signature = current_signature
        last_storage_datetime = current_datetime
        return True

    return False


def on_message(client, userdata, msg):
    global last_alert_signature

    print(f"\n[EDGE] Mensaje recibido en topic: {msg.topic}")

    try:
        payload = msg.payload.decode("utf-8")
        data = json.loads(payload)

        telemetry = TelemetryMessage(**data)

        print(f"[EDGE] Source: {telemetry.source}")
        print(f"[EDGE] Timestamp: {telemetry.timestamp}")
        print(f"[EDGE] Variables: {telemetry.variables}")

        fusion_buffer.update(telemetry)

        if not fusion_buffer.can_fuse():
            return

        observation = fusion_buffer.build_joint_observation()

        print(
            f"[EDGE] Contexto -> "
            f"aemet_included={observation.get('aemet_included')}, "
            f"ree_included={observation.get('ree_included')}, "
            f"aemet_age_seconds={observation.get('aemet_age_seconds')}, "
            f"ree_age_seconds={observation.get('ree_age_seconds')}"
        )

        print("[EDGE] Observación fusionada generada:")
        print(json.dumps(observation, indent=2, ensure_ascii=False, default=str))

        features = observation.get("features", {}) or {}

        anomaly_detected, score, _severity, message = detect_anomaly_dummy(features)
        severity = normalize_severity_from_score(score)

        print(
            f"[EDGE] Resultado detector base -> "
            f"anomaly={anomaly_detected}, "
            f"score={score:.3f}, "
            f"severity={severity}, "
            f"message={message}"
        )
        print("[EDGE] Nota: dominant_node, graph_score y criticality_score se calculan en Fog")

        alert_published = False
        alert_duplicate = False

        if anomaly_detected:
            signature = (
                severity,
                round(score, 2),
                message,
            )

            if signature != last_alert_signature:
                alert = AlertMessage(
                    source="fusion",
                    timestamp=observation["timestamp"],
                    severity=severity,
                    anomaly_score=score,
                    message=message,
                    variables={**features},
                )

                alert_published = publish_alert(client, alert.model_dump(mode="json"))
                last_alert_signature = signature
            else:
                alert_duplicate = True
                print("[EDGE] Alerta duplicada evitada")

        enriched_observation = dict(observation)

        enriched_observation["fusion_quality"] = compute_fusion_quality(observation)

        enriched_observation["anomaly_detected"] = anomaly_detected
        enriched_observation["score"] = score
        enriched_observation["severity"] = severity
        enriched_observation["alert_message"] = message

        # Estos campos se completan posteriormente en Fog mediante el grafo de dependencias.
        enriched_observation["dominant_node"] = None
        enriched_observation["graph_score"] = None
        enriched_observation["criticality_score"] = None

        enriched_observation["alert_published"] = alert_published
        enriched_observation["alert_duplicate"] = alert_duplicate

        publish_fused_observation(client, enriched_observation)

        if should_store_observation(enriched_observation):
            fusion_storage.save(enriched_observation)
            print("[EDGE] Observación enriquecida guardada en CSV")
        else:
            print("[EDGE] Observación duplicada evitada en CSV")

    except Exception as e:
        print(f"[EDGE] Error procesando mensaje: {e}")


def main():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
    client.loop_forever()


if __name__ == "__main__":
    main()