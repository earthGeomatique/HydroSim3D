# PointCloud2BIM

Plugin QGIS (PyQt) qui triangule un **MNT raster (GeoTIFF, .tif)** et
exporte le maillage obtenu au format **IFC** (IFC2X3 ou IFC4), pour
reutilisation directe dans les logiciels BIM (Revit, ArchiCAD, FreeCAD,
BIMvision...).

> Le nom du plugin est herite d'une version anterieure basee sur des nuages
> de points LAS/LAZ. L'entree a ete changee pour un MNT raster (.tif), plus
> adaptee aux flux de travail topographiques courants ; le nom n'a pas ete
> change pour rester coherent avec l'historique du projet.

## Architecture

```
PointCloud2BIM/
├── __init__.py              # classFactory (point d'entree QGIS)
├── plugin.py                 # initGui / unload, action de la barre d'outils
├── dialog.py                  # QDialog a 3 onglets (Input/Output, Processing, Project Info)
├── converter/
│   ├── dem_reader.py           # lecture GeoTIFF pleine resolution -> grille numpy (GDAL)
│   ├── mesh_builder.py          # triangulation de la grille (gestion des cellules nodata)
│   ├── ifc_writer.py             # export IFC2X3 (Brep) / IFC4 (PolygonalFaceSet) via ifcopenshell
│   └── pipeline.py                # orchestration bout-en-bout (lecture -> maillage -> export)
├── tasks/
│   └── conversion_task.py         # execution non-bloquante (QgsTask)
└── resources/icons/
```

## Installation

1. Cloner ce depot dans le repertoire des extensions QGIS, ou copier
   uniquement le sous-dossier `PointCloud2BIM/` (le depot `HydroSim3D`
   heberge plusieurs plugins independants) :
   - Linux : `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/PointCloud2BIM`
   - Windows : `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\PointCloud2BIM`
   - macOS : `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/PointCloud2BIM`
2. Installer les dependances Python dans l'environnement de QGIS :
   ```
   pip install -r PointCloud2BIM/requirements.txt
   ```
3. Redemarrer QGIS puis activer **PointCloud2BIM** dans
   **Extensions > Installer/Gerer les extensions > Extensions installees**.

## Utilisation

1. **Input / Output** : selectionner le MNT source (fichier **GeoTIFF .tif**,
   une bande) et le chemin du fichier IFC de sortie.
2. **Processing** :
   - **Schema IFC** : `IFC4` (recommande, maillage compact
     `IfcPolygonalFaceSet`) ou `IFC2X3` (compatibilite historique, un
     `IfcFacetedBrep` par triangle — plus volumineux, prevoir une
     decimation pour les MNT resolus) ;
   - **Decimation** : ne garde qu'une cellule sur N dans chaque direction,
     pour reduire le nombre de triangles ;
   - **Exageration verticale** et **decalage altimetrique** : appliques a
     la coordonnee Z avant export ;
   - **EPSG** : force le systeme de coordonnees si celui du MNT est absent
     ou incorrect (sinon detecte automatiquement).
3. **Project Info** : metadonnees du fichier IFC (nom du projet, du site,
   auteur, organisation, description).
4. **Run Conversion** : la conversion s'execute en arriere-plan (QGIS reste
   utilisable), avec barre de progression et journal detaille. **Cancel**
   interrompt la tache en cours.

## Limites connues

* L'entree doit etre un MNT **mono-bande** (une seule valeur d'elevation
  par cellule) ; un raster multi-bandes (ex: orthophoto) n'est pas
  interprete correctement.
* Le schema **IFC2X3** represente chaque triangle par un `IfcFacetedBrep`
  individuel (ce schema ne connait pas la tessellation, introduite avec
  IFC4) : au-dela d'environ 20 000 triangles, le fichier devient tres
  volumineux et lent a ouvrir. Un avertissement est affiche dans le journal
  dans ce cas ; augmenter la decimation ou utiliser IFC4 resout le probleme.
* Les cellules "nodata" du MNT ne sont pas interpolees : les triangles qui
  les touchent sont simplement omis, laissant un trou dans le maillage.
* Pas de georeferencement IFC natif (`IfcMapConversion`) pour le moment :
  le systeme de coordonnees source est indique en texte dans la
  description du site IFC, a titre informatif.

## Tests

Les tests unitaires (executes depuis **ce dossier**, independamment du
depot HydroSim3D voisin) couvrent la triangulation (sans dependance GDAL)
et l'export IFC (necessite `ifcopenshell`, ignore automatiquement sinon) :

```
cd PointCloud2BIM
pytest tests/
```
