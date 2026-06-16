import os
import time
import json
import pandas as pd

from ml.preprocessing import clean_csv
from cloud.retrain import main as retrain_main

RAW_CSV = "data/fused_observations.csv"
CLEAN_CSV = "data/fused_clean.csv"
METADATA_PATH = "models/metadata.json"

RETRAIN_INTERVAL_SECONDS = 300
MIN_NEW_ROWS = 30


def get_last_trained_rows():
    if not os.path.exists(METADATA_PATH):
        return 0

    with open(METADATA_PATH, "r") as f:
        data = json.load(f)

    return data.get("num_rows", 0)


def main():
    print("[CLOUD] Servicio de entrenamiento inteligente iniciado")

    while True:
        try:
            clean_csv(RAW_CSV, CLEAN_CSV)

            df = pd.read_csv(CLEAN_CSV)
            current_rows = len(df)
            last_rows = get_last_trained_rows()

            print(f"[CLOUD] Filas actuales: {current_rows}, últimas entrenadas: {last_rows}")

            if current_rows - last_rows >= MIN_NEW_ROWS:
                print("[CLOUD] Reentrenando modelo...")
                retrain_main()
            else:
                print("[CLOUD] No hay suficientes datos nuevos para reentrenar")

        except Exception as e:
            print(f"[CLOUD] Error: {e}")

        time.sleep(RETRAIN_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()