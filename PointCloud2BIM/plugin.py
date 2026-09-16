"""Classe principale du plugin QGIS PointCloud2BIM (initGui / unload)."""
from __future__ import annotations

import os

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

PLUGIN_DIR = os.path.dirname(__file__)


class PointCloud2BimPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None

    def initGui(self) -> None:
        icon_path = os.path.join(PLUGIN_DIR, "resources", "icons", "pointcloud2bim.svg")
        self.action = QAction(QIcon(icon_path), "PointCloud2BIM", self.iface.mainWindow())
        self.action.triggered.connect(self.show_dialog)

        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&PointCloud2BIM", self.action)

    def show_dialog(self) -> None:
        from .dialog import PointCloud2BimDialog

        if self.dialog is None:
            self.dialog = PointCloud2BimDialog(self.iface.mainWindow())
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()

    def unload(self) -> None:
        if self.dialog is not None:
            self.dialog.close()
            self.dialog.deleteLater()
            self.dialog = None
        if self.action is not None:
            self.iface.removePluginMenu("&PointCloud2BIM", self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action = None
