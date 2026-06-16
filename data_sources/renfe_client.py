import json
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

import requests
import paho.mqtt.client as mqtt

from shared.config import (
    MQTT_BROKER,
    MQTT_PORT,
    MQTT_KEEPALIVE,
    RENFE_ALERTS_URL,
    RENFE_TRIP_UPDATES_URL,
    RENFE_REQUEST_TIMEOUT,
    RENFE_POLL_SECONDS,
    TOPIC_RENFE,
)


RENFE_LOCATION = "madrid_renfe_cercanias"

# Líneas de Cercanías Madrid que queremos considerar
MADRID_LINES = {"C1", "C2", "C3", "C4", "C5", "C7", "C8", "C9", "C10"}


def extract_line_code(route_id: str) -> Optional[str]:
    """
    Intenta extraer el código de línea del final del routeId.
    Ejemplos esperados:
    - 10T0035C5  -> C5
    - 10T0012C10 -> C10
    """
    if not route_id:
        return None

    route_upper = route_id.upper().strip()
    match = re.search(r"(C10|C[1-9])$", route_upper)

    if match:
        return match.group(1)

    return None


def is_madrid_route(route_id: str) -> bool:
    line_code = extract_line_code(route_id)
    return line_code in MADRID_LINES


def fetch_json(url: str) -> Dict[str, Any]:
    response = requests.get(url, timeout=RENFE_REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def unix_to_iso(ts: int) -> str:
    if ts <= 0:
        return datetime.now(timezone.utc).isoformat()
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def extract_alert_text(alert_obj: Dict[str, Any]) -> str:
    description = alert_obj.get("descriptionText", {})
    translations = description.get("translation", [])

    if translations and isinstance(translations, list):
        first = translations[0]
        if isinstance(first, dict):
            return first.get("text", "") or ""

    return ""


def extract_alert_routes(alert_obj: Dict[str, Any]) -> List[str]:
    informed_entities = alert_obj.get("informedEntity", [])
    routes: List[str] = []

    for entity in informed_entities:
        route_id = entity.get("routeId")
        if route_id:
            routes.append(route_id)

    return routes


def classify_alert_text(text: str) -> Dict[str, int]:
    lowered = text.lower()

    return {
        "accessibility_alert": int(
            any(
                word in lowered
                for word in [
                    "accesibilidad",
                    "ascensor",
                    "escalera mecánica",
                    "movilidad reducida",
                ]
            )
        ),
        "bus_service_alert": int(
            any(word in lowered for word in ["autobús", "autobus"])
        ),
        "infrastructure_alert": int(
            any(
                word in lowered
                for word in [
                    "vía",
                    "via",
                    "infraestructura",
                    "obras",
                    "señalización",
                    "señalizacion",
                ]
            )
        ),
        "service_cut_alert": int(
            any(
                word in lowered
                for word in [
                    "sin servicio",
                    "finalizan",
                    "inician su recorrido",
                    "corte",
                    "interrumpido",
                    "suspendido",
                ]
            )
        ),
    }


def summarize_alerts(alerts_feed: Dict[str, Any]) -> Dict[str, Any]:
    entities = alerts_feed.get("entity", [])
    header = alerts_feed.get("header", {})
    feed_timestamp = safe_int(header.get("timestamp"))

    affected_routes: Set[str] = set()
    matched_lines: Set[str] = set()

    accessibility_alert_count = 0
    bus_service_alert_count = 0
    infrastructure_alert_count = 0
    service_cut_alert_count = 0

    filtered_incident_count = 0
    skipped_non_madrid_alerts = 0

    for entity in entities:
        alert_obj = entity.get("alert", {})

        routes = extract_alert_routes(alert_obj)
        madrid_routes = [r for r in routes if is_madrid_route(r)]

        if not madrid_routes:
            skipped_non_madrid_alerts += 1
            continue

        filtered_incident_count += 1
        affected_routes.update(madrid_routes)

        for route_id in madrid_routes:
            line_code = extract_line_code(route_id)
            if line_code:
                matched_lines.add(line_code)

        text = extract_alert_text(alert_obj)
        categories = classify_alert_text(text)

        accessibility_alert_count += categories["accessibility_alert"]
        bus_service_alert_count += categories["bus_service_alert"]
        infrastructure_alert_count += categories["infrastructure_alert"]
        service_cut_alert_count += categories["service_cut_alert"]

    return {
        "feed_timestamp": feed_timestamp,
        "incident_count": filtered_incident_count,
        "affected_route_count": len(affected_routes),
        "affected_line_count": len(matched_lines),
        "accessibility_alert_count": accessibility_alert_count,
        "bus_service_alert_count": bus_service_alert_count,
        "infrastructure_alert_count": infrastructure_alert_count,
        "service_cut_alert_count": service_cut_alert_count,
        "skipped_non_madrid_alerts": skipped_non_madrid_alerts,
        "matched_lines_alerts": sorted(matched_lines),
    }


def extract_delay_from_stop_update(stop_update: Dict[str, Any]) -> Optional[int]:
    arrival = stop_update.get("arrival", {})
    departure = stop_update.get("departure", {})

    if "delay" in arrival:
        return safe_int(arrival.get("delay"))
    if "delay" in departure:
        return safe_int(departure.get("delay"))

    return None


def summarize_trip_updates(trips_feed: Dict[str, Any]) -> Dict[str, Any]:
    entities = trips_feed.get("entity", [])
    header = trips_feed.get("header", {})
    feed_timestamp = safe_int(header.get("timestamp"))

    delayed_trip_count = 0
    cancelled_trip_count = 0
    added_trip_count = 0
    total_delay_samples = 0
    total_delay_seconds = 0
    max_delay_seconds = 0

    affected_routes: Set[str] = set()
    affected_stops: Set[str] = set()
    matched_lines: Set[str] = set()

    filtered_entities_count = 0
    skipped_non_madrid_trip_updates = 0

    for entity in entities:
        trip_update = entity.get("tripUpdate", {})
        trip = trip_update.get("trip", {})

        route_id = trip.get("routeId")
        schedule_relationship = trip.get("scheduleRelationship", "")

        if not is_madrid_route(route_id):
            skipped_non_madrid_trip_updates += 1
            continue

        filtered_entities_count += 1
        affected_routes.add(route_id)

        line_code = extract_line_code(route_id)
        if line_code:
            matched_lines.add(line_code)

        if schedule_relationship == "CANCELED":
            cancelled_trip_count += 1
        elif schedule_relationship == "ADDED":
            added_trip_count += 1

        trip_has_delay = False

        for stop_update in trip_update.get("stopTimeUpdate", []):
            stop_id = stop_update.get("stopId")
            if stop_id:
                affected_stops.add(stop_id)

            delay = extract_delay_from_stop_update(stop_update)
            if delay is not None:
                total_delay_samples += 1
                total_delay_seconds += delay
                max_delay_seconds = max(max_delay_seconds, delay)
                if delay > 0:
                    trip_has_delay = True

        if trip_has_delay:
            delayed_trip_count += 1

    mean_delay_seconds = (
        total_delay_seconds / total_delay_samples if total_delay_samples > 0 else 0.0
    )

    return {
        "feed_timestamp": feed_timestamp,
        "trip_update_count": filtered_entities_count,
        "delayed_trip_count": delayed_trip_count,
        "cancelled_trip_count": cancelled_trip_count,
        "added_trip_count": added_trip_count,
        "affected_route_count_from_trips": len(affected_routes),
        "affected_line_count_from_trips": len(matched_lines),
        "affected_stop_count": len(affected_stops),
        "mean_delay_seconds": round(mean_delay_seconds, 2),
        "max_delay_seconds": max_delay_seconds,
        "skipped_non_madrid_trip_updates": skipped_non_madrid_trip_updates,
        "matched_lines_trip_updates": sorted(matched_lines),
    }


def build_telemetry_payload(
    alerts_summary: Dict[str, Any],
    trips_summary: Dict[str, Any],
) -> Dict[str, Any]:
    feed_timestamp = max(
        safe_int(alerts_summary.get("feed_timestamp")),
        safe_int(trips_summary.get("feed_timestamp")),
    )

    return {
        "source": "renfe",
        "timestamp": unix_to_iso(feed_timestamp),
        "location": RENFE_LOCATION,
        "variables": {
            "incident_count": alerts_summary.get("incident_count", 0),
            "affected_route_count": max(
                alerts_summary.get("affected_route_count", 0),
                trips_summary.get("affected_route_count_from_trips", 0),
            ),
            "affected_line_count": max(
                alerts_summary.get("affected_line_count", 0),
                trips_summary.get("affected_line_count_from_trips", 0),
            ),
            "accessibility_alert_count": alerts_summary.get("accessibility_alert_count", 0),
            "bus_service_alert_count": alerts_summary.get("bus_service_alert_count", 0),
            "infrastructure_alert_count": alerts_summary.get("infrastructure_alert_count", 0),
            "service_cut_alert_count": alerts_summary.get("service_cut_alert_count", 0),
            "trip_update_count": trips_summary.get("trip_update_count", 0),
            "delayed_trip_count": trips_summary.get("delayed_trip_count", 0),
            "cancelled_trip_count": trips_summary.get("cancelled_trip_count", 0),
            "added_trip_count": trips_summary.get("added_trip_count", 0),
            "affected_stop_count": trips_summary.get("affected_stop_count", 0),
            "mean_delay_seconds": trips_summary.get("mean_delay_seconds", 0.0),
            "max_delay_seconds": trips_summary.get("max_delay_seconds", 0),
            "skipped_non_madrid_alerts": alerts_summary.get("skipped_non_madrid_alerts", 0),
            "skipped_non_madrid_trip_updates": trips_summary.get("skipped_non_madrid_trip_updates", 0),
            "matched_lines_alerts": alerts_summary.get("matched_lines_alerts", []),
            "matched_lines_trip_updates": trips_summary.get("matched_lines_trip_updates", []),
        },
    }


def publish_payload(client: mqtt.Client, payload: Dict[str, Any]) -> None:
    result = client.publish(TOPIC_RENFE, json.dumps(payload), qos=0, retain=False)
    if result.rc != 0:
        print(f"[RENFE CLIENT] Error publicando en MQTT. Código: {result.rc}")


def main() -> None:
    mqtt_client = mqtt.Client()
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)

    print("[RENFE CLIENT] Conectado a MQTT")
    print(f"[RENFE CLIENT] Publicando en topic '{TOPIC_RENFE}'")
    print(f"[RENFE CLIENT] Filtro de líneas Madrid: {sorted(MADRID_LINES)}")

    while True:
        try:
            alerts_feed = fetch_json(RENFE_ALERTS_URL)
            trips_feed = fetch_json(RENFE_TRIP_UPDATES_URL)

            alerts_summary = summarize_alerts(alerts_feed)
            trips_summary = summarize_trip_updates(trips_feed)

            payload = build_telemetry_payload(alerts_summary, trips_summary)
            publish_payload(mqtt_client, payload)

            print("[RENFE CLIENT] Telemetría publicada correctamente")
            print(json.dumps(payload, ensure_ascii=False, indent=2))

        except Exception as e:
            print(f"[RENFE CLIENT] Error: {e}")

        time.sleep(RENFE_POLL_SECONDS)


if __name__ == "__main__":
    main()