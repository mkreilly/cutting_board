import glob
import pandas as pd
import geopandas as gpd
import shared
import numpy as np

xwalk = pd.read_csv('data/GeogXWalk2010_Blocks_MAZ_TAZ.csv')
maz_controls = pd.read_csv("data/maz_controls.csv")

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

buildings.loc[buildings.building_type == 'RT', 'building_type'] = 'HT'
buildings.loc[buildings.building_type == 'RC', 'building_type'] = 'REC'
buildings.loc[buildings.building_type == 0.0, 'building_type'] = ''
buildings = buildings.loc[~buildings.building_type.isin(['VAC', 'VA',
                                                         'VT', 'VP'])]

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
buildings["maz_id"] = buildings.maz_id.astype("int")

# there are at least 2 reasons right now to have a dummy building per maz which
# does not technically have a parcel link - 1) for group quarters and 2) for
# jobs in mazs which have no building.  instead of just randomly selecting a
# parcel to add a building record to, we leave them associated with each maz


def add_dummy_buildings_per_maz(buildings):
    dummy_df = pd.DataFrame({"maz_id": maz_controls.MAZ_ORIGINAL})
    dummy_df["name"] = "MAZ-level dummy building"
    dummy_df['building_id'] = ["MAZBLDG-" + str(d) for d in dummy_df.maz_id.values]
    df = pd.concat([buildings, dummy_df])
    #df.index.name = "building_id"
    return df


buildings = add_dummy_buildings_per_maz(buildings)

buildings.loc[buildings.name == 'MAZ-level dummy building', 'apn'] = \
    buildings.loc[buildings.name == 'MAZ-level dummy building',
                  'building_id'].str.replace('BLDG', 'PCL')

buildings.drop('geometry', axis=1).to_csv("cache/merged_buildings.csv", index=False)
buildings[['building_id', 'geometry']].to_csv("cache/buildings_geography.csv", index=False)

parcels = glob.glob("cache/*moved_attribute_parcels.csv")
juris_names = [p.replace("_moved_attribute_parcels.csv", "").
               replace("cache/", "") for p in parcels]
parcels = [gpd.read_geocsv(p) for p in parcels]
for i in range(len(parcels)):
    parcels[i]["juris_name"] = juris_names[i]
parcels = gpd.GeoDataFrame(pd.concat(parcels))

# FIXME this appends the whole juris name to the apn to make it unique
# instead this should be 4 character abbreviations
parcels["apn"] = parcels.juris_name.str.cat(
    parcels.apn.astype("str"), sep="-")

maz_pcls = xwalk.groupby('MAZ_ORIGINAL').TAZ_ORIGINAL.first()
mazpcl_dummies = buildings.loc[buildings.name == 'MAZ-level dummy building',
                               ['apn', 'maz_id']]
mazpcl_dummies['taz_id'] = mazpcl_dummies.maz_id.map(maz_pcls)
for col in parcels.columns[~parcels.columns.isin(mazpcl_dummies.columns)]:
    mazpcl_dummies[col] = np.nan
parcels = pd.concat([parcels, mazpcl_dummies])

parcels["maz_id"] = parcels.maz_id.astype("int")
parcels["taz_id"] = parcels.taz_id.fillna(-1).astype("int")

parcels[['apn', 'county_id', 'geometry', 'maz_id', 'taz_id', 'orig_apn',
         'juris_name']].to_csv("cache/merged_parcels.csv", index=False)
