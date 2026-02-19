"""This script can be used to generate the ifc of
the entire site plan. The terrain height is included in the XPlannung objects.
The existing building is also added."""
from ifcopenshell.guid import new as new_guid
import os
import sys
import time
import uuid
import tempfile
import itertools
from typing import List, Tuple, Union
import xml.etree.ElementTree as ET
import numpy as np
import math
from pyproj import Transformer
import ifcopenshell
from Xplan2IFC import main
O = (0.0, 0.0, 0.0)
X = (0.0, 0.0, 1.0)
Y = (0.0, 1.0, 0.0)
Z = (1.0, 0.0, 0.0)
_GUID_BASE64 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz__"

def generate_ifc_guid() -> str:
    """
    Create a valid IFC GUID (22‐character Base64) from a new UUID4.
    """
    u = uuid.uuid4()
    b = u.bytes_le
    num = int.from_bytes(b, byteorder="big")
    chars = []
    for _ in range(22):
        chars.append(_GUID_BASE64[num & 0x3F])
        num >>= 6
    return "".join(chars)

create_guid = generate_ifc_guid
data= main()
generator = data["generator"]
#vertical_faces = data["vertical_faces"]
flurstueck_dict = data["flurstueck_dict"]
baugrenze_dict = data["baugrenze_dict"] 
baulinie_dict = data["baulinie_dict"]
UTM_EASTING_ORIGIN   = generator.UTM_EASTING_ORIGIN
UTM_NORTHING_ORIGIN  = generator.UTM_NORTHING_ORIGIN
angle= generator.angle
UTM_HEIGHT_ORIGIN    = generator.UTM_HEIGHT_ORIGIN
X_AXIS_ABSCISSA      = generator.X_AXIS_ABSCISSA
X_AXIS_ORDINATE      = generator.X_AXIS_ORDINATE
MAP_SCALE            = generator.MAP_SCALE

def create_ifcaxis2placement(ifcfile, point: Tuple[float, float, float] = O,
                              dir1: Tuple[float, float, float] = Z,
                              dir2: Tuple[float, float, float] = X):
    point_obj = ifcfile.createIfcCartesianPoint(point)
    dir1_obj = ifcfile.createIfcDirection(dir1)
    dir2_obj = ifcfile.createIfcDirection(dir2)
    return ifcfile.createIfcAxis2Placement3D(point_obj, dir1_obj, dir2_obj)

def create_ifclocalplacement(ifcfile, relation, point: Tuple[float, float, float] = O,
                             dir1: Tuple[float, float, float] = Z,
                             dir2: Tuple[float, float, float] = X):
    axis2placement = create_ifcaxis2placement(ifcfile, point, dir1, dir2)
    return ifcfile.createIfcLocalPlacement(relation, axis2placement)
def create_ifc_poly(ifcfile, point_list: List[Tuple[float, float, float]],
                    is_loop: bool = False):
    """
    Given a list of 3D points (x, y, z), create either an IfcPolyLine (is_loop=False)
    or an IfcPolyLoop (is_loop=True).
    """
    if not point_list:
        raise ValueError("point_list cannot be empty.")

    ifc_points = []
    for point in point_list:
        if len(point) != 3:
            raise ValueError(f"Point {point} must be a 3D coordinate.")
        ifc_points.append(ifcfile.createIfcCartesianPoint(point))

    if is_loop:
        return ifcfile.createIfcPolyLoop(ifc_points)
    else:
        return ifcfile.createIfcPolyLine(ifc_points)

def convert_to_local(point):
    utm_x, utm_y, utm_z = point
    ref_x, ref_y= UTM_EASTING_ORIGIN, UTM_NORTHING_ORIGIN
    total_scale = MAP_SCALE
    dx = utm_x - ref_x
    dy = utm_y - ref_y
    dz = utm_z - UTM_HEIGHT_ORIGIN
    delta_east = dx / total_scale
    delta_north = dy / total_scale
    local_x = math.cos(-angle) * delta_east - math.sin(-angle) * delta_north
    local_y = math.sin(-angle) * delta_east + math.cos(-angle) * delta_north
    return round(local_x, 4), round(local_y, 4), round(dz, 4)
def get_boundingpoints(pos: ET.Element, reference_point: Tuple[float, float, float]):
    """
    Given an <gml:posList> element, split it into triples, convert each with convert_to_local.
    """
    raw_vals = [float(val) for val in pos.text.strip().split()]
    raw_points = [raw_vals[i:i+3] for i in range(0, len(raw_vals), 3)]

    converted = []
    for p in raw_points:
        if len(p) != 3:
            raise ValueError(f"Point {p} does not have 3 coordinates.")
        local_pt = convert_to_local(tuple(p))
        converted.append(local_pt)

    return converted
