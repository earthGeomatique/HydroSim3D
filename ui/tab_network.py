"""Onglet Reseau d'assainissement : couches d'entree pour l'export SWMM."""
from __future__ import annotations

from qgis.core import QgsMapLayerProxyModel
from qgis.PyQt.QtWidgets import QGroupBox, QVBoxLayout, QWidget

from ..controller import SimulationController
from .widgets import LayerFieldRow


class NetworkTab(QWidget):
    def __init__(self, controller: SimulationController, parent=None):
        super().__init__(parent)
        self.controller = controller

        layout = QVBoxLayout(self)
        group = QGroupBox("Couches du reseau d'assainissement (SWMM)", self)
        group_layout = QVBoxLayout(group)

        group_layout.addWidget(LayerFieldRow(
            "Regards / jonctions :",
            lambda layer: controller.set_network_layer("junctions", layer),
            geometry_filter=QgsMapLayerProxyModel.PointLayer,
            field_label="Cote radier :",
            on_field_changed=lambda f: controller.config.network.junctions.field_map.__setitem__("invert", f),
        ))
        group_layout.addWidget(LayerFieldRow(
            "Conduites :",
            lambda layer: controller.set_network_layer("conduits", layer),
            geometry_filter=QgsMapLayerProxyModel.LineLayer,
            field_label="Diametre :",
            on_field_changed=lambda f: controller.config.network.conduits.field_map.__setitem__("diameter", f),
        ))
        group_layout.addWidget(LayerFieldRow(
            "Exutoires :",
            lambda layer: controller.set_network_layer("outfalls", layer),
            geometry_filter=QgsMapLayerProxyModel.PointLayer,
            field_label="Cote radier :",
            on_field_changed=lambda f: controller.config.network.outfalls.field_map.__setitem__("invert", f),
        ))
        group_layout.addWidget(LayerFieldRow(
            "Sous-bassins versants :",
            lambda layer: controller.set_network_layer("subcatchments", layer),
            geometry_filter=QgsMapLayerProxyModel.PolygonLayer,
            field_label="Exutoire (id noeud) :",
            on_field_changed=lambda f: controller.config.network.subcatchments.field_map.__setitem__("outlet", f),
        ))
        group_layout.addWidget(LayerFieldRow(
            "Pluviometres (optionnel) :",
            lambda layer: controller.set_network_layer("raingages", layer),
            geometry_filter=QgsMapLayerProxyModel.PointLayer,
        ))

        layout.addWidget(group)
        layout.addStretch()
