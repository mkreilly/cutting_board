import pandas as pd
import geopandas as gpd
from shared import compute_area
import sys
import time

args = sys.argv[1:]
prefix = args[0] + "_" if len(args) else ""

building_id_start_val = 1

# this file reads the split_parcels.csv and the
# buildings_linked_to_parcels.csv and splits up the attribuets
# from parcels to buildings.  Since it also removes attributes
# from the parcel tables it writes out both moved_attribute_parcels.csv
# and moved_attribute_buildings.csv

parcels = gpd.read_geocsv("cache/%ssplit_parcels_unioned.csv" % prefix,
                          index_col="apn", low_memory=False)
buildings_linked_to_parcels = gpd.read_geocsv(
    "cache/%sbuildings_linked_to_parcels.csv" % prefix, low_memory=False,
    index_col="building_id")

# this file contains mapping of blocks to mazs to tazs, but we want
# the maz to taz mapping
maz_to_taz = pd.read_csv("data/GeogXWalk2010_Blocks_MAZ_TAZ.csv").\
    drop_duplicates(subset=["MAZ_ORIGINAL"]).\
    set_index("MAZ_ORIGINAL").TAZ_ORIGINAL

parcels["taz_id"] = parcels.maz_id.map(maz_to_taz)

buildings_linked_to_parcels['building:levels'] = pd.to_numeric(
    buildings_linked_to_parcels['building:levels'], errors='coerce')


def drop_parcel_attributes(parcels):
    # used in two place so make a function
    return parcels[['county_id', 'geometry', 'maz_id', 'taz_id', 'orig_apn']]


def assign_parcel_attributes_to_buildings(buildings, parcels):
    # attributes of the first parcel get applied to the buildings - if
    # we did this right, the attributes of all subparcels will be the
    # same - we pass in the parcels in order to set the schema for all
    # the parcels.  test this a little bit:
    for col in ['bldg_sqft', 'res_units', 'nres_sqft']:
        assert len(parcels) == 1 or \
            parcels[col].fillna(0).describe()['std'] == 0
    # take attributes of the first parcel
    parcel = parcels.iloc[0]

    # drop address and amenity - they're great columns but infrequently used
    buildings = buildings[[
        'name', 'geometry', 'apn', 'building:levels', 'building']]
    buildings = buildings.rename(columns={
        'building:levels': 'stories',
        'building': 'osm_building_type'})
    buildings['calc_area'] = compute_area(buildings).round()

    # generated buildings don't count as small sheds - geometry is made up
    small_buildings_mask = \
        (buildings.name.astype("str") != "Generated from parcel centroid") & \
        (buildings.calc_area < 80)

    # we call a building a shed if it's less than 50 meters large and it
    # doesn't get any of the parcel data
    small_buildings = buildings[small_buildings_mask].copy()
    small_buildings["small_building"] = True
    large_buildings = buildings[~small_buildings_mask].copy()
    large_buildings["small_building"] = False

    large_buildings["stories"] = large_buildings.stories.fillna(
        parcel.stories).fillna(1).clip(1)
    large_buildings["year_built"] = parcel.year_built
    large_buildings["building_type"] = parcel.dev_type

    # account for height
    built_area = large_buildings.calc_area * \
        large_buildings.stories.astype('float')
    # get built area proportion in each building footprint
    proportion_built_area = built_area / built_area.sum()

    large_buildings["building_sqft"] = \
        (proportion_built_area * parcel.bldg_sqft).round()
    large_buildings["residential_units"] = \
        (proportion_built_area * parcel.res_units).round()
    large_buildings["non_residential_sqft"] = \
        (proportion_built_area * parcel.nres_sqft).round()

    return pd.concat([small_buildings, large_buildings]),\
        drop_parcel_attributes(parcels)


def make_dummy_building(parcels):
    global building_id_start_val

    # when there's more than one parcel, we put the dummy building on the
    # biggest sub parcel
    parcel = parcels.sort_values(by="calc_area", ascending=False).head(1)

    if parcels.bldg_sqft.fillna(0).sum() == 0 and \
            parcels.res_units.fillna(0).sum() == 0:
        # there's no reason to make a dummy building if the attributes aren't
        # there
        return pd.DataFrame(), drop_parcel_attributes(parcels)

    parcel.crs = {'init': 'epsg:4326'}
    parcel = parcel.to_crs(epsg=3857)  # switch to meters
    circle = parcel.centroid.buffer(5).values[0]  # buffer a circle in meters
    parcel = parcel.to_crs(epsg=4326)  # back to lat-lng
    building = gpd.GeoDataFrame({
        'name': ['Generated from parcel centroid'],
        'geometry': [circle],
        'apn': [parcel.index[0]],
        'building:levels': [1],
        'building': ['yes']
    }, index=[building_id_start_val])
    building_id_start_val += 1
    building.crs = {'init': 'epsg:3857'}
    building = building.to_crs(epsg=4326)
    return assign_parcel_attributes_to_buildings(building, parcels)

new_buildings_list = []
new_parcel_list = []

cnt = 0

grps = parcels.groupby("orig_apn")
total_cnt = len(grps)
# iterate over parcels (not sub-parcels)
for index, shared_apn_parcels in grps:
    # get all buildngs that are on any subparcel of this parcel
    buildings = buildings_linked_to_parcels[
        buildings_linked_to_parcels.apn.isin(shared_apn_parcels.index)]

    if len(buildings) == 0:
        new_buildings, new_parcels = make_dummy_building(shared_apn_parcels)
    else:
        new_buildings, new_parcels = assign_parcel_attributes_to_buildings(
            gpd.GeoDataFrame(buildings), shared_apn_parcels)

    new_buildings_list.append(new_buildings)
    new_parcel_list.append(new_parcels)

    cnt += 1
    if cnt % 250 == 0:
        print "Finished %d of %d" % (cnt, total_cnt)


new_parcels = pd.concat(new_parcel_list)
new_buildings = pd.concat(new_buildings_list)
new_buildings.index.name = "building_id"

# make sure we didn't end up with any duplicate building ids
assert new_buildings.index.value_counts().values[0] == 1

new_parcels.to_csv("cache/%smoved_attribute_parcels.csv" % prefix)
new_buildings.to_csv("cache/%smoved_attribute_buildings.csv" % prefix)
