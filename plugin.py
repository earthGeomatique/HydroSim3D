"""Classe principale du plugin QGIS HydroSim3D (initGui / unload)."""
from __future__ import annotations

import os

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .ui.main_dock import HydroSim3DDock

PLUGIN_DIR = os.path.dirname(__file__)


class HydroSim3DPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.dock = None
        self.action = None

    def initGui(self) -> None:
        icon_path = os.path.join(PLUGIN_DIR, "resources", "icons", "hydrosim3d.svg")
        self.action = QAction(QIcon(icon_path), "HydroSim3D", self.iface.mainWindow())
        self.action.setCheckable(True)
        self.action.triggered.connect(self.toggle_dock)

        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&HydroSim3D", self.action)

    def toggle_dock(self, checked: bool) -> None:
        if self.dock is None:
            self.dock = HydroSim3DDock(self.iface, self.iface.mainWindow())
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)
            self.dock.visibilityChanged.connect(self._on_visibility_changed)
        self.dock.setVisible(checked)

    def _on_visibility_changed(self, visible: bool) -> None:
        if self.action is not None:
            self.action.setChecked(visible)

    def unload(self) -> None:
        if self.dock is not None:
            self.iface.removeDockWidget(self.dock)
            self.dock.deleteLater()
            self.dock = None
        if self.action is not None:
            self.iface.removePluginMenu("&HydroSim3D", self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action = None
