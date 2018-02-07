import glob
import pandas as pd
import numpy as np

buildings = glob.glob("cache/*buildings_match_controls.csv")
juris_names = [b.replace("_buildings_match_controls.csv", "").
               replace("cache/", "") for b in buildings]
buildings = [pd.read_csv(b) for b in buildings]
for i in range(len(buildings)):
    buildings[i]["juris_name"] = juris_names[i]
buildings = pd.concat(buildings)

# the foreign key apn has to have the transformation we apply to the parcel
# apn below
# FIXME this appends the whole juris name to the apn to make it unique
# instead this should be 4 character abbreviations
buildings["apn"] = buildings.juris_name.str.cat(
    buildings.apn.astype("str"), sep="-")

# we assign counting numbers to building ids when we create a circular
# buildling footprint on a parcel centroid.  when we take them from osm
# we use the osm_id.  So the osm_ids are unique but the circular building
# ids are duplicate across cities.  Fortunately the osm buildings ids are
# very large and we can pick an arbitrary cutoff and create globally
# unique building ids for those
mask = pd.to_numeric(buildings.building_id, errors="coerce") < 100000
unique_buildings = buildings[~mask].copy()
dup_buildings = buildings[mask].copy()

dup_buildings["building_id"] = np.arange(len(dup_buildings))+1
buildings = pd.concat([unique_buildings, dup_buildings])

buildings["osm_building_id"] = buildings.building_id
buildings["building_id"] = np.arange(len(buildings))+1

buildings.to_csv("cache/merged_buildings.csv", index=False)

parcels = glob.glob("cache/*moved_attribute_parcels.csv")
juris_names = [p.replace("_moved_attribute_parcels.csv", "").
               replace("cache/", "") for p in parcels]
parcels = [pd.read_csv(p) for p in parcels]
for i in range(len(parcels)):
    parcels[i]["juris_name"] = juris_names[i]
parcels = pd.concat(parcels)

mask = pd.to_numeric(parcels.apn, errors="coerce") < 100000
unique_parcels = parcels[~mask].copy()
dup_parcels = parcels[mask].copy()

dup_parcels["apn"] = np.arange(len(dup_parcels))+1
parcels = pd.concat([unique_parcels, dup_parcels])

# FIXME this appends the whole juris name to the apn to make it unique
# instead this should be 4 character abbreviations
parcels["apn"] = parcels.juris_name.str.cat(
    parcels.apn.astype("str"), sep="-")

parcels.to_csv("cache/merged_parcels.csv", index=False)
