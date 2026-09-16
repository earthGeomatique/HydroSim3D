"""Export des couches QGIS vers les formats GIS attendus par HEC-RAS.

HEC-RAS ne propose pas de format d'entree texte simple comme SWMM : la
geometrie (ligne d'axe, profils en travers, berges) et le terrain sont
importes dans RAS Mapper via son assistant "Import GIS Data", qui attend
des shapefiles respectant un schema d'attributs precis
(``River``, ``Reach``, ``RS`` pour les profils en travers notamment).

Ce module produit :

* le MNT au format GeoTIFF (terrain source pour RAS Mapper) ;
* les shapefiles de geometrie (centerline, cross-sections, banks) avec le
  schema attendu par HEC-RAS ;
* un manifeste JSON recapitulant les fichiers generes, pour guider
  l'utilisateur lors de l'import (ou un futur script d'automatisation).
"""
from __future__ import annotations

import json
import os
from typing import Optional

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsField,
    QgsFields,
    QgsRasterFileWriter,
    QgsRasterLayer,
    QgsRasterPipe,
    QgsVectorFileWriter,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QVariant


def export_terrain(dem: QgsRasterLayer, out_dir: str) -> str:
    terrain_path = os.path.join(out_dir, "terrain.tif")
    pipe = QgsRasterPipe()
    if not pipe.set(dem.dataProvider().clone()):
        raise RuntimeError("Impossible de preparer le pipeline raster pour l'export du MNT.")

    writer = QgsRasterFileWriter(terrain_path)
    writer.writeRaster(
        pipe,
        dem.dataProvider().xSize(),
        dem.dataProvider().ySize(),
        dem.extent(),
        dem.crs(),
    )
    return terrain_path


def _add_missing_fields(layer: QgsVectorLayer, required: dict) -> QgsVectorLayer:
    """Retourne une copie memoire de ``layer`` avec les champs HEC-RAS requis.

    ``required`` associe nom de champ -> valeur par defaut. Les couches de
    l'utilisateur n'ont pas forcement de champs ``River``/``Reach``/``RS`` :
    on les ajoute avec des valeurs par defaut plutot que d'echouer.
    """
    clone = layer.materialize(layer.extent())
    provider = clone.dataProvider()
    existing = {f.name() for f in clone.fields()}
    new_fields = QgsFields()
    for name, default in required.items():
        if name in existing:
            continue
        field_type = QVariant.Double if isinstance(default, float) else QVariant.String
        new_fields.append(QgsField(name, field_type))
    if len(new_fields) > 0:
        provider.addAttributes(new_fields)
        clone.updateFields()

    clone.startEditing()
    for feat in clone.getFeatures():
        for name, default in required.items():
            idx = clone.fields().indexFromName(name)
            if idx >= 0 and (feat[name] is None or feat[name] == ""):
                clone.changeAttributeValue(feat.id(), idx, default)
    clone.commitChanges()
    return clone


def _write_shapefile(layer: QgsVectorLayer, out_path: str) -> str:
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "ESRI Shapefile"
    options.fileEncoding = "UTF-8"
    error = QgsVectorFileWriter.writeAsVectorFormatV3(
        layer, out_path, layer.transformContext(), options
    )
    if isinstance(error, tuple):
        code = error[0]
    else:
        code = error
    if code != QgsVectorFileWriter.NoError:
        raise RuntimeError(f"Echec de l'export shapefile vers {out_path} (code {code}).")
    return out_path


def export_river_centerline(layer: QgsVectorLayer, out_dir: str) -> str:
    prepared = _add_missing_fields(layer, {"River": "River1", "Reach": "Reach1"})
    return _write_shapefile(prepared, os.path.join(out_dir, "river_centerline.shp"))


def export_cross_sections(layer: QgsVectorLayer, out_dir: str) -> str:
    prepared = _add_missing_fields(layer, {"River": "River1", "Reach": "Reach1", "RS": 0.0})
    # Numerote les profils par ordre d'entite si RS n'est pas deja rempli
    prepared.startEditing()
    rs_idx = prepared.fields().indexFromName("RS")
    for i, feat in enumerate(prepared.getFeatures()):
        if not feat["RS"]:
            prepared.changeAttributeValue(feat.id(), rs_idx, float((i + 1) * 100))
    prepared.commitChanges()
    return _write_shapefile(prepared, os.path.join(out_dir, "cross_sections.shp"))


def export_bank_lines(layer: QgsVectorLayer, out_dir: str) -> str:
    return _write_shapefile(layer.materialize(layer.extent()), os.path.join(out_dir, "bank_lines.shp"))


def export_hecras_gis_data(
    working_dir: str,
    dem: QgsRasterLayer,
    river_centerline: QgsVectorLayer,
    cross_sections: QgsVectorLayer,
    bank_lines: Optional[QgsVectorLayer],
) -> dict:
    gis_dir = os.path.join(working_dir, "gis_export")
    os.makedirs(gis_dir, exist_ok=True)

    manifest = {
        "terrain": export_terrain(dem, gis_dir),
        "river_centerline": export_river_centerline(river_centerline, gis_dir),
        "cross_sections": export_cross_sections(cross_sections, gis_dir),
        "bank_lines": export_bank_lines(bank_lines, gis_dir) if bank_lines else None,
        "crs": dem.crs().authid(),
    }
    with open(os.path.join(gis_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    return manifest
