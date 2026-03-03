import os
import ifcopenshell
import ifcopenshell.geom

from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_REVERSED, TopAbs_WIRE
from OCC.Core.TopoDS import topods, TopoDS_Compound
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
from OCC.Core.GeomAbs import GeomAbs_Plane
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.GProp import GProp_GProps
from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Lin
from OCC.Core.BRep import BRep_Builder, BRep_Tool
from OCC.Core.BRepTools import BRepTools_WireExplorer
from OCC.Core.IntCurvesFace import IntCurvesFace_ShapeIntersector

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

def load_ifc(filename):
    cwd = os.getcwd()
    path = os.path.join(cwd, "model", filename)
    return ifcopenshell.open(path)

def get_elements_by_types(ifc_file, types):
    elements = []
    for t in types:
        elements.extend(ifc_file.by_type(t))
    return elements

def create_shapes(elements, settings):
    shapes = []
    for element in elements:
        shape = ifcopenshell.geom.create_shape(settings, element)
        shapes.append((element, shape.geometry))
    return shapes

def build_compound(shapes):
    builder = BRep_Builder()
    compound = TopoDS_Compound()
    builder.MakeCompound(compound)

    for _, shape in shapes:
        builder.Add(compound, shape)

    return compound

def classify_faces(shapes, compound):

    intersector = IntCurvesFace_ShapeIntersector()
    intersector.Load(compound, 1e-6)

    exterior_faces = []

    for element, solid in shapes:

        print(f"\nProcessing: {element.GlobalId}")

        explorer = TopExp_Explorer(solid, TopAbs_FACE)

        while explorer.More():

            face = topods.Face(explorer.Current())
            adaptor = BRepAdaptor_Surface(face)
            if adaptor.GetType() == GeomAbs_Plane:
                props = GProp_GProps()
                brepgprop.SurfaceProperties(face, props)
                center = props.CentreOfMass()
                normal = adaptor.Plane().Axis().Direction()

                if face.Orientation() == TopAbs_REVERSED:
                    normal.Reverse()
                ray_origin = gp_Pnt(
                    center.X() + normal.X() * 0.01,
                    center.Y() + normal.Y() * 0.01,
                    center.Z() + normal.Z() * 0.01
                )

                ray = gp_Lin(ray_origin, normal)

                # Cast ray infinitely
                intersector.Perform(ray, 0, 1e10)
                if intersector.NbPnt() == 0:
                    exterior_faces.append((element.GlobalId, face))

            explorer.Next()
    return exterior_faces
def extract_coordinates(exterior_faces):

    for i, (element_id, face) in enumerate(exterior_faces):

        exp = TopExp_Explorer(face, TopAbs_WIRE)
        if not exp.More():
            continue

        wire = topods.Wire(exp.Current())
        wire_explorer = BRepTools_WireExplorer(wire)

        points = []

        while wire_explorer.More():
            p = BRep_Tool.Pnt(wire_explorer.CurrentVertex())
            points.append(f"{p.X():.3f} {p.Y():.3f} {p.Z():.3f}")
            wire_explorer.Next()

        if points:
            if points[0] != points[-1]:
                points.append(points[0])

            pos_list = " ".join(points)

            print("Element ID:", element_id)
            print(f"<gml:posList>{pos_list}</gml:posList>")

def plot_exterior_faces(exterior_faces):

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    all_polygons = []

    for element_id, face in exterior_faces:

        exp = TopExp_Explorer(face, TopAbs_WIRE)

        while exp.More():

            wire = topods.Wire(exp.Current())
            wire_explorer = BRepTools_WireExplorer(wire)

            points = []

            while wire_explorer.More():
                p = BRep_Tool.Pnt(wire_explorer.CurrentVertex())
                points.append([p.X(), p.Y(), p.Z()])
                wire_explorer.Next()

            if len(points) >= 3:
                all_polygons.append(points)

            exp.Next()

    # Create 3D polygon collection
    poly3d = Poly3DCollection(all_polygons, alpha=0.5)
    ax.add_collection3d(poly3d)

    # Auto scale
    all_points = [pt for poly in all_polygons for pt in poly]
    xs = [p[0] for p in all_points]
    ys = [p[1] for p in all_points]
    zs = [p[2] for p in all_points]

    ax.set_xlim(min(xs), max(xs))
    ax.set_ylim(min(ys), max(ys))
    ax.set_zlim(min(zs), max(zs))

    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")

    plt.show()
def main():
    ifc_file = load_ifc("building_wo_site.ifc")
    elements = get_elements_by_types(
        ifc_file,
        ["IfcWall", "IfcWallStandardCase", "IfcRoof","IfcSlab"]
    )
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    settings.set(settings.USE_PYTHON_OPENCASCADE, True)

    shapes = create_shapes(elements, settings)

    compound = build_compound(shapes)

    exterior_faces = classify_faces(shapes, compound)
    plot_exterior_faces(exterior_faces)
    extract_coordinates(exterior_faces)


