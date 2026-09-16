"""Lecture des resultats SWMM (fichier binaire .out) vers SimulationResult.

On s'appuie sur ``pyswmm`` (module ``pyswmm.output``, base sur SWMM-Toolkit)
qui sait lire directement le fichier binaire ``.out`` produit par le moteur,
sans avoir a reimplementer le format binaire proprietaire de SWMM.

Pour chaque noeud on recupere la profondeur d'eau (``depth``). Pour chaque
conduite on recupere le debit (``flow``) et on le convertit en vecteur
d'ecoulement porte par la direction amont -> aval du lien ; ce vecteur est
accumule sur les deux noeuds extremites (moyenne si un noeud a plusieurs
conduites) pour servir de glyphe de direction dans le panneau 3D.
"""
from __future__ import annotations

from typing import Dict

import numpy as np

from ..results import SimulationResult


def read_swmm_output(out_path: str, index: Dict[str, dict]) -> SimulationResult:
    try:
        from pyswmm.output import Output
        from pyswmm.output.enums import NodeAttribute, LinkAttribute
    except ImportError as exc:  # pragma: no cover - depend de l'env QGIS
        raise RuntimeError(
            "Le module 'pyswmm' est requis pour lire les resultats SWMM. "
            "Installez-le dans l'environnement Python de QGIS : "
            "pip install pyswmm"
        ) from exc

    node_index = index["nodes"]
    link_index = index.get("links", {})
    node_ids = list(node_index.keys())
    node_pos = {n: i for i, n in enumerate(node_ids)}
    points = np.array([[node_index[n]["x"], node_index[n]["y"], node_index[n]["invert"]] for n in node_ids])

    with Output(out_path) as out:
        times = list(out.times)
        n_steps = len(times)
        depth_series = np.zeros((n_steps, len(node_ids)))

        for j, nid in enumerate(node_ids):
            try:
                series = out.node_series(nid, NodeAttribute.INVERT_DEPTH)
                depth_series[:, j] = [series[t] for t in times]
            except Exception:  # noqa: BLE001 - noeud absent des resultats
                continue

        vectors = np.zeros((n_steps, len(node_ids), 3))
        contrib_count = np.zeros(len(node_ids))

        for lid, link in link_index.items():
            from_node, to_node = link.get("from"), link.get("to")
            if from_node not in node_pos or to_node not in node_pos:
                continue
            i_from, i_to = node_pos[from_node], node_pos[to_node]
            direction = points[i_to, :2] - points[i_from, :2]
            norm = np.linalg.norm(direction)
            if norm < 1e-9:
                continue
            unit = direction / norm

            try:
                flow_series = out.link_series(lid, LinkAttribute.FLOW_RATE)
                flows = np.array([flow_series[t] for t in times])
            except Exception:  # noqa: BLE001
                continue

            contrib = np.outer(flows, unit)  # (n_steps, 2)
            vectors[:, i_from, 0] += contrib[:, 0]
            vectors[:, i_from, 1] += contrib[:, 1]
            vectors[:, i_to, 0] += contrib[:, 0]
            vectors[:, i_to, 1] += contrib[:, 1]
            contrib_count[i_from] += 1
            contrib_count[i_to] += 1

        nonzero = contrib_count > 0
        vectors[:, nonzero, :] /= contrib_count[nonzero][None, :, None]

    metadata = {"source": out_path, "n_links": len(link_index)}
    return SimulationResult(
        engine="swmm",
        times=times,
        points=points,
        scalars={"depth": depth_series},
        vectors=vectors,
        topology=[(link_index[l]["from"], link_index[l]["to"]) for l in link_index],
        metadata=metadata,
    )
