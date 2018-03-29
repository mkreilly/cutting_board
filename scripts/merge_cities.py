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

buildings.drop("building_id", axis=1, inplace=True)
buildings["maz_id"] = buildings.maz_id.astype("int")

# there are at least 2 reasons right now to have a dummy building per maz which
# does not technically have a parcel link - 1) for group quarters and 2) for
# jobs in mazs which have no building.  instead of just randomly selecting a
# parcel to add a building record to, we leave them associated with each maz


def add_dummy_buildings_per_maz(buildings):
    dummy_df = pd.DataFrame({"maz_id": maz_controls.MAZ_ORIGINAL})
    dummy_df["name"] = "MAZ-level dummy building"
    dummy_df['maz_building_id'] = [
        "MAZBLDG-" + str(d) for d in dummy_df.maz_id.values]
    df = pd.concat([buildings, dummy_df])
    return df

buildings = add_dummy_buildings_per_maz(buildings)

buildings.loc[buildings.name == 'MAZ-level dummy building', 'apn'] = \
    buildings.loc[buildings.name == 'MAZ-level dummy building',
                  'maz_building_id'].str.replace('BLDG', 'PCL')

buildings.reset_index(drop=True, inplace=True)
buildings.index += 1

buildings.drop('geometry', axis=1).to_csv(
     "cache/merged_buildings.csv", index_label="building_id")
buildings[['geometry']].to_csv(
     "cache/buildings_geometry.csv", index_label="building_id")
print "Finished writing buildings"

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
