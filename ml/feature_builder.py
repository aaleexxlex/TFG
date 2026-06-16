NUMERIC_FEATURES = [
    "dgt_incidents",
    "dgt_severity_high",
    "dgt_severity_highest",
    "renfe_alerts",
    "renfe_lines_affected",
    "aemet_temp",
    "aemet_wind",
    "aemet_rain",
    "ree_demand",
    "ree_wind",
    "fusion_quality",
]


def build_feature_row_from_observation(observation: dict) -> dict:
    f = observation.get("features", {})

    fusion_quality_map = {
        "complete": 1.0,
        "partial": 0.5,
        "incomplete": 0.0,
    }

    fusion_quality = observation.get("fusion_quality", 0)

    if isinstance(fusion_quality, str):
        fusion_quality = fusion_quality_map.get(fusion_quality.lower(), 0.0)

    row = {
        "dgt_incidents": f.get("dgt_incident_count", 0),
        "dgt_severity_high": f.get("dgt_severity_high_count", 0),
        "dgt_severity_highest": f.get("dgt_severity_highest_count", 0),

        "renfe_alerts": f.get("renfe_incident_count", 0),
        "renfe_lines_affected": f.get("renfe_affected_line_count", 0),

        "aemet_temp": f.get("aemet_temperature", 0),
        "aemet_wind": f.get("aemet_wind_speed", 0),
        "aemet_rain": f.get("aemet_precipitation", 0),

        "ree_demand": f.get("ree_demand", 0),
        "ree_wind": f.get("ree_wind_generation", 0),

        "fusion_quality": fusion_quality,
    }

    return row
