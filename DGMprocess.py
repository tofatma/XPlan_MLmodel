# from owslib.wcs import WebCoverageService
# from Xplan2IFC import main, IFCFloorplanGenerator
# import numpy as np
# import rasterio

# import ifcopenshell
# import ifcopenshell.api

# data= main()

# generator = data["generator"]
# UTM_EASTING_ORIGIN   = generator.UTM_EASTING_ORIGIN
# UTM_NORTHING_ORIGIN  = generator.UTM_NORTHING_ORIGIN
# angle= generator.angle
# utm_x_origin = generator.origin_x
# utm_y_origin=  generator.origin_y
# UTM_HEIGHT_ORIGIN    = generator.UTM_HEIGHT_ORIGIN
# X_AXIS_ABSCISSA      = generator.X_AXIS_ABSCISSA
# X_AXIS_ORDINATE      = generator.X_AXIS_ORDINATE
# MAP_SCALE            = generator.MAP_SCALE

# flurstueck_dict = data.get("flurstueck_dict", {})

# all_points = []
# for fs_id in flurstueck_dict:
#     all_points.extend(flurstueck_dict[fs_id]['points'])

# pts_array = np.array(all_points)
# l_min = pts_array.min(axis=0)
# l_max = pts_array.max(axis=0)

# bbox = (
#     utm_x_origin + l_min[0] - 20.0,
#     utm_y_origin + l_min[1] - 20.0,
#     utm_x_origin + l_max[0] + 20.0,
#     utm_y_origin + l_max[1] + 20.0
# )
# clean_bbox = [round(float(v), 3) for v in bbox]

# wcs_url = "https://www.wcs.nrw.de/geobasis/wcs_nw_dgm"
# wcs = WebCoverageService(wcs_url, version="2.0.1")
# for cid in wcs.contents:
#     print(cid)

# print(f"Downloading DGM for BBOX: {clean_bbox}")
# """got nw_dgm from for cid in wcs.contents:
#     print(cid)"""
# response = wcs.getCoverage(
#     identifier=["nw_dgm"],
#     subsets=[
#         ("x", clean_bbox[0], clean_bbox[2]),
#         ("y", clean_bbox[1], clean_bbox[3]),
#     ],
#     format="image/tiff"
# )


# with open("nrw_terrain.tif", "wb") as f:
#     f.write(response.read())
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np
import rasterio
from owslib.wcs import WebCoverageService
import ifcopenshell
import ifcopenshell.api

@dataclass
class WCSConfig:
    url: str
    version: str = "2.0.1"
    coverage_id: str = "nw_dgm"
    format: str = "image/tiff"


@dataclass
class TerrainConfig:
    margin: float = 20.0
    step: int = 1

class BBoxBuilder:
    def __init__(self, origin_x: float, origin_y: float):
        self.origin_x = origin_x
        self.origin_y = origin_y

    def from_local_points(
        self,
        points: List[Tuple[float, float]],
        margin: float
    ) -> List[float]:

        pts = np.array(points)
        if pts.size == 0:
            raise ValueError("No points provided for BBOX computation")

        min_xy = pts.min(axis=0)
        max_xy = pts.max(axis=0)

        return [
            self.origin_x + min_xy[0] - margin,
            self.origin_y + min_xy[1] - margin,
            self.origin_x + max_xy[0] + margin,
            self.origin_y + max_xy[1] + margin,
        ]


class WCSTerrainSource:
    def __init__(self, config: WCSConfig):
        self.wcs = WebCoverageService(config.url, version=config.version)
        self.coverage_id = config.coverage_id
        self.format = config.format

    def download(self, bbox: List[float], out_path: str):
        clean = [round(float(v), 3) for v in bbox]
        response = self.wcs.getCoverage(
            identifier=self.coverage_id,   # ← string only
            subsets=[
                ("x", clean[0], clean[2]),
                ("y", clean[1], clean[3]),
            ],
            format=self.format,
        )


        with open(out_path, "wb") as f:
            f.write(response.read())
