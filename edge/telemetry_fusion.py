from datetime import datetime


class TelemetryFusionBuffer:
    """
    Fusión defendible para el TFG:

    - Núcleo rápido obligatorio: DGT + RENFE
    - Contexto opcional: AEMET + REE

    Filosofía:
    - Las alertas rápidas salen con transporte (DGT y Renfe).
    - AEMET y REE enriquecen la observación si su antigüedad es aceptable.
    - max_delta_seconds se usa para controlar el desfase entre DGT y RENFE.
    """

    def __init__(
        self,
        max_delta_seconds: int = 3600,
        aemet_max_age_seconds: int = 86400,
        ree_max_age_seconds: int = 86400,
    ):
        self.max_delta_seconds = max_delta_seconds
        self.aemet_max_age_seconds = aemet_max_age_seconds
        self.ree_max_age_seconds = ree_max_age_seconds

        self.last_messages = {
            "ree": None,
            "aemet": None,
            "dgt": None,
            "renfe": None,
        }

    @staticmethod
    def _parse_ts(ts):
        if isinstance(ts, datetime):
            return ts
        if isinstance(ts, str):
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        raise TypeError(f"Tipo de timestamp no soportado: {type(ts)}")

    def update(self, telemetry):
        if telemetry.source in self.last_messages:
            self.last_messages[telemetry.source] = telemetry

    # ==========================================================
    # BLOQUE RÁPIDO: DGT + RENFE
    # ==========================================================
    def _fast_available(self) -> bool:
        return (
            self.last_messages["dgt"] is not None
            and self.last_messages["renfe"] is not None
        )

    def _fast_delta_seconds(self):
        if not self._fast_available():
            return None

        dgt_ts = self._parse_ts(self.last_messages["dgt"].timestamp)
        renfe_ts = self._parse_ts(self.last_messages["renfe"].timestamp)

        return abs((dgt_ts - renfe_ts).total_seconds())

    def can_fuse(self) -> bool:
        delta = self._fast_delta_seconds()
        return delta is not None and delta <= self.max_delta_seconds

    # ==========================================================
    # FUENTES CONTEXTUALES: AEMET + REE
    # ==========================================================
    def _reference_ts(self):
        """
        Usamos DGT como referencia temporal principal del bloque rápido.
        """
        if self.last_messages["dgt"] is None:
            return None
        return self._parse_ts(self.last_messages["dgt"].timestamp)

    def _aemet_age_seconds(self):
        if self.last_messages["aemet"] is None:
            return None

        ref_ts = self._reference_ts()
        if ref_ts is None:
            return None

        aemet_ts = self._parse_ts(self.last_messages["aemet"].timestamp)
        return abs((ref_ts - aemet_ts).total_seconds())

    def _ree_age_seconds(self):
        if self.last_messages["ree"] is None:
            return None

        ref_ts = self._reference_ts()
        if ref_ts is None:
            return None

        ree_ts = self._parse_ts(self.last_messages["ree"].timestamp)
        return abs((ref_ts - ree_ts).total_seconds())

    def _aemet_is_usable(self) -> bool:
        age = self._aemet_age_seconds()
        return age is not None and age <= self.aemet_max_age_seconds

    def _ree_is_usable(self) -> bool:
        age = self._ree_age_seconds()
        return age is not None and age <= self.ree_max_age_seconds

    # ==========================================================
    # CONSTRUCCIÓN DE OBSERVACIÓN
    # ==========================================================
    def build_joint_observation(self):
        if not self.can_fuse():
            return None

        dgt = self.last_messages["dgt"]
        renfe = self.last_messages["renfe"]
        aemet = self.last_messages["aemet"]
        ree = self.last_messages["ree"]

        dgt_ts = self._parse_ts(dgt.timestamp)
        renfe_ts = self._parse_ts(renfe.timestamp)

        features = {}

        # --------------------------
        # Núcleo rápido obligatorio
        # --------------------------
        for key, value in dgt.variables.items():
            features[f"dgt_{key}"] = value

        for key, value in renfe.variables.items():
            features[f"renfe_{key}"] = value

        # --------------------------
        # Contexto AEMET opcional
        # --------------------------
        aemet_included = False
        aemet_age = self._aemet_age_seconds()

        if aemet is not None and self._aemet_is_usable():
            for key, value in aemet.variables.items():
                features[f"aemet_{key}"] = value
            aemet_included = True

        # --------------------------
        # Contexto REE opcional
        # --------------------------
        ree_included = False
        ree_age = self._ree_age_seconds()

        if ree is not None and self._ree_is_usable():
            for key, value in ree.variables.items():
                features[f"ree_{key}"] = value
            ree_included = True

        observation = {
            "timestamp": str(dgt.timestamp),
            "dgt_timestamp": str(dgt.timestamp),
            "renfe_timestamp": str(renfe.timestamp),
            "delta_seconds": self._fast_delta_seconds(),
            "delta_dgt_renfe_seconds": abs((dgt_ts - renfe_ts).total_seconds()),
            "location": dgt.location,
            "aemet_included": aemet_included,
            "ree_included": ree_included,
            "features": features,
        }

        if aemet is not None:
            observation["aemet_timestamp"] = str(aemet.timestamp)
            observation["aemet_age_seconds"] = aemet_age

        if ree is not None:
            observation["ree_timestamp"] = str(ree.timestamp)
            observation["ree_age_seconds"] = ree_age

        return observation