def update_z_coordinates_simple(geometry_dict, new_z):
    for obj in geometry_dict.values():
        obj["points"] = [[x, y, new_z] for x, y, z in obj["points"]]
def CityGML2IFC(path: str, ifc_file=None,existing_ifc=None,project_obj =None, site_main = None):
    """
    1) Read orientation_data via IFCFloorplanGenerator (unchanged).
    2) Parse CityGML and collect <Building> elements (unchanged).
    3) Create an in-memory IFC4 file with ifcopenshell.file(schema="IFC4X3").
    4) Directly create OwnerHistory, Project, Units, MapConversion, Site, Floorplan, Buildings.
    5) Write out via ifcfile.write(filename).
    """
    if existing_ifc:
        ifcfile = existing_ifc  # use your terrain IFC
    else:
        ifcfile = ifcopenshell.file(schema="IFC4X3")
    tree = ET.parse(path)
    root = tree.getroot()
    if root.tag == "{http://www.opengis.net/citygml/1.0}CityModel":
        ns_citygml = "http://www.opengis.net/citygml/1.0"
        ns_bldg    = "http://www.opengis.net/citygml/building/1.0"
        ns_gml     = "http://www.opengis.net/gml"
        ns_core    = "http://www.opengis.net/citygml/3.0"
        ns_con     = "http://www.opengis.net/citygml/construction/3.0"

    elif root.tag == "{http://www.opengis.net/citygml/2.0}CityModel":
        ns_citygml = "http://www.opengis.net/citygml/2.0"
        ns_bldg    = "http://www.opengis.net/citygml/building/2.0"
        ns_gml     = "http://www.opengis.net/gml"
        ns_core    = "http://www.opengis.net/citygml/3.0"
        ns_con     = "http://www.opengis.net/citygml/construction/3.0"

    elif root.tag == "{http://www.opengis.net/citygml/3.0}CityModel":
        ns_citygml = "http://www.opengis.net/citygml/3.0"
        ns_bldg    = "http://www.opengis.net/citygml/building/3.0"
        ns_gml     = "http://www.opengis.net/gml/3.2"
        ns_core    = "http://www.opengis.net/citygml/3.0"
        ns_con     = "http://www.opengis.net/citygml/construction/3.0"

    else:
        raise ValueError("Unsupported CityGML version or root tag.")
    #ifcfile = ifcopenshell.file(schema="IFC4X3")

    creator_name   = "Fatma Ahmad (GIA)"
    organization   = "RWTH Aachen"
    application    = "Autodesk Revit 2025.4 (DEU)"
    application_ver= "2025"
    timestamp      = int(time.time())

    person = ifcfile.createIfcPerson(
        None,
        None,
        creator_name,
        None,
        None,
        None, 
        None,
        None
    )
    org = ifcfile.createIfcOrganization(
        None,
        organization,
        None,
        None,
        None
    )

    person_and_org = ifcfile.createIfcPersonAndOrganization(
        ThePerson=person,
        TheOrganization=org,
        Roles=None
    )

    application_entity = ifcfile.createIfcApplication(
        ApplicationDeveloper=org,
        Version=application_ver,
        ApplicationFullName=application,
        ApplicationIdentifier=application
    )

    owner_history = ifcfile.createIfcOwnerHistory(
        OwningUser=person_and_org,
        OwningApplication=application_entity,
        State="READWRITE",
        ChangeAction="NOCHANGE",
        LastModifiedDate=None,
        LastModifyingUser=None,
        LastModifyingApplication=None,
        CreationDate=timestamp
    )
    dir_x = ifcfile.createIfcDirection((1.0, 0.0, 0.0))
    dir_z = ifcfile.createIfcDirection((0.0, 0.0, 1.0))
    origin_pt = ifcfile.createIfcCartesianPoint((0.0, 0.0, 0.0))

    axis2placement = ifcfile.createIfcAxis2Placement3D(origin_pt, dir_z, dir_x)

    axis_y = ifcfile.createIfcDirection((0.0, 1.0, 0.0))
    true_north = ifcfile.create_entity("IfcDirection", DirectionRatios=[0.0, 1.0]) 
    geom_context = ifcfile.createIfcGeometricRepresentationContext(
        ContextIdentifier=None,
        ContextType="Model",
        CoordinateSpaceDimension=3,
        Precision=0.01,
        WorldCoordinateSystem=axis2placement,
        TrueNorth=true_north
    )
    project_globalid = generate_ifc_guid()
    # project_obj  = ifcfile.createIfcProject(
    #     GlobalId=project_globalid,
    #     OwnerHistory=owner_history,
    #     Name="Lageplan",
    #     Description=None,
    #     ObjectType=None,
    #     LongName=None,
    #     Phase=None,
    #     RepresentationContexts=[geom_context]
    # )

    length_si_unit = ifcfile.createIfcSIUnit(UnitType="LENGTHUNIT", Prefix=None, Name="METRE")
    area_si_unit   = ifcfile.createIfcSIUnit(UnitType="AREAUNIT", Prefix=None, Name="SQUARE_METRE")
    volume_si_unit = ifcfile.createIfcSIUnit(UnitType="VOLUMEUNIT", Prefix=None, Name="CUBIC_METRE")
    angle_si_unit  = ifcfile.createIfcSIUnit(UnitType="PLANEANGLEUNIT", Prefix=None, Name="RADIAN")
    mass_si_unit   = ifcfile.createIfcSIUnit(UnitType="MASSUNIT", Prefix="KILO", Name="GRAM")
    time_si_unit   = ifcfile.createIfcSIUnit(UnitType="TIMEUNIT", Prefix=None, Name="SECOND")
    freq_si_unit   = ifcfile.createIfcSIUnit(UnitType="FREQUENCYUNIT", Prefix=None, Name="HERTZ")
    temp_si_unit   = ifcfile.createIfcSIUnit(UnitType="THERMODYNAMICTEMPERATUREUNIT", Prefix=None, Name="KELVIN")
    tempc_si_unit  = ifcfile.createIfcSIUnit(UnitType="THERMODYNAMICTEMPERATUREUNIT", Prefix=None, Name="DEGREE_CELSIUS")
    elec_i_unit    = ifcfile.createIfcSIUnit(UnitType="ELECTRICCURRENTUNIT", Prefix=None, Name="AMPERE")
    elec_v_unit    = ifcfile.createIfcSIUnit(UnitType="ELECTRICVOLTAGEUNIT", Prefix=None, Name="VOLT")
    power_unit     = ifcfile.createIfcSIUnit(UnitType="POWERUNIT", Prefix=None, Name="WATT")
    force_unit     = ifcfile.createIfcSIUnit(UnitType="FORCEUNIT", Prefix="KILO", Name="NEWTON")
    illum_unit     = ifcfile.createIfcSIUnit(UnitType="ILLUMINANCEUNIT", Prefix=None, Name="LUX")
    lum_flux_unit  = ifcfile.createIfcSIUnit(UnitType="LUMINOUSFLUXUNIT", Prefix=None, Name="LUMEN")
    lum_int_unit   = ifcfile.createIfcSIUnit(UnitType="LUMINOUSINTENSITYUNIT", Prefix=None, Name="CANDELA")
    pressure_unit  = ifcfile.createIfcSIUnit(UnitType="PRESSUREUNIT", Prefix=None, Name="PASCAL")

    all_units = [
        length_si_unit, area_si_unit, volume_si_unit, angle_si_unit,
        mass_si_unit, time_si_unit, freq_si_unit, temp_si_unit, tempc_si_unit,
        elec_i_unit, elec_v_unit, power_unit, force_unit,
        illum_unit, lum_flux_unit, lum_int_unit, pressure_unit
    ]
    unit_assignment = ifcfile.createIfcUnitAssignment(all_units)
    project_obj.UnitsInContext = unit_assignment

    target_crs = ifcfile.create_entity(
        "IfcCoordinateReferenceSystem",
        Name="ETRS89 / UTM zone 32N"
    )
    source_crs = ifcfile.create_entity(
        "IfcCoordinateReferenceSystem",
        Name="Local Coordinate System"
    )
    map_conversion = ifcfile.create_entity(
        "IfcMapConversion",
        source_crs,
        target_crs,
        UTM_EASTING_ORIGIN,
        UTM_NORTHING_ORIGIN,
        UTM_HEIGHT_ORIGIN,
        X_AXIS_ABSCISSA,
        X_AXIS_ORDINATE,
        MAP_SCALE
    )
    anchor_pt   = ifcfile.createIfcCartesianPoint((0.0, 0.0, 0.0))
    anchor_axis = ifcfile.createIfcAxis2Placement3D(anchor_pt, None, None)
    root_site_placement = ifcfile.createIfcLocalPlacement(PlacementRelTo=None, RelativePlacement=anchor_axis)
    # site_flurstueck = ifcfile.createIfcSite(
    #     GlobalId=generate_ifc_guid(),
    #     OwnerHistory=owner_history,
    #     Name="Flurstuecke",
    #     Description="Contains only flurstueck parcels",
    #     ObjectType="FLURSTUECK",
    #     ObjectPlacement=root_site_placement,
    #     Representation=None,
    #     LongName=None,
    #     CompositionType="ELEMENT",
    #     RefLatitude=None,
    #     RefLongitude=None,
    #     RefElevation=None
    # )
    # site_main = ifcfile.createIfcSite(
    #     GlobalId=generate_ifc_guid(),
    #     OwnerHistory=owner_history,
    #     Name="Pre_SitePlan",
    #     Description=None,
    #     ObjectType=None,
    #     ObjectPlacement=root_site_placement,
    #     Representation=None,
    #     LongName=None,
    #     CompositionType="ELEMENT",
    #     RefLatitude=None,
    #     RefLongitude=None,
    #     RefElevation=None
    # )

    ifcfile.createIfcRelAggregates(
        GlobalId=generate_ifc_guid(),
        OwnerHistory=owner_history,
        Name="Project to Site",
        Description=None,
        RelatingObject=project_obj ,
        RelatedObjects=[site_main]
    )
    terrain_heights = []
    for building in root.findall(f'.//{{{ns_bldg}}}Building'):
        lod2_terrain = building.find(f'.//{{{ns_bldg}}}lod2TerrainIntersection')
        if lod2_terrain is not None:
            poslist_elem = lod2_terrain.find(f'.//{{{ns_gml}}}posList')
            if poslist_elem is not None and poslist_elem.text:
                coords = list(map(float, poslist_elem.text.strip().split()))
                z_values = coords[2::3]
                terrain_heights.extend(z_values)
    if terrain_heights:
        min_height = min(terrain_heights)
    else:
        min_height = 0.0
    update_z_coordinates_simple(flurstueck_dict, min_height)
    update_z_coordinates_simple(baugrenze_dict, min_height)
    update_z_coordinates_simple(baulinie_dict, min_height)
    ifcfile.create_entity(
        "IfcRelAggregates",
        GlobalId=generate_ifc_guid(),
        OwnerHistory=owner_history,
        Name="Project to Site",
        Description="Project contains Site",
        RelatingObject=project_obj,
        RelatedObjects=[site_main]
    )
    context = ifcfile.createIfcGeometricRepresentationContext(
        None,
        "Model",
        3,
        0.01,
        axis2placement,
        axis_y
    )
    subcontext_axis = ifcfile.createIfcGeometricRepresentationSubContext(
        "Axis", "Model", None, None, None, None, context, None, "MODEL_VIEW", None
    )
    subcontext_body = ifcfile.createIfcGeometricRepresentationSubContext(
        "Body", "Model", None, None, None, None, context, None, "MODEL_VIEW", None
    )
    cityObjects = []
    buildings   = []
    other       = []

    for obj in tree.iter(f'{{{ns_citygml}}}cityObjectMember'):
        cityObjects.append(obj)
    for cityObject in cityObjects:
        for child in cityObject.iter():
            if child.tag == f'{{{ns_bldg}}}Building':
                buildings.append(child)
            else:
                other.append(child)

        for building in buildings:
            ifcsurfaceid_list = []
        building_placement = create_ifclocalplacement(ifcfile, root_site_placement)
        ifcbuilding = ifcfile.createIfcBuilding(
            create_guid(),
            owner_history,
            "Building",
            None,
            None,
            building_placement,
            None,
            None,
            "ELEMENT",
            None,
            None,
            None,
        )

        storey_placement = create_ifclocalplacement(ifcfile, building_placement)
        building_storey = ifcfile.createIfcBuildingStorey(
            create_guid(),
            owner_history,
            "Storey",
            None,
            None,
            storey_placement,
            None,
            None,
            "ELEMENT",
            0.0,
        )
        ifcfile.createIfcRelAggregates(
            create_guid(),
            owner_history,
            "Site Container",
            None,
            site_main,
            [ifcbuilding],
        )
        ifcfile.createIfcRelAggregates(
            create_guid(),
            owner_history,
            "Building Container",
            None,
            ifcbuilding,
            [building_storey],
        )

        object_placement = create_ifclocalplacement(ifcfile, building_placement)

        bounding = building.findall(f'.//{{{ns_bldg}}}boundedBy')
        if not bounding:
            bounding = building.findall(f'.//{{{ns_core}}}boundedBy')
        if not bounding:
            bounding = building.findall(f'.//{{{ns_core}}}boundary')

        for boundary in bounding:
            surfaces = boundary.findall(f'.//{{{ns_gml}}}surfaceMember')
            for Surface in surfaces:
                pos = Surface.find(f'.//{{{ns_gml}}}posList')
                bounding_points = get_boundingpoints(pos, O)
                
                polyline = create_ifc_poly(ifcfile, bounding_points, is_loop=False)
                polyloop = create_ifc_poly(ifcfile, bounding_points, is_loop=True)

                faceouterbound = ifcfile.createIfcFaceOuterBound(polyloop, True)
                face = ifcfile.createIfcFace([faceouterbound])
                openshell = ifcfile.createIfcOpenShell([face])
                surfacemodel = ifcfile.createIfcShellBasedSurfaceModel([openshell])

                shaperepresentation = ifcfile.createIfcShapeRepresentation(
                    subcontext_body, "Body", "SurfaceModel", [surfacemodel]
                )
                axis_representation = ifcfile.createIfcShapeRepresentation(
                    subcontext_axis, "Axis", "Curve3D", [polyline]
                )
                product_shape = ifcfile.createIfcProductDefinitionShape(
                    None, None, [axis_representation, shaperepresentation]
                )
                if (
                    boundary.find(f'{{{ns_bldg}}}GroundSurface') or
                    boundary.find(f'{{{ns_bldg}}}FloorSurface') or
                    boundary.find(f'{{{ns_con}}}GroundSurface') or
                    boundary.find(f'{{{ns_con}}}FloorSurface')
                ):
                    ifcslab = ifcfile.createIfcSlab(
                        create_guid(),
                        owner_history,
                        "GroundSlab",
                        None,
                        None,
                        object_placement,
                        product_shape,
                        None,
                    )
                    ifcsurfaceid_list.append(ifcslab)

                if (
                    boundary.find(f'{{{ns_bldg}}}RoofSurface') or
                    boundary.find(f'{{{ns_con}}}RoofSurface')
                ):
                    ifcroof = ifcfile.createIfcRoof(
                        create_guid(),
                        owner_history,
                        "RoofSlab",
                        None,
                        None,
                        object_placement,
                        product_shape,
                        None,
                        "FLAT_ROOF",
                    )
                    ifcsurfaceid_list.append(ifcroof)

                if (
                    boundary.find(f'{{{ns_bldg}}}WallSurface') or
                    boundary.find(f'{{{ns_bldg}}}InteriorWallSurface') or
                    boundary.find(f'{{{ns_con}}}WallSurface') or
                    boundary.find(f'{{{ns_con}}}InteriorWallSurface')
                ):
                    ifcwall = ifcfile.createIfcWallStandardCase(
                        create_guid(),
                        owner_history,
                        "Wall",
                        None,
                        None,
                        object_placement,
                        product_shape,
                        None,
                    )
                    ifcsurfaceid_list.append(ifcwall)

                if (
                    boundary.find(f'{{{ns_bldg}}}CeilingSurface') or
                    boundary.find(f'{{{ns_con}}}CeilingSurface')
                ):
                    ifccovering = ifcfile.createIfcCovering(
                        create_guid(),
                        owner_history,
                        "Covering",
                        None,
                        None,
                        object_placement,
                        product_shape,
                        None,
                    )
                    ifcsurfaceid_list.append(ifccovering)

        if ifcsurfaceid_list:
            ifcfile.createIfcRelContainedInSpatialStructure(
                create_guid(),
                owner_history,
                None,
                None,
                ifcsurfaceid_list,
                building_storey,
             )
    # if ifc_file:
    #     ifcfile.write(ifc_file)

    return ifcfile
            
# if __name__ == "__main__":
#     script_dir = os.path.dirname(os.path.abspath(__file__))
#     #print(script_dir)
#     data_folder = os.path.join(script_dir, "data")
#     citygml_source = os.path.join(data_folder, "Lod2existingbuilding.gml")
#     result_ifc = os.path.join(script_dir,"combined_siteplan_data.ifc")
#     ifc = CityGML2IFC(citygml_source, ifc_file=result_ifc)
#     ifc.write(result_ifc)