if __name__ == "__main__":
    main()

# import os
# import ifcopenshell
# import ifcopenshell.geom

# from OCC.Core.TopExp import TopExp_Explorer
# from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_REVERSED, TopAbs_WIRE
# from OCC.Core.TopoDS import topods, TopoDS_Compound
# from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
# from OCC.Core.GeomAbs import GeomAbs_Plane
# from OCC.Core.BRepGProp import brepgprop
# from OCC.Core.GProp import GProp_GProps
# from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Lin
# from OCC.Core.BRep import BRep_Builder, BRep_Tool
# from OCC.Core.BRepTools import BRepTools_WireExplorer
# from OCC.Core.IntCurvesFace import IntCurvesFace_ShapeIntersector

# def load_ifc_model(filename: str):
#     cwd = os.getcwd()
#     ifc_path = os.path.join(cwd, "model", filename)
#     return ifcopenshell.open(ifc_path)

# def get_building_elements(ifc_file):
#     walls = ifc_file.by_type("IfcWall") + ifc_file.by_type("IfcWallStandardCase")
#     return walls

# def create_wall_shapes(walls, settings):
#     shapes = []
#     for wall in walls:
#         shape = ifcopenshell.geom.create_shape(settings, wall)
#         shapes.append(shape.geometry)
#     return shapes

# def build_compound(shapes):
#     builder = BRep_Builder()
#     compound = TopoDS_Compound()
#     builder.MakeCompound(compound)

#     for shape in shapes:
#         builder.Add(compound, shape)

#     return compound

# def classify_faces(walls, wall_shapes, compound):
#     intersector = IntCurvesFace_ShapeIntersector()
#     intersector.Load(compound, 1e-6)

#     exterior_faces = []
#     interior_faces = []

#     for wall, solid in zip(walls, wall_shapes):
#         print(f"\nWall: {wall.GlobalId}")

#         explorer = TopExp_Explorer(solid, TopAbs_FACE)

#         while explorer.More():
#             face = topods.Face(explorer.Current())
#             adaptor = BRepAdaptor_Surface(face)

#             if adaptor.GetType() == GeomAbs_Plane:
#                 normal = adaptor.Plane().Axis().Direction()

#                 if face.Orientation() == TopAbs_REVERSED:
#                     normal.Reverse()

#                 # Only consider vertical faces
#                 if abs(normal.Z()) < 0.01:

#                     props = GProp_GProps()
#                     brepgprop.SurfaceProperties(face, props)
#                     center = props.CentreOfMass()

#                     # Ray slightly offset from surface
#                     ray_origin = gp_Pnt(
#                         center.X() + normal.X() * 0.01,
#                         center.Y() + normal.Y() * 0.01,
#                         center.Z() + normal.Z() * 0.01
#                     )

#                     ray = gp_Lin(ray_origin, gp_Dir(normal.X(), normal.Y(), normal.Z()))
#                     intersector.Perform(ray, 0, 1e10)

#                     if intersector.NbPnt() > 0:
#                         print("   -> Interior face")
#                         interior_faces.append(face)
#                     else:
#                         print("   -> Exterior face")
#                         exterior_faces.append((wall.GlobalId, face))

#             explorer.Next()

#     return exterior_faces, interior_faces

# def extract_face_coordinates(exterior_faces):
#     for i, (wall_id, face) in enumerate(exterior_faces):

#         exp = TopExp_Explorer(face, TopAbs_WIRE)
#         if not exp.More():
#             continue

#         wire = topods.Wire(exp.Current())
#         wire_explorer = BRepTools_WireExplorer(wire)

#         points = []

#         while wire_explorer.More():
#             p = BRep_Tool.Pnt(wire_explorer.CurrentVertex())
#             points.append(f"{p.X():.3f} {p.Y():.3f} {p.Z():.3f}")
#             wire_explorer.Next()

#         if points:
#             if points[0] != points[-1]:
#                 points.append(points[0])

#             pos_list = " ".join(points)

#             print("Wall ID:", wall_id)
#             print(f"Face {i}")
#             print(f"<gml:posList>{pos_list}</gml:posList>")

# def main():

#     # Load model
#     ifc_file = load_ifc_model("smallhouse.ifc")

#     # Get walls
#     walls = get_building_elements(ifc_file)

#     # Geometry settings
#     settings = ifcopenshell.geom.settings()
#     settings.set(settings.USE_WORLD_COORDS, True)
#     settings.set(settings.USE_PYTHON_OPENCASCADE, True)

#     # Create shapes
#     wall_shapes = create_wall_shapes(walls, settings)

#     # Build compound
#     compound = build_compound(wall_shapes)

#     # Classify faces
#     exterior_faces, interior_faces = classify_faces(walls, wall_shapes, compound)

#     # Extract coordinates
#     extract_face_coordinates(exterior_faces)

# if __name__ == "__main__":
#     main()