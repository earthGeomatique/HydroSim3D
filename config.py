"""Modeles de configuration partages par le controleur et l'interface.

Ce module ne depend d'aucune API QGIS ou Qt : il ne contient que des
structures de donnees (dataclasses) et des enums, ce qui permet de les
tester unitairement sans environnement QGIS.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional


class EngineType(Enum):
    SWMM = "swmm"
    HECRAS = "hecras"


class ResultVariable(Enum):
    DEPTH = "depth"
    VELOCITY = "velocity"
    FLOW = "flow"
    ELEVATION = "elevation"


@dataclass
class LayerRef:
    """Reference legere vers une couche QGIS (par id) + mapping de champs.

    On ne stocke jamais l'objet ``QgsMapLayer`` lui-meme dans la
    configuration : uniquement son id, recupere via
    ``QgsProject.instance().mapLayer(layer_id)`` au moment de l'usage. Cela
    evite les references pendantes si une couche est retiree du projet.
    """

    layer_id: Optional[str] = None
    field_map: Dict[str, str] = field(default_factory=dict)


@dataclass
class TopographyConfig:
    dem: LayerRef = field(default_factory=LayerRef)
    vertical_exaggeration: float = 1.0


@dataclass
class NetworkConfig:
    """Couches du reseau d'assainissement pour l'export SWMM."""

    junctions: LayerRef = field(default_factory=LayerRef)
    conduits: LayerRef = field(default_factory=LayerRef)
    outfalls: LayerRef = field(default_factory=LayerRef)
    subcatchments: LayerRef = field(default_factory=LayerRef)
    raingages: LayerRef = field(default_factory=LayerRef)


@dataclass
class HydraulicsConfig:
    """Couches hydrauliques pour l'export HEC-RAS."""

    river_centerline: LayerRef = field(default_factory=LayerRef)
    cross_sections: LayerRef = field(default_factory=LayerRef)
    bank_lines: LayerRef = field(default_factory=LayerRef)
    manning_zones: LayerRef = field(default_factory=LayerRef)
    hecras_install_dir: Optional[str] = None


@dataclass
class SimulationParams:
    engine: EngineType = EngineType.SWMM
    start: datetime = field(default_factory=lambda: datetime.now())
    duration: timedelta = field(default_factory=lambda: timedelta(hours=6))
    time_step_seconds: int = 60
    working_dir: Optional[str] = None
    executable_path: Optional[str] = None

    @property
    def end(self) -> datetime:
        return self.start + self.duration


@dataclass
class ProjectConfig:
    """Etat complet edite par les onglets et consomme par les moteurs."""

    topography: TopographyConfig = field(default_factory=TopographyConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    hydraulics: HydraulicsConfig = field(default_factory=HydraulicsConfig)
    simulation: SimulationParams = field(default_factory=SimulationParams)
