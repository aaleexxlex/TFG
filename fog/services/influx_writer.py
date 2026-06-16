from datetime import datetime, timezone

from influxdb_client import InfluxDBClient, Point, WritePrecision


INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "tfg-token"
INFLUX_ORG = "tfg"
INFLUX_BUCKET = "fog_data"


def safe_float(value, default=0.0):
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int_bool(value):
    return 1 if bool(value) else 0


def safe_tag(value, default="unknown"):
    if value is None or value == "":
        return default
    return str(value)


class InfluxWriter:
    def __init__(self):
        self.client = InfluxDBClient(
            url=INFLUX_URL,
            token=INFLUX_TOKEN,
            org=INFLUX_ORG,
        )
        self.write_api = self.client.write_api()

    def write_observation(self, obs: dict):
        try:
            timestamp = obs.get("timestamp")

            if timestamp:
                dt = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
            else:
                dt = datetime.now(timezone.utc)

            features = obs.get("features", {}) or {}

            point = (
                Point("anomalies")
                # TAGS
                .tag("source", safe_tag(obs.get("source"), "fog"))
                .tag("location", safe_tag(obs.get("location")))
                .tag("target_area", safe_tag(obs.get("target_area")))
                .tag("fusion_quality", safe_tag(obs.get("fusion_quality")))
                .tag("decision_mode", safe_tag(obs.get("decision_mode")))
                .tag("severity", safe_tag(obs.get("final_severity")))
                .tag("rule_severity", safe_tag(obs.get("rule_severity")))
                .tag("dominant_node", safe_tag(obs.get("dominant_node")))

                # SCORES PRINCIPALES
                .field("final_score", safe_float(obs.get("final_score")))
                .field("rule_score", safe_float(obs.get("rule_score")))
                .field("ml_score", safe_float(obs.get("ml_score"), default=-1.0))
                .field("graph_score", safe_float(obs.get("graph_score")))
                .field("criticality_score", safe_float(obs.get("criticality_score")))

                # FLAGS
                .field("final_anomaly", safe_int_bool(obs.get("final_anomaly")))
                .field("rule_anomaly", safe_int_bool(obs.get("rule_anomaly")))
                .field("aemet_included", safe_int_bool(obs.get("aemet_included")))
                .field("ree_included", safe_int_bool(obs.get("ree_included")))

                # CALIDAD TEMPORAL
                .field("aemet_age_seconds", safe_float(obs.get("aemet_age_seconds")))
                .field("ree_age_seconds", safe_float(obs.get("ree_age_seconds")))
                .field("delta_dgt_renfe_seconds", safe_float(obs.get("delta_dgt_renfe_seconds")))

                # DGT
                .field("dgt_incident_count", safe_float(features.get("dgt_incident_count")))
                .field("dgt_severity_medium_count", safe_float(features.get("dgt_severity_medium_count")))
                .field("dgt_severity_high_count", safe_float(features.get("dgt_severity_high_count")))
                .field("dgt_severity_highest_count", safe_float(features.get("dgt_severity_highest_count")))
                .field("dgt_affected_municipality_count", safe_float(features.get("dgt_affected_municipality_count")))
                .field("dgt_affected_road_count", safe_float(features.get("dgt_affected_road_count")))
                .field("dgt_abnormal_traffic_count", safe_float(features.get("dgt_type_sit_AbnormalTraffic_count")))

                # RENFE
                .field("renfe_incident_count", safe_float(features.get("renfe_incident_count")))
                .field("renfe_affected_line_count", safe_float(features.get("renfe_affected_line_count")))
                .field("renfe_infrastructure_alert_count", safe_float(features.get("renfe_infrastructure_alert_count")))
                .field("renfe_service_cut_alert_count", safe_float(features.get("renfe_service_cut_alert_count")))
                .field("renfe_mean_delay_seconds", safe_float(features.get("renfe_mean_delay_seconds")))
                .field("renfe_max_delay_seconds", safe_float(features.get("renfe_max_delay_seconds")))

                # AEMET
                .field("aemet_temperature", safe_float(features.get("aemet_temperature")))
                .field("aemet_humidity", safe_float(features.get("aemet_humidity")))
                .field("aemet_pressure", safe_float(features.get("aemet_pressure")))
                .field("aemet_precipitation", safe_float(features.get("aemet_precipitation")))
                .field("aemet_wind_speed", safe_float(features.get("aemet_wind_speed")))

                # REE
                .field("ree_wind_generation", safe_float(features.get("ree_wind_generation")))
                .field("ree_solar_generation", safe_float(features.get("ree_solar_generation")))

                .time(dt, WritePrecision.S)
            )

            self.write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)

            print("[FOG] Escrito en InfluxDB")

        except Exception as e:
            print(f"[FOG] Error escribiendo en InfluxDB: {e}")