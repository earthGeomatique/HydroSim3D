"""Point d'entree du plugin QGIS PointCloud2BIM."""


def classFactory(iface):
    from .plugin import PointCloud2BimPlugin

    return PointCloud2BimPlugin(iface)
