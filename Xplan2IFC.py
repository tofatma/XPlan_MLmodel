"""
This script writes Xplanung and CityGML objects in to the IFC Objects. 
So that the Architechts have the informed site plan.
"""
import math
import os
import random
import xml.etree.ElementTree as ET
import ifcopenshell

class IFCFloorplanGenerator:
    """to georeference and create IFC objects."""
    def __init__ (self, flurstueck_path, Xplanung_path, georeferencing_info_path, tolerance=0.001):
        self.flurstueck_path = flurstueck_path
        self.Xplanung_path = Xplanung_path
        self.ifc_file = ifcopenshell.file(schema="IFC4")
        self.nsmap = {
            "gml":  "http://www.opengis.net/gml/3.2",
            "xplan":"http://www.xplanung.de/xplangml/5/1",
            "xlink":"http://www.w3.org/1999/xlink",
            "adv": "http://www.adv-online.de/namespaces/adv/gid/6.0"
        }
        self.tolerance = tolerance
        self.context = None
        self.UTM_EASTING_ORIGIN = 0.0
        self.UTM_NORTHING_ORIGIN=0.0
        self.UTM_HEIGHT_ORIGIN=0.0
        self.origin_x = 0.0
        self.origin_y=0.0
        self.origin_z=0.0
        self.X_AXIS_ABSCISSA =1
        self.X_AXIS_ORDINATE =0
        self.MAP_SCALE = 1.0
        self.angle= 0.0
        if georeferencing_info_path:
            self.load_wld3_values(georeferencing_info_path)
    def load_wld3_values(self, wld3_path):
        """It loads the georeferencing data from the wld3 file and calculates 
        the angle and scale"""
        with open(wld3_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        def parse_line(line):
            parts = line.replace(",", " ").split()
            local = tuple(float(x) for x in parts[0:3])
            utm = tuple(float(x) for x in parts[3:6])
            return local, utm
        local1, utm1 = parse_line(lines[0])
        local2, utm2 = parse_line(lines[1])
        
        dx = utm2[0] - utm1[0]
        dy = utm2[1] - utm1[1]

        self.angle = math.atan2(dy, dx)
        length = math.hypot(dx, dy)
        if length != 0:
            self.X_AXIS_ABSCISSA = dx / length
            self.X_AXIS_ORDINATE = dy / length
        else:
            self.X_AXIS_ABSCISSA = 1.0
            self.X_AXIS_ORDINATE = 0.0

        self.UTM_EASTING_ORIGIN, self.UTM_NORTHING_ORIGIN, self.UTM_HEIGHT_ORIGIN = utm1
        self.origin_x, self.origin_y, self.origin_z = utm1
        d_local = math.dist(local1, local2)
        d_UTM = math.dist(utm1, utm2)
        self.MAP_SCALE = d_UTM / d_local if d_local != 0 else 1.0
    def get_site_geometry_dict(self):
        """Load Flurstueck, BauLinie, BauGrenze and return their shifted coordinates."""
        flurstueck_dict = {}
        baulinie_dict = {}
        baugrenze_dict = {}

        tree = ET.parse(self.flurstueck_path)
        root = tree.getroot()
        for flurstueck in root.findall(".//adv:AX_Flurstueck", self.nsmap):
            poslist = flurstueck.find(".//gml:posList", self.nsmap)
            if poslist is not None:
                coords = [float(x) for x in poslist.text.strip().split()]
                dim = 3 if len(coords) % 3 == 0 else 2
                points = []
                for i in range(0, len(coords), dim):
                    x = coords[i]
                    y = coords[i+1]
                    z = coords[i+2] if dim == 3 else 0.0
                    points.append([x, y, z])

                shifted_points = []
                for x, y, z in points:
                    x_local = (x - self.origin_x) * self.MAP_SCALE
                    y_local = (y - self.origin_y) * self.MAP_SCALE
                    z_local = (z - self.origin_z)
                    x_rot = x_local * self.X_AXIS_ABSCISSA + y_local * self.X_AXIS_ORDINATE
                    y_rot = -x_local * self.X_AXIS_ORDINATE + y_local * self.X_AXIS_ABSCISSA
                    shifted_points.append([x_rot, y_rot, z_local])

                flurstueck_id = flurstueck.get("{http://www.opengis.net/gml/3.2}id", "id_not_known")
                flurstueck_dict[flurstueck_id] = {
                "name": f"Flurstueck_{flurstueck_id}",
                "points": shifted_points}
        tree_xplan = ET.parse(self.Xplanung_path)
        root_xplan = tree_xplan.getroot()
        for tag, target_dict, type_name in [("xplan:BP_BauGrenze", baugrenze_dict, "Baugrenze"),
            ("xplan:BP_BauLinie", baulinie_dict, "Baulinie")]:
            for element in root_xplan.findall(f".//{tag}", self.nsmap):
                poslist = element.find(".//gml:posList", self.nsmap)
                if poslist is not None:
                    coords = [float(x) for x in poslist.text.strip().split()]
                    srs_dim = poslist.get("srsDimension")
                    dim = int(srs_dim) if srs_dim is not None else (3 if len(coords) % 3 == 0 else 2)

                    points = []
                    for i in range(0, len(coords), dim):
                        x = coords[i]
                        y = coords[i+1]
                        z = coords[i+2] if dim == 3 else 0.0
                        points.append([x, y, z])

                    shifted_points = []
                    for x, y, z in points:
                        x_local = (x - self.origin_x) * self.MAP_SCALE
                        y_local = (y - self.origin_y) * self.MAP_SCALE
                        z_local = (z - self.origin_z)
                        x_rot = x_local * self.X_AXIS_ABSCISSA + y_local * self.X_AXIS_ORDINATE
                        y_rot = -x_local * self.X_AXIS_ORDINATE + y_local * self.X_AXIS_ABSCISSA
                        shifted_points.append([x_rot, y_rot, z_local])

                    elem_id = element.get("{http://www.opengis.net/gml/3.2}id", "id_not_found_inGML")
                    target_dict[elem_id] = {
                    "name": f"{type_name}_{elem_id}",
                    "points": shifted_points
                }
        return flurstueck_dict, baugrenze_dict, baulinie_dict
def main():
    """Main function to run the script"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_folder = os.path.join(script_dir, "data")
    flurstueck_gml = os.path.join(data_folder, "flurstueckrequired.gml")
    xplan_file = os.path.join(data_folder, "XPlanung_lines.gml")
    wld3_file = os.path.join(data_folder, "Beispieldatei.wld3.wld3")
    
    generator = IFCFloorplanGenerator(flurstueck_gml, xplan_file, wld3_file, tolerance=0.001)
    flurstueck_dict, baugrenze_dict, baulinie_dict = generator.get_site_geometry_dict()
    # print(flurstueck_dict)
    # print(baugrenze_dict)
    return {
        "flurstueck_dict": flurstueck_dict,
        "baugrenze_dict": baugrenze_dict,
        "baulinie_dict": baulinie_dict,
        "generator": generator
    }
if __name__ == "__main__":
    main()
