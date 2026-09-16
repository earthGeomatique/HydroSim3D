"""Tests de la triangulation (aucune dependance GDAL/QGIS).

On utilise un objet leger reproduisant l'interface de ``DemGrid`` plutot que
la vraie classe, pour ne pas avoir a importer ``osgeo`` (non necessaire pour
tester la seule logique de triangulation).
"""
from dataclasses import dataclass

import numpy as np
import pytest

from converter.mesh_builder import build_terrain_mesh


@dataclass
class FakeDemGrid:
    z: np.ndarray
    origin_x: float = 0.0
    origin_y: float = 0.0
    pixel_width: float = 1.0
    pixel_height: float = -1.0

    @property
    def shape(self):
        return self.z.shape


def test_full_grid_produces_two_triangles_per_cell():
    z = np.array([[1.0, 2.0], [3.0, 4.0]])
    dem = FakeDemGrid(z=z)
    mesh = build_terrain_mesh(dem)
    assert mesh.n_skipped_nodata == 0
    assert len(mesh.triangles) == 2  # 1x1 cellules -> 2 triangles
    assert len(mesh.vertices) == 4


def test_nodata_cell_is_skipped():
    z = np.ones((4, 4))
    z[1, 1] = np.nan
    dem = FakeDemGrid(z=z)
    mesh = build_terrain_mesh(dem)
    # grille 4x4 = 9 cellules ; les 4 qui touchent le NaN sont ignorees
    assert mesh.n_skipped_nodata == 4
    assert len(mesh.triangles) == 5 * 2
    assert all(not np.isnan(mesh.vertices[i, 2]) for tri in mesh.triangles for i in tri)


def test_all_nodata_raises():
    z = np.full((2, 2), np.nan)
    dem = FakeDemGrid(z=z)
    with pytest.raises(ValueError):
        build_terrain_mesh(dem)


def test_z_exaggeration_and_offset_applied():
    z = np.array([[1.0, 1.0], [1.0, 1.0]])
    dem = FakeDemGrid(z=z)
    mesh = build_terrain_mesh(dem, z_exaggeration=2.0, z_offset=10.0)
    assert np.allclose(mesh.vertices[:, 2], 12.0)


def test_too_small_grid_raises():
    dem = FakeDemGrid(z=np.array([[1.0, 2.0]]))
    with pytest.raises(ValueError):
        build_terrain_mesh(dem)
