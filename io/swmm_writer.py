"""Export de couches QGIS vers un fichier d'entree SWMM (.inp).

Le format .inp de SWMM est un fichier texte structure en sections
``[NOM_SECTION]``. On construit chaque section a partir des attributs des
entites des couches ``QgsVectorLayer`` fournies par l'onglet Reseau.

Champs attendus (mappables depuis l'UI, avec ces noms par defaut) :

* Jonctions   : ``InvertElev`` (cote radier), ``MaxDepth`` (profondeur du regard)
* Conduites   : ``FromNode``, ``ToNode``, ``Length``, ``Roughness``, ``Diameter``
* Exutoires   : ``InvertElev``, ``OutfallType`` (FREE, NORMAL, FIXED...)
* Sous-bassins: ``Outlet``, ``Area``, ``PctImperv``, ``Width``, ``Slope``
"""
from __future__ import annotations

import textwrap
from datetime import datetime
from typing import Dict, Optional

from qgis.core import QgsVectorLayer

from ..config import NetworkConfig, SimulationParams


def _attr(feature, field_map: Dict[str, str], key: str, default_field: str, cast=float, default=None):
    field_name = field_map.get(key, default_field)
    idx = feature.fields().indexFromName(field_name)
    if idx < 0 or feature[field_name] is None:
        return default
    try:
        return cast(feature[field_name])
    except (TypeError, ValueError):
        return default


def _node_id(feature) -> str:
    """Identifiant SWMM d'un noeud : id d'entite QGIS prefixe pour lisibilite."""
    return f"N{feature.id()}"


