import os
import joblib
import pandas as pd

from ml.feature_builder import build_feature_row_from_observation

MODEL_PATH = "models/latest_model.joblib"


class FogMLInference:
    def __init__(self, model_path: str = MODEL_PATH):
        self.model_path = model_path
        self.model = None
        self.features = []
        self.loaded = False
        self.load_model()

    def load_model(self):
        if not os.path.exists(self.model_path):
            print("[FOG][ML] No hay modelo entrenado. Modo rules_only.")
            return

        bundle = joblib.load(self.model_path)

        self.model = bundle["model"]
        self.features = bundle["features"]
        self.loaded = True

        print(f"[FOG][ML] Modelo cargado desde {self.model_path}")
        print(f"[FOG][ML] Features del modelo: {self.features}")

    def predict_score(self, observation: dict):
        if not self.loaded:
            return None

        feature_row = build_feature_row_from_observation(observation)

        print("[FOG][ML] Feature row:", feature_row)

        X = pd.DataFrame([feature_row])
        X = X.reindex(columns=self.features, fill_value=0)
        X = X.fillna(0)

        ml_score = float(self.model.predict(X)[0])
        ml_score = max(0.0, min(1.0, ml_score))

        print(f"[FOG][ML] ml_score={ml_score:.4f}")

        return ml_score