import os
from dotenv import load_dotenv

load_dotenv()

# REE
REE_BASE_URL = "https://apidatos.ree.es/es/datos"
REE_TIME_TRUNC = "day"

# AEMET
AEMET_API_KEY = os.getenv("AEMET_API_KEY")
AEMET_STATION_ID = "3195"  # Madrid-Retiro
AEMET_BASE_URL = "https://opendata.aemet.es/opendata/api"
AEMET_TIMEOUT_SECONDS = 20

# DGT
DGT_URL = "https://nap.dgt.es/datex2/v3/dgt/SituationPublication/datex2_v36.xml"
DGT_TIMEOUT_SECONDS = 20
TOPIC_DGT = "telemetry/dgt"

# RENFE
RENFE_ALERTS_URL = "https://gtfsrt.renfe.com/alerts.json"
RENFE_TRIP_UPDATES_URL = "https://gtfsrt.renfe.com/trip_updates.json"
RENFE_REQUEST_TIMEOUT = 20
RENFE_POLL_SECONDS = 20
TOPIC_RENFE = "telemetry/renfe"

# MQTT
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_KEEPALIVE = 60

TOPIC_REE = "telemetry/ree"
TOPIC_AEMET = "telemetry/aemet"

# Alerta generada directamente por Edge
TOPIC_ALERTS = "alerts/anomaly"

# Observaciones enriquecidas que publica Edge para que Fog las consuma
TOPIC_FUSED_OBSERVATIONS = "edge/fused_observations"

# Alerta final que publicará Fog tras combinar reglas + ML
TOPIC_FINAL_ALERTS = "alerts/final"

# FUSIÓN
FUSION_MAX_DELTA_SECONDS = 3600  # 1 hora

# HISTÓRICO
FUSED_OBSERVATIONS_PATH = "data/fused_observations.csv"