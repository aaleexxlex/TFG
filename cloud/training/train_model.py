import os
import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from ml.feature_builder import NUMERIC_FEATURES

CSV_PATH = "data/fused_clean.csv"
TARGET = "score"


def load_data():
    if not os.path.exists(CSV_PATH):
        raise ValueError(f"No existe {CSV_PATH}. Primero genera el CSV limpio.")

    df = pd.read_csv(CSV_PATH)

    if TARGET not in df.columns:
        raise ValueError(f"Falta la columna {TARGET} en el CSV")

    available_features = [f for f in NUMERIC_FEATURES if f in df.columns]

    if not available_features:
        raise ValueError("No hay features numéricas disponibles para entrenar")

    df = df[available_features + [TARGET]].copy()

    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df, available_features


def train_model():
    df, features = load_data()

    if len(df) < 30:
        print(f"[CLOUD] Muy pocos datos ({len(df)} filas). Espera más histórico.")
        return None

    X = df[features]
    y = df[TARGET].astype(float)

    if y.nunique() < 3:
        print("[CLOUD] El score tiene muy poca variabilidad. Deja correr más tiempo.")
        print("[CLOUD] Valores distintos:", sorted(y.unique()))
        return None

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
    )

    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=10,
        min_samples_leaf=2,
        random_state=42,
    )

    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    print("\n[CLOUD] Evaluación modelo de regresión:")
    print(f"MAE:  {mae:.4f}")
    print(f"RMSE: {rmse:.4f}")
    print(f"R2:   {r2:.4f}")

    return model, features, len(df), {
        "mae": float(mae),
        "rmse": float(rmse),
        "r2": float(r2),
        "target": TARGET,
        "task": "regression",
        "model_type": "RandomForestRegressor",
    }