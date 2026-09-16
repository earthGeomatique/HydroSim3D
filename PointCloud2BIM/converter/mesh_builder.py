"""Triangulation d'une grille de MNT en maillage (sommets + faces).

Chaque cellule de la grille devient un sommet (a son centre). Chaque bloc de
2x2 sommets adjacents est decoupe en 2 triangles, sauf si l'un des quatre
coins est en zone "nodata" (NaN) : le trou reste alors non maille plutot que
d'interpoler une valeur arbitraire.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:  # evite de rendre GDAL obligatoire pour tester ce module seul
    from .dem_reader import DemGrid


@dataclass
class TerrainMesh:
    #: sommets (N, 3) en coordonnees du MNT (x, y, z)
    vertices: np.ndarray
    #: faces triangulaires (M, 3), indices dans ``vertices``
    triangles: np.ndarray
    n_skipped_nodata: int


def build_terrain_mesh(dem: DemGrid, z_exaggeration: float = 1.0, z_offset: float = 0.0) -> TerrainMesh:
    rows, cols = dem.shape
    if rows < 2 or cols < 2:
        raise ValueError("Le MNT est trop petit pour etre triangule (2x2 cellules minimum).")

    row_idx, col_idx = np.meshgrid(np.arange(rows), np.arange(cols), indexing="ij")
    xs = dem.origin_x + (col_idx + 0.5) * dem.pixel_width
    ys = dem.origin_y + (row_idx + 0.5) * dem.pixel_height
    zs = dem.z * z_exaggeration + z_offset

    vertices = np.column_stack([xs.ravel(), ys.ravel(), zs.ravel()])
    valid = ~np.isnan(dem.z)

    def vid(r, c):
        return r * cols + c

    triangles = []
    n_skipped = 0
    for r in range(rows - 1):
        for c in range(cols - 1):
            corners_valid = (
                valid[r, c] and valid[r, c + 1] and valid[r + 1, c] and valid[r + 1, c + 1]
            )
            if not corners_valid:
                n_skipped += 1
                continue
            tl, tr = vid(r, c), vid(r, c + 1)
            bl, br = vid(r + 1, c), vid(r + 1, c + 1)
            triangles.append((tl, bl, tr))
            triangles.append((tr, bl, br))

    if not triangles:
        raise ValueError(
            "Aucun triangle valide n'a pu etre genere : le MNT ne contient que "
            "des cellules nodata, ou une grille trop fragmentee."
        )

    return TerrainMesh(
        vertices=vertices,
        triangles=np.array(triangles, dtype=np.int64),
        n_skipped_nodata=n_skipped,
    )
