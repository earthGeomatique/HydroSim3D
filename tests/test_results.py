"""Tests du modele pivot SimulationResult (aucune dependance QGIS)."""
from datetime import datetime, timedelta

import numpy as np

from results import SimulationResult


def _make_result(n_steps=3, n_points=4):
    times = [datetime(2024, 1, 1) + timedelta(minutes=i) for i in range(n_steps)]
    points = np.zeros((n_points, 3))
    depth = np.random.rand(n_steps, n_points)
    vectors = np.zeros((n_steps, n_points, 3))
    return SimulationResult(
        engine="swmm", times=times, points=points,
        scalars={"depth": depth}, vectors=vectors,
    )


def test_n_steps_and_n_points():
    result = _make_result(n_steps=5, n_points=7)
    assert result.n_steps == 5
    assert result.n_points == 7


def test_scalar_at_returns_correct_step():
    result = _make_result()
    values = result.scalar_at("depth", 1)
    assert np.array_equal(values, result.scalars["depth"][1])


def test_vector_at_returns_none_when_no_vectors():
    result = _make_result()
    result.vectors = None
    assert result.vector_at(0) is None


def test_available_scalars_sorted():
    result = _make_result()
    result.scalars["velocity"] = result.scalars["depth"].copy()
    assert result.available_scalars() == ["depth", "velocity"]
