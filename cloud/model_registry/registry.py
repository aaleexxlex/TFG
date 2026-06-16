import os
import json
import joblib
from datetime import datetime

MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "latest_model.joblib")
METADATA_PATH = os.path.join(MODEL_DIR, "metadata.json")


def save_model(model, features, num_rows, metrics=None):
    os.makedirs(MODEL_DIR, exist_ok=True)

    joblib.dump(
        {
            "model": model,
            "features": features,
            "target": "score",
            "task": "regression",
        },
        MODEL_PATH,
    )

    metadata = {
        "trained_at": datetime.now().isoformat(),
        "num_rows": num_rows,
        "num_features": len(features),
        "model_type": "RandomForestRegressor",
        "target": "score",
        "task": "regression",
        "features": features,
        "metrics": metrics or {},
    }

    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"[MODEL REGISTRY] Modelo guardado en {MODEL_PATH}")
    print(f"[MODEL REGISTRY] Metadata guardada en {METADATA_PATH}")