class TerrainMesh:
    def __init__(self, step=1):
        self.step = step

    def from_geotiff(self, path, utm_origin_x, utm_origin_y, step=2):
        import rasterio
        import numpy as np
        with rasterio.open(path) as src:
            elevations = src.read(1)
            transform = src.transform

        n_rows, n_cols = elevations.shape
        n_rows_ds = (n_rows - 1) // step + 1
        n_cols_ds = (n_cols - 1) // step + 1

        vertices = []
        for r in range(0, n_rows, step):
            for c in range(0, n_cols, step):
                x, y = rasterio.transform.xy(transform, r, c)
                z = float(elevations[r, c])
                vertices.append([float(x - utm_origin_x), float(y - utm_origin_y), z])

        faces = []
        def idx(r, c):
            return r * n_cols_ds + c

        for r in range(n_rows_ds - 1):
            for c in range(n_cols_ds - 1):
                faces.append([idx(r, c), idx(r + 1, c), idx(r, c + 1)])
                faces.append([idx(r, c + 1), idx(r + 1, c), idx(r + 1, c + 1)])
        # print(f"Number of vertices: {len(vertices)}")
        # print(f"First 5 vertices: {vertices[:5]}")
        # print(f"Type of vertices[0]: {type(vertices[0])}, length: {len(vertices[0])}")

        # print(f"Number of faces: {len(faces)}")
        # print(f"First 5 faces: {faces[:5]}")
        # print(f"Type of faces[0]: {type(faces[0])}, length: {len(faces[0])}")

        return vertices, faces

class IFCTerrainWriter:
    def __init__(self):
        self.model = ifcopenshell.api.run("project.create_file")

        # Project
        self.project = ifcopenshell.api.run(
            "root.create_entity",
            self.model,
            ifc_class="IfcProject",
            name="Terrain Project"
        )

        # Contexts
        self.model_context = ifcopenshell.api.run(
            "context.add_context",
            self.model,
            context_type="Model"
        )
        self.body_context = ifcopenshell.api.run(
            "context.add_context",
            self.model,
            context_type="Model",
            context_identifier="Body",
            target_view="MODEL_VIEW",
            parent=self.model_context
        )

        # Site
        self.site = ifcopenshell.api.run(
            "root.create_entity",
            self.model,
            ifc_class="IfcSite",
            name="Site"
        )

        ifcopenshell.api.run(
            "geometry.edit_object_placement",
            self.model,
            product=self.site
        )
        ifcopenshell.api.run(
            "aggregate.assign_object",
            self.model,
            relating_object=self.project,
            products=[self.site]
        )

    def add_terrain(self, vertices, faces, name="Terrain"):
        terrain = ifcopenshell.api.run(
            "root.create_entity",
            self.model,
            ifc_class="IfcGeographicElement",
            name=name
        )
        ifcopenshell.api.run(
            "geometry.edit_object_placement",
            self.model,
            product=terrain,
            matrix=np.identity(4)
        )

        # --- Build the IFC Cartesian point list ---
        cartesian_points = self.model.create_entity(
            "IfcCartesianPointList3D",
            CoordList=vertices  # list of [x,y,z] floats
        )

        # --- Build IFC polygonal faces ---
        polygonal_faces = [
            self.model.create_entity("IfcIndexedPolygonalFace", [i + 1 for i in face])
            for face in faces
        ]

        # --- Create the face set ---
        face_set = self.model.create_entity(
            "IfcPolygonalFaceSet",
            Coordinates=cartesian_points,
            Faces=polygonal_faces
        )

        # --- Wrap in shape representation ---
        shape_rep = self.model.create_entity(
            "IfcShapeRepresentation",
            ContextOfItems=self.body_context,
            RepresentationType="Tessellation",
            RepresentationIdentifier="Body",
            Items=[face_set]
        )

        # Assign the representation to the terrain
        ifcopenshell.api.run(
            "geometry.assign_representation",
            self.model,
            product=terrain,
            representation=shape_rep
        )

    def write(self, path):
        self.model.write(path)


def run_pipeline(data):
    generator = data["generator"]

    points = []
    for fs in data.get("flurstueck_dict", {}).values():
        points.extend(fs["points"])

    bbox = BBoxBuilder(
        generator.origin_x,
        generator.origin_y
    ).from_local_points(points, margin=20.0)

    WCS = WCSTerrainSource(
        WCSConfig(url="https://www.wcs.nrw.de/geobasis/wcs_nw_dgm")
    )

    WCS.download(bbox, "nrw_dgm.tif")

    mesh = TerrainMesh(step=2)
    vertices, faces = mesh.from_geotiff(
    "nrw_dgm.tif",
    generator.origin_x,
    generator.origin_y,
    step=2
    )

    writer = IFCTerrainWriter()
    writer.add_terrain(vertices, faces, "NRW_DGM1")

    writer.write("site_terrain.ifc")


if __name__ == "__main__":
    from Xplan2IFC import main
    data = main()
    run_pipeline(data)