def write_swmm_inp(
    inp_path: str,
    network: NetworkConfig,
    sim: SimulationParams,
    resolve_layer,
) -> Dict[str, dict]:
    """Ecrit ``inp_path`` et retourne un index des noeuds pour l'import ulterieur.

    L'index retourne mappe ``node_id -> {"x": ..., "y": ..., "invert": ...}``
    afin que le lecteur de resultats puisse replacer les series temporelles
    dans l'espace pour la visualisation 3D.
    """
    junctions: QgsVectorLayer = resolve_layer(network.junctions.layer_id)
    conduits: QgsVectorLayer = resolve_layer(network.conduits.layer_id)
    outfalls: QgsVectorLayer = resolve_layer(network.outfalls.layer_id)
    subcatchments = resolve_layer(network.subcatchments.layer_id)
    raingages = resolve_layer(network.raingages.layer_id)

    node_index: Dict[str, dict] = {}
    junction_lines = []
    for feat in junctions.getFeatures():
        nid = _node_id(feat)
        invert = _attr(feat, network.junctions.field_map, "invert", "InvertElev", float, 0.0)
        max_depth = _attr(feat, network.junctions.field_map, "max_depth", "MaxDepth", float, 1.5)
        pt = feat.geometry().asPoint()
        node_index[nid] = {"x": pt.x(), "y": pt.y(), "invert": invert, "type": "junction"}
        junction_lines.append(f"{nid:<16}{invert:<12}{max_depth:<12}0{'':<12}0{'':<12}0")

    outfall_lines = []
    for feat in outfalls.getFeatures():
        nid = _node_id(feat)
        invert = _attr(feat, network.outfalls.field_map, "invert", "InvertElev", float, 0.0)
        outfall_type = network.outfalls.field_map.get("outfall_type", "FREE")
        pt = feat.geometry().asPoint()
        node_index[nid] = {"x": pt.x(), "y": pt.y(), "invert": invert, "type": "outfall"}
        outfall_lines.append(f"{nid:<16}{invert:<12}{outfall_type:<12}{'':<12}NO")

    conduit_lines = []
    xsection_lines = []
    link_index: Dict[str, dict] = {}
    coord_lookup = {(round(v["x"], 3), round(v["y"], 3)): k for k, v in node_index.items()}

    def _nearest_node(pt) -> Optional[str]:
        key = (round(pt.x(), 3), round(pt.y(), 3))
        return coord_lookup.get(key)

    for feat in conduits.getFeatures():
        cid = f"C{feat.id()}"
        geom = feat.geometry()
        line = geom.asPolyline() if not geom.isMultipart() else geom.asMultiPolyline()[0]
        from_node = _nearest_node(line[0]) or "N?"
        to_node = _nearest_node(line[-1]) or "N?"
        length = _attr(feat, network.conduits.field_map, "length", "Length", float, geom.length())
        roughness = _attr(feat, network.conduits.field_map, "roughness", "Roughness", float, 0.013)
        diameter = _attr(feat, network.conduits.field_map, "diameter", "Diameter", float, 0.3)

        conduit_lines.append(
            f"{cid:<16}{from_node:<16}{to_node:<16}{length:<12}{roughness:<12}0{'':<12}0{'':<12}0{'':<12}0"
        )
        xsection_lines.append(f"{cid:<16}CIRCULAR{'':<8}{diameter:<12}0{'':<12}0{'':<12}0{'':<12}1")
        link_index[cid] = {"from": from_node, "to": to_node}

    subcatchment_lines = []
    subarea_lines = []
    if subcatchments is not None:
        raingage_name = "RG1"
        for feat in subcatchments.getFeatures():
            sid = f"S{feat.id()}"
            outlet = network.subcatchments.field_map.get("outlet")
            outlet_val = feat[outlet] if outlet and outlet in [f.name() for f in feat.fields()] else None
            area = _attr(feat, network.subcatchments.field_map, "area", "Area", float, feat.geometry().area() / 10000.0)
            pct_imperv = _attr(feat, network.subcatchments.field_map, "pct_imperv", "PctImperv", float, 25.0)
            width = _attr(feat, network.subcatchments.field_map, "width", "Width", float, 100.0)
            slope = _attr(feat, network.subcatchments.field_map, "slope", "Slope", float, 0.5)
            outlet_final = outlet_val or (list(node_index.keys())[0] if node_index else "N?")
            subcatchment_lines.append(
                f"{sid:<16}{raingage_name:<16}{outlet_final:<16}{area:<10}{pct_imperv:<10}{width:<10}{slope:<10}0"
            )
            subarea_lines.append(f"{sid:<16}0.01{'':<8}0.1{'':<8}0.05{'':<8}0.05{'':<8}25{'':<8}OUTLET")

    raingage_lines = []
    if raingages is not None:
        for feat in raingages.getFeatures():
            raingage_lines.append("RG1             INTENSITY 1:00     1.0      TIMESERIES TS1")
    elif subcatchments is not None:
        raingage_lines.append("RG1             INTENSITY 1:00     1.0      TIMESERIES TS1")

    content = f"""
    [TITLE]
    ;; Genere automatiquement par le plugin QGIS HydroSim3D le {datetime.now().isoformat()}

    [OPTIONS]
    FLOW_UNITS           CMS
    INFILTRATION         HORTON
    FLOW_ROUTING         DYNWAVE
    START_DATE           {sim.start.strftime('%m/%d/%Y')}
    START_TIME           {sim.start.strftime('%H:%M:%S')}
    END_DATE             {sim.end.strftime('%m/%d/%Y')}
    END_TIME             {sim.end.strftime('%H:%M:%S')}
    REPORT_STEP          00:{max(1, sim.time_step_seconds // 60):02d}:00
    WET_STEP             00:05:00
    DRY_STEP             01:00:00
    ROUTING_STEP         {sim.time_step_seconds}

    [JUNCTIONS]
    ;;Name           Elevation   MaxDepth    InitDepth   SurDepth    Aponded
    {textwrap.indent(chr(10).join(junction_lines), '')}

    [OUTFALLS]
    ;;Name           Elevation   Type        StageData   Gated
    {textwrap.indent(chr(10).join(outfall_lines), '')}

    [CONDUITS]
    ;;Name           From        To          Length      Roughness   InOffset OutOffset InitFlow MaxFlow
    {textwrap.indent(chr(10).join(conduit_lines), '')}

    [XSECTIONS]
    ;;Link           Shape       Geom1       Geom2       Geom3       Geom4       Barrels
    {textwrap.indent(chr(10).join(xsection_lines), '')}

    [SUBCATCHMENTS]
    ;;Name           Raingage    Outlet      Area        %Imperv     Width       %Slope      CurbLen
    {textwrap.indent(chr(10).join(subcatchment_lines), '')}

    [SUBAREAS]
    ;;Subcatchment   N-Imperv    N-Perv      S-Imperv    S-Perv      PctZero     RouteTo
    {textwrap.indent(chr(10).join(subarea_lines), '')}

    [RAINGAGES]
    ;;Name           Format      Interval    SCF         Source
    {textwrap.indent(chr(10).join(raingage_lines), '')}

    [TIMESERIES]
    TS1  0:00  0.0
    TS1  1:00  10.0
    TS1  2:00  0.0

    [COORDINATES]
    ;;Node           X-Coord     Y-Coord
    {textwrap.indent(chr(10).join(f"{nid:<16}{v['x']:<14}{v['y']:<14}" for nid, v in node_index.items()), '')}

    [REPORT]
    INPUT      NO
    CONTROLS   NO
    SUBCATCHMENTS ALL
    NODES      ALL
    LINKS      ALL
    """
    with open(inp_path, "w", encoding="utf-8") as fh:
        fh.write(textwrap.dedent(content).strip() + "\n")

    return {"nodes": node_index, "links": link_index}
