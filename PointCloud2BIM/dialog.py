"""Dialogue principal PointCloud2BIM : 3 onglets, conforme a la maquette
d'origine (Input/Output, Processing, Project Info), avec en entree un MNT
raster GeoTIFF (.tif) plutot qu'un nuage de points LAS/LAZ.
"""
from __future__ import annotations

import os

from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .converter.ifc_writer import ProjectInfo


class PointCloud2BimDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PointCloud2BIM — Convert MNT to IFC")
        self.resize(720, 560)

        self._active_task = None

        root = QVBoxLayout(self)
        self.tabs = QTabWidget(self)
        self.tabs.addTab(self._build_io_tab(), "Input / Output")
        self.tabs.addTab(self._build_processing_tab(), "Processing")
        self.tabs.addTab(self._build_project_info_tab(), "Project Info")
        root.addWidget(self.tabs, stretch=1)

        root.addWidget(QLabel("Progress"))
        self.progress_bar = QProgressBar(self)
        root.addWidget(self.progress_bar)

        self.log_console = QPlainTextEdit(self)
        self.log_console.setReadOnly(True)
        self.log_console.setPlaceholderText("Ready.")
        root.addWidget(self.log_console, stretch=1)

        button_row = QHBoxLayout()
        self.run_button = QPushButton("Run Conversion", self)
        self.run_button.setStyleSheet("background-color:#2e7d32; color:white; font-weight:bold;")
        self.run_button.clicked.connect(self._on_run_clicked)
        button_row.addWidget(self.run_button)

        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        button_row.addWidget(self.cancel_button)

        button_row.addStretch()

        close_button = QPushButton("Close", self)
        close_button.clicked.connect(self.close)
        button_row.addWidget(close_button)

        root.addLayout(button_row)

    # ------------------------------------------------------------------
    # Onglet Input / Output
    # ------------------------------------------------------------------
    def _build_io_tab(self) -> QWidget:
        tab = QWidget(self)
        layout = QFormLayout(tab)

        row = QHBoxLayout()
        self.dem_edit = QLineEdit(tab)
        self.dem_edit.setPlaceholderText("Select a DEM/MNT (.tif) file...")
        row.addWidget(self.dem_edit)
        browse_dem = QPushButton("Browse...", tab)
        browse_dem.clicked.connect(self._browse_dem)
        row.addWidget(browse_dem)
        layout.addRow("MNT (GeoTIFF - .tif) :", row)

        row2 = QHBoxLayout()
        self.output_edit = QLineEdit(tab)
        self.output_edit.setPlaceholderText("Output IFC file path...")
        row2.addWidget(self.output_edit)
        browse_out = QPushButton("Browse...", tab)
        browse_out.clicked.connect(self._browse_output)
        row2.addWidget(browse_out)
        layout.addRow("Output IFC :", row2)

        info1 = QLabel(
            "Supported input: single-band GeoTIFF DEM (.tif), any CRS "
            "(projected CRS recommended for accurate metric geometry)."
        )
        info1.setStyleSheet("color: #b8860b;")
        info1.setWordWrap(True)
        layout.addRow(info1)

        info2 = QLabel(
            "Output: IFC2X3 or IFC4 — compatible with Revit, ArchiCAD, FreeCAD, BIMvision..."
        )
        info2.setStyleSheet("color: #b8860b;")
        info2.setWordWrap(True)
        layout.addRow(info2)

        return tab

    def _browse_dem(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Selectionner un MNT", "", "GeoTIFF (*.tif *.tiff)")
        if path:
            self.dem_edit.setText(path)
            if not self.output_edit.text():
                default_out = os.path.splitext(path)[0] + ".ifc"
                self.output_edit.setText(default_out)

    def _browse_output(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Fichier IFC de sortie", "", "IFC files (*.ifc)")
        if path:
            if not path.lower().endswith(".ifc"):
                path += ".ifc"
            self.output_edit.setText(path)

    # ------------------------------------------------------------------
    # Onglet Processing
    # ------------------------------------------------------------------
    def _build_processing_tab(self) -> QWidget:
        tab = QWidget(self)
        layout = QFormLayout(tab)

        self.schema_combo = QComboBox(tab)
        self.schema_combo.addItems(["IFC4", "IFC2X3"])
        layout.addRow("Schema IFC :", self.schema_combo)

        self.decimation_spin = QSpinBox(tab)
        self.decimation_spin.setRange(1, 100)
        self.decimation_spin.setValue(1)
        self.decimation_spin.setToolTip(
            "1 = pleine resolution du MNT. Augmenter reduit le nombre de "
            "triangles (utile pour un MNT tres resolu ou le schema IFC2X3)."
        )
        layout.addRow("Decimation :", self.decimation_spin)

        self.z_exaggeration_spin = QDoubleSpinBox(tab)
        self.z_exaggeration_spin.setRange(0.01, 100.0)
        self.z_exaggeration_spin.setValue(1.0)
        self.z_exaggeration_spin.setSingleStep(0.1)
        layout.addRow("Exageration verticale (Z) :", self.z_exaggeration_spin)

        self.z_offset_spin = QDoubleSpinBox(tab)
        self.z_offset_spin.setRange(-10000.0, 10000.0)
        self.z_offset_spin.setValue(0.0)
        layout.addRow("Decalage altimetrique (Z offset) :", self.z_offset_spin)

        self.epsg_edit = QLineEdit(tab)
        self.epsg_edit.setPlaceholderText("Auto (detecte depuis le MNT)")
        layout.addRow("EPSG (optionnel, force le CRS) :", self.epsg_edit)

        return tab

    # ------------------------------------------------------------------
    # Onglet Project Info
    # ------------------------------------------------------------------
    def _build_project_info_tab(self) -> QWidget:
        tab = QWidget(self)
        layout = QFormLayout(tab)

        self.project_name_edit = QLineEdit("MNT vers IFC", tab)
        layout.addRow("Nom du projet :", self.project_name_edit)

        self.site_name_edit = QLineEdit("Site", tab)
        layout.addRow("Nom du site :", self.site_name_edit)

        self.author_given_edit = QLineEdit("", tab)
        layout.addRow("Prenom de l'auteur :", self.author_given_edit)

        self.author_family_edit = QLineEdit("", tab)
        layout.addRow("Nom de l'auteur :", self.author_family_edit)

        self.organisation_edit = QLineEdit("EGEO - Earth Geomatique", tab)
        layout.addRow("Organisation :", self.organisation_edit)

        self.description_edit = QTextEdit(tab)
        self.description_edit.setMaximumHeight(80)
        layout.addRow("Description :", self.description_edit)

        return tab

    def _project_info(self) -> ProjectInfo:
        return ProjectInfo(
            project_name=self.project_name_edit.text() or "MNT vers IFC",
            site_name=self.site_name_edit.text() or "Site",
            author_given_name=self.author_given_edit.text() or "EGEO",
            author_family_name=self.author_family_edit.text() or "Earth Geomatique",
            organisation=self.organisation_edit.text() or "EGEO - Earth Geomatique",
            description=self.description_edit.toPlainText(),
        )

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------
    def _on_run_clicked(self) -> None:
        dem_path = self.dem_edit.text().strip()
        output_path = self.output_edit.text().strip()

        errors = []
        if not dem_path or not os.path.isfile(dem_path):
            errors.append("Selectionnez un MNT (.tif) valide.")
        elif not dem_path.lower().endswith((".tif", ".tiff")):
            errors.append("Le MNT doit etre un fichier GeoTIFF (.tif/.tiff).")
        if not output_path:
            errors.append("Indiquez un chemin de sortie pour le fichier IFC.")

        if errors:
            QMessageBox.warning(self, "Configuration incomplete", "\n".join(errors))
            return

        epsg_override = None
        if self.epsg_edit.text().strip():
            try:
                epsg_override = int(self.epsg_edit.text().strip())
            except ValueError:
                QMessageBox.warning(self, "EPSG invalide", "Le code EPSG doit etre un entier.")
                return

        kwargs = dict(
            tif_path=dem_path,
            ifc_path=output_path,
            schema=self.schema_combo.currentText(),
            decimation=self.decimation_spin.value(),
            z_exaggeration=self.z_exaggeration_spin.value(),
            z_offset=self.z_offset_spin.value(),
            project_info=self._project_info(),
            epsg_override=epsg_override,
        )

        self.log_console.clear()
        self.progress_bar.setValue(0)
        self.run_button.setEnabled(False)

        from .tasks.conversion_task import ConversionTask
        from qgis.core import QgsApplication

        task = ConversionTask(kwargs)
        task.progressChanged.connect(self._on_progress)
        task.logEmitted.connect(self.log_console.appendPlainText)
        task.finishedOk.connect(self._on_finished)
        task.finishedError.connect(self._on_failed)

        self._active_task = task
        QgsApplication.taskManager().addTask(task)

    def _on_progress(self, pct: int, message: str) -> None:
        self.progress_bar.setValue(pct)
        if message:
            self.log_console.appendPlainText(message)

    def _on_finished(self, report: dict) -> None:
        self.run_button.setEnabled(True)
        self._active_task = None
        self.log_console.appendPlainText(
            f"--- Conversion terminee : {report['n_vertices']} sommets, "
            f"{report['n_triangles']} triangles, schema {report['schema']} ---"
        )

    def _on_failed(self, message: str) -> None:
        self.run_button.setEnabled(True)
        self._active_task = None
        self.log_console.appendPlainText(f"--- ECHEC : {message} ---")
        QMessageBox.critical(self, "Echec de la conversion", message)

    def _on_cancel_clicked(self) -> None:
        if self._active_task is not None:
            self._active_task.cancel()
            self.log_console.appendPlainText("--- Annulation demandee ---")
        else:
            self.close()
