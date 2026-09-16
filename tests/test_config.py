"""Tests du modele de configuration (aucune dependance QGIS)."""
from datetime import datetime, timedelta

from config import (
    EngineType,
    LayerRef,
    NetworkConfig,
    ProjectConfig,
    SimulationParams,
)


def test_layer_ref_defaults_to_no_layer():
    ref = LayerRef()
    assert ref.layer_id is None
    assert ref.field_map == {}


def test_project_config_has_independent_sub_configs():
    a = ProjectConfig()
    b = ProjectConfig()
    a.network.junctions.layer_id = "layer-1"
    assert b.network.junctions.layer_id is None, "les instances ne doivent pas partager d'etat mutable"


def test_simulation_params_end_is_start_plus_duration():
    start = datetime(2024, 1, 1, 8, 0, 0)
    sim = SimulationParams(start=start, duration=timedelta(hours=3))
    assert sim.end == datetime(2024, 1, 1, 11, 0, 0)


def test_network_config_roles_are_independent_layer_refs():
    net = NetworkConfig()
    net.junctions.layer_id = "junctions-id"
    assert net.conduits.layer_id is None
    assert net.outfalls.layer_id is None


def test_engine_type_values():
    assert EngineType.SWMM.value == "swmm"
    assert EngineType.HECRAS.value == "hecras"
