from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class InfraNode:
    name: str
    base_weight: float
    depends_on: List[str] = field(default_factory=list)
    state_score: float = 0.0
    propagated_score: float = 0.0
    final_score: float = 0.0


DEFAULT_NODE_CONFIG = {
    "energia": {
        "base_weight": 1.00,
        "depends_on": [],
    },
    "meteorologia": {
        "base_weight": 0.70,
        "depends_on": [],
    },
    "movilidad_carretera": {
        "base_weight": 0.95,
        "depends_on": ["meteorologia"],
    },
    "movilidad_ferroviaria": {
        "base_weight": 1.00,
        "depends_on": ["energia", "meteorologia"],
    },
    "movilidad_urbana": {
        "base_weight": 1.05,
        "depends_on": ["movilidad_carretera", "movilidad_ferroviaria"],
    },
    "telecomunicaciones": {
        "base_weight": 1.10,
        "depends_on": ["energia"],
    },
    "hospitales": {
        "base_weight": 1.30,
        "depends_on": ["energia", "movilidad_urbana", "telecomunicaciones"],
    },
    "emergencias": {
        "base_weight": 1.25,
        "depends_on": ["energia", "movilidad_urbana", "telecomunicaciones"],
    },
    "logistica": {
        "base_weight": 0.85,
        "depends_on": ["movilidad_carretera", "movilidad_ferroviaria", "energia"],
    },
}


def clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    return max(min_value, min(value, max_value))


def build_nodes() -> Dict[str, InfraNode]:
    nodes = {}
    for name, cfg in DEFAULT_NODE_CONFIG.items():
        nodes[name] = InfraNode(
            name=name,
            base_weight=cfg["base_weight"],
            depends_on=cfg["depends_on"],
        )
    return nodes


def score_energia(variables: dict) -> float:
    score = 0.0

    wind_generation = variables.get("ree_wind_generation")
    solar_generation = variables.get("ree_solar_generation")
    wind_speed = variables.get("aemet_wind_speed")

    if wind_generation is not None and wind_generation < 15000:
        score += 0.45

    if solar_generation is not None and solar_generation < 40000:
        score += 0.20

    if (
        wind_speed is not None
        and wind_generation is not None
        and wind_speed > 8
        and wind_generation < 15000
    ):
        score += 0.35

    return clamp(score)


def score_meteorologia(variables: dict) -> float:
    score = 0.0

    wind_speed = variables.get("aemet_wind_speed")
    precipitation = variables.get("aemet_precipitation")

    if precipitation is not None and precipitation > 0:
        score += 0.30

    if wind_speed is not None and wind_speed > 8:
        score += 0.35
    elif wind_speed is not None and wind_speed > 6:
        score += 0.20

    return clamp(score)


def score_movilidad_carretera(variables: dict) -> float:
    score = 0.0

    incident_count = variables.get("dgt_incident_count")
    severity_high_count = variables.get("dgt_severity_high_count")
    severity_highest_count = variables.get("dgt_severity_highest_count")
    abnormal_traffic_count = variables.get("dgt_type_sit_AbnormalTraffic_count")
    affected_municipality_count = variables.get("dgt_affected_municipality_count")
    affected_road_count = variables.get("dgt_affected_road_count")

    if incident_count is not None:
        if incident_count > 80:
            score += 0.42
        elif incident_count > 45:
            score += 0.25
        elif incident_count > 25:
            score += 0.12

    if severity_high_count is not None and severity_high_count > 8:
        score += 0.15
    elif severity_high_count is not None and severity_high_count > 3:
        score += 0.08

    if severity_highest_count is not None and severity_highest_count > 0:
        score += 0.10

    if abnormal_traffic_count is not None and abnormal_traffic_count > 8:
        score += 0.10
    elif abnormal_traffic_count is not None and abnormal_traffic_count > 1:
        score += 0.04

    if affected_municipality_count is not None and affected_municipality_count > 20:
        score += 0.06

    if affected_road_count is not None and affected_road_count > 20:
        score += 0.08

    return clamp(score)


def score_movilidad_ferroviaria(variables: dict) -> float:
    score = 0.0

    renfe_incident_count = variables.get("renfe_incident_count")
    renfe_affected_line_count = variables.get("renfe_affected_line_count")
    renfe_infrastructure_alert_count = variables.get("renfe_infrastructure_alert_count")
    renfe_service_cut_alert_count = variables.get("renfe_service_cut_alert_count")
    renfe_cancelled_trip_count = variables.get("renfe_cancelled_trip_count")
    renfe_mean_delay_seconds = variables.get("renfe_mean_delay_seconds")
    renfe_max_delay_seconds = variables.get("renfe_max_delay_seconds")

    if renfe_incident_count is not None:
        if renfe_incident_count > 30:
            score += 0.40
        elif renfe_incident_count > 15:
            score += 0.22
        elif renfe_incident_count > 5:
            score += 0.10

    if renfe_affected_line_count is not None and renfe_affected_line_count >= 6:
        score += 0.15
    elif renfe_affected_line_count is not None and renfe_affected_line_count >= 3:
        score += 0.08

    if renfe_infrastructure_alert_count is not None and renfe_infrastructure_alert_count > 10:
        score += 0.16
    elif renfe_infrastructure_alert_count is not None and renfe_infrastructure_alert_count > 3:
        score += 0.10

    if renfe_service_cut_alert_count is not None and renfe_service_cut_alert_count > 1:
        score += 0.18
    elif renfe_service_cut_alert_count is not None and renfe_service_cut_alert_count > 0:
        score += 0.10

    if renfe_cancelled_trip_count is not None and renfe_cancelled_trip_count > 1:
        score += 0.10

    if renfe_mean_delay_seconds is not None and renfe_mean_delay_seconds > 600:
        score += 0.08
    elif renfe_mean_delay_seconds is not None and renfe_mean_delay_seconds > 180:
        score += 0.04

    if renfe_max_delay_seconds is not None and renfe_max_delay_seconds > 1200:
        score += 0.06
    elif renfe_max_delay_seconds is not None and renfe_max_delay_seconds > 600:
        score += 0.03

    return clamp(score)


