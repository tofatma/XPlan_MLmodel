"""
This module creates an IFC file from multiple geometry sources.
"""

import ifcopenshell
from ifcopenshell.guid import new as new_guid
import numpy as np
from Xplan2IFC import main, IFCFloorplanGenerator


def create_ifc_file(schema="IFC4"):
    return ifcopenshell.file(schema=schema)


def create_basic_entities(ifc):
    origin = ifc.create_entity("IfcCartesianPoint", Coordinates=[0.0, 0.0, 0.0])
    placement = ifc.create_entity("IfcAxis2Placement3D", Location=origin)
    world_placement = ifc.create_entity("IfcLocalPlacement", RelativePlacement=placement)

    context_model = ifc.create_entity(
        "IfcGeometricRepresentationContext",
        ContextIdentifier="Body",
        ContextType="Model",
        CoordinateSpaceDimension=3,
        Precision=1e-6,
        WorldCoordinateSystem=placement
    )

    context_plan = ifc.create_entity(
        "IfcGeometricRepresentationContext",
        ContextIdentifier="Plan",
        ContextType="Plan",
        CoordinateSpaceDimension=3,
        Precision=1e-6,
        WorldCoordinateSystem=placement
    )

    context_annotation = ifc.create_entity(
        "IfcGeometricRepresentationSubContext",
        ContextIdentifier="Annotation",
        ContextType="Plan",
        ParentContext=context_plan,
        TargetView="PLAN_VIEW"
    )

    project = ifc.create_entity("IfcProject", GlobalId=new_guid(), Name="CompositeModel", RepresentationContexts=[context_model, context_plan])
    site = ifc.create_entity("IfcSite", GlobalId=new_guid(), Name="Site", ObjectPlacement=world_placement)
    building = ifc.create_entity("IfcBuilding", GlobalId=new_guid(), Name="Building")
    storey = ifc.create_entity("IfcBuildingStorey", GlobalId=new_guid(), Name="Storey")

    ifc.create_entity("IfcRelAggregates", GlobalId=new_guid(), RelatingObject=project, RelatedObjects=[site])
    ifc.create_entity("IfcRelAggregates", GlobalId=new_guid(), RelatingObject=site, RelatedObjects=[building])
    ifc.create_entity("IfcRelAggregates", GlobalId=new_guid(), RelatingObject=building, RelatedObjects=[storey])

    return project, site, building, storey, context_annotation

def create_fill_style(ifc):
    black = ifc.create_entity("IfcColourRgb", Red=0.0, Green=0.0, Blue=0.0)
    curve_font = ifc.create_entity("IfcDraughtingPreDefinedCurveFont", Name="continuous")
    curve_style = ifc.create_entity("IfcCurveStyle", CurveFont=curve_font, CurveWidth=None, CurveColour=black)
    hatch_spacing = ifc.create_entity("IfcPositiveLengthMeasure", 1000.0)
    fill_hatching = ifc.create_entity(
        "IfcFillAreaStyleHatching",
        HatchLineAppearance=curve_style,
        StartOfNextHatchLine=hatch_spacing,
        HatchLineAngle=45.0
    )
    fill_style = ifc.create_entity("IfcFillAreaStyle", Name="FlurstueckFill", FillStyles=[fill_hatching])
    return fill_style

def add_flurstueck_annotations(ifc, site, context_annotation, flurstueck_dict, fill_style):
    for key, data in flurstueck_dict.items():
        name = data.get("name", f"Flurstueck_{key}")
        points = data["points"]

        # Convert points to IFC points
        ifc_points = [
            ifc.create_entity("IfcCartesianPoint", Coordinates=[float(x), float(y), float(z)])
            for x, y, z in points
        ]

        polyline = ifc.create_entity("IfcPolyline", Points=ifc_points)

        # Create fill area and style
        fill_area = ifc.create_entity("IfcAnnotationFillArea", OuterBoundary=polyline)
        ifc.create_entity("IfcStyledItem", Item=fill_area, Styles=[fill_style])

        # Shape representation
        shape = ifc.create_entity(
            "IfcShapeRepresentation",
            ContextOfItems=context_annotation,
            RepresentationIdentifier="Annotation",
            RepresentationType="Annotation2D",
            Items=[fill_area]
        )

        annotation = ifc.create_entity(
            "IfcAnnotation",
            GlobalId=new_guid(),
            Name=name,
            ObjectType="FLURSTUECK",
            ObjectPlacement=site.ObjectPlacement,
            Representation=ifc.create_entity("IfcProductDefinitionShape", Representations=[shape])
        )

        ifc.create_entity(
            "IfcRelContainedInSpatialStructure",
            GlobalId=new_guid(),
            RelatingStructure=site,
            RelatedElements=[annotation]
        )

def export_ifc(filename="site_boundaries.ifc"):
    ifc = create_ifc_file()
    project, site, building, storey, context_annotation = create_basic_entities(ifc)
    fill_style = create_fill_style(ifc)
    data = main()
    flurstueck_dict = data.get("flurstueck_dict", {})
    add_flurstueck_annotations(ifc, site, context_annotation, flurstueck_dict, fill_style)
    ifc.write(filename)
    print(f"IFC file saved as {filename}")

if __name__ == "__main__":
    export_ifc()
