"""Panneau de controle principal : QDockWidget a onglets.

Assemble les cinq onglets (Topographie, Reseau, Hydraulique, Simulation, 3D)
autour d'un unique :class:`~hydrosim3d.controller.SimulationController`. Les
onglets ne communiquent jamais directement entre eux : toute interaction
passe par le controleur (couches selectionnees, configuration, resultats).
"""
from __future__ import annotations

from qgis.PyQt.QtWidgets import QDockWidget, QTabWidget

from ..controller import SimulationController
from .tab_hydraulics import HydraulicsTab
from .tab_network import NetworkTab
from .tab_simulation import SimulationTab
from .tab_topography import TopographyTab
from .tab_viewer3d import Viewer3DTab


class HydroSim3DDock(QDockWidget):
    def __init__(self, iface, parent=None):
        super().__init__("HydroSim3D", parent)
        self.iface = iface
        self.controller = SimulationController(self)

        self.tabs = QTabWidget(self)
        self.tabs.addTab(TopographyTab(self.controller, self.tabs), "Topographie")
        self.tabs.addTab(NetworkTab(self.controller, self.tabs), "Reseau d'assainissement")
        self.tabs.addTab(HydraulicsTab(self.controller, self.tabs), "Hydraulique")
        self.tabs.addTab(SimulationTab(self.controller, self.tabs), "Simulation")
        self.tabs.addTab(Viewer3DTab(self.controller, self.tabs), "Visualisation 3D")

        self.setWidget(self.tabs)
