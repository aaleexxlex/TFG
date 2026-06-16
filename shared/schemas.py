from datetime import datetime
from typing import Any
from pydantic import BaseModel


class TelemetryMessage(BaseModel):
    source: str
    timestamp: datetime
    location: str | None = None
    variables: dict[str, Any]


class AlertMessage(BaseModel):
    source: str
    timestamp: datetime
    severity: str
    anomaly_score: float
    message: str
    variables: dict[str, Any]