def score_movilidad_urbana(variables: dict, node_scores: dict) -> float:
    carretera = node_scores.get("movilidad_carretera", 0.0)
    ferroviaria = node_scores.get("movilidad_ferroviaria", 0.0)

    score = (
        0.50 * carretera +
        0.50 * ferroviaria
    )
    return clamp(score)


def score_telecomunicaciones(variables: dict, node_scores: dict) -> float:
    energia_score = node_scores.get("energia", 0.0)

    if energia_score >= 0.7:
        return 0.45
    if energia_score >= 0.4:
        return 0.20
    return 0.0


def score_hospitales(variables: dict, node_scores: dict) -> float:
    energia_score = node_scores.get("energia", 0.0)
    movilidad_urbana_score = node_scores.get("movilidad_urbana", 0.0)
    telecom_score = node_scores.get("telecomunicaciones", 0.0)

    score = (
        0.40 * energia_score +
        0.35 * movilidad_urbana_score +
        0.25 * telecom_score
    )
    return clamp(score)


def score_emergencias(variables: dict, node_scores: dict) -> float:
    energia_score = node_scores.get("energia", 0.0)
    movilidad_urbana_score = node_scores.get("movilidad_urbana", 0.0)
    telecom_score = node_scores.get("telecomunicaciones", 0.0)

    score = (
        0.30 * energia_score +
        0.45 * movilidad_urbana_score +
        0.25 * telecom_score
    )
    return clamp(score)


def score_logistica(variables: dict, node_scores: dict) -> float:
    carretera_score = node_scores.get("movilidad_carretera", 0.0)
    ferroviaria_score = node_scores.get("movilidad_ferroviaria", 0.0)
    energia_score = node_scores.get("energia", 0.0)

    score = (
        0.40 * carretera_score +
        0.35 * ferroviaria_score +
        0.25 * energia_score
    )
    return clamp(score)


def compute_initial_node_scores(variables: dict) -> Dict[str, float]:
    scores = {
        "energia": score_energia(variables),
        "meteorologia": score_meteorologia(variables),
        "movilidad_carretera": score_movilidad_carretera(variables),
        "movilidad_ferroviaria": score_movilidad_ferroviaria(variables),
    }

    scores["movilidad_urbana"] = score_movilidad_urbana(variables, scores)
    scores["telecomunicaciones"] = score_telecomunicaciones(variables, scores)
    scores["hospitales"] = score_hospitales(variables, scores)
    scores["emergencias"] = score_emergencias(variables, scores)
    scores["logistica"] = score_logistica(variables, scores)

    return scores


def propagate_dependency_risk(nodes: Dict[str, InfraNode], attenuation: float = 0.55) -> None:
    for node in nodes.values():
        if not node.depends_on:
            node.propagated_score = 0.0
            node.final_score = clamp(node.state_score)
            continue

        inherited = sum(nodes[d].final_score for d in node.depends_on) / len(node.depends_on)
        node.propagated_score = attenuation * inherited
        node.final_score = clamp((0.70 * node.state_score) + (0.30 * node.propagated_score))


def compute_graph_risk(variables: dict) -> dict:
    nodes = build_nodes()
    initial_scores = compute_initial_node_scores(variables)

    for name, score in initial_scores.items():
        nodes[name].state_score = score

    for _ in range(2):
        propagate_dependency_risk(nodes, attenuation=0.55)

    node_scores = {
        name: {
            "state_score": round(node.state_score, 3),
            "propagated_score": round(node.propagated_score, 3),
            "final_score": round(node.final_score, 3),
            "base_weight": node.base_weight,
            "depends_on": node.depends_on,
        }
        for name, node in nodes.items()
    }

    weighted_sum = 0.0
    total_weight = 0.0
    for node in nodes.values():
        weighted_sum += node.final_score * node.base_weight
        total_weight += node.base_weight

    global_graph_score = weighted_sum / total_weight if total_weight > 0 else 0.0

    critical_nodes = ["hospitales", "emergencias", "telecomunicaciones"]
    criticality_score = sum(nodes[n].final_score for n in critical_nodes) / len(critical_nodes)

    top_node_name, top_node = max(
        node_scores.items(),
        key=lambda item: item[1]["final_score"]
    )

    return {
        "global_graph_score": round(clamp(global_graph_score), 3),
        "criticality_score": round(clamp(criticality_score), 3),
        "dominant_node": {
            "name": top_node_name,
            "score": round(top_node["final_score"], 3),
        },
        "node_scores": node_scores,
    }