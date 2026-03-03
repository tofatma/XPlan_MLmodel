"""
Export terrain (TIN) to CityGML 3.0
for site plan / development verification
"""
from lxml import etree as ET
import copy
from all_stakeholder2IFC import export_ifc_unified
from Xplan2IFC import main
CITYGML_NS = "http://www.opengis.net/citygml/3.0"
GML_NS = "http://www.opengis.net/gml/3.2"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

NSMAP = {
    None: CITYGML_NS,
    "gml": GML_NS,
    "xsi": XSI_NS,
    "xlink": "http://www.w3.org/1999/xlink",
    "dem": "http://www.opengis.net/citygml/relief/3.0",
    "bldg": "http://www.opengis.net/citygml/building/3.0",
    "con": "http://www.opengis.net/citygml/construction/3.0",
    "tran": "http://www.opengis.net/citygml/transportation/3.0",
    "wtr": "http://www.opengis.net/citygml/waterBody/3.0",
    "veg": "http://www.opengis.net/citygml/vegetation/3.0",
    "luse": "http://www.opengis.net/citygml/landUse/3.0",
    "brid": "http://www.opengis.net/citygml/bridge/3.0",
    "tun": "http://www.opengis.net/citygml/tunnel/3.0",
    "frn": "http://www.opengis.net/citygml/cityFurniture/3.0",
    "gen": "http://www.opengis.net/citygml/generics/3.0",
    "dyn": "http://www.opengis.net/citygml/dynamizer/3.0",
    "pcl": "http://www.opengis.net/citygml/pointCloud/3.0",
    "app": "http://www.opengis.net/citygml/appearance/3.0",
    "grp": "http://www.opengis.net/citygml/cityObjectGroup/3.0",
    "vers": "http://www.opengis.net/citygml/versioning/3.0",
    "xAL": "urn:oasis:names:tc:ciq:xal:3",
    "ct": "urn:oasis:names:tc:ciq:ct:3",
}
schema_pairs = [
    f"{CITYGML_NS} https://schemas.opengis.net/citygml/3.0/cityGML.xsd",
    f"{NSMAP['bldg']} https://schemas.opengis.net/citygml/building/3.0/building.xsd",
    f"{NSMAP['con']} https://schemas.opengis.net/citygml/construction/3.0/construction.xsd",
    f"{NSMAP['tran']} https://schemas.opengis.net/citygml/transportation/3.0/transportation.xsd",
    f"{NSMAP['wtr']} https://schemas.opengis.net/citygml/waterBody/3.0/waterBody.xsd",
    f"{NSMAP['veg']} https://schemas.opengis.net/citygml/vegetation/3.0/vegetation.xsd",
    f"{NSMAP['luse']} https://schemas.opengis.net/citygml/landUse/3.0/landUse.xsd",
    f"{NSMAP['dem']} https://schemas.opengis.net/citygml/relief/3.0/relief.xsd",
    f"{NSMAP['gen']} https://schemas.opengis.net/citygml/generics/3.0/generics.xsd",
    f"{NSMAP['pcl']} https://schemas.opengis.net/citygml/pointCloud/3.0/pointCloud.xsd",
    f"{NSMAP['app']} https://schemas.opengis.net/citygml/appearance/3.0/appearance.xsd",
    f"{NSMAP['dyn']} https://schemas.opengis.net/citygml/dynamizer/3.0/dynamizer.xsd",
    f"{NSMAP['frn']} https://schemas.opengis.net/citygml/cityfurniture/3.0/cityfurniture.xsd",
    f"{NSMAP['grp']} https://schemas.opengis.net/citygml/cityObjectGroup/3.0/cityObjectGroup.xsd",
    f"{NSMAP['brid']} https://schemas.opengis.net/citygml/bridge/3.0/bridge.xsd",
    f"{NSMAP['tun']} https://schemas.opengis.net/citygml/tunnel/3.0/tunnel.xsd",
    f"{NSMAP['vers']} https://schemas.opengis.net/citygml/versioning/3.0/versioning.xsd"
]
root = ET.Element(
    "{%s}CityModel" % CITYGML_NS,
    nsmap=NSMAP,
    #attrib={"{%s}schemaLocation" % XSI_NS: " ".join(schema_pairs)}
    attrib={}
)
bounded_by = ET.SubElement(root, "{%s}boundedBy" % GML_NS)
envelope = ET.SubElement(
    bounded_by,
    "{%s}Envelope" % GML_NS,
    attrib={
        "srsName": "urn:ogc:def:crs:EPSG::25832",
        "srsDimension": "3"
    }
)
tree = ET.ElementTree(root)
output_file = "CityGML3_26BM.gml"
source_file = "data\Lod2existingbuilding__v3.gml"
source_tree = ET.parse(source_file)
source_root = source_tree.getroot()
buildings = source_root.findall(".//{%s}Building" % NSMAP["bldg"])
if buildings:
    for building in buildings:
        building_copy = copy.deepcopy(building)
        city_object_member = ET.Element("{%s}cityObjectMember" % CITYGML_NS)
        city_object_member.append(building_copy)
        root.append(city_object_member)
