"""Lecture d'un MNT QGIS sous forme de grille numpy pour le rendu 3D.

Le rendu PyVista a besoin d'un maillage regulier (X, Y, Z). On s'appuie sur
GDAL (toujours disponible dans une installation QGIS) plutot que sur l'API
``QgsRasterBlock`` pour beneficier du rechantillonnage rapide en une seule
lecture. Le MNT est sous-echantillonne a ``max_cells`` maximum par cote pour
garder un rendu 3D interactif meme sur un MNT tres resolu : la
visualisation reste indicative, le calcul hydraulique lui utilise le MNT
complet via son propre export (:mod:`hydrosim3d.io.hecras_writer`).
"""
from __future__ import annotations

from typing import Tuple

import numpy as np
from osgeo import gdal

from qgis.core import QgsRasterLayer

gdal.UseExceptions()


def read_dem_as_grid(dem: QgsRasterLayer, max_cells: int = 400) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Retourne (X, Y, Z), trois grilles 2D de meme forme, en coordonnees du MNT."""
    ds = gdal.Open(dem.source())
    if ds is None:
        raise RuntimeError(f"Impossible d'ouvrir le MNT avec GDAL : {dem.source()}")

    width, height = ds.RasterXSize, ds.RasterYSize
    x_scale = max(1, width // max_cells)
    y_scale = max(1, height // max_cells)
    out_width = max(2, width // x_scale)
    out_height = max(2, height // y_scale)

    band = ds.GetRasterBand(1)
    nodata = band.GetNoDataValue()
    z = band.ReadAsArray(0, 0, width, height, out_width, out_height).astype(float)
    if nodata is not None:
        z = np.where(z == nodata, np.nan, z)

    gt = ds.GetGeoTransform()  # (origin_x, px_w, 0, origin_y, 0, px_h)
    cols = np.arange(out_width)
    rows = np.arange(out_height)
    px_w = gt[1] * (width / out_width)
    px_h = gt[5] * (height / out_height)
    xs = gt[0] + cols * px_w + px_w / 2.0
    ys = gt[3] + rows * px_h + px_h / 2.0
    x, y = np.meshgrid(xs, ys)

    return x, y, z
