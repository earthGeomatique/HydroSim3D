"""Onglet Topographie : selection du MNT (QgsRasterLayer)."""
from __future__ import annotations

from qgis.core import QgsMapLayerProxyModel
from qgis.gui import QgsMapLayerComboBox
from qgis.PyQt.QtWidgets import QDoubleSpinBox, QFormLayout, QLabel, QWidget

from ..controller import SimulationController


class TopographyTab(QWidget):
    def __init__(self, controller: SimulationController, parent=None):
        super().__init__(parent)
        self.controller = controller

        layout = QFormLayout(self)

        self.dem_combo = QgsMapLayerComboBox(self)
        self.dem_combo.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.dem_combo.setAllowEmptyLayer(True)
        self.dem_combo.layerChanged.connect(self._on_dem_changed)
        layout.addRow("Modele numerique de terrain (MNT) :", self.dem_combo)

        self.exaggeration_spin = QDoubleSpinBox(self)
        self.exaggeration_spin.setRange(0.1, 20.0)
        self.exaggeration_spin.setSingleStep(0.5)
        self.exaggeration_spin.setValue(1.0)
        self.exaggeration_spin.valueChanged.connect(self._on_exaggeration_changed)
        layout.addRow("Exageration verticale (rendu 3D) :", self.exaggeration_spin)

        info = QLabel(
            "Le MNT sert de base a l'export du terrain vers HEC-RAS et au "
            "rendu du relief dans le panneau 3D."
        )
        info.setWordWrap(True)
        layout.addRow(info)

    def _on_dem_changed(self, layer) -> None:
        self.controller.set_dem(layer)

    def _on_exaggeration_changed(self, value: float) -> None:
        self.controller.config.topography.vertical_exaggeration = value
        self.controller.configChanged.emit()