else:
    print("No buildings found in source file.")
vertices,vertices_UTM, faces = export_ifc_unified()
terrain_vertices = vertices_UTM
relief_feature = ET.Element(
    "{%s}ReliefFeature" % NSMAP["dem"],
    attrib={"{%s}id" % GML_NS: "dem_001"}
)
name = ET.SubElement(relief_feature, "{%s}name" % GML_NS)
name.text = "DEM 001"

lod = ET.SubElement(relief_feature, "{%s}lod" % NSMAP["dem"])
lod.text = "2"
relief_component = ET.SubElement(
    relief_feature,
    "{%s}reliefComponent" % NSMAP["dem"]
)
tin_relief = ET.SubElement(
    relief_component,
    "{%s}TINRelief" % NSMAP["dem"],
    attrib={"{%s}id" % GML_NS: "dem_001_tin"}
)
lod2 = ET.SubElement(tin_relief, "{%s}lod" % NSMAP["dem"])
lod2.text = "2"
tin = ET.SubElement(tin_relief, "{%s}tin" % NSMAP["dem"])
tri_surface = ET.SubElement(
    tin,
    "{%s}TriangulatedSurface" % GML_NS,
    attrib={"{%s}id" % GML_NS: "dem_surface"}
)
patches = ET.SubElement(tri_surface, "{%s}patches" % GML_NS)
for face in faces:
    triangle = ET.SubElement(patches, "{%s}Triangle" % GML_NS)
    exterior = ET.SubElement(triangle, "{%s}exterior" % GML_NS)
    linear_ring = ET.SubElement(exterior, "{%s}LinearRing" % GML_NS)
    pos_list = ET.SubElement(linear_ring, "{%s}posList" % GML_NS)
    coords = []
    for index in face:
        x, y, z = terrain_vertices[index]
        coords.append(f"{x} {y} {z}")
    coords.append(coords[0])
    pos_list.text = " ".join(coords)
terrain_member = ET.Element("{%s}cityObjectMember" % CITYGML_NS)
terrain_member.append(relief_feature)
root.append(terrain_member)

XPLAN_FILE = "data/XPlanung_lines.gml"
XPLAN_NS = "http://www.xplanung.de/xplangml/5/1"
NS_XPLAN = {
    "xplan": XPLAN_NS,
    "gml": GML_NS
}
xplan_objects = []

xplan_tree = ET.parse(XPLAN_FILE)
xplan_root = xplan_tree.getroot()
def extract_xplan_feature(feature, feature_type):

    feature_id = feature.get("{%s}id" % GML_NS)

    poslist = feature.find(".//gml:posList", namespaces=NS_XPLAN)

    if poslist is None:
        return None

    return {
        "type": feature_type,
        "gml_id": feature_id,
        "poslist": poslist.text
    }
