# import ifcopenshell

# file1 = ifcopenshell.open("site_full.ifc")
# file2 = ifcopenshell.open("combined_siteplan_data.ifc")

# # Merge file2 into file1
# for e in file2:
#     if e.is_a() != "IfcProject":
#         file1.add(e)

# file1.write("combined2ifcs.ifc")
# import ifcopenshell
# import ifcopenshell.guid

# file1 = ifcopenshell.open("siteF_BBBL.ifc")
# file2 = ifcopenshell.open("combined_siteplan_data.ifc")# site + site objects + buildings

# main_site = file1.by_type("IfcSite")[0]
# copied = {}

# def copy_building(building, parent_site):
#     """Copy a building and its children under an existing site."""
#     if building.id() in copied:
#         return copied[building.id()]

#     new_building = file2.add(building)
#     copied[building.id()] = new_building

#     file2.create_entity(
#         "IfcRelAggregates",
#         GlobalId=ifcopenshell.guid.new(),
#         RelatingObject=parent_site,
#         RelatedObjects=[new_building]
#     )
#     for rel in getattr(building, "IsDecomposedBy", []):
#         for child in rel.RelatedObjects:
#             copy_building(child, new_building)

#     for rel in getattr(building, "ContainsElements", []):
#         for child in rel.RelatedElements:
#             copy_building(child, new_building)

#     return new_building
# for building in file1.by_type("IfcBuilding"):
#     copy_building(building, main_site)

# file2.write("merged_.ifc")
# print("Merge complete: merged.ifc")
import ifcopenshell

file1 = ifcopenshell.open("site_full.ifc")
file2 = ifcopenshell.open("combined_siteplan_data.ifc")

target_contexts = file1.by_type("IfcGeometricRepresentationContext")
body_context = next((c for c in target_contexts if c.ContextType == "Model" or c.ContextType == "Body"), target_contexts[0])

for element in file2.by_type("IfcProduct"):
    if element.is_a("IfcProject"): continue
    
    new_el = file1.add(element)
    
    # FIX: Re-map the geometry context so it isn't "lost"
    if new_el.Representation:
        for rep in new_el.Representation.Representations:
            rep.ContextOfItems = body_context

# 3. Save
file1.write("merged_manual_fix.ifc")
print("Merge complete with manual context re-mapping.")
