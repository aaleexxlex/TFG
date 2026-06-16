import pandas as pd

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

    clean_df = pd.DataFrame({
        "dgt_incidents": df.iloc[:, 21],
        "dgt_severity_high": df.iloc[:, 19],
        "dgt_severity_highest": df.iloc[:, 20],

        "renfe_alerts": df.iloc[:, 32],
        "renfe_lines_affected": df.iloc[:, 33],

        "aemet_temp": df.iloc[:, 50],
        "aemet_wind": df.iloc[:, 51],
        "aemet_rain": df.iloc[:, 52],

        "ree_demand": df.iloc[:, 55],
        "ree_wind": df.iloc[:, 56],

        "fusion_quality": df.iloc[:, 3],
        "rules_score": df.iloc[:, 58],
        "score": df.iloc[:, 58],
        "severity": df.iloc[:, 59],
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