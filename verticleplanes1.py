import ifcopenshell
from ifcopenshell.guid import new as new_guid

from Xplan2IFC import main, IFCFloorplanGenerator
# === Create IFC file ===
ifc = ifcopenshell.file(schema="IFC4X3_ADD2")
data = main()
flurstueck_dict = data["flurstueck_dict"]
print(flurstueck_dict)
# --- Owner History (minimal) ---
org = ifc.create_entity("IfcOrganization", Name="MyOrganization")
app = ifc.create_entity("IfcApplication", ApplicationDeveloper=org, Version="1.0", ApplicationFullName="Python IFC", ApplicationIdentifier="PyIFC")
person = ifc.create_entity("IfcPerson", FamilyName="Ahmad", GivenName="Fatma")
owner_hist = ifc.create_entity("IfcOwnerHistory", OwningUser=ifc.create_entity("IfcPersonAndOrganization", ThePerson=person, TheOrganization=org), OwningApplication=app)

# --- Units ---
length_unit = ifc.create_entity("IfcSIUnit", UnitType="LENGTHUNIT", Prefix="MILLI", Name="METRE")
area_unit = ifc.create_entity("IfcSIUnit", UnitType="AREAUNIT", Name="SQUARE_METRE")
volume_unit = ifc.create_entity("IfcSIUnit", UnitType="VOLUMEUNIT", Name="CUBIC_METRE")
unit_assignment = ifc.create_entity("IfcUnitAssignment", Units=[length_unit, area_unit, volume_unit])

# --- Context ---
origin = ifc.create_entity("IfcCartesianPoint", [0.0,0.0,0.0])
placement = ifc.create_entity("IfcAxis2Placement3D", Location=origin)
context = ifc.create_entity(
    "IfcGeometricRepresentationContext",
    ContextIdentifier="Body",
    ContextType="Model",
    CoordinateSpaceDimension=3,
    Precision=0.01,
    WorldCoordinateSystem=placement
)

# --- Project, Site, Building, Storey ---
project = ifc.create_entity("IfcProject", GlobalId=new_guid(), Name="ProjectName", RepresentationContexts=[context], UnitsInContext=unit_assignment, OwnerHistory=owner_hist)
site_placement = ifc.create_entity("IfcLocalPlacement", RelativePlacement=placement)
site = ifc.create_entity("IfcSite", GlobalId=new_guid(), Name="DefaultSite", ObjectPlacement=site_placement)
building_placement = ifc.create_entity("IfcLocalPlacement", RelativePlacement=placement)
building = ifc.create_entity("IfcBuilding", GlobalId=new_guid(), Name="BuildingName", ObjectPlacement=building_placement)
storey_placement = ifc.create_entity("IfcLocalPlacement", RelativePlacement=placement)
storey = ifc.create_entity("IfcBuildingStorey", GlobalId=new_guid(), Name="Storey1", ObjectPlacement=storey_placement)

# --- Aggregate structure ---
ifc.create_entity("IfcRelAggregates", GlobalId=new_guid(), RelatingObject=project, RelatedObjects=[site])
ifc.create_entity("IfcRelAggregates", GlobalId=new_guid(), RelatingObject=site, RelatedObjects=[building])
ifc.create_entity("IfcRelAggregates", GlobalId=new_guid(), RelatingObject=building, RelatedObjects=[storey])
# --- Create a visible Virtual Element ---
def create_virtual_element(ifc, points, context, storey, name="VirtualElement"):
    # Remove duplicate consecutive points
    unique_pts = []
    for pt in points:
        if not unique_pts or pt != unique_pts[-1]:
            unique_pts.append(pt)

    if len(unique_pts) < 3:
        return None  # Not enough points for a face

    # IFC expects tuples of floats
    ifc_points = [ifc.create_entity("IfcCartesianPoint", Coordinates=tuple(float(x) for x in pt))
                  for pt in unique_pts]

    polyloop = ifc.create_entity("IfcPolyLoop", Polygon=ifc_points)
    outer_bound = ifc.create_entity("IfcFaceOuterBound", Bound=polyloop, Orientation=True)
    face = ifc.create_entity("IfcFace", Bounds=[outer_bound])
    cfs = ifc.create_entity("IfcConnectedFaceSet", CfsFaces=[face])
    surface_model = ifc.create_entity("IfcFaceBasedSurfaceModel", FbsmFaces=[cfs])
    shape_rep = ifc.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=context,
        RepresentationIdentifier="Body",
        RepresentationType="SurfaceModel",
        Items=[surface_model]
    )
    prod_def = ifc.create_entity("IfcProductDefinitionShape", Representations=[shape_rep])
    virtual = ifc.create_entity(
        "IfcVirtualElement",
        GlobalId=new_guid(),
        Name=name,
        ObjectPlacement=storey.ObjectPlacement,
        Representation=prod_def
    )
    ifc.create_entity(
        "IfcRelContainedInSpatialStructure",
        GlobalId=new_guid(),
        RelatingStructure=storey,
        RelatedElements=[virtual]
    )


# --- Example Flurstück data ---
flurstueck_dict = {
    'DENW21AL100077H6': {
        'name': 'Flurstueck_DENW21AL100077H6',
        'points': [
            [0.0, 0.0, 0.0],
            [19.11339341026207, 0.0, 0.0],
            [26.95115774103939, 0.48843650619003753, 0.0],
            [26.091640951807435, 17.477748692858924, 0.0],
            [0.054256798672096096, 34.488348326781654, 0.0],
            [0.0, 0.0, 0.0]  # closing the loop
        ]
    }
}


Z_min = 0
Z_max = 12  # extrusion height in mm

# --- Loop through polygon edges and create vertical faces ---
for key, data in flurstueck_dict.items():
    name = data.get("name", f"Flurstueck_{key}")
    points = data["points"]

    for i in range(len(points) - 1):  # segment by segment
        p1 = points[i]
        p2 = points[i + 1]

        face_pts = [
            (p1[0], p1[1], Z_min),
            (p2[0], p2[1], Z_min),
            (p2[0], p2[1], Z_max),
            (p1[0], p1[1], Z_max)
        ]

        # Remove duplicates and create virtual element if valid
        unique_pts = []
        for pt in face_pts:
            if not unique_pts or pt != unique_pts[-1]:
                unique_pts.append(pt)

        if len(unique_pts) >= 3:
            create_virtual_element(ifc, unique_pts, context, storey, name=f"{name}_face_{i + 1}")


# --- Save IFC ---
ifc.write("project_site_building_storey.ifc")
