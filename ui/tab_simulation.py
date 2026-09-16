"""Onglet Simulation : choix du moteur, parametres temporels, lancement."""
from __future__ import annotations

from datetime import datetime, timedelta

from qgis.PyQt.QtCore import QDateTime
from qgis.PyQt.QtWidgets import (
    QDateTimeEdit,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..config import EngineType
from ..controller import SimulationController


class SimulationTab(QWidget):
    def __init__(self, controller: SimulationController, parent=None):
        super().__init__(parent)
        self.controller = controller

        layout = QVBoxLayout(self)

        engine_group = QGroupBox("Moteur de simulation", self)
        engine_layout = QHBoxLayout(engine_group)
        self.swmm_radio = QRadioButton("SWMM (reseau d'assainissement)", engine_group)
        self.hecras_radio = QRadioButton("HEC-RAS (hydraulique fluviale 2D)", engine_group)
        self.swmm_radio.setChecked(True)
        self.swmm_radio.toggled.connect(self._on_engine_toggled)
        engine_layout.addWidget(self.swmm_radio)
        engine_layout.addWidget(self.hecras_radio)
        layout.addWidget(engine_group)

        params_group = QGroupBox("Parametres temporels", self)
        form = QFormLayout(params_group)

        self.start_edit = QDateTimeEdit(QDateTime.currentDateTime(), params_group)
        self.start_edit.setCalendarPopup(True)
        self.start_edit.dateTimeChanged.connect(self._on_params_changed)
        form.addRow("Debut :", self.start_edit)

        self.duration_spin = QSpinBox(params_group)
        self.duration_spin.setRange(1, 720)
        self.duration_spin.setValue(6)
        self.duration_spin.setSuffix(" h")
        self.duration_spin.valueChanged.connect(self._on_params_changed)
        form.addRow("Duree :", self.duration_spin)

        self.timestep_spin = QSpinBox(params_group)
        self.timestep_spin.setRange(1, 3600)
        self.timestep_spin.setValue(60)
        self.timestep_spin.setSuffix(" s")
        self.timestep_spin.valueChanged.connect(self._on_params_changed)
        form.addRow("Pas de temps de calcul :", self.timestep_spin)

        layout.addWidget(params_group)

        paths_group = QGroupBox("Repertoires et executables", self)
        paths_form = QFormLayout(paths_group)

        self.workdir_edit = QLineEdit(paths_group)
        workdir_row = QHBoxLayout()
        workdir_row.addWidget(self.workdir_edit)
        workdir_btn = QPushButton("Parcourir...", paths_group)
        workdir_btn.clicked.connect(self._browse_workdir)
        workdir_row.addWidget(workdir_btn)
        paths_form.addRow("Repertoire de travail :", workdir_row)

        self.exe_edit = QLineEdit(paths_group)
        exe_row = QHBoxLayout()
        exe_row.addWidget(self.exe_edit)
        exe_btn = QPushButton("Parcourir...", paths_group)
        exe_btn.clicked.connect(self._browse_executable)
        exe_row.addWidget(exe_btn)
        paths_form.addRow("Executable (swmm5, si pyswmm absent) :", exe_row)

        layout.addWidget(paths_group)

        run_row = QHBoxLayout()
        self.run_button = QPushButton("Lancer la simulation", self)
        self.run_button.clicked.connect(self._on_run_clicked)
        run_row.addWidget(self.run_button)
        layout.addLayout(run_row)

        self.progress_bar = QProgressBar(self)
        layout.addWidget(self.progress_bar)

        self.log_console = QPlainTextEdit(self)
        self.log_console.setReadOnly(True)
        layout.addWidget(self.log_console, stretch=1)

        controller.simulationStarted.connect(self._on_started)
        controller.simulationProgress.connect(self._on_progress)
        controller.simulationFinished.connect(self._on_finished)
        controller.simulationFailed.connect(self._on_failed)
        controller.logMessage.connect(self.log_console.appendPlainText)

        self._sync_from_config()

    def _sync_from_config(self) -> None:
        sim = self.controller.config.simulation
        if sim.working_dir:
            self.workdir_edit.setText(sim.working_dir)
        if sim.executable_path:
            self.exe_edit.setText(sim.executable_path)

    def _on_engine_toggled(self, checked: bool) -> None:
        self.controller.config.simulation.engine = EngineType.SWMM if self.swmm_radio.isChecked() else EngineType.HECRAS
        self.controller.configChanged.emit()

    def _on_params_changed(self, *_args) -> None:
        sim = self.controller.config.simulation
        qdt = self.start_edit.dateTime().toPyDateTime()
        sim.start = qdt
        sim.duration = timedelta(hours=self.duration_spin.value())
        sim.time_step_seconds = self.timestep_spin.value()
        self.controller.configChanged.emit()

    def _browse_workdir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Repertoire de travail")
        if path:
            self.workdir_edit.setText(path)
            self.controller.config.simulation.working_dir = path
            self.controller.configChanged.emit()

    def _browse_executable(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Executable de simulation")
        if path:
            self.exe_edit.setText(path)
            self.controller.config.simulation.executable_path = path
            self.controller.configChanged.emit()

    def _on_run_clicked(self) -> None:
        self.controller.config.simulation.working_dir = self.workdir_edit.text() or None
        self.controller.config.simulation.executable_path = self.exe_edit.text() or None

        errors = self.controller.validate(self.controller.config.simulation.engine)
        if errors:
            QMessageBox.warning(self, "Configuration incomplete", "\n".join(errors))
            return

        self.log_console.clear()
        self.progress_bar.setValue(0)
        self.run_button.setEnabled(False)
        self.controller.run_simulation()

    def _on_started(self, engine_name: str) -> None:
        self.log_console.appendPlainText(f"--- Demarrage de la simulation ({engine_name}) ---")

    def _on_progress(self, pct: int, message: str) -> None:
        self.progress_bar.setValue(pct)
        if message:
            self.log_console.appendPlainText(message)

    def _on_finished(self, result) -> None:
        self.run_button.setEnabled(True)
        self.log_console.appendPlainText("--- Simulation terminee avec succes ---")

    def _on_failed(self, message: str) -> None:
        self.run_button.setEnabled(True)
        self.log_console.appendPlainText(f"--- ECHEC : {message} ---")
        QMessageBox.critical(self, "Echec de la simulation", message)
