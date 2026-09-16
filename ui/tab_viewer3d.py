"""Onglet 3D : heberge le panneau PyVista et le connecte au controleur."""
from __future__ import annotations

from qgis.PyQt.QtWidgets import QVBoxLayout, QWidget

from ..controller import SimulationController
from ..viewer3d.pyvista_panel import Pyvista3DPanel


class Viewer3DTab(QWidget):
    def __init__(self, controller: SimulationController, parent=None):
        super().__init__(parent)
        self.controller = controller

        layout = QVBoxLayout(self)
        self.panel = Pyvista3DPanel(self)
        layout.addWidget(self.panel)

        controller.simulationFinished.connect(self._on_simulation_finished)
        controller.configChanged.connect(self._on_config_changed)

    def _on_config_changed(self) -> None:
        exaggeration = self.controller.config.topography.vertical_exaggeration
        self.panel.set_vertical_exaggeration(exaggeration)

        dem = self.controller.resolve_layer(self.controller.config.topography.dem.layer_id)
        if dem is not None:
            self._load_terrain(dem)

    def _load_terrain(self, dem) -> None:
        from ..io.raster_utils import read_dem_as_grid

        try:
            x, y, z = read_dem_as_grid(dem)
            self.panel.set_terrain(x, y, z)
        except Exception:  # noqa: BLE001 - le rendu 3D est secondaire, pas bloquant
            pass

    def _on_simulation_finished(self, result) -> None:
        self.panel.set_result(result)
