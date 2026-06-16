import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from shared.config import (
    DGT_URL,
    DGT_TIMEOUT_SECONDS,
    MQTT_BROKER,
    MQTT_PORT,
    MQTT_KEEPALIVE,
    TOPIC_DGT,
)

import json
import time
import paho.mqtt.client as mqtt


NAMESPACES = {
    "sit": "http://levelC/schema/3/situation",
    "com": "http://levelC/schema/3/common",
    "loc": "http://levelC/schema/3/locationReferencing",
    "loces": "http://levelC/schema/3/locationReferencingSpanishExtension",
}


TARGET_PROVINCE = "Madrid"
TARGET_AUTONOMOUS_COMMUNITY = "Comunidad de Madrid"


def _safe_text(element, path, namespaces, default=None):
    if element is None:
        return default

    value = element.findtext(path, default=default, namespaces=namespaces)
    if isinstance(value, str):
        return value.strip()
    return value


def _safe_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def extract_record_location_info(record):
    """
    Extrae provincia, comunidad, municipio y coordenadas
    desde el bloque locationReference del situationRecord.
    """
    province = _safe_text(
        record,
        ".//loces:province",
        NAMESPACES,
        default=None
    )

    autonomous_community = _safe_text(
        record,
        ".//loces:autonomousCommunity",
        NAMESPACES,
        default=None
    )

    municipality = _safe_text(
        record,
        ".//loces:municipality",
        NAMESPACES,
        default=None
    )

    latitude = _safe_float(
        _safe_text(record, ".//loc:latitude", NAMESPACES, default=None)
    )

    longitude = _safe_float(
        _safe_text(record, ".//loc:longitude", NAMESPACES, default=None)
    )

    return {
        "province": province,
        "autonomous_community": autonomous_community,
        "municipality": municipality,
        "latitude": latitude,
        "longitude": longitude,
    }


def is_madrid_incident(location_info: dict) -> bool:
    province = location_info.get("province")
    autonomous_community = location_info.get("autonomous_community")

    if province == TARGET_PROVINCE:
        return True

    if autonomous_community == TARGET_AUTONOMOUS_COMMUNITY:
        return True

    return False


def fetch_dgt_summary():
    """
    Descarga el feed DATEX2 de DGT y devuelve una telemetría resumida
    filtrada a la Comunidad/Provincia de Madrid.
    """
    response = requests.get(DGT_URL, timeout=DGT_TIMEOUT_SECONDS)
    response.raise_for_status()

    root = ET.fromstring(response.content)

    publication_time = _safe_text(
        root,
        ".//com:publicationTime",
        NAMESPACES,
        default=None
    )
    timestamp = publication_time or datetime.now(timezone.utc).isoformat()

    situations = root.findall(".//sit:situation", NAMESPACES)

    total_incidents = 0
    low_count = 0
    medium_count = 0
    high_count = 0
    highest_count = 0
    unknown_count = 0
    active_count = 0
    certain_count = 0

    event_type_counts = {}

    skipped_outside_madrid_count = 0
    missing_location_info_count = 0

    municipalities = set()
    roads = set()

    for situation in situations:
        record = situation.find(".//sit:situationRecord", NAMESPACES)
        if record is None:
            continue

        location_info = extract_record_location_info(record)

        province = location_info.get("province")
        autonomous_community = location_info.get("autonomous_community")
        municipality = location_info.get("municipality")

        if province is None and autonomous_community is None:
            missing_location_info_count += 1
            continue

        if not is_madrid_incident(location_info):
            skipped_outside_madrid_count += 1
            continue

        total_incidents += 1

        if municipality:
            municipalities.add(municipality)

        road_name = _safe_text(
            record,
            ".//loc:roadName",
            NAMESPACES,
            default=None
        )
        if road_name:
            roads.add(road_name)

        severity = _safe_text(
            record,
            ".//sit:severity",
            NAMESPACES,
            default="unknown"
        )

        if severity == "low":
            low_count += 1
        elif severity == "medium":
            medium_count += 1
        elif severity == "high":
            high_count += 1
        elif severity == "highest":
            highest_count += 1
        else:
            unknown_count += 1

        validity_status = _safe_text(
            record,
            ".//com:validityStatus",
            NAMESPACES,
            default=""
        )
        if validity_status == "active":
            active_count += 1

        probability = _safe_text(
            record,
            ".//sit:probabilityOfOccurrence",
            NAMESPACES,
            default=""
        )
        if probability == "certain":
            certain_count += 1

        event_type = record.attrib.get(
            "{http://www.w3.org/2001/XMLSchema-instance}type",
            "unknown"
        )
        event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1

    telemetry = {
        "source": "dgt",
        "timestamp": timestamp,
        "location": "madrid_road_network",
        "variables": {
            "incident_count": total_incidents,
            "severity_low_count": low_count,
            "severity_medium_count": medium_count,
            "severity_high_count": high_count,
            "severity_highest_count": highest_count,
            "severity_unknown_count": unknown_count,
            "validity_active_count": active_count,
            "probability_certain_count": certain_count,
            "missing_location_info_count": missing_location_info_count,
            "skipped_outside_madrid_count": skipped_outside_madrid_count,
            "affected_municipality_count": len(municipalities),
            "affected_road_count": len(roads),
        },
    }

    for event_type, count in event_type_counts.items():
        safe_key = event_type.replace(":", "_").replace(".", "_").replace("-", "_")
        telemetry["variables"][f"type_{safe_key}_count"] = count

    return telemetry


def main():
    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)

    print("[DGT CLIENT] Conectado a MQTT")
    print(f"[DGT CLIENT] Publicando en '{TOPIC_DGT}'")

    while True:
        try:
            telemetry = fetch_dgt_summary()

            client.publish(TOPIC_DGT, json.dumps(telemetry), qos=0, retain=False)

            print("[DGT CLIENT] Telemetría publicada:")
            print(json.dumps(telemetry, indent=2, ensure_ascii=False))

        except Exception as e:
            print(f"[DGT CLIENT] Error: {e}")

        time.sleep(60)


if __name__ == "__main__":
    main()