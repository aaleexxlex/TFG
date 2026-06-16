from cloud.training.train_model import train_model
from cloud.model_registry.registry import save_model


def main():
    print("[CLOUD] Iniciando entrenamiento...")

    result = train_model()

    if result is None:
        print("[CLOUD] No se ha entrenado modelo")
        return

    model, features, num_rows, metrics = result

    save_model(model, features, num_rows, metrics)

    print("[CLOUD] Entrenamiento completado")


if __name__ == "__main__":
    main()