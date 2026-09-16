"""Onglet Hydraulique : couches d'entree pour l'export HEC-RAS."""
from __future__ import annotations

from qgis.core import QgsMapLayerProxyModel
from qgis.PyQt.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..controller import SimulationController
from .widgets import LayerFieldRow


class HydraulicsTab(QWidget):
    def __init__(self, controller: SimulationController, parent=None):
        super().__init__(parent)
        self.controller = controller

        layout = QVBoxLayout(self)
        group = QGroupBox("Couches hydrauliques (HEC-RAS)", self)
        group_layout = QVBoxLayout(group)

        group_layout.addWidget(LayerFieldRow(
            "Ligne d'axe (centerline) :",
            lambda layer: controller.set_hydraulics_layer("river_centerline", layer),
            geometry_filter=QgsMapLayerProxyModel.LineLayer,
        ))
        group_layout.addWidget(LayerFieldRow(
            "Profils en travers (cross-sections) :",
            lambda layer: controller.set_hydraulics_layer("cross_sections", layer),
            geometry_filter=QgsMapLayerProxyModel.LineLayer,
        ))
        group_layout.addWidget(LayerFieldRow(
            "Lignes de berge (optionnel) :",
            lambda layer: controller.set_hydraulics_layer("bank_lines", layer),
            geometry_filter=QgsMapLayerProxyModel.LineLayer,
        ))
        group_layout.addWidget(LayerFieldRow(
            "Zones de rugosite / Manning (optionnel) :",
            lambda layer: controller.set_hydraulics_layer("manning_zones", layer),
            geometry_filter=QgsMapLayerProxyModel.PolygonLayer,
        ))

        layout.addWidget(group)

        path_group = QGroupBox("Installation HEC-RAS (Windows uniquement)", self)
        path_layout = QFormLayout(path_group)
        path_row = QHBoxLayout()
        self.install_edit = QLineEdit(path_group)
        browse_btn = QPushButton("Parcourir...", path_group)
        browse_btn.clicked.connect(self._browse_install_dir)
        path_row.addWidget(self.install_edit)
        path_row.addWidget(browse_btn)
        path_layout.addRow("Repertoire d'installation :", path_row)
        layout.addWidget(path_group)

        layout.addStretch()

    def _browse_install_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Repertoire d'installation HEC-RAS")
        if path:
            self.install_edit.setText(path)
            self.controller.config.hydraulics.hecras_install_dir = path
            self.controller.configChanged.emit()
