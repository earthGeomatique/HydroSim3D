"""Controleur centralise du plugin HydroSim3D.

Architecture retenue : un unique objet ``SimulationController`` sert de
mediateur entre :

* les couches QGIS (``QgsVectorLayer`` / ``QgsRasterLayer``) selectionnees
  dans les onglets ;
* la configuration de simulation (:mod:`hydrosim3d.config`) ;
* les moteurs de calcul SWMM / HEC-RAS (:mod:`hydrosim3d.engines`) ;
* le panneau de visualisation 3D.

Les onglets de l'interface ne se parlent jamais directement : ils lisent et
ecrivent l'etat via le controleur, qui emet des signaux Qt pour notifier les
autres composants (pattern "single source of truth"). Cela permet d'ajouter
ou de retirer un onglet sans toucher aux autres.
"""
from __future__ import annotations

from typing import Optional

from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer

from .config import EngineType, ProjectConfig
from .results import SimulationResult


class SimulationController(QObject):
    """Etat central + orchestration des moteurs de simulation."""

    #: emis a chaque modification de la configuration (onglet -> reste de l'UI)
    configChanged = pyqtSignal()

    #: emis quand une simulation demarre : (nom_moteur)
    simulationStarted = pyqtSignal(str)

    #: emis pendant l'execution : (pourcentage 0-100, message)
    simulationProgress = pyqtSignal(int, str)

    #: emis a la fin d'une simulation reussie, avec le resultat pret pour la 3D
    simulationFinished = pyqtSignal(object)  # SimulationResult

    #: emis en cas d'echec : (message d'erreur)
    simulationFailed = pyqtSignal(str)

    #: emis quand un log doit etre affiche dans la console de l'onglet Simulation
    logMessage = pyqtSignal(str)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.config = ProjectConfig()
        self.last_result: Optional[SimulationResult] = None
        self._active_task = None  # reference forte vers la QgsTask en cours

    # ------------------------------------------------------------------
    # Gestion des couches QGIS
    # ------------------------------------------------------------------
    @staticmethod
    def resolve_layer(layer_id: Optional[str]):
        """Retrouve une couche du projet QGIS courant a partir de son id.

        On ne garde jamais de reference directe a la couche dans la config :
        uniquement l'id, resolu ici a la demande. Si la couche a ete
        supprimee du projet, ``None`` est retourne plutot que de lever une
        exception, pour que l'UI puisse simplement griser les actions.
        """
        if not layer_id:
            return None
        return QgsProject.instance().mapLayer(layer_id)

    def set_dem(self, layer: Optional[QgsRasterLayer]) -> None:
        self.config.topography.dem.layer_id = layer.id() if layer else None
        self.configChanged.emit()

    def set_network_layer(self, role: str, layer: Optional[QgsVectorLayer]) -> None:
        """``role`` in {junctions, conduits, outfalls, subcatchments, raingages}."""
        ref = getattr(self.config.network, role)
        ref.layer_id = layer.id() if layer else None
        self.configChanged.emit()

    def set_hydraulics_layer(self, role: str, layer: Optional[QgsVectorLayer]) -> None:
        """``role`` in {river_centerline, cross_sections, bank_lines, manning_zones}."""
        ref = getattr(self.config.hydraulics, role)
        ref.layer_id = layer.id() if layer else None
        self.configChanged.emit()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self, engine: EngineType) -> list:
        """Retourne la liste des erreurs bloquantes pour le moteur choisi.

        Une liste vide signifie que la configuration est valide et que la
        simulation peut etre lancee.
        """
        errors = []
        if self.resolve_layer(self.config.topography.dem.layer_id) is None:
            errors.append("Aucun modele numerique de terrain (MNT) selectionne.")

        if engine is EngineType.SWMM:
            net = self.config.network
            if self.resolve_layer(net.junctions.layer_id) is None:
                errors.append("Couche des regards/jonctions manquante.")
            if self.resolve_layer(net.conduits.layer_id) is None:
                errors.append("Couche des conduites manquante.")
            if self.resolve_layer(net.outfalls.layer_id) is None:
                errors.append("Couche des exutoires manquante.")
        elif engine is EngineType.HECRAS:
            hyd = self.config.hydraulics
            if self.resolve_layer(hyd.river_centerline.layer_id) is None:
                errors.append("Ligne d'axe (centerline) de la riviere manquante.")
            if self.resolve_layer(hyd.cross_sections.layer_id) is None:
                errors.append("Couche des profils en travers manquante.")

        if not self.config.simulation.working_dir:
            errors.append("Aucun repertoire de travail defini pour la simulation.")

        return errors

    # ------------------------------------------------------------------
    # Orchestration des simulations
    # ------------------------------------------------------------------
    def build_engine(self):
        """Instancie le moteur correspondant a ``self.config.simulation.engine``."""
        engine_type = self.config.simulation.engine
        if engine_type is EngineType.SWMM:
            from .engines.swmm_engine import SwmmEngine

            return SwmmEngine(self.config, self.resolve_layer)
        elif engine_type is EngineType.HECRAS:
            from .engines.hecras_engine import HecRasEngine

            return HecRasEngine(self.config, self.resolve_layer)
        raise ValueError(f"Moteur inconnu : {engine_type}")

    def run_simulation(self, use_background_task: bool = True) -> None:
        """Lance la simulation configuree.

        Par defaut, l'execution se fait dans une ``QgsTask`` en arriere-plan
        pour ne pas geler l'interface de QGIS pendant que SWMM / HEC-RAS
        calculent. ``use_background_task=False`` est reserve aux tests
        unitaires (execution synchrone, sans QGIS).
        """
        errors = self.validate(self.config.simulation.engine)
        if errors:
            self.simulationFailed.emit("\n".join(errors))
            return

        engine = self.build_engine()
        engine_name = self.config.simulation.engine.value

        if not use_background_task:
            self._run_engine_sync(engine, engine_name)
            return

        from .tasks.simulation_task import SimulationTask

        task = SimulationTask(engine_name, engine, self.config.simulation.working_dir)
        task.progressChanged.connect(self.simulationProgress.emit)
        task.logEmitted.connect(self.logMessage.emit)
        task.finishedOk.connect(self._on_task_finished)
        task.finishedError.connect(self._on_task_failed)

        self._active_task = task
        self.simulationStarted.emit(engine_name)

        from qgis.core import QgsApplication

        QgsApplication.taskManager().addTask(task)

    def _run_engine_sync(self, engine, engine_name: str) -> None:
        self.simulationStarted.emit(engine_name)
        try:
            result = engine.execute(
                self.config.simulation.working_dir,
                progress_cb=lambda p, m: self.simulationProgress.emit(p, m),
                log_cb=lambda m: self.logMessage.emit(m),
            )
            self._on_task_finished(result)
        except Exception as exc:  # noqa: BLE001 - relaye a l'UI, pas de crash
            self._on_task_failed(str(exc))

    def _on_task_finished(self, result: SimulationResult) -> None:
        self.last_result = result
        self._active_task = None
        self.simulationFinished.emit(result)

    def _on_task_failed(self, message: str) -> None:
        self._active_task = None
        self.simulationFailed.emit(message)
