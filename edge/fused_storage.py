import csv
import json
import os
from typing import Any


class FusedObservationStorage:
    FIELDNAMES = [
        # Identificación general
        "timestamp",
        "target_area",
        "location",
        "fusion_quality",

        # Timestamps por fuente
        "dgt_timestamp",
        "renfe_timestamp",
        "aemet_timestamp",
        "ree_timestamp",

        # Diferencias temporales / edad del contexto
        "delta_seconds",
        "delta_dgt_renfe_seconds",
        "aemet_age_seconds",
        "ree_age_seconds",

        # Flags de inclusión
        "dgt_included",
        "renfe_included",
        "aemet_included",
        "ree_included",

        # Features DGT
        "dgt_incident_count",
        "dgt_severity_low_count",
        "dgt_severity_medium_count",
        "dgt_severity_high_count",
        "dgt_severity_highest_count",
        "dgt_severity_unknown_count",
        "dgt_validity_active_count",
        "dgt_probability_certain_count",
        "dgt_missing_location_info_count",
        "dgt_skipped_outside_madrid_count",
        "dgt_affected_municipality_count",
        "dgt_affected_road_count",
        "dgt_type_sit_RoadOrCarriagewayOrLaneManagement_count",
        "dgt_type_sit_SpeedManagement_count",
        "dgt_type_sit_AbnormalTraffic_count",
        "dgt_type_sit_GenericSituationRecord_count",

        # Features Renfe
        "renfe_incident_count",
        "renfe_affected_route_count",
        "renfe_affected_line_count",
        "renfe_accessibility_alert_count",
        "renfe_bus_service_alert_count",
        "renfe_infrastructure_alert_count",
        "renfe_service_cut_alert_count",
        "renfe_trip_update_count",
        "renfe_delayed_trip_count",
        "renfe_cancelled_trip_count",
        "renfe_added_trip_count",
        "renfe_affected_stop_count",
        "renfe_mean_delay_seconds",
        "renfe_max_delay_seconds",
        "renfe_skipped_non_madrid_alerts",
        "renfe_skipped_non_madrid_trip_updates",
        "renfe_matched_lines_alerts",
        "renfe_matched_lines_trip_updates",

        # Features AEMET
        "aemet_temperature",
        "aemet_humidity",
        "aemet_pressure",
        "aemet_precipitation",
        "aemet_wind_speed",

        # Features REE
        "ree_wind_generation",
        "ree_solar_generation",

        # Resultado del detector
        "anomaly_detected",
        "score",
        "severity",
        "alert_message",

        # Resultado del grafo / criticidad
        "dominant_node",
        "graph_score",
        "criticality_score",

        # Gestión de alertas
        "alert_published",
        "alert_duplicate",

        # Campo auxiliar para no perder información si aparece una feature nueva
        "extra_features_json",
    ]

    def __init__(self, output_path: str = "data/fused_observations.csv"):
        self.output_path = output_path
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

    def _to_csv_value(self, value: Any):
        if isinstance(value, (list, dict)):
            return json.dumps(value, ensure_ascii=False)
        return value

    def _get_feature(self, features: dict, key: str, default=None):
        return self._to_csv_value(features.get(key, default))

    def save(self, observation: dict):
        file_exists = os.path.isfile(self.output_path)

        features = observation.get("features", {})

        known_feature_keys = set(self.FIELDNAMES)

        extra_features = {
            key: value
            for key, value in features.items()
            if key not in known_feature_keys
        }

        row = {
            # Identificación general
            "timestamp": observation.get("timestamp"),
            "target_area": observation.get("target_area", "madrid"),
            "location": observation.get("location"),
            "fusion_quality": observation.get("fusion_quality"),

            # Timestamps por fuente
            "dgt_timestamp": observation.get("dgt_timestamp"),
            "renfe_timestamp": observation.get("renfe_timestamp"),
            "aemet_timestamp": observation.get("aemet_timestamp"),
            "ree_timestamp": observation.get("ree_timestamp"),

            # Diferencias temporales / edad del contexto
            "delta_seconds": observation.get("delta_seconds"),
            "delta_dgt_renfe_seconds": observation.get("delta_dgt_renfe_seconds"),
            "aemet_age_seconds": observation.get("aemet_age_seconds"),
            "ree_age_seconds": observation.get("ree_age_seconds"),

            # Flags de inclusión
            "dgt_included": observation.get("dgt_timestamp") is not None,
            "renfe_included": observation.get("renfe_timestamp") is not None,
            "aemet_included": observation.get("aemet_included", False),
            "ree_included": observation.get("ree_included", False),

            # Features DGT
            "dgt_incident_count": self._get_feature(features, "dgt_incident_count"),
            "dgt_severity_low_count": self._get_feature(features, "dgt_severity_low_count"),
            "dgt_severity_medium_count": self._get_feature(features, "dgt_severity_medium_count"),
            "dgt_severity_high_count": self._get_feature(features, "dgt_severity_high_count"),
            "dgt_severity_highest_count": self._get_feature(features, "dgt_severity_highest_count"),
            "dgt_severity_unknown_count": self._get_feature(features, "dgt_severity_unknown_count"),
            "dgt_validity_active_count": self._get_feature(features, "dgt_validity_active_count"),
            "dgt_probability_certain_count": self._get_feature(features, "dgt_probability_certain_count"),
            "dgt_missing_location_info_count": self._get_feature(features, "dgt_missing_location_info_count"),
            "dgt_skipped_outside_madrid_count": self._get_feature(features, "dgt_skipped_outside_madrid_count"),
            "dgt_affected_municipality_count": self._get_feature(features, "dgt_affected_municipality_count"),
            "dgt_affected_road_count": self._get_feature(features, "dgt_affected_road_count"),
            "dgt_type_sit_RoadOrCarriagewayOrLaneManagement_count": self._get_feature(
                features,
                "dgt_type_sit_RoadOrCarriagewayOrLaneManagement_count"
            ),
            "dgt_type_sit_SpeedManagement_count": self._get_feature(features, "dgt_type_sit_SpeedManagement_count"),
            "dgt_type_sit_AbnormalTraffic_count": self._get_feature(features, "dgt_type_sit_AbnormalTraffic_count"),
            "dgt_type_sit_GenericSituationRecord_count": self._get_feature(
                features,
                "dgt_type_sit_GenericSituationRecord_count"
            ),

            # Features Renfe
            "renfe_incident_count": self._get_feature(features, "renfe_incident_count"),
            "renfe_affected_route_count": self._get_feature(features, "renfe_affected_route_count"),
            "renfe_affected_line_count": self._get_feature(features, "renfe_affected_line_count"),
            "renfe_accessibility_alert_count": self._get_feature(features, "renfe_accessibility_alert_count"),
            "renfe_bus_service_alert_count": self._get_feature(features, "renfe_bus_service_alert_count"),
            "renfe_infrastructure_alert_count": self._get_feature(features, "renfe_infrastructure_alert_count"),
            "renfe_service_cut_alert_count": self._get_feature(features, "renfe_service_cut_alert_count"),
            "renfe_trip_update_count": self._get_feature(features, "renfe_trip_update_count"),
            "renfe_delayed_trip_count": self._get_feature(features, "renfe_delayed_trip_count"),
            "renfe_cancelled_trip_count": self._get_feature(features, "renfe_cancelled_trip_count"),
            "renfe_added_trip_count": self._get_feature(features, "renfe_added_trip_count"),
            "renfe_affected_stop_count": self._get_feature(features, "renfe_affected_stop_count"),
            "renfe_mean_delay_seconds": self._get_feature(features, "renfe_mean_delay_seconds"),
            "renfe_max_delay_seconds": self._get_feature(features, "renfe_max_delay_seconds"),
            "renfe_skipped_non_madrid_alerts": self._get_feature(features, "renfe_skipped_non_madrid_alerts"),
            "renfe_skipped_non_madrid_trip_updates": self._get_feature(features, "renfe_skipped_non_madrid_trip_updates"),
            "renfe_matched_lines_alerts": self._get_feature(features, "renfe_matched_lines_alerts"),
            "renfe_matched_lines_trip_updates": self._get_feature(features, "renfe_matched_lines_trip_updates"),

            # Features AEMET
            "aemet_temperature": self._get_feature(features, "aemet_temperature"),
            "aemet_humidity": self._get_feature(features, "aemet_humidity"),
            "aemet_pressure": self._get_feature(features, "aemet_pressure"),
            "aemet_precipitation": self._get_feature(features, "aemet_precipitation"),
            "aemet_wind_speed": self._get_feature(features, "aemet_wind_speed"),

            # Features REE
            "ree_wind_generation": self._get_feature(features, "ree_wind_generation"),
            "ree_solar_generation": self._get_feature(features, "ree_solar_generation"),

            # Resultado del detector
            "anomaly_detected": observation.get("anomaly_detected"),
            "score": observation.get("score"),
            "severity": observation.get("severity"),
            "alert_message": observation.get("alert_message"),

            # Resultado del grafo / criticidad
            "dominant_node": observation.get("dominant_node"),
            "graph_score": observation.get("graph_score"),
            "criticality_score": observation.get("criticality_score"),

            # Gestión de alertas
            "alert_published": observation.get("alert_published"),
            "alert_duplicate": observation.get("alert_duplicate"),

            # Extras
            "extra_features_json": json.dumps(extra_features, ensure_ascii=False, default=str),
        }

        with open(self.output_path, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=self.FIELDNAMES,
                extrasaction="ignore"
            )

            if not file_exists:
                writer.writeheader()

            writer.writerow(row)