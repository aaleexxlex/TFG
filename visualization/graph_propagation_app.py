from pathlib import Path
import sys
import json

import networkx as nx
import pandas as pd
import streamlit as st
from pyvis.network import Network
from streamlit.components.v1 import html


# Ruta raíz del proyecto.
# Si este archivo está en visualization/graph_propagation_app.py,
# parents[1] apunta a la raíz del proyecto.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from shared.critical_infra import (
    DEFAULT_NODE_CONFIG,
    propagate_dependency_risk,
    InfraNode,
)


ALPHA = 0.55
LATEST_STATE_PATH = PROJECT_ROOT / "data" / "latest_graph_state.json"


SCENARIOS = {
    "Estado normal": {
        "energia": 0.05,
        "meteorologia": 0.05,
        "movilidad_carretera": 0.10,
        "movilidad_ferroviaria": 0.10,
        "movilidad_urbana": 0.00,
        "telecomunicaciones": 0.00,
        "hospitales": 0.00,
        "emergencias": 0.00,
        "logistica": 0.00,
    },
    "Escenario 1: Incidencia en movilidad": {
        "energia": 0.00,
        "meteorologia": 0.00,
        "movilidad_carretera": 0.91,
        "movilidad_ferroviaria": 1.00,
        "movilidad_urbana": 0.955,
        "telecomunicaciones": 0.00,
        "hospitales": 0.334,
        "emergencias": 0.430,
        "logistica": 0.714,
    },
    "Escenario 2: Perturbación energética": {
        "energia": 0.95,
        "meteorologia": 0.00,
        "movilidad_carretera": 0.10,
        "movilidad_ferroviaria": 0.55,
        "movilidad_urbana": 0.25,
        "telecomunicaciones": 0.70,
        "hospitales": 0.45,
        "emergencias": 0.45,
        "logistica": 0.35,
    },
    "Escenario 3: Condiciones meteorológicas adversas": {
        "energia": 0.05,
        "meteorologia": 0.90,
        "movilidad_carretera": 0.65,
        "movilidad_ferroviaria": 0.55,
        "movilidad_urbana": 0.25,
        "telecomunicaciones": 0.05,
        "hospitales": 0.15,
        "emergencias": 0.30,
        "logistica": 0.35,
    },
}


PRETTY_LABELS = {
    "energia": "Energía",
    "meteorologia": "Meteorología",
    "movilidad_carretera": "Movilidad carretera",
    "movilidad_ferroviaria": "Movilidad ferroviaria",
    "movilidad_urbana": "Movilidad urbana",
    "telecomunicaciones": "Telecomunicaciones",
    "hospitales": "Hospitales",
    "emergencias": "Emergencias",
    "logistica": "Logística",
}


GRAPH_POSITIONS = {
    "energia": (-500, -120),
    "meteorologia": (-500, 170),

    "movilidad_carretera": (-150, 180),
    "movilidad_ferroviaria": (-150, -120),
    "movilidad_urbana": (180, 30),

    "telecomunicaciones": (180, -260),
    "logistica": (180, 260),

    "hospitales": (520, 110),
    "emergencias": (520, -110),
}


def pretty_name(name: str) -> str:
    return PRETTY_LABELS.get(name, name.replace("_", " ").title())


def build_graph_networkx() -> nx.DiGraph:
    graph = nx.DiGraph()

    for name, cfg in DEFAULT_NODE_CONFIG.items():
        graph.add_node(
            name,
            label=pretty_name(name),
            weight=cfg["base_weight"],
        )

        for dependency in cfg["depends_on"]:
            graph.add_edge(dependency, name)

    return graph


