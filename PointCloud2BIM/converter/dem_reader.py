"""Lecture d'un MNT (GeoTIFF) en grille numpy, en pleine resolution.

Contrairement a ``hydrosim3d.io.raster_utils`` (qui sous-echantillonne pour
un apercu 3D interactif), la conversion IFC doit pouvoir travailler sur le
MNT a sa resolution native (ou avec une decimation explicitement choisie
par l'utilisateur), puisque le maillage exporte est le livrable final.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
from osgeo import gdal, osr

gdal.UseExceptions()


@dataclass
class DemGrid:
    """Grille d'elevations + informations de georeferencement."""

    z: np.ndarray  # (rows, cols), NaN pour les cellules nodata
    origin_x: float
    origin_y: float
    pixel_width: float
    pixel_height: float  # negatif (nord -> sud), convention GDAL standard
    crs_wkt: str
    epsg: Optional[int]

    @property
    def shape(self) -> Tuple[int, int]:
        return self.z.shape

    def cell_center_xy(self, row: int, col: int) -> Tuple[float, float]:
        x = self.origin_x + (col + 0.5) * self.pixel_width
        y = self.origin_y + (row + 0.5) * self.pixel_height
        return x, y


def read_dem(tif_path: str, decimation: int = 1) -> DemGrid:
    """Charge un MNT GeoTIFF.

    ``decimation`` > 1 ne garde qu'une cellule sur N dans chaque direction,
    ce qui reduit d'autant le nombre de sommets/triangles du maillage final
    (utile pour les MNT tres resolus ou l'IFC resultant serait trop lourd).
    """
    if decimation < 1:
        raise ValueError("La decimation doit etre >= 1.")

    ds = gdal.Open(tif_path)
    if ds is None:
        raise RuntimeError(f"Impossible d'ouvrir le fichier MNT : {tif_path}")

    band = ds.GetRasterBand(1)
    nodata = band.GetNoDataValue()
    z = band.ReadAsArray().astype(np.float64)
    if nodata is not None:
        z = np.where(np.isclose(z, nodata), np.nan, z)

    if decimation > 1:
        z = z[::decimation, ::decimation]

    gt = ds.GetGeoTransform()
    pixel_width = gt[1] * decimation
    pixel_height = gt[5] * decimation

    crs_wkt = ds.GetProjection() or ""
    epsg = None
    if crs_wkt:
        srs = osr.SpatialReference()
        srs.ImportFromWkt(crs_wkt)
        code = srs.GetAuthorityCode(None)
        epsg = int(code) if code else None

    return DemGrid(
        z=z,
        origin_x=gt[0],
        origin_y=gt[3],
        pixel_width=pixel_width,
        pixel_height=pixel_height,
        crs_wkt=crs_wkt,
        epsg=epsg,
    )
