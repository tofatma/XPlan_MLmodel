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
import os
import xml.etree.ElementTree as ET

# You need your helper functions:
# get_boundingpoints(pos, origin), create_ifc_poly(ifcfile, points, is_loop)

class CityGML2IFC:
    def __init__(self, ifcfile=None, owner_history=None, site=None, storey=None, context_body=None, context_axis=None):
        """ Initialize the transformer with an optional existing IFC. """
        self.ifcfile = ifcfile
        self.owner_history = owner_history
        self.site = site
        self.storey = storey
        self.context_body = context_body
        self.context_axis = context_axis

    def _parse_citygml(self, path):
        """ Parse CityGML file and return tree, root, and namespaces. """
        tree = ET.parse(path)
        root = tree.getroot()
        ns = {}
        if root.tag.endswith("CityModel"):
            if "1.0" in root.tag:
                ns["citygml"] = "http://www.opengis.net/citygml/1.0"
                ns["bldg"] = "http://www.opengis.net/citygml/building/1.0"
                ns["gml"] = "http://www.opengis.net/gml"
                ns["core"] = "http://www.opengis.net/citygml/3.0"
                ns["con"] = "http://www.opengis.net/citygml/construction/3.0"
            elif "2.0" in root.tag:
                ns["citygml"] = "http://www.opengis.net/citygml/2.0"
                ns["bldg"] = "http://www.opengis.net/citygml/building/2.0"
                ns["gml"] = "http://www.opengis.net/gml"
                ns["core"] = "http://www.opengis.net/citygml/3.0"
                ns["con"] = "http://www.opengis.net/citygml/construction/3.0"
            elif "3.0" in root.tag:
                ns["citygml"] = "http://www.opengis.net/citygml/3.0"
                ns["bldg"] = "http://www.opengis.net/citygml/building/3.0"
                ns["gml"] = "http://www.opengis.net/gml/3.2"
                ns["core"] = "http://www.opengis.net/citygml/3.0"
                ns["con"] = "http://www.opengis.net/citygml/construction/3.0"
            else:
                raise ValueError("Unsupported CityGML version or root tag.")
        return tree, root, ns

    def _create_local_placement(self, placement_rel_to):
        """ Helper to create an IfcLocalPlacement relative to another. """
        origin = self.ifcfile.createIfcCartesianPoint((0.0, 0.0, 0.0))
        axis2placement = self.ifcfile.createIfcAxis2Placement3D(origin, None, None)
        return self.ifcfile.createIfcLocalPlacement(placement_rel_to, axis2placement)

    def _create_building(self, building_element, ns):
        """ Create IFC building and storey from a <Building> element. """
        ifcfile = self.ifcfile
        owner_history = self.owner_history
        site = self.site

        building_placement = self._create_local_placement(site.ObjectPlacement)
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

        storey_placement = self._create_local_placement(building_placement)
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

        # Aggregate relationships
        ifcfile.createIfcRelAggregates(create_guid(), owner_history, "Site Container", None, site, [ifcbuilding])
        ifcfile.createIfcRelAggregates(create_guid(), owner_history, "Building Container", None, ifcbuilding, [building_storey])

        return ifcbuilding, building_storey

    def _create_faces_for_building(self, ifcbuilding, building_element, building_storey, ns):
        """ Convert CityGML surfaces to IFC elements and assign them. """
        ifcfile = self.ifcfile
        owner_history = self.owner_history
        object_placement = self._create_local_placement(building_storey.ObjectPlacement)
        ifcsurfaceid_list = []

        # Find boundedBy elements
        bounding = building_element.findall(f'.//{{{ns["bldg"]}}}boundedBy')
        if not bounding:
            bounding = building_element.findall(f'.//{{{ns["core"]}}}boundedBy')
        if not bounding:
            bounding = building_element.findall(f'.//{{{ns["core"]}}}boundary')

        for boundary in bounding:
            surfaces = boundary.findall(f'.//{{{ns["gml"]}}}surfaceMember')
            for Surface in surfaces:
                pos = Surface.find(f'.//{{{ns["gml"]}}}posList')
                if pos is None or pos.text is None:
                    continue
                bounding_points = get_boundingpoints(pos, O)

                polyline = create_ifc_poly(ifcfile, bounding_points, is_loop=False)
                polyloop = create_ifc_poly(ifcfile, bounding_points, is_loop=True)

                faceouterbound = ifcfile.createIfcFaceOuterBound(polyloop, True)
                face = ifcfile.createIfcFace([faceouterbound])
                openshell = ifcfile.createIfcOpenShell([face])
                surfacemodel = ifcfile.createIfcShellBasedSurfaceModel([openshell])

                shaperepresentation = ifcfile.createIfcShapeRepresentation(
                    self.context_body, "Body", "SurfaceModel", [surfacemodel]
                )
                axis_representation = ifcfile.createIfcShapeRepresentation(
                    self.context_axis, "Axis", "Curve3D", [polyline]
                )
                product_shape = ifcfile.createIfcProductDefinitionShape(None, None, [axis_representation, shaperepresentation])

                # Decide IFC type
                tag = boundary.tag
                if "GroundSurface" in tag or "FloorSurface" in tag:
                    elem = ifcfile.createIfcSlab(create_guid(), owner_history, "GroundSlab", None, None, object_placement, product_shape, None)
                elif "RoofSurface" in tag:
                    elem = ifcfile.createIfcRoof(create_guid(), owner_history, "RoofSlab", None, None, object_placement, product_shape, None, "FLAT_ROOF")
                elif "WallSurface" in tag or "InteriorWallSurface" in tag:
                    elem = ifcfile.createIfcWallStandardCase(create_guid(), owner_history, "Wall", None, None, object_placement, product_shape, None)
                elif "CeilingSurface" in tag:
                    elem = ifcfile.createIfcCovering(create_guid(), owner_history, "Covering", None, None, object_placement, product_shape, None)
                else:
                    continue

                # Assign representation to element
                elem.Representation = product_shape
                ifcsurfaceid_list.append(elem)

        # Link surfaces to storey
        if ifcsurfaceid_list:
            ifcfile.createIfcRelContainedInSpatialStructure(create_guid(), owner_history, None, None, ifcsurfaceid_list, building_storey)

        # Combine all shapes for the building
        building_shapes = [elem.Representation for elem in ifcsurfaceid_list if elem.Representation]
        if building_shapes:
            combined_shape = ifcfile.createIfcProductDefinitionShape(None, None, building_shapes)
            ifcbuilding.Representation = combined_shape

    def add_citygml(self, path: str):
        """ Add CityGML buildings to the IFC model. """
        tree, root, ns = self._parse_citygml(path)
        for building_element in root.findall(f'.//{{{ns["bldg"]}}}Building'):
            ifcbuilding, building_storey = self._create_building(building_element, ns)
            self._create_faces_for_building(ifcbuilding, building_element, building_storey, ns)

    def write_ifc(self, filename: str):
        """ Save IFC to disk. """
        if self.ifcfile is None:
            raise ValueError("No IFC file to write.")
        self.ifcfile.write(filename)
        print(f"IFC file saved: {filename}")


# Example usage:
if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_folder = os.path.join(script_dir, "data")
    citygml_source = os.path.join(data_folder, "Lod2existingbuilding.gml")
    result_ifc = os.path.join(script_dir, "combined_.ifc")

    transformer = CityGML2IFC(ifcfile=ifc, owner_history=owner_hist, site=site,
                            storey=storey, context_body=context_b, context_axis=context_a)
    transformer.add_citygml(citygml_source)
    transformer.write_ifc("site_full.ifc")
