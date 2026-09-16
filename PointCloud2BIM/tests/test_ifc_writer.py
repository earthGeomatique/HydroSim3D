"""Tests de l'export IFC (necessite ifcopenshell ; ignores sinon)."""
import numpy as np
import pytest

ifcopenshell = pytest.importorskip("ifcopenshell")

from converter.ifc_writer import ProjectInfo, write_ifc
from converter.mesh_builder import TerrainMesh


def _make_mesh():
    vertices = np.array(
        [[0, 0, 0], [1, 0, 0.2], [2, 0, 0.1], [0, 1, 0.3], [1, 1, 0.5], [2, 1, 0.2]],
        dtype=float,
    )
    triangles = np.array([[0, 3, 1], [1, 3, 4], [1, 4, 2], [2, 4, 5]])
    return TerrainMesh(vertices=vertices, triangles=triangles, n_skipped_nodata=0)


@pytest.mark.parametrize("schema", ["IFC4", "IFC2X3"])
def test_write_ifc_produces_valid_file(tmp_path, schema):
    mesh = _make_mesh()
    output = tmp_path / f"terrain_{schema}.ifc"

    report = write_ifc(mesh, str(output), schema=schema, project_info=ProjectInfo(project_name="Test"), epsg=32628)

    assert output.exists()
    assert report["n_vertices"] == 6
    assert report["n_triangles"] == 4
    assert report["schema"] == schema

    reopened = ifcopenshell.open(str(output))
    assert reopened.by_type("IfcProject")[0].Name == "Test"
    if schema == "IFC4":
        assert len(reopened.by_type("IfcPolygonalFaceSet")) == 1
        assert len(reopened.by_type("IfcGeographicElement")) == 1
    else:
        assert len(reopened.by_type("IfcFacetedBrep")) == 1
        assert len(reopened.by_type("IfcBuildingElementProxy")) == 1


def test_unsupported_schema_raises():
    mesh = _make_mesh()
    with pytest.raises(ValueError):
        write_ifc(mesh, "/tmp/whatever.ifc", schema="IFC2X2")


def test_ifc2x3_large_mesh_emits_warning(tmp_path, monkeypatch):
    import converter.ifc_writer as ifc_writer_module

    monkeypatch.setattr(ifc_writer_module, "IFC2X3_BREP_TRIANGLE_WARNING_THRESHOLD", 2)
    mesh = _make_mesh()
    report = write_ifc(mesh, str(tmp_path / "big.ifc"), schema="IFC2X3")
    assert report["warnings"], "un avertissement est attendu au-dela du seuil"
