"""Export d'un maillage de terrain vers un fichier IFC (IFC2X3 ou IFC4).

S'appuie sur l'API haut niveau d'``ifcopenshell`` (``geometry.add_mesh_representation``)
qui choisit automatiquement la bonne representation selon le schema :

* IFC2X3 ne connait pas la tessellation (``IfcPolygonalFaceSet`` /
  ``IfcTriangulatedFaceSet`` sont apparus avec IFC4) : chaque face devient un
  ``IfcFacetedBrep`` individuel. Fonctionnel mais volumineux pour un grand
  nombre de triangles.
* IFC4 utilise ``IfcPolygonalFaceSet``, une structure compacte (une seule
  liste de sommets + une liste de faces), adaptee aux MNT de taille
  significative.

Le terrain est modelise comme ``IfcGeographicElement`` (PredefinedType =
TERRAIN) en IFC4, ou comme ``IfcBuildingElementProxy`` en IFC2X3 (ce dernier
schema ne definit pas ``IfcGeographicElement``).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import ifcopenshell
import ifcopenshell.api

from .mesh_builder import TerrainMesh

#: au-dela de ce nombre de triangles, IFC2X3 (un IfcFacetedBrep par face)
#: produit un fichier tres volumineux et lent a ouvrir : on avertit
#: l'utilisateur plutot que d'echouer silencieusement.
IFC2X3_BREP_TRIANGLE_WARNING_THRESHOLD = 20_000

SUPPORTED_SCHEMAS = ("IFC4", "IFC2X3")


@dataclass
class ProjectInfo:
    project_name: str = "MNT vers IFC"
    site_name: str = "Site"
    author_given_name: str = "EGEO"
    author_family_name: str = "Earth Geomatique"
    organisation: str = "EGEO - Earth Geomatique"
    description: str = ""


def write_ifc(
    mesh: TerrainMesh,
    output_path: str,
    schema: str = "IFC4",
    project_info: Optional[ProjectInfo] = None,
    epsg: Optional[int] = None,
) -> dict:
    """Ecrit ``output_path`` et retourne un petit rapport de conversion."""
    if schema not in SUPPORTED_SCHEMAS:
        raise ValueError(f"Schema IFC non supporte : {schema} (attendu {SUPPORTED_SCHEMAS})")

    project_info = project_info or ProjectInfo()
    n_triangles = len(mesh.triangles)
    warnings = []
    if schema == "IFC2X3" and n_triangles > IFC2X3_BREP_TRIANGLE_WARNING_THRESHOLD:
        warnings.append(
            f"{n_triangles} triangles avec le schema IFC2X3 (un IfcFacetedBrep par "
            "face) : le fichier resultant peut etre tres volumineux et lent a "
            "ouvrir. Augmentez la decimation ou choisissez le schema IFC4."
        )

    f = ifcopenshell.file(schema=schema)

    # IFC2X3 exige un utilisateur/application avant la premiere entite avec
    # historique (IfcProject inclus) ; on les cree dans tous les cas pour une
    # attribution correcte du fichier produit.
    person = ifcopenshell.api.run(
        "owner.add_person",
        f,
        identification=project_info.author_given_name,
        given_name=project_info.author_given_name,
        family_name=project_info.author_family_name,
    )
    organisation = ifcopenshell.api.run("owner.add_organisation", f, name=project_info.organisation)
    ifcopenshell.api.run("owner.add_person_and_organisation", f, person=person, organisation=organisation)
    ifcopenshell.api.run(
        "owner.add_application",
        f,
        application_developer=organisation,
        version="1.0",
        application_full_name="PointCloud2BIM",
        application_identifier="PointCloud2BIM",
    )

    project = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcProject", name=project_info.project_name)
    ifcopenshell.api.run("unit.assign_unit", f, length={"is_metric": True, "raw": "METERS"})

    model_context = ifcopenshell.api.run("context.add_context", f, context_type="Model")
    body_context = ifcopenshell.api.run(
        "context.add_context",
        f,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=model_context,
    )

    site = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcSite", name=project_info.site_name)
    description = project_info.description
    if epsg:
        description = f"{description} (CRS source : EPSG:{epsg})".strip()
    if description:
        site.Description = description
    ifcopenshell.api.run("aggregate.assign_object", f, products=[site], relating_object=project)

    if schema == "IFC4":
        terrain = ifcopenshell.api.run(
            "root.create_entity", f, ifc_class="IfcGeographicElement",
            name="MNT (terrain)", predefined_type="TERRAIN",
        )
    else:
        terrain = ifcopenshell.api.run(
            "root.create_entity", f, ifc_class="IfcBuildingElementProxy", name="MNT (terrain)",
        )
    ifcopenshell.api.run("spatial.assign_container", f, products=[terrain], relating_structure=site)

    vertices = [tuple(float(c) for c in v) for v in mesh.vertices]
    faces = [tuple(int(i) for i in tri) for tri in mesh.triangles]
    representation = ifcopenshell.api.run(
        "geometry.add_mesh_representation", f, context=body_context, vertices=[vertices], faces=[faces],
    )
    ifcopenshell.api.run("geometry.assign_representation", f, product=terrain, representation=representation)
    ifcopenshell.api.run("geometry.edit_object_placement", f, product=terrain)

    f.write(output_path)

    return {
        "n_vertices": len(mesh.vertices),
        "n_triangles": n_triangles,
        "n_skipped_nodata": mesh.n_skipped_nodata,
        "schema": schema,
        "warnings": warnings,
    }
