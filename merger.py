import uuid
import ifcopenshell

# --- IFC GUID generator ---
_GUID_BASE64 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz__"

def generate_ifc_guid() -> str:
    """Create a valid IFC GUID (22-character Base64) from a new UUID4."""
    u = uuid.uuid4()
    b = u.bytes_le
    num = int.from_bytes(b, byteorder="big")
    chars = []
    for _ in range(22):
        chars.append(_GUID_BASE64[num & 0x3F])
        num >>= 6
    return "".join(chars)


def merge_ifc_files_one_project(target_file, source_file):
    """
    Merge source_file into target_file while preserving sites.
    Keeps only the first project from target_file, attaches all sites and products under it.
    """
    # --- 1. Pick main project ---
    main_projects = target_file.by_type("IfcProject")
    if not main_projects:
        raise ValueError("Target IFC has no IfcProject")
    main_project = main_projects[0]

    # --- 2. Geometric context ---
    contexts = target_file.by_type("IfcGeometricRepresentationContext")
    body_context = next((c for c in contexts if c.ContextType in ("Model", "Body")), contexts[0])

    old_to_new = {}

    # --- 3. Copy all products ---
    for prod in source_file.by_type("IfcProduct"):
        if prod.is_a("IfcProject"):
            continue  # skip project

        new_prod = target_file.add(prod)
        old_to_new[prod.GlobalId] = new_prod

        # Update geometry context
        if getattr(new_prod, "Representation", None):
            for rep in new_prod.Representation.Representations:
                rep.ContextOfItems = body_context

    # --- 4. Copy relationships ---
    for rel_type in ["IfcRelAggregates", "IfcRelContainedInSpatialStructure"]:
        for rel in source_file.by_type(rel_type):
            if rel_type == "IfcRelAggregates":
                new_related = [old_to_new.get(o.GlobalId, o) for o in rel.RelatedObjects]

                # If relating object is a project, map to main_project
                new_relating = rel.RelatingObject
                if new_relating.is_a("IfcProject"):
                    new_relating = main_project
                else:
                    new_relating = old_to_new.get(new_relating.GlobalId, new_relating)

                if not new_related or not new_relating:
                    continue

                target_file.createIfcRelAggregates(
                    GlobalId=generate_ifc_guid(),
                    OwnerHistory=rel.OwnerHistory,
                    Name=rel.Name,
                    Description=rel.Description,
                    RelatingObject=new_relating,
                    RelatedObjects=new_related
                )

            elif rel_type == "IfcRelContainedInSpatialStructure":
                new_related = [old_to_new.get(o.GlobalId, o) for o in rel.RelatedElements]

                new_relating = rel.RelatingStructure
                if new_relating.is_a("IfcProject"):
                    new_relating = main_project
                else:
                    new_relating = old_to_new.get(new_relating.GlobalId, new_relating)

                if not new_related or not new_relating:
                    continue

                target_file.createIfcRelContainedInSpatialStructure(
                    GlobalId=generate_ifc_guid(),
                    OwnerHistory=rel.OwnerHistory,
                    Name=rel.Name,
                    Description=rel.Description,
                    RelatedElements=new_related,
                    RelatingStructure=new_relating
                )

    return target_file


# --- Run merge ---
file1 = ifcopenshell.open("site_full.ifc")
file2 = ifcopenshell.open("site_building.ifc")

merged = merge_ifc_files_one_project(file1, file2)
merged.write("merged_one_project.ifc")

print("Merge complete: one project, multiple sites, all objects preserved.")
