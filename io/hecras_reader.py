"""Lecture des resultats 2D HEC-RAS (fichier plan .pXX.hdf) via h5py.

HEC-RAS >= 5.0 stocke les resultats de ses zones d'ecoulement 2D dans un
fichier HDF5 associe au plan calcule (``<projet>.p01.hdf``). La structure
utile est, pour chaque zone de maillage 2D nommee ``<area>`` :

``Geometry/2D Flow Areas/<area>/Cells Center Coordinate``
    coordonnees (x, y) du centre de chaque cellule du maillage

``Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/
2D Flow Areas/<area>/Water Surface``
    hauteur d'eau (surface libre) par cellule et par pas de temps

``.../Cell Velocity - Velocity X`` et ``... - Velocity Y``
    composantes de vitesse par cellule et par pas de temps

Cette structure peut varier legerement selon la version de HEC-RAS ; la
fonction ci-dessous explore le fichier pour trouver la premiere zone 2D
disponible plutot que de coder un chemin fige.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import numpy as np

from ..results import SimulationResult

_GEOM_BASE = "Geometry/2D Flow Areas"
_RESULT_BASE = "Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/2D Flow Areas"


def _first_2d_area_name(h5file) -> Optional[str]:
    if _GEOM_BASE not in h5file:
        return None
    names = list(h5file[_GEOM_BASE].keys())
    return names[0] if names else None


def _read_times(h5file) -> list:
    time_path = "Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/Time"
    if time_path in h5file:
        raw = h5file[time_path][()]
        base = datetime(1900, 1, 1)
        return [base + timedelta(days=float(t)) for t in raw]
    return []


def read_hecras_hdf(hdf_path: str) -> SimulationResult:
    try:
        import h5py
    except ImportError as exc:  # pragma: no cover - depend de l'env QGIS
        raise RuntimeError(
            "Le module 'h5py' est requis pour lire les resultats HEC-RAS. "
            "Installez-le dans l'environnement Python de QGIS : pip install h5py"
        ) from exc

    with h5py.File(hdf_path, "r") as h5file:
        area = _first_2d_area_name(h5file)
        if area is None:
            raise RuntimeError(
                f"Aucune zone d'ecoulement 2D trouvee dans {hdf_path}. "
                "Verifiez que le plan HEC-RAS utilise bien une geometrie 2D."
            )

        coords = np.asarray(h5file[f"{_GEOM_BASE}/{area}/Cells Center Coordinate"][()])
        n_cells = coords.shape[0]
        points = np.zeros((n_cells, 3))
        points[:, :2] = coords[:, :2]

        result_group = f"{_RESULT_BASE}/{area}"
        times = _read_times(h5file)

        scalars = {}
        if f"{result_group}/Water Surface" in h5file:
            ws = np.asarray(h5file[f"{result_group}/Water Surface"][()])
            scalars["water_surface"] = ws
            if f"{_GEOM_BASE}/{area}/Cells Minimum Elevation" in h5file:
                min_elev = np.asarray(h5file[f"{_GEOM_BASE}/{area}/Cells Minimum Elevation"][()])
                points[:, 2] = min_elev
                scalars["depth"] = np.clip(ws - min_elev[None, :], a_min=0, a_max=None)

        vectors = None
        vx_path, vy_path = f"{result_group}/Cell Velocity - Velocity X", f"{result_group}/Cell Velocity - Velocity Y"
        if vx_path in h5file and vy_path in h5file:
            vx = np.asarray(h5file[vx_path][()])
            vy = np.asarray(h5file[vy_path][()])
            vectors = np.zeros((vx.shape[0], vx.shape[1], 3))
            vectors[:, :, 0] = vx
            vectors[:, :, 1] = vy
            scalars["velocity"] = np.sqrt(vx**2 + vy**2)

        if not times:
            n_steps = next(iter(scalars.values())).shape[0] if scalars else 0
            times = [datetime.now() + timedelta(minutes=i) for i in range(n_steps)]

    return SimulationResult(
        engine="hecras",
        times=times,
        points=points,
        scalars=scalars,
        vectors=vectors,
        topology=None,
        metadata={"source": hdf_path, "flow_area": area, "n_cells": n_cells},
    )
