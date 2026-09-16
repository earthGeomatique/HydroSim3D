"""Moteur HEC-RAS : export GIS -> automatisation COM (Windows) -> lecture HDF5.

Limite connue et assumee : HEC-RAS ne fournit pas d'API multiplateforme ni
de format d'entree texte simple comme SWMM. Deux consequences pour ce
moteur :

1. L'import de la geometrie (ligne d'axe, profils en travers, terrain) dans
   un projet HEC-RAS se fait via l'assistant "Import GIS Data" de RAS
   Mapper. Ce plugin exporte les shapefiles/GeoTIFF au bon format
   (:mod:`hydrosim3d.io.hecras_writer`) mais ne peut pas piloter cet
   assistant graphique a la place de l'utilisateur : c'est une etape
   manuelle a realiser une fois par projet.
2. Une fois un projet HEC-RAS (.prj) present dans le repertoire de travail
   avec sa geometrie importee, le calcul du plan est automatise via
   l'interface COM ``HECRASController``, disponible uniquement sous
   Windows (HEC-RAS lui-meme n'existe que sous Windows).
"""
from __future__ import annotations

import glob
import os
import sys

from .base import LogCallback, ProgressCallback, SimulationEngine
from ..io.hecras_reader import read_hecras_hdf
from ..io.hecras_writer import export_hecras_gis_data
from ..results import SimulationResult


class HecRasEngine(SimulationEngine):
    name = "hecras"

    def export_inputs(self, working_dir: str, log_cb: LogCallback) -> str:
        dem = self.resolve_layer(self.config.topography.dem.layer_id)
        river = self.resolve_layer(self.config.hydraulics.river_centerline.layer_id)
        cross_sections = self.resolve_layer(self.config.hydraulics.cross_sections.layer_id)
        bank_lines = self.resolve_layer(self.config.hydraulics.bank_lines.layer_id)

        manifest = export_hecras_gis_data(working_dir, dem, river, cross_sections, bank_lines)
        log_cb(f"Donnees GIS exportees pour HEC-RAS dans {os.path.join(working_dir, 'gis_export')}")

        existing_prj = self._find_project_file(working_dir)
        if existing_prj:
            log_cb(f"Projet HEC-RAS existant detecte : {existing_prj}")
            return existing_prj

        log_cb(
            "Aucun projet HEC-RAS (.prj) trouve dans le repertoire de travail. "
            "Ouvrez RAS Mapper, creez un projet, puis importez les fichiers du "
            "dossier 'gis_export' via Import GIS Data avant de relancer le calcul."
        )
        return manifest["terrain"]  # chemin non-.prj : signale l'etape manuelle a run()

    @staticmethod
    def _find_project_file(working_dir: str):
        matches = glob.glob(os.path.join(working_dir, "*.prj"))
        # Un .prj de projection (WKT) peut aussi exister a cote des shapefiles ;
        # on ne retient que ceux situes a la racine du repertoire de travail
        # et pas dans le sous-dossier d'export GIS.
        return matches[0] if matches else None

    def run(self, input_path: str, working_dir: str,
            progress_cb: ProgressCallback, log_cb: LogCallback) -> str:
        if not input_path.lower().endswith(".prj"):
            raise RuntimeError(
                "Import GIS manuel requis avant le premier calcul : voir le "
                "dossier 'gis_export' et le journal ci-dessus."
            )

        if sys.platform != "win32":
            raise RuntimeError(
                "L'automatisation de HEC-RAS necessite Windows (interface COM "
                "HECRASController). Sur cette plateforme, lancez le calcul "
                "manuellement dans HEC-RAS puis utilisez 'Charger des resultats "
                "existants' pour visualiser le fichier .pXX.hdf en 3D."
            )

        try:
            import win32com.client
        except ImportError as exc:
            raise RuntimeError(
                "Le module 'pywin32' est requis pour piloter HEC-RAS "
                "(pip install pywin32)."
            ) from exc

        progress_cb(40, "Ouverture du projet HEC-RAS...")
        controller = win32com.client.Dispatch("RAS507.HECRASController")
        controller.Project_Open(input_path)
        try:
            plan_names, plan_ids = None, None
            n_msg, messages = 0, []
            progress_cb(60, "Calcul du plan courant...")
            controller.Compute_CurrentPlan(None, None, True)
            progress_cb(85, "Calcul termine, recherche des sorties...")
        finally:
            controller.QuitRAS()

        hdf_candidates = sorted(glob.glob(os.path.join(os.path.dirname(input_path), "*.p*.hdf")))
        if not hdf_candidates:
            raise RuntimeError("Le calcul HEC-RAS n'a produit aucun fichier de resultats .pXX.hdf.")
        return hdf_candidates[-1]

    def import_results(self, output_path: str, log_cb: LogCallback) -> SimulationResult:
        result = read_hecras_hdf(output_path)
        log_cb(
            f"Resultats HEC-RAS charges : {result.n_points} cellules, "
            f"{result.n_steps} pas de temps (zone '{result.metadata.get('flow_area')}')."
        )
        return result
