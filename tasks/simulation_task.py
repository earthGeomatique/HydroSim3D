"""Encapsule l'execution d'un moteur de simulation dans une QgsTask.

QGIS deconseille fortement les operations longues sur le thread principal
(l'UI se figerait pendant tout le calcul SWMM/HEC-RAS). ``QgsTask`` fournit
un pool de threads gere par QGIS ; ce module fait le pont entre son API
(methode ``run`` executee hors thread principal, ``finished`` rappelee sur
le thread principal) et les signaux Qt consommes par le controleur.
"""
from __future__ import annotations

from qgis.core import QgsTask
from qgis.PyQt.QtCore import pyqtSignal


class SimulationTask(QgsTask):
    progressChanged = pyqtSignal(int, str)
    logEmitted = pyqtSignal(str)
    finishedOk = pyqtSignal(object)
    finishedError = pyqtSignal(str)

    def __init__(self, engine_name: str, engine, working_dir: str):
        super().__init__(f"HydroSim3D - simulation {engine_name}", QgsTask.CanCancel)
        self._engine = engine
        self._working_dir = working_dir
        self._result = None
        self._error = None

    def run(self) -> bool:
        """Execute hors du thread principal : ne touche a aucune API Qt/QGIS
        non thread-safe (les objets couches ont deja ete resolus avant)."""
        try:
            self._result = self._engine.execute(
                self._working_dir,
                progress_cb=self._on_progress,
                log_cb=self._on_log,
            )
            return True
        except Exception as exc:  # noqa: BLE001 - remonte proprement a l'UI
            self._error = str(exc)
            return False

    def _on_progress(self, pct: int, message: str) -> None:
        self.setProgress(pct)
        self.progressChanged.emit(pct, message)

    def _on_log(self, message: str) -> None:
        self.logEmitted.emit(message)

    def finished(self, result: bool) -> None:
        """Rappelee sur le thread principal par le gestionnaire de taches QGIS."""
        if result and self._result is not None:
            self.finishedOk.emit(self._result)
        else:
            self.finishedError.emit(self._error or "Echec inconnu de la simulation.")
