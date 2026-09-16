"""Interface commune aux moteurs de simulation (SWMM, HEC-RAS, ...).

Chaque moteur suit le meme template method : ``export_inputs`` ->
``run`` -> ``import_results``. Le controleur (ou la QgsTask qui l'encapsule)
appelle uniquement :meth:`SimulationEngine.execute`, ce qui garantit que
tous les moteurs exposent le meme cycle de vie et facilite l'ajout d'un
troisieme moteur a l'avenir sans toucher au controleur.
"""
from __future__ import annotations

import os
from typing import Callable, Optional

from ..results import SimulationResult

ProgressCallback = Callable[[int, str], None]
LogCallback = Callable[[str], None]


def _noop_progress(pct: int, msg: str) -> None:  # pragma: no cover - trivial
    pass


def _noop_log(msg: str) -> None:  # pragma: no cover - trivial
    pass


class SimulationEngine:
    """Classe de base : ne pas instancier directement."""

    #: identifiant court utilise dans les logs / metadonnees de resultat
    name = "base"

    def __init__(self, config, layer_resolver: Callable[[Optional[str]], object]):
        self.config = config
        self.resolve_layer = layer_resolver

    # -- a implementer par les sous-classes ---------------------------------
    def export_inputs(self, working_dir: str, log_cb: LogCallback) -> str:
        """Ecrit les fichiers d'entree du moteur et retourne le chemin
        du fichier principal (ex: .inp pour SWMM)."""
        raise NotImplementedError

    def run(self, input_path: str, working_dir: str,
             progress_cb: ProgressCallback, log_cb: LogCallback) -> str:
        """Execute le moteur et retourne le chemin du fichier de resultats."""
        raise NotImplementedError

    def import_results(self, output_path: str, log_cb: LogCallback) -> SimulationResult:
        """Parse les sorties du moteur en :class:`SimulationResult`."""
        raise NotImplementedError

    # -- template method -----------------------------------------------
    def execute(self, working_dir: str,
                progress_cb: ProgressCallback = _noop_progress,
                log_cb: LogCallback = _noop_log) -> SimulationResult:
        os.makedirs(working_dir, exist_ok=True)

        progress_cb(5, f"[{self.name}] Export des donnees QGIS...")
        input_path = self.export_inputs(working_dir, log_cb)

        progress_cb(30, f"[{self.name}] Lancement du moteur de calcul...")
        output_path = self.run(input_path, working_dir, progress_cb, log_cb)

        progress_cb(90, f"[{self.name}] Lecture des resultats...")
        result = self.import_results(output_path, log_cb)

        progress_cb(100, f"[{self.name}] Termine.")
        return result
