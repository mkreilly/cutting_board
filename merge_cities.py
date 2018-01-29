import glob
import pandas as pd
import numpy as np

buildings = glob.glob("cache/*buildings_match_controls.csv")
buildings = [pd.read_csv(b) for b in buildings]
buildings = pd.concat(buildings)

# we assign counting numbers to building ids when we create a circular
# buildling footprint on a parcel centroid.  when we take them from osm
# we use the osm_id.  So the osm_ids are unique but the circular building
# ids are duplicate across cities.  Fortunately the osm buildings ids are
# very large and we can pick an arbitrary cutoff and create globally
# unique building ids for those
mask = pd.to_numeric(buildings.building_id, errors="coerce") > 100000
unique_buildings = buildings[mask].copy()
dup_buildings = buildings[~mask].copy()

dup_buildings["building_id"] = np.arange(len(dup_buildings))+1
buildings = pd.concat([unique_buildings, dup_buildings])

still_duplicate_buildings = buildings.set_index("building_id").loc["484538827"]
still_duplicate_buildings.to_csv("foo.csv")

buildings.to_csv("bayarea_buildings.csv", index=False)


parcels = glob.glob("cache/*moved_attribute_parcels.csv")
juris_names = [p.replace("_moved_attribute_parcels.csv", "").
               replace("cache/", "") for p in parcels]
parcels = [pd.read_csv(p) for p in parcels]
for i in range(len(parcels)):
    parcels[i]["juris_name"] = juris_names[i]
parcels = pd.concat(parcels)

print parcels.apn.value_counts()
parcels[parcels.apn.isin(still_duplicate_buildings.apn)].to_csv("foo2.csv")

parcels.to_csv("bayarea_parcels.csv", index=False)