def run_propagation_logic(base_scores: dict[str, float]) -> tuple[dict[str, dict], dict]:
    nodes = {
        name: InfraNode(
            name=name,
            base_weight=cfg["base_weight"],
            depends_on=cfg["depends_on"],
        )
        for name, cfg in DEFAULT_NODE_CONFIG.items()
    }

    for name, score in base_scores.items():
        if name in nodes:
            nodes[name].state_score = float(score)

    # Se replica la lógica de propagación del sistema.
    for _ in range(2):
        propagate_dependency_risk(nodes, attenuation=ALPHA)

    node_scores = {}

    for name, node in nodes.items():
        node_scores[name] = {
            "state_score": round(float(node.state_score), 3),
            "propagated_score": round(float(node.propagated_score), 3),
            "final_score": round(float(node.final_score), 3),
            "base_weight": float(node.base_weight),
            "depends_on": list(node.depends_on),
            "label": pretty_name(name),
        }

    weighted_sum = sum(node.final_score * node.base_weight for node in nodes.values())
    total_weight = sum(node.base_weight for node in nodes.values())
    global_score = weighted_sum / total_weight if total_weight > 0 else 0.0

    critical_nodes = ["hospitales", "emergencias", "telecomunicaciones"]
    criticality_score = sum(
        node_scores[node]["final_score"] for node in critical_nodes
    ) / len(critical_nodes)

    dominant_node = max(
        node_scores.keys(),
        key=lambda node: node_scores[node]["final_score"],
    )

    metrics = {
        "global_score": round(float(global_score), 3),
        "criticality_score": round(float(criticality_score), 3),
        "dominant_node": dominant_node,
    }

    return node_scores, metrics


def normalize_node_scores(raw_node_scores: dict) -> dict[str, dict]:
    node_scores = {}

    for name, cfg in DEFAULT_NODE_CONFIG.items():
        raw = raw_node_scores.get(name, {})

        node_scores[name] = {
            "state_score": round(float(raw.get("state_score", 0.0)), 3),
            "propagated_score": round(float(raw.get("propagated_score", 0.0)), 3),
            "final_score": round(float(raw.get("final_score", 0.0)), 3),
            "base_weight": float(raw.get("base_weight", cfg["base_weight"])),
            "depends_on": raw.get("depends_on", cfg["depends_on"]),
            "label": pretty_name(name),
        }

    return node_scores


def color_for_score(score: float) -> str:
    if score < 0.35:
        return "#2ECC71"  # Verde
    if score < 0.60:
        return "#F1C40F"  # Amarillo
    if score < 0.80:
        return "#E67E22"  # Naranja
    return "#E74C3C"      # Rojo


def build_pyvis_html(node_scores: dict[str, dict]) -> str:
    graph = build_graph_networkx()

    net = Network(
        height="650px",
        width="100%",
        directed=True,
        bgcolor="#ffffff",
        font_color="#222222",
        cdn_resources="remote",
    )

    for node in graph.nodes():
        scores = node_scores[node]

        final_score = scores["final_score"]
        base_score = scores["state_score"]
        propagated_score = scores["propagated_score"]

        size = 25 + (40 * final_score)
        color = color_for_score(final_score)

        tooltip = (
            f"<b>{scores['label']}</b><br>"
            f"Score base: {base_score:.3f}<br>"
            f"Score propagado: {propagated_score:.3f}<br>"
            f"Score final: {final_score:.3f}<br>"
            f"Peso crítico: {scores['base_weight']:.2f}"
        )

        x, y = GRAPH_POSITIONS.get(node, (0, 0))

        net.add_node(
            node,
            label=scores["label"],
            title=tooltip,
            size=size,
            color=color,
            x=x,
            y=y,
            fixed=True,
            physics=False,
            borderWidth=3,
            borderWidthSelected=5,
        )

    for source, target in graph.edges():
        source_score = node_scores[source]["final_score"]
        edge_color = color_for_score(source_score)
        width = 1.5 + (5.0 * source_score)

        net.add_edge(
            source,
            target,
            width=width,
            color=edge_color,
            title=f"{source} -> {target} | Riesgo origen: {source_score:.3f}",
            arrows="to",
        )

    net.set_options("""
    var options = {
      "nodes": {
        "font": {
          "size": 18,
          "face": "Tahoma",
          "color": "#222222"
        },
        "shadow": {
          "enabled": true
        }
      },
      "edges": {
        "arrows": {
          "to": {
            "enabled": true,
            "scaleFactor": 0.85
          }
        },
        "smooth": {
          "type": "cubicBezier",
          "roundness": 0.35
        },
        "shadow": {
          "enabled": false
        }
      },
      "physics": {
        "enabled": false
      },
      "interaction": {
        "hover": true,
        "dragNodes": true,
        "dragView": true,
        "zoomView": true,
        "navigationButtons": false,
        "keyboard": false
      }
    }
    """)

    graph_html = net.generate_html(notebook=False)
    graph_html = graph_html.replace("<head>", "<head><meta charset='utf-8'>")

    return graph_html


