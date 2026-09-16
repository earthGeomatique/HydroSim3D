"""Petits widgets composites reutilises par les onglets Reseau / Hydraulique.

``LayerFieldRow`` regroupe un selecteur de couche QGIS (``QgsMapLayerComboBox``)
et, en option, un selecteur de champ (``QgsFieldComboBox``) synchronise avec
la couche choisie. C'est le brique de base de tous les mappings
"role logique -> couche + attribut" utilises pour configurer SWMM / HEC-RAS.
"""
from __future__ import annotations

from typing import Callable, Optional

from qgis.core import QgsMapLayerProxyModel
from qgis.gui import QgsFieldComboBox, QgsMapLayerComboBox
from qgis.PyQt.QtWidgets import QHBoxLayout, QLabel, QWidget


class LayerFieldRow(QWidget):
    """Une ligne : libelle + combo de couche (+ combo de champ optionnel)."""

    def __init__(
        self,
        label: str,
        on_layer_changed: Callable,
        geometry_filter: QgsMapLayerProxyModel.Filter = QgsMapLayerProxyModel.VectorLayer,
        field_label: Optional[str] = None,
        on_field_changed: Optional[Callable] = None,
        parent=None,
    ):
        super().__init__(parent)
        self._on_layer_changed = on_layer_changed
        self._on_field_changed = on_field_changed

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(label))

        self.layer_combo = QgsMapLayerComboBox(self)
        self.layer_combo.setFilters(geometry_filter)
        self.layer_combo.setAllowEmptyLayer(True)
        self.layer_combo.layerChanged.connect(self._handle_layer_changed)
        layout.addWidget(self.layer_combo, stretch=2)

        self.field_combo = None
        if field_label is not None:
            layout.addWidget(QLabel(field_label))
            self.field_combo = QgsFieldComboBox(self)
            self.field_combo.setLayer(self.layer_combo.currentLayer())
            self.field_combo.fieldChanged.connect(self._handle_field_changed)
            layout.addWidget(self.field_combo, stretch=1)

    def _handle_layer_changed(self, layer) -> None:
        if self.field_combo is not None:
            self.field_combo.setLayer(layer)
        self._on_layer_changed(layer)

    def _handle_field_changed(self, field_name: str) -> None:
        if self._on_field_changed:
            self._on_field_changed(field_name)

    def current_layer(self):
        return self.layer_combo.currentLayer()
