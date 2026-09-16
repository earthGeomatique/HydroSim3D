"""Point d'entree du plugin QGIS HydroSim3D.

QGIS appelle ``classFactory(iface)`` pour instancier le plugin ; toute la
logique reste dans :mod:`hydrosim3d.plugin`.
"""


def classFactory(iface):
    from .plugin import HydroSim3DPlugin

    return HydroSim3DPlugin(iface)
