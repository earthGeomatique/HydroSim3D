"""Panneau de rendu 3D des resultats, base sur PyVista (style ParaView).

Le panneau affiche :

* le terrain (MNT), en surface structuree, exagere verticalement ;
* les resultats de simulation par-dessus, colores par une grandeur scalaire
  choisie par l'utilisateur (hauteur d'eau, vitesse...) avec un degrade de
  couleurs et une barre d'echelle ;
* des glyphes (fleches) representant la direction et l'intensite de
  l'ecoulement, lorsque des vecteurs sont disponibles dans le resultat ;
* un curseur temporel pour rejouer la simulation pas a pas.

``pyvistaqt.QtInteractor`` embarque directement une scene VTK dans un
widget Qt, ce qui permet d'integrer ce rendu dans un dock QGIS comme un
widget normal, sans fenetre externe.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ..results import SimulationResult

try:
    import pyvista as pv
    from pyvistaqt import QtInteractor

    PYVISTA_AVAILABLE = True
except ImportError:  # pragma: no cover - depend de l'environnement QGIS
    PYVISTA_AVAILABLE = False


class Pyvista3DPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._result: Optional[SimulationResult] = None
        self._terrain_mesh = None
        self._result_actor = None
        self._vector_actor = None
        self._vertical_exaggeration = 1.0

        layout = QVBoxLayout(self)

        if not PYVISTA_AVAILABLE:
            layout.addWidget(QLabel(
                "PyVista / pyvistaqt ne sont pas installes dans l'environnement "
                "Python de QGIS. Installez-les pour activer le rendu 3D :\n"
                "pip install pyvista pyvistaqt"
            ))
            self.plotter = None
            return

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Grandeur :"))
        self.scalar_combo = QComboBox(self)
        self.scalar_combo.currentTextChanged.connect(self._on_display_options_changed)
        controls.addWidget(self.scalar_combo)

        self.show_vectors_check = QCheckBox("Vecteurs d'ecoulement", self)
        self.show_vectors_check.setChecked(True)
        self.show_vectors_check.toggled.connect(self._on_display_options_changed)
        controls.addWidget(self.show_vectors_check)

        controls.addWidget(QLabel("Echelle vecteurs :"))
        self.vector_scale_spin = QDoubleSpinBox(self)
        self.vector_scale_spin.setRange(0.01, 100.0)
        self.vector_scale_spin.setValue(1.0)
        self.vector_scale_spin.valueChanged.connect(self._on_display_options_changed)
        controls.addWidget(self.vector_scale_spin)

        self.reset_camera_btn = QPushButton("Reinitialiser la vue", self)
        self.reset_camera_btn.clicked.connect(self._reset_camera)
        controls.addWidget(self.reset_camera_btn)
        controls.addStretch()
        layout.addLayout(controls)

        self.plotter = QtInteractor(self)
        layout.addWidget(self.plotter.interactor, stretch=1)

        time_row = QHBoxLayout()
        time_row.addWidget(QLabel("Pas de temps :"))
        self.time_slider = QSlider(Qt.Horizontal, self)
        self.time_slider.valueChanged.connect(self._on_time_changed)
        time_row.addWidget(self.time_slider, stretch=1)
        self.time_label = QLabel("-", self)
        time_row.addWidget(self.time_label)
        layout.addLayout(time_row)

    # ------------------------------------------------------------------
    def set_vertical_exaggeration(self, factor: float) -> None:
        self._vertical_exaggeration = factor
        if self._terrain_mesh is not None:
            self._rebuild_terrain_actor()

    def set_terrain(self, x: np.ndarray, y: np.ndarray, z: np.ndarray) -> None:
        if not PYVISTA_AVAILABLE:
            return
        grid = pv.StructuredGrid(x, y, z)
        grid["elevation"] = z.ravel(order="F")
        self._terrain_mesh = grid
        self._rebuild_terrain_actor()

    def _rebuild_terrain_actor(self) -> None:
        mesh = self._terrain_mesh.copy()
        mesh.points[:, 2] *= self._vertical_exaggeration
        self.plotter.add_mesh(
            mesh, scalars="elevation", cmap="gist_earth", name="terrain",
            show_scalar_bar=False, opacity=0.85,
        )
        self.plotter.reset_camera()

    def set_result(self, result: SimulationResult) -> None:
        if not PYVISTA_AVAILABLE:
            return
        self._result = result

        self.scalar_combo.blockSignals(True)
        self.scalar_combo.clear()
        self.scalar_combo.addItems(result.available_scalars())
        self.scalar_combo.blockSignals(False)

        self.time_slider.blockSignals(True)
        self.time_slider.setRange(0, max(0, result.n_steps - 1))
        self.time_slider.setValue(0)
        self.time_slider.blockSignals(False)

        self._render_step(0)

    # ------------------------------------------------------------------
    def _on_time_changed(self, step: int) -> None:
        self._render_step(step)

    def _on_display_options_changed(self, *_args) -> None:
        self._render_step(self.time_slider.value())

    def _render_step(self, step: int) -> None:
        if self._result is None or not PYVISTA_AVAILABLE:
            return
        result = self._result
        step = max(0, min(step, result.n_steps - 1))
        self.time_label.setText(str(result.times[step]))

        points = result.points.copy()
        points[:, 2] *= self._vertical_exaggeration

        cloud = pv.PolyData(points)
        scalar_name = self.scalar_combo.currentText()
        if scalar_name and scalar_name in result.scalars:
            values = result.scalar_at(scalar_name, step)
            cloud[scalar_name] = values
            self.plotter.add_mesh(
                cloud, scalars=scalar_name, cmap="turbo", point_size=10,
                render_points_as_spheres=True, name="result_points",
                scalar_bar_args={"title": scalar_name},
            )

        if self._vector_actor is not None:
            self.plotter.remove_actor(self._vector_actor, render=False)
            self._vector_actor = None

        if self.show_vectors_check.isChecked() and result.vectors is not None:
            vectors = result.vector_at(step)
            magnitude = np.linalg.norm(vectors, axis=1)
            if magnitude.max() > 0:
                cloud["vectors"] = vectors
                cloud["magnitude"] = magnitude
                glyphs = cloud.glyph(
                    orient="vectors", scale="magnitude",
                    factor=self.vector_scale_spin.value(), geom=pv.Arrow(),
                )
                self._vector_actor = self.plotter.add_mesh(
                    glyphs, color="white", name="flow_vectors",
                )

        self.plotter.render()

    def _reset_camera(self) -> None:
        if self.plotter is not None:
            self.plotter.reset_camera()
