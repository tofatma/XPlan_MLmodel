import uuid
import ifcopenshell
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

def merge_ifc_files(target_file, source_file):
    """
    Merge source_file into target_file while preserving hierarchy.
    """
    contexts = target_file.by_type("IfcGeometricRepresentationContext")
    body_context = next((c for c in contexts if c.ContextType in ("Model", "Body")), contexts[0])

    old_to_new = {}

    # Copy all products except project itself
    for prod in source_file.by_type("IfcProduct"):
        if prod.is_a("IfcProject"):
            continue
        new_prod = target_file.add(prod)
        old_to_new[prod.GlobalId] = new_prod

        if new_prod.Representation:
            for rep in new_prod.Representation.Representations:
                rep.ContextOfItems = body_context

    # Copy relationships
    for rel in source_file.by_type("IfcRelAggregates"):
        new_related = [old_to_new.get(o.GlobalId, o) for o in rel.RelatedObjects]
        new_relating = old_to_new.get(rel.RelatingObject.GlobalId, rel.RelatingObject)
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

    for rel in source_file.by_type("IfcRelContainedInSpatialStructure"):
        new_related = [old_to_new.get(o.GlobalId, o) for o in rel.RelatedElements]
        new_relating = old_to_new.get(rel.RelatingStructure.GlobalId, rel.RelatingStructure)
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

file1 = ifcopenshell.open("site_full.ifc")
file2 = ifcopenshell.open("combined_siteplan_data.ifc")

merged = merge_ifc_files(file1, file2)
merged.write("merged_fixed.ifc")

print("Merge complete with hierarchy preserved.")
