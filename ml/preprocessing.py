import pandas as pd
from edge.fused_storage import FusedObservationStorage

SEVERITY_MAP = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "critical": 3,
    "unknown": 0,
}

FUSION_QUALITY_MAP = {
    "complete": 1.0,
    "partial": 0.5,
    "incomplete": 0.0,
}


def clean_csv(input_path, output_path):
    df = pd.read_csv(input_path, header=None)

    # Assign correct column names from the official storage scheme
    df.columns = FusedObservationStorage.FIELDNAMES[:len(df.columns)]

    clean_df = pd.DataFrame({
        "dgt_incidents": df["dgt_incident_count"],
        "dgt_severity_high": df["dgt_severity_high_count"],
        "dgt_severity_highest": df["dgt_severity_highest_count"],

        "renfe_alerts": df["renfe_incident_count"],
        "renfe_lines_affected": df["renfe_affected_line_count"],

        "aemet_temp": df["aemet_temperature"],
        "aemet_wind": df["aemet_wind_speed"],
        "aemet_rain": df["aemet_precipitation"],

        "ree_demand": 0.0,  # ree_demand doesn't exist in saved features; default to 0.0
        "ree_wind": df["ree_wind_generation"],

        "fusion_quality": df["fusion_quality"],
        "rules_score": df["score"],
        "score": df["score"],
        "severity": df["severity"],
    })

    clean_df["fusion_quality"] = (
        clean_df["fusion_quality"]
        .map(FUSION_QUALITY_MAP)
        .fillna(0)
    )

    clean_df["severity"] = (
        clean_df["severity"]
        .map(SEVERITY_MAP)
        .fillna(0)
    )

    for col in clean_df.columns:
        clean_df[col] = pd.to_numeric(clean_df[col], errors="coerce").fillna(0)

    clean_df.to_csv(output_path, index=False)

    print(f"[ML] CSV limpio generado en {output_path}")
    print(f"[ML] Filas: {len(clean_df)}")
    print(f"[ML] Score únicos: {clean_df['score'].nunique()}")