def load_real_fog_state() -> tuple[dict[str, dict], dict, dict]:
    with open(LATEST_STATE_PATH, "r", encoding="utf-8") as file:
        latest_state = json.load(file)

    node_scores = normalize_node_scores(latest_state.get("node_scores", {}))

    dominant_node = latest_state.get("dominant_node")
    if dominant_node not in node_scores:
        dominant_node = max(
            node_scores.keys(),
            key=lambda node: node_scores[node]["final_score"],
        )

    metrics = {
        "global_score": round(float(latest_state.get("graph_score", 0.0)), 3),
        "criticality_score": round(float(latest_state.get("criticality_score", 0.0)), 3),
        "dominant_node": dominant_node,
    }

    return node_scores, metrics, latest_state


def main():
    st.set_page_config(
        page_title="Propagación de Riesgo - TFG",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("Simulación de propagación de riesgos en infraestructuras críticas")

    st.markdown(
        "Esta interfaz permite visualizar la propagación del riesgo sobre el grafo "
        "de dependencias de servicios esenciales definido en el sistema."
    )

    mode = st.sidebar.radio(
        "Selecciona modo de operación",
        ["Simulación de escenarios", "Monitorización en tiempo real (Fog)"],
    )

    latest_state = None

    if mode == "Simulación de escenarios":
        scenario_name = st.sidebar.selectbox(
            "Selecciona escenario predefinido",
            list(SCENARIOS.keys()),
        )

        base_scores = SCENARIOS[scenario_name].copy()

        st.sidebar.markdown("---")
        st.sidebar.markdown("### Ajuste manual de riesgos base")

        for node, cfg in DEFAULT_NODE_CONFIG.items():
            label = pretty_name(node)
            base_scores[node] = st.sidebar.slider(
                f"{label} ({cfg['base_weight']:.2f})",
                min_value=0.0,
                max_value=1.0,
                value=float(base_scores.get(node, 0.0)),
                step=0.05,
            )

        node_scores, metrics = run_propagation_logic(base_scores)

    else:
        if LATEST_STATE_PATH.exists():
            try:
                node_scores, metrics, latest_state = load_real_fog_state()
                st.sidebar.success(
                    f"Datos del Fog cargados: {latest_state.get('generated_at')}"
                )
            except Exception as error:
                st.sidebar.error(f"Error leyendo el estado real: {error}")
                node_scores, metrics = run_propagation_logic(
                    {name: 0.0 for name in DEFAULT_NODE_CONFIG}
                )
        else:
            st.sidebar.warning(
                f"No existe {LATEST_STATE_PATH}. Ejecuta primero el nodo Fog."
            )
            node_scores, metrics = run_propagation_logic(
                {name: 0.0 for name in DEFAULT_NODE_CONFIG}
            )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        label="Riesgo global del sistema",
        value=f"{metrics['global_score']:.3f}",
    )

    col2.metric(
        label="Índice de criticidad",
        value=f"{metrics['criticality_score']:.3f}",
    )

    dominant_node = metrics["dominant_node"]
    dominant_label = pretty_name(dominant_node)
    dominant_value = node_scores[dominant_node]["final_score"]

    col3.metric(
        label="Nodo dominante",
        value=f"{dominant_label} ({dominant_value:.3f})",
    )

    if latest_state:
        final_score = float(latest_state.get("final_score", 0.0))

        st.info(
            f"Última observación Fog | "
            f"final_score={final_score:.3f} | "
            f"severity={latest_state.get('final_severity')} | "
            f"anomaly={latest_state.get('final_anomaly')} | "
            f"decision_mode={latest_state.get('decision_mode')}"
        )

    st.markdown("---")

    st.subheader("Visualización dinámica del grafo de dependencias")
    graph_html = build_pyvis_html(node_scores)
    html(graph_html, height=700, scrolling=True)

    st.subheader("Desglose analítico por servicio")

    table_data = []

    for node, scores in node_scores.items():
        table_data.append(
            {
                "Servicio/Infraestructura": scores["label"],
                "Riesgo base": scores["state_score"],
                "Riesgo propagado": scores["propagated_score"],
                "Riesgo final": scores["final_score"],
                "Peso crítico": scores["base_weight"],
            }
        )

    df = pd.DataFrame(table_data).sort_values("Riesgo final", ascending=False)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.caption(
        "Clasificación visual: verde < 0.35; amarillo 0.35-0.60; "
        "naranja 0.60-0.80; rojo >= 0.80."
    )


if __name__ == "__main__":
    main()
