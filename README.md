# HydroSim3D

Plugin QGIS (PyQt) integrant les moteurs de modelisation **SWMM**
(reseau d'assainissement / hydrologie urbaine) et **HEC-RAS** (hydraulique
fluviale 2D), avec visualisation 3D des resultats directement dans QGIS
(rendu de type ParaView, via PyVista).

Ce depot est directement le dossier du plugin HydroSim3D (pas de
sous-dossier intermediaire) : son contenu (hors `PointCloud2BIM/`, voir
ci-dessous) doit etre copie dans un dossier nomme `HydroSim3D` sous le
repertoire des extensions QGIS.

> Ce depot heberge egalement un second plugin QGIS independant,
> **[PointCloud2BIM](PointCloud2BIM/README.md)** (triangulation d'un MNT et
> export IFC pour les logiciels BIM), dans son propre sous-dossier avec sa
> propre installation.

## Architecture

```
./ (racine du depot = dossier du plugin)
├── __init__.py            # classFactory (point d'entree QGIS)
├── plugin.py               # initGui / unload, action de la barre d'outils
├── controller.py            # SimulationController : etat central + orchestration
├── config.py                 # dataclasses de configuration (topo, reseau, hydraulique, simulation)
├── results.py                # modele pivot SimulationResult (consomme par le viewer 3D)
├── engines/
│   ├── base.py                # interface commune (template method execute())
│   ├── swmm_engine.py          # export -> pyswmm/swmm5 -> import
│   └── hecras_engine.py        # export GIS -> COM HECRASController -> import HDF5
├── io/
│   ├── swmm_writer.py / swmm_reader.py
│   ├── hecras_writer.py / hecras_reader.py
│   └── raster_utils.py        # lecture MNT -> grille numpy (rendu 3D)
├── tasks/
│   └── simulation_task.py     # execution non-bloquante (QgsTask)
├── ui/
│   ├── main_dock.py            # QDockWidget a onglets
│   ├── tab_topography.py       # selection du MNT (QgsRasterLayer)
│   ├── tab_network.py          # couches SWMM (QgsVectorLayer)
│   ├── tab_hydraulics.py       # couches HEC-RAS (QgsVectorLayer)
│   ├── tab_simulation.py       # parametres temporels + lancement + logs
│   └── tab_viewer3d.py         # heberge le panneau PyVista
└── viewer3d/
    └── pyvista_panel.py        # terrain + degrades de couleur + glyphes vecteurs
```

Le **controleur** (`SimulationController`) est l'unique point de verite :
les onglets lisent/ecrivent la configuration via ses methodes et signaux
Qt (`configChanged`, `simulationStarted/Progress/Finished/Failed`,
`logMessage`). Aucun onglet ne connait les autres, ce qui permet d'ajouter
un troisieme moteur de calcul sans toucher a l'UI existante.

## Installation

1. Cloner ce depot (ou en telecharger le ZIP) directement dans un dossier
   nomme `HydroSim3D` sous le repertoire des extensions QGIS :
   - Linux : `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/HydroSim3D`
   - Windows : `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\HydroSim3D`
   - macOS : `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/HydroSim3D`

   ```
   git clone https://github.com/earthGeomatique/HydroSim3D.git HydroSim3D
   ```
2. Installer les dependances Python dans l'environnement de QGIS :
   ```
   pip install -r HydroSim3D/requirements.txt
   ```
   (sous Windows, executer cette commande depuis l'invite **OSGeo4W Shell**
   fournie avec QGIS, pour cibler le bon interpreteur Python).
3. Redemarrer QGIS puis activer **HydroSim3D** dans
   **Extensions > Installer/Gerer les extensions > Extensions installees**.

## Utilisation

1. **Topographie** : selectionner le MNT (`QgsRasterLayer`) du projet.
2. **Reseau d'assainissement** (pour SWMM) : selectionner les couches
   regards, conduites, exutoires, sous-bassins (`QgsVectorLayer`) et
   mapper les champs d'attributs necessaires (cote radier, diametre...).
3. **Hydraulique** (pour HEC-RAS) : selectionner la ligne d'axe et les
   profils en travers.
4. **Simulation** : choisir le moteur, la fenetre temporelle et le
   repertoire de travail, puis cliquer sur **Lancer la simulation**. Le
   calcul s'execute en arriere-plan (QGIS reste utilisable) et les logs
   s'affichent dans la console de l'onglet.
5. **Visualisation 3D** : une fois la simulation terminee, le terrain et
   les resultats (hauteur d'eau, vitesse) s'affichent automatiquement,
   avec un curseur pour rejouer les pas de temps et des fleches pour la
   direction de l'ecoulement.

## Limites connues

* **SWMM** est entierement automatise via `pyswmm` (multiplateforme). Si
  `pyswmm` n'est pas installe, le plugin retombe sur un executable
  `swmm5` configure manuellement dans l'onglet Simulation.
* **HEC-RAS** n'expose pas d'API multiplateforme : l'import de la
  geometrie (terrain, ligne d'axe, profils) dans un projet HEC-RAS se fait
  via l'assistant **Import GIS Data** de RAS Mapper (etape manuelle unique
  par projet). Le plugin exporte les shapefiles/GeoTIFF au format attendu
  dans `<repertoire_de_travail>/gis_export/`. Une fois le projet HEC-RAS
  (`.prj`) present avec sa geometrie importee, le calcul du plan est
  automatise via l'interface COM `HECRASController`, disponible uniquement
  sous **Windows** (HEC-RAS lui-meme n'existe que sous Windows).
* Le rendu 3D sous-echantillonne le MNT (400 x 400 cellules par defaut)
  pour rester interactif ; cela n'affecte pas la precision des calculs
  hydrauliques, uniquement l'apercu visuel.

## Tests

Les tests unitaires (`tests/`) couvrent le controleur, la configuration et
le modele de resultats sans dependre de QGIS ni des moteurs externes :

```
pytest tests/
```
