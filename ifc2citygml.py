import ifcopenshell
import ifcopenshell.geom


model = ifcopenshell.open("Project1.ifc")



walls = model.by_type("IfcWall")

for wall in walls:
    if wall.Representation:
        for rep in wall.Representation.Representations:
            if rep.RepresentationIdentifier == "Axis":
                for item in rep.Items:
                    print("Wall:", wall.GlobalId)
                    print("Axis geometry:", item)