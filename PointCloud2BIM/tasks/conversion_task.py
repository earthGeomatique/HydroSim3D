"""Encapsule la conversion MNT -> IFC dans une QgsTask (non bloquant pour QGIS)."""
from __future__ import annotations

from qgis.core import QgsTask
from qgis.PyQt.QtCore import pyqtSignal

from ..converter.pipeline import run_conversion


class ConversionTask(QgsTask):
    progressChanged = pyqtSignal(int, str)
    logEmitted = pyqtSignal(str)
    finishedOk = pyqtSignal(dict)
    finishedError = pyqtSignal(str)

    def __init__(self, kwargs: dict):
        super().__init__("PointCloud2BIM - conversion MNT vers IFC", QgsTask.CanCancel)
        self._kwargs = kwargs
        self._report = None
        self._error = None

    def run(self) -> bool:
        try:
            self._report = run_conversion(
                progress_cb=self._on_progress,
                log_cb=self._on_log,
                **self._kwargs,
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
        if result and self._report is not None:
            self.finishedOk.emit(self._report)
        else:
            self.finishedError.emit(self._error or "Echec inconnu de la conversion.")
