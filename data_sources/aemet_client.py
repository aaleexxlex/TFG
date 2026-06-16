import json
import time
from datetime import datetime, timezone
from typing import Any

import requests
import paho.mqtt.client as mqtt

from shared.config import (
    AEMET_API_KEY,
    AEMET_STATION_ID,
    AEMET_BASE_URL,
    AEMET_TIMEOUT_SECONDS,
    MQTT_BROKER,
    MQTT_PORT,
    MQTT_KEEPALIVE,
    TOPIC_AEMET,
)
from shared.schemas import TelemetryMessage


# Consultar cada 10 minutos es más razonable que cada 5.
# Si la estación solo actualiza datos horarios, consultar cada 5 minutos no mejora nada.
AEMET_POLL_SECONDS = 600


class AemetClient:
    def __init__(self, api_key=None, station_id=None, timeout=None):
        self.api_key = api_key or AEMET_API_KEY
        self.station_id = station_id or AEMET_STATION_ID
        self.timeout = timeout or AEMET_TIMEOUT_SECONDS

        if not self.api_key:
            raise ValueError("Falta AEMET_API_KEY en config.py")
        if not self.station_id:
            raise ValueError("Falta AEMET_STATION_ID en config.py")

    def _call_opendata_endpoint(self, endpoint: str):
        url = f"{AEMET_BASE_URL}{endpoint}"

        response = requests.get(
            url,
            params={"api_key": self.api_key},
            timeout=self.timeout
        )
        response.raise_for_status()

        envelope = response.json()

        if envelope.get("estado") not in (200, 0) or not envelope.get("datos"):
            raise RuntimeError(f"Respuesta AEMET inválida: {envelope}")

        data_url = envelope["datos"]

        data_response = requests.get(data_url, timeout=self.timeout)
        data_response.raise_for_status()

        return data_response.json()

    @staticmethod
    def _to_float(value: Any):
        if value is None or value == "":
            return None

        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            value = value.strip().replace(",", ".")
            try:
                return float(value)
            except ValueError:
                return None

        return None

    @staticmethod
    def _pick_first(d: dict, keys: list[str]):
        for key in keys:
            if key in d and d[key] not in (None, ""):
                return d[key]
        return None

    @staticmethod
    def _parse_aemet_timestamp(value: Any):
        if value is None or value == "":
            return None

        if isinstance(value, datetime):
            dt = value
        else:
            raw = str(value).strip()

            # AEMET suele devolver formato ISO, por ejemplo:
            # 2026-04-30T22:00:00
            # o con zona horaria.
            try:
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except ValueError:
                return None

        if dt.tzinfo is None:
            # AEMET suele dar la hora local de la estación si no aparece zona.
            # Para el prototipo lo dejamos como UTC si viene sin zona para evitar errores.
            # Si quieres hilar fino, aquí se podría asignar Europe/Madrid.
            dt = dt.replace(tzinfo=timezone.utc)

        return dt

    def fetch_station_observation(self) -> dict:
        endpoint = f"/observacion/convencional/datos/estacion/{self.station_id}"
        data = self._call_opendata_endpoint(endpoint)

        if isinstance(data, dict):
            return data

        if not isinstance(data, list):
            raise RuntimeError(f"Formato inesperado en observación AEMET: {type(data)}")

        if not data:
            raise RuntimeError("AEMET devolvió una lista vacía")

        valid_observations = []

        for obs in data:
            if not isinstance(obs, dict):
                continue

            raw_ts = self._pick_first(obs, ["fint", "fecha", "timestamp"])
            parsed_ts = self._parse_aemet_timestamp(raw_ts)

            if parsed_ts is not None:
                valid_observations.append((parsed_ts, obs))

        if not valid_observations:
            raise RuntimeError(f"No se encontró timestamp válido en observaciones AEMET: {data}")

        # Aquí está la corrección importante:
        # elegimos la observación más reciente, no la primera de la lista.
        latest_ts, latest_obs = max(valid_observations, key=lambda item: item[0])

        print(f"[AEMET CLIENT] Observaciones recibidas: {len(data)}")
        print(f"[AEMET CLIENT] Observación más reciente seleccionada: {latest_ts.isoformat()}")

        return latest_obs

    def get_telemetry(self) -> TelemetryMessage:
        obs = self.fetch_station_observation()

        raw_ts = self._pick_first(obs, ["fint", "fecha", "timestamp"])
        timestamp = raw_ts or datetime.now(timezone.utc).isoformat()

        variables = {}

        temperature = self._to_float(self._pick_first(obs, ["ta", "temperatura", "temp"]))
        humidity = self._to_float(self._pick_first(obs, ["hr", "humedad"]))
        pressure = self._to_float(self._pick_first(obs, ["pres", "p"]))
        precipitation = self._to_float(self._pick_first(obs, ["prec", "precipitacion"]))

        # En AEMET la velocidad del viento puede venir con distintas claves según producto/estación.
        wind_speed = self._to_float(self._pick_first(obs, ["vv", "viento", "vel", "vmax"]))

        if temperature is not None:
            variables["temperature"] = temperature
        if humidity is not None:
            variables["humidity"] = humidity
        if pressure is not None:
            variables["pressure"] = pressure
        if precipitation is not None:
            variables["precipitation"] = precipitation
        if wind_speed is not None:
            variables["wind_speed"] = wind_speed

        return TelemetryMessage(
            source="aemet",
            timestamp=timestamp,
            location=self.station_id,
            variables=variables,
        )


def publish_payload(client: mqtt.Client, payload: dict) -> None:
    result = client.publish(TOPIC_AEMET, json.dumps(payload), qos=0, retain=False)

    if result.rc != 0:
        print(f"[AEMET CLIENT] Error publicando en MQTT. Código: {result.rc}")


def main():
    aemet_client = AemetClient()

    mqtt_client = mqtt.Client()
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)

    print("[AEMET CLIENT] Conectado a MQTT")
    print(f"[AEMET CLIENT] Publicando en '{TOPIC_AEMET}'")

    while True:
        try:
            telemetry = aemet_client.get_telemetry()
            payload = telemetry.model_dump(mode="json")

            publish_payload(mqtt_client, payload)

            print("[AEMET CLIENT] Telemetría publicada:")
            print(json.dumps(payload, indent=2, ensure_ascii=False))

        except Exception as e:
            print(f"[AEMET CLIENT] Error: {e}")

        time.sleep(AEMET_POLL_SECONDS)


if __name__ == "__main__":
    main()