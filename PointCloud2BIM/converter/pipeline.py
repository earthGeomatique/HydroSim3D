"""Orchestration bout-en-bout : lecture MNT -> triangulation -> export IFC.

Point d'entree unique consomme par le dialogue (execution synchrone, pour
les tests) et par la QgsTask (execution en arriere-plan) : les deux se
contentent d'appeler :func:`run_conversion` avec des callbacks de log/progres.
"""
from __future__ import annotations

from typing import Callable, Optional

from .dem_reader import read_dem
from .ifc_writer import ProjectInfo, write_ifc
from .mesh_builder import build_terrain_mesh

ProgressCallback = Callable[[int, str], None]
LogCallback = Callable[[str], None]


def _noop_progress(pct: int, msg: str) -> None:  # pragma: no cover - trivial
    pass


def _noop_log(msg: str) -> None:  # pragma: no cover - trivial
    pass


def run_conversion(
    tif_path: str,
    ifc_path: str,
    schema: str = "IFC4",
    decimation: int = 1,
    z_exaggeration: float = 1.0,
    z_offset: float = 0.0,
    project_info: Optional[ProjectInfo] = None,
    epsg_override: Optional[int] = None,
    progress_cb: ProgressCallback = _noop_progress,
    log_cb: LogCallback = _noop_log,
) -> dict:
    progress_cb(5, f"Lecture du MNT : {tif_path}")
    dem = read_dem(tif_path, decimation=decimation)
    log_cb(f"MNT charge : {dem.shape[0]}x{dem.shape[1]} cellules (decimation={decimation}).")

    progress_cb(35, "Triangulation du maillage...")
    mesh = build_terrain_mesh(dem, z_exaggeration=z_exaggeration, z_offset=z_offset)
    log_cb(
        f"Maillage genere : {len(mesh.vertices)} sommets, {len(mesh.triangles)} triangles "
        f"({mesh.n_skipped_nodata} cellules ignorees pour nodata)."
    )

    progress_cb(70, f"Export IFC ({schema})...")
    epsg = epsg_override if epsg_override is not None else dem.epsg
    report = write_ifc(mesh, ifc_path, schema=schema, project_info=project_info, epsg=epsg)
    for warning in report["warnings"]:
        log_cb(f"ATTENTION : {warning}")

    progress_cb(100, f"Termine : {ifc_path}")
    report["dem_shape"] = dem.shape
    report["epsg"] = epsg
    return report
