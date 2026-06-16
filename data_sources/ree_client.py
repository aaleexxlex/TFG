from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import json
import time

import requests
import paho.mqtt.client as mqtt

from shared.config import (
    REE_BASE_URL,
    MQTT_BROKER,
    MQTT_PORT,
    MQTT_KEEPALIVE,
    TOPIC_REE,
)
from shared.schemas import TelemetryMessage


# REE se usa como contexto energético agregado, no como fuente operativa en tiempo real.
REE_POLL_SECONDS = 1800  # 30 minutos

# Para balance-electrico, en tu caso hour falla. day es lo estable.
REE_TIME_TRUNC = "day"

# Comunidad de Madrid en REData. Si el widget no lo acepta, se hace fallback.
REE_MADRID_GEO_ID = "13"


def _iso_no_seconds(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M")


def _build_time_range(days_back: int = 7) -> tuple[str, str]:
    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=days_back)
    return _iso_no_seconds(start_dt), _iso_no_seconds(end_dt)


def _call_ree_api(
    category: str,
    widget: str,
    days_back: int = 7,
    use_madrid: bool = False,
) -> Dict[str, Any]:
    start_date, end_date = _build_time_range(days_back)

    url = f"{REE_BASE_URL}/{category}/{widget}"

    params = {
        "start_date": start_date,
        "end_date": end_date,
        "time_trunc": REE_TIME_TRUNC,
    }

    if use_madrid:
        params.update({
            "geo_trunc": "electric_system",
            "geo_limit": "ccaa",
            "geo_ids": REE_MADRID_GEO_ID,
        })

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    response = requests.get(url, params=params, headers=headers, timeout=30)

    if response.status_code != 200:
        print(f"[REE ERROR] status={response.status_code}")
        print(f"[REE ERROR] url={response.url}")
        print(f"[REE ERROR] body={response.text[:1000]}")
        response.raise_for_status()

    return response.json()


def _parse_ree_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None

    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt


def _extract_latest_nested_value_by_title(
    payload: Dict[str, Any],
    expected_titles: list[str],
) -> Optional[float]:
    included = payload.get("included", [])
    candidates = []

    for group in included:
        group_attrs = group.get("attributes", {})
        content = group_attrs.get("content", [])

        for item in content:
            attrs = item.get("attributes", {})
            title = attrs.get("title", "")
            values = attrs.get("values", [])

            if title not in expected_titles:
                continue

            for value_item in values:
                raw_value = value_item.get("value")
                raw_datetime = value_item.get("datetime")
                parsed_datetime = _parse_ree_datetime(raw_datetime)

                if raw_value is None or parsed_datetime is None:
                    continue

                try:
                    numeric_value = float(raw_value)
                except (TypeError, ValueError):
                    continue

                candidates.append((parsed_datetime, numeric_value))

    if not candidates:
        return None

    latest_datetime, latest_value = max(candidates, key=lambda item: item[0])
    return latest_value


def _extract_latest_nested_datetime(payload: Dict[str, Any]) -> Optional[str]:
    included = payload.get("included", [])
    candidates = []

    for group in included:
        group_attrs = group.get("attributes", {})
        content = group_attrs.get("content", [])

        for item in content:
            attrs = item.get("attributes", {})
            values = attrs.get("values", [])

            for value_item in values:
                raw_datetime = value_item.get("datetime")
                parsed_datetime = _parse_ree_datetime(raw_datetime)

                if parsed_datetime is not None:
                    candidates.append(parsed_datetime)

    if not candidates:
        return None

    return max(candidates).isoformat()


def fetch_ree_balance(days_back: int = 7) -> dict:
    location = "Comunidad de Madrid"

    try:
        payload = _call_ree_api(
            "balance",
            "balance-electrico",
            days_back=days_back,
            use_madrid=True,
        )
        print("[REE CLIENT] Datos obtenidos para Comunidad de Madrid")

    except Exception as e:
        print(f"[REE CLIENT] No se pudo obtener REE para Comunidad de Madrid: {e}")
        print("[REE CLIENT] Usando fallback nacional/peninsular")

        payload = _call_ree_api(
            "balance",
            "balance-electrico",
            days_back=days_back,
            use_madrid=False,
        )
        location = "Spain"

    wind = _extract_latest_nested_value_by_title(
        payload,
        ["Eólica", "Wind"]
    )

    solar = _extract_latest_nested_value_by_title(
        payload,
        ["Solar fotovoltaica", "Solar photovoltaic"]
    )

    timestamp = _extract_latest_nested_datetime(payload)

    if timestamp is None:
        timestamp = datetime.now(timezone.utc).isoformat()

    telemetry = TelemetryMessage(
        source="ree",
        timestamp=timestamp,
        location=location,
        variables={
            "wind_generation": wind,
            "solar_generation": solar,
        },
    )

    return telemetry.model_dump(mode="json")


def publish_payload(client: mqtt.Client, payload: dict) -> None:
    # retain=True es importante para fuentes lentas/contextuales.
    # Así edge.main recibe el último dato aunque arranque después.
    result = client.publish(TOPIC_REE, json.dumps(payload), qos=1, retain=True)

    if result.rc != 0:
        print(f"[REE CLIENT] Error publicando en MQTT. Código: {result.rc}")
    else:
        print("[REE CLIENT] Telemetría publicada y retenida en MQTT")


def main():
    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)

    print("[REE CLIENT] Conectado a MQTT")
    print(f"[REE CLIENT] Publicando en '{TOPIC_REE}'")

    while True:
        try:
            data = fetch_ree_balance()
            publish_payload(client, data)

            print("[REE CLIENT] Telemetría publicada:")
            print(json.dumps(data, indent=2, ensure_ascii=False))

        except Exception as e:
            print(f"[REE CLIENT] Error: {e}")

        time.sleep(REE_POLL_SECONDS)


if __name__ == "__main__":
    main()