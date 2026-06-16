from email.mime import message

from shared.critical_infra import compute_graph_risk


def detect_anomaly_dummy(variables: dict) -> tuple[bool, float, str, str]:
    """
    Detector provisional coherente con la nueva filosofía:

    - Núcleo rápido principal: DGT + RENFE
    - Contexto opcional: AEMET + REE
    - Capa adicional: grafo de dependencias de infraestructuras críticas
    """

    # ===============================
    # VARIABLES REE (CONTEXTO)
    # ===============================
    wind_generation = variables.get("ree_wind_generation")
    solar_generation = variables.get("ree_solar_generation")

    # ===============================
    # VARIABLES AEMET (CONTEXTO)
    # ===============================
    wind_speed = variables.get("aemet_wind_speed")
    temperature = variables.get("aemet_temperature")
    precipitation = variables.get("aemet_precipitation")

    # ===============================
    # VARIABLES DGT (NÚCLEO RÁPIDO)
    # ===============================
    incident_count = variables.get("dgt_incident_count")
    severity_high_count = variables.get("dgt_severity_high_count")
    severity_medium_count = variables.get("dgt_severity_medium_count")
    severity_highest_count = variables.get("dgt_severity_highest_count")
    road_lane_mgmt_count = variables.get("dgt_type_sit_RoadOrCarriagewayOrLaneManagement_count")
    obstruction_count = variables.get("dgt_type_sit_GeneralObstruction_count")
    abnormal_traffic_count = variables.get("dgt_type_sit_AbnormalTraffic_count")
    affected_municipality_count = variables.get("dgt_affected_municipality_count")
    affected_road_count = variables.get("dgt_affected_road_count")

    # ===============================
    # VARIABLES RENFE (NÚCLEO RÁPIDO)
    # ===============================
    renfe_incident_count = variables.get("renfe_incident_count")
    renfe_affected_route_count = variables.get("renfe_affected_route_count")
    renfe_affected_line_count = variables.get("renfe_affected_line_count")
    renfe_accessibility_alert_count = variables.get("renfe_accessibility_alert_count")
    renfe_bus_service_alert_count = variables.get("renfe_bus_service_alert_count")
    renfe_infrastructure_alert_count = variables.get("renfe_infrastructure_alert_count")
    renfe_service_cut_alert_count = variables.get("renfe_service_cut_alert_count")
    renfe_trip_update_count = variables.get("renfe_trip_update_count")
    renfe_delayed_trip_count = variables.get("renfe_delayed_trip_count")
    renfe_cancelled_trip_count = variables.get("renfe_cancelled_trip_count")
    renfe_added_trip_count = variables.get("renfe_added_trip_count")
    renfe_affected_stop_count = variables.get("renfe_affected_stop_count")
    renfe_mean_delay_seconds = variables.get("renfe_mean_delay_seconds")
    renfe_max_delay_seconds = variables.get("renfe_max_delay_seconds")

    if incident_count is None and renfe_incident_count is None:
        return False, 0.0, "low", "No aplica detector rápido de transporte"

    score = 0.0
    reasons = []

    # 1) CALIDAD DE DATO
    if wind_generation is not None and wind_generation < 0:
        score += 0.6
        reasons.append("Valor inválido en generación eólica")

    if solar_generation is not None and solar_generation < 0:
        score += 0.6
        reasons.append("Valor inválido en generación solar")

    # 2) DGT
    if incident_count is not None:
        if incident_count > 80:
            score += 0.20
            reasons.append("Volumen elevado de incidencias en red viaria de Madrid")
        elif incident_count > 45:
            score += 0.12
            reasons.append("Presión operativa moderada en red viaria de Madrid")
        elif incident_count > 25:
            score += 0.06
            reasons.append("Aumento relevante de incidencias en red viaria de Madrid")

    if severity_high_count is not None and severity_high_count > 8:
        score += 0.10
        reasons.append("Número elevado de incidencias viarias severas")
    elif severity_high_count is not None and severity_high_count > 3:
        score += 0.05
        reasons.append("Incidencias viarias severas presentes")

    if severity_highest_count is not None and severity_highest_count > 0:
        score += 0.08
        reasons.append("Existencia de incidencias viarias de máxima severidad")

    if abnormal_traffic_count is not None and abnormal_traffic_count > 8:
        score += 0.10
        reasons.append("Tráfico anómalo relevante en la red viaria")
    elif abnormal_traffic_count is not None and abnormal_traffic_count > 1:
        score += 0.04
        reasons.append("Tráfico anómalo detectado en la red viaria")

    if road_lane_mgmt_count is not None and road_lane_mgmt_count > 20:
        score += 0.08
        reasons.append("Elevado número de incidencias de gestión viaria")

    if affected_municipality_count is not None and affected_municipality_count > 20:
        score += 0.08
        reasons.append("Afectación territorial amplia en la red viaria")

    if affected_road_count is not None and affected_road_count > 20:
        score += 0.08
        reasons.append("Afectación a múltiples carreteras")

    # 3) RENFE
    if renfe_incident_count is not None:
        if renfe_incident_count > 30:
            score += 0.18
            reasons.append("Número elevado de incidencias ferroviarias")
        elif renfe_incident_count > 15:
            score += 0.10
            reasons.append("Presión operativa moderada en ferrocarril")
        elif renfe_incident_count > 5:
            score += 0.06
            reasons.append("Afectación ferroviaria apreciable")

    if renfe_affected_line_count is not None and renfe_affected_line_count >= 6:
        score += 0.14
        reasons.append("Afectación a múltiples líneas de Cercanías")
    elif renfe_affected_line_count is not None and renfe_affected_line_count >= 3:
        score += 0.08
        reasons.append("Afectación a varias líneas de Cercanías")

    if renfe_infrastructure_alert_count is not None and renfe_infrastructure_alert_count > 10:
        score += 0.12
        reasons.append("Incidencias ferroviarias relacionadas con infraestructura")
    elif renfe_infrastructure_alert_count is not None and renfe_infrastructure_alert_count > 3:
        score += 0.08
        reasons.append("Señales de afectación de infraestructura ferroviaria")

    if renfe_service_cut_alert_count is not None and renfe_service_cut_alert_count > 1:
        score += 0.14
        reasons.append("Interrupción o recorte del servicio ferroviario")
    elif renfe_service_cut_alert_count is not None and renfe_service_cut_alert_count > 0:
        score += 0.08
        reasons.append("Afectación parcial del servicio ferroviario")

    if renfe_cancelled_trip_count is not None and renfe_cancelled_trip_count > 1:
        score += 0.12
        reasons.append("Servicios ferroviarios cancelados")

    if renfe_mean_delay_seconds is not None and renfe_mean_delay_seconds > 600:
        score += 0.10
        reasons.append("Retraso medio ferroviario elevado")
    elif renfe_mean_delay_seconds is not None and renfe_mean_delay_seconds > 180:
        score += 0.05
        reasons.append("Retraso medio ferroviario apreciable")

    if renfe_max_delay_seconds is not None and renfe_max_delay_seconds > 1200:
        score += 0.08
        reasons.append("Retraso máximo ferroviario muy alto")
    elif renfe_max_delay_seconds is not None and renfe_max_delay_seconds > 600:
        score += 0.05
        reasons.append("Retraso máximo ferroviario elevado")

    # 4) CORRELACIÓN
    if incident_count is not None and renfe_incident_count is not None:
        if incident_count > 45 and renfe_incident_count > 15:
            score += 0.10
            reasons.append("Degradación simultánea en carretera y ferrocarril")

    if severity_high_count is not None and renfe_service_cut_alert_count is not None:
        if severity_high_count > 3 and renfe_service_cut_alert_count > 0:
            score += 0.05
            reasons.append("Incidencias viarias severas coinciden con afectación ferroviaria")

    # 5) AEMET
    if precipitation is not None and precipitation > 0:
        if incident_count is not None and incident_count > 45:
            score += 0.08
            reasons.append("La precipitación puede estar contribuyendo a la presión viaria")

        if renfe_incident_count is not None and renfe_incident_count > 15:
            score += 0.08
            reasons.append("La precipitación puede estar contribuyendo a la afectación ferroviaria")

    if wind_speed is not None and wind_speed > 6:
        if road_lane_mgmt_count is not None and road_lane_mgmt_count > 20:
            score += 0.08
            reasons.append("El viento puede estar afectando a la movilidad por carretera")

        if renfe_infrastructure_alert_count is not None and renfe_infrastructure_alert_count > 5:
            score += 0.08
            reasons.append("El viento puede estar afectando a infraestructura ferroviaria")

    # 6) REE
    if wind_generation is not None and wind_generation < 15000:
        if incident_count is not None and incident_count > 45:
            score += 0.08
            reasons.append("Contexto energético débil coincidente con presión viaria")

        if renfe_service_cut_alert_count is not None and renfe_service_cut_alert_count > 0:
            score += 0.08
            reasons.append("Contexto energético débil coincidente con afectación ferroviaria")

    if solar_generation is not None and solar_generation < 40000:
        if renfe_delayed_trip_count is not None and renfe_delayed_trip_count > 5:
            score += 0.08
            reasons.append("Baja generación solar coincidente con retrasos ferroviarios")

        if obstruction_count is not None and obstruction_count > 10:
            score += 0.08
            reasons.append("Baja generación solar coincidente con obstrucciones viarias")

    # 7) REGLA ENERGÉTICA EXTREMA
    if wind_speed is not None and wind_generation is not None:
        if wind_speed > 8 and wind_generation < 15000:
            return True, 0.90, "high", "Inconsistencia fuerte: viento alto pero generación eólica anormalmente baja"

    # 8) GRAFO
    graph_data = compute_graph_risk(variables)
    graph_score = graph_data["global_graph_score"]
    criticality_score = graph_data["criticality_score"]
    dominant_node = graph_data["dominant_node"]

    hospital_score = graph_data["node_scores"]["hospitales"]["final_score"]
    emergency_score = graph_data["node_scores"]["emergencias"]["final_score"]
    telecom_score = graph_data["node_scores"]["telecomunicaciones"]["final_score"]

    final_score = min(
        1.0,
        (0.55 * score) + (0.25 * graph_score) + (0.20 * criticality_score)
    )

    if hospital_score >= 0.75:
        final_score = min(1.0, final_score + 0.05)
        reasons.append("Riesgo elevado sobre hospitales")

    if emergency_score >= 0.75:
        final_score = min(1.0, final_score + 0.05)
        reasons.append("Riesgo elevado sobre servicios de emergencias")

    if telecom_score >= 0.70:
        final_score = min(1.0, final_score + 0.03)
        reasons.append("Riesgo apreciable sobre telecomunicaciones")

    # 9) MENSAJE
    if graph_score >= 0.55:
        reasons.append(f"Grafo de dependencias activado (score={graph_score})")

    if criticality_score >= 0.60:
        reasons.append(
            f"Alta criticidad potencial sobre infraestructuras esenciales (score={criticality_score})"
        )

    if dominant_node["score"] >= 0.60:
        reasons.append(
            f"Nodo crítico dominante: {dominant_node['name']} (score={dominant_node['score']})"
        )

    message = "OK" if not reasons else " | ".join(reasons)

    if final_score >= 0.90:
        return True, final_score, "critical", message

    elif final_score >= 0.75:
        return True, final_score, "high", message

    elif final_score >= 0.60:
        return False, final_score, "medium", message
    
    else:
        return False, final_score, "low", message