for feature in xplan_root.findall(".//xplan:BP_BauLinie", namespaces=NS_XPLAN):
    data = extract_xplan_feature(feature, "BauLinie")
    if data:
        xplan_objects.append(data)
for feature in xplan_root.findall(".//xplan:BP_BauGrenze", namespaces=NS_XPLAN):
    data = extract_xplan_feature(feature, "BauGrenze")
    if data:
        xplan_objects.append(data)
#print("XPlan objects extracted:", xplan_objects)
terrain_z_values = [v[2] for v in vertices]
terrain_z_min = min(terrain_z_values)
Z_MIN = terrain_z_min
Z_MAX = terrain_z_min + 12.0

for obj in xplan_objects:

    clean_poslist = " ".join(obj["poslist"].split())
    coords_2d = list(map(float, clean_poslist.split()))
    city_member = ET.Element("{%s}cityObjectMember" % CITYGML_NS)

    thematic_surface = ET.SubElement(
        city_member,
        "{%s}GenericThematicSurface" % NSMAP["gen"],
        attrib={"{%s}id" % GML_NS: obj["gml_id"]}
    )

    name = ET.SubElement(thematic_surface, "{%s}name" % GML_NS)
    name.text = obj["type"]

    lod2 = ET.SubElement(thematic_surface, "{%s}lod2MultiSurface" % CITYGML_NS)

    multi_surface = ET.SubElement(
        lod2,
        "{%s}MultiSurface" % GML_NS,
        attrib={"srsName": "urn:ogc:def:crs:EPSG::25832"}
    )
    for i in range(0, len(coords_2d) - 2, 2):

        x1 = coords_2d[i]
        y1 = coords_2d[i + 1]
        x2 = coords_2d[i + 2]
        y2 = coords_2d[i + 3]

        surface_member = ET.SubElement(multi_surface, "{%s}surfaceMember" % GML_NS)

        polygon = ET.SubElement(surface_member, "{%s}Polygon" % GML_NS)

        exterior = ET.SubElement(polygon, "{%s}exterior" % GML_NS)
        linear_ring = ET.SubElement(exterior, "{%s}LinearRing" % GML_NS)

        pos_list = ET.SubElement(
            linear_ring,
            "{%s}posList" % GML_NS,
            attrib={"srsDimension": "3"}
        )

        wall_coords = [
            f"{x1} {y1} {Z_MIN}",
            f"{x2} {y2} {Z_MIN}",
            f"{x2} {y2} {Z_MAX}",
            f"{x1} {y1} {Z_MAX}",
            f"{x1} {y1} {Z_MIN}"
        ]

        pos_list.text = " ".join(wall_coords)

    root.append(city_member)

flur_tree = ET.parse("data/flurstueckrequired.gml")
flur_root = flur_tree.getroot()
NS_flur = {
    "gml": "http://www.opengis.net/gml/3.2",
    "wfs": "http://www.opengis.net/wfs/2.0",
    "adv": "http://www.adv-online.de/namespaces/adv/gid/6.0"
}
parcel = flur_root.find(".//adv:AX_Flurstueck", NS_flur)
if parcel is None:
    raise Exception("AX_Flurstueck not found in WFS file")
gml_id = parcel.attrib["{http://www.opengis.net/gml/3.2}id"]
pos_list = parcel.find(".//gml:posList", NS_flur).text
clean_poslist = " ".join(pos_list.split())
coords_2d = list(map(float, clean_poslist.split()))
parcel_id = gml_id
solid_id = f"Flurstueck_{parcel_id}"
points = []
for i in range(0, len(coords_2d), 2):
    points.append((coords_2d[i], coords_2d[i+1]))
points = []
for i in range(0, len(coords_2d), 2):
    points.append((coords_2d[i], coords_2d[i+1]))
if points[0] == points[-1]:
    points_no_close = points[:-1]
else:
    points_no_close = points
city_member = ET.Element("{%s}cityObjectMember" % CITYGML_NS)

logical_space = ET.SubElement(
    city_member,
    "{%s}GenericLogicalSpace" % NSMAP["gen"],
    attrib={"{%s}id" % GML_NS: solid_id}
)

name = ET.SubElement(logical_space, "{%s}name" % GML_NS)
name.text = solid_id

gen_class = ET.SubElement(logical_space, "{%s}class" % NSMAP["gen"])
gen_class.text = "parcel"

lod2 = ET.SubElement(logical_space, "{%s}lod2Solid" % CITYGML_NS)

solid = ET.SubElement(
    lod2,
    "{%s}Solid" % GML_NS,
    attrib={"srsName": "urn:ogc:def:crs:EPSG::25832"}
)

exterior = ET.SubElement(solid, "{%s}exterior" % GML_NS)
composite = ET.SubElement(exterior, "{%s}CompositeSurface" % GML_NS)
surface_member = ET.SubElement(composite, "{%s}surfaceMember" % GML_NS)

bottom_poly = ET.SubElement(
    surface_member,
    "{%s}Polygon" % GML_NS,
    attrib={"{%s}id" % GML_NS: f"FlurstueckBottom_{parcel_id}"}
)

ext = ET.SubElement(bottom_poly, "{%s}exterior" % GML_NS)
ring = ET.SubElement(ext, "{%s}LinearRing" % GML_NS)

pos = ET.SubElement(ring, "{%s}posList" % GML_NS,
                    attrib={"srsDimension": "3"})

bottom_coords = []
for x, y in points:
    bottom_coords.append(f"{x} {y} {Z_MIN}")

pos.text = " ".join(bottom_coords)
surface_member = ET.SubElement(composite, "{%s}surfaceMember" % GML_NS)

top_poly = ET.SubElement(
    surface_member,
    "{%s}Polygon" % GML_NS,
    attrib={"{%s}id" % GML_NS: f"FlurstueckTop_{parcel_id}"}
)

ext = ET.SubElement(top_poly, "{%s}exterior" % GML_NS)
ring = ET.SubElement(ext, "{%s}LinearRing" % GML_NS)

pos = ET.SubElement(ring, "{%s}posList" % GML_NS,
                    attrib={"srsDimension": "3"})

top_coords = []
for x, y in reversed(points):
    top_coords.append(f"{x} {y} {Z_MAX}")

pos.text = " ".join(top_coords)
n = len(points_no_close)

for i in range(n):

    x1, y1 = points_no_close[i]
    x2, y2 = points_no_close[(i + 1) % n]   # wrap to first point

    surface_member = ET.SubElement(composite, "{%s}surfaceMember" % GML_NS)

    wall_poly = ET.SubElement(
        surface_member,
        "{%s}Polygon" % GML_NS,
        attrib={"{%s}id" % GML_NS:
                f"FlurstueckWall_{parcel_id}_{i}"}
    )

    ext = ET.SubElement(wall_poly, "{%s}exterior" % GML_NS)
    ring = ET.SubElement(ext, "{%s}LinearRing" % GML_NS)

    pos = ET.SubElement(ring, "{%s}posList" % GML_NS,
                        attrib={"srsDimension": "3"})

    wall_coords = [
        f"{x1} {y1} {Z_MIN}",
        f"{x2} {y2} {Z_MIN}",
        f"{x2} {y2} {Z_MAX}",
        f"{x1} {y1} {Z_MAX}",
        f"{x1} {y1} {Z_MIN}"
    ]

    pos.text = " ".join(wall_coords)
root.append(city_member)

print("Parcel BREP solid created with dynamic terrain height.")
tree = ET.ElementTree(root)
tree.write(
    output_file,
    encoding="UTF-8",
    xml_declaration=True,
    pretty_print=True
)
data = main()
generator = data["generator"]
angle = generator.angle
print(angle)