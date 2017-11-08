import geopandas as gpd
import pandas as pd
import shared
import osmnx

print "Reading data"
buildings = gpd.read_geocsv(
    "cache/buildings_match_controls.csv", index_col="building_id")
parcels = gpd.read_geocsv("cache/moved_attribute_parcels.csv", index_col="apn")
establishments = gpd.read_geocsv("establishments.csv", index_col="duns_number")
mazs = gpd.read_geocsv("mazs.csv", index_col="maz_id")

berkeley = osmnx.gdf_from_place("Berkeley, California")
berkeley_mazs = gpd.sjoin(mazs, berkeley).drop("index_right", axis=1)

print "Intersecting with buildings"
# goal here is to create a dictionary where keys are establishments ids and
# values are possible building_ids - this lets us write a function to assign
# jobs to buildings.  when we have a match to a parcel, we list the buildings
# on that parcel; when we have a match to a maz, we list the buildings in
# that maz.
establishments_intersect_buildings = gpd.sjoin(establishments, buildings)
establishments_possible_buildings = {
    k: [v]
    for k, v
    in establishments_intersect_buildings.index_right.to_dict().iteritems()
}


print "Intersecting with parcels"
# intersect establishments and parcels, and drop intersections from buildings
parcels["num_buildings"] = \
    buildings.apn.value_counts().reindex(parcels.index).fillna(0)
# don't bother intersect with parcels which don't have buildings
# we'll cover those with mazs
establishments_intersect_parcels = gpd.sjoin(
    establishments, parcels[parcels.num_buildings > 0])
establishments_intersect_parcels.drop(establishments_possible_buildings.keys(),
                                      inplace=True, errors='ignore')
del parcels["num_buildings"]

establishments_possible_buildings.update({
    establishment_id: buildings[buildings.apn == apn].index
    for establishment_id, apn
    in establishments_intersect_parcels.index_right.iteritems()
})


print "Intersecting with mazs"
# intersect establishments from mazs, and drop intersections from buildings
# and parcels
berkeley_mazs["num_buildings"] = buildings.maz_id.value_counts().\
    reindex(berkeley_mazs.index).fillna(0)
establishments_intersect_mazs = gpd.sjoin(
    establishments, berkeley_mazs[berkeley_mazs.num_buildings > 0])
establishments_intersect_mazs.drop(establishments_possible_buildings.keys(),
                                   inplace=True, errors='ignore')
del berkeley_mazs["num_buildings"]

establishments_possible_buildings.update({
    establishment_id: buildings[buildings.maz_id == maz_id].index
    for establishment_id, maz_id
    in establishments_intersect_mazs.index_right.iteritems()
})


def assign_establishments_to_buildings(establishments_possible_buildings):
    def assign_establishment_to_buildings(eid, building_ids):
        if len(buildings) == 1:
            return building_ids[0]

        possible_buildings = buildings.loc[building_ids]

        if possible_buildings.non_residential_sqft.sum() == 0:
            # there's no non-res buildings - assign to random building
            return possible_buildings.sample().index[0]

        return possible_buildings.sample(
            weights="non_residential_sqft").index[0]

    return pd.Series({
        eid: assign_establishment_to_buildings(eid, buildings)
        for eid, buildings in establishments_possible_buildings.iteritems()
    })


print "Picking buildings from among options"
establishments["building_id"] = \
    assign_establishments_to_buildings(establishments_possible_buildings)
berkeley_establishments = establishments[establishments.building_id.notnull()]

outdf = berkeley_establishments.loc[
    berkeley_establishments.index.repeat(
        berkeley_establishments.local_employment)
][["PBA_category", "building_id"]]


print "Writing data"
outdf.index.name = "establishment_id"
outdf.reset_index(inplace=True)
outdf.index.name = "job_id"
outdf.index = outdf.index + 1  # starts at zero
outdf.to_csv("jobs.csv")
