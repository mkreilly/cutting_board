# this module is used to slice parcels based to micro-transportation
# zones and building footprints
# more information is available in the README of this repo
# there are 3 major steps
# 1) split on maz boundaries
# 2) join to building footprints
# 3) move parcel attributes (building sizes) to footprints proportionally

import pandas as pd
import geopandas as gpd
import numpy as np
from shapely import wkt
import time

print "Reading buildings"
buildings = gpd.read_geocsv("buildings.csv", low_memory=False)
# XXX we should really have the osm_ids for this shouldn't we?
buildings["building_id_tmp"] = buildings.index

# now we have our new parcels (the split ones and want to join buildings
joined_buildings = gpd.sjoin(buildings, split_parcels)


# ### identify overlaps of buildings and split parcels
cnts = joined_buildings.index.value_counts().loc[lambda x: x > 1]
overlaps = joined_buildings.loc[cnts.index].copy()
print len(cnts)
len(overlaps)


def compute_overlap_areas(overlaps, overlapees):
    '''
    After a spatial join is done, this computes the actual area of the overlap.
    overlaps is the result of the spatial join (which contains geometry for the overlaper)
    overlapees is the geometry of the right side of the join
    the "index_right" column of overlaps should be the index of overlapees
    '''
    total_overlaps = len(overlaps)
    cnt = 0
    overlap_area = []
    for index, overlap in overlaps.iterrows():
        overlapee = overlapees.loc[overlap.index_right]
        #ax = overlaper.head(1).plot(alpha=.5)
        #overlapee.loc[overlaper.index_right].tail(1).plot(ax=ax, color="red")
        try:
            overlap_poly = gpd.overlay(gpd.GeoDataFrame([overlap]), gpd.GeoDataFrame([overlapee]), how="intersection")
        except:
            overlap_area.append(np.nan)
            print "Failed:", index
            continue
        cnt += 1
        if cnt % 25 == 0:
            print "Finished %d of %d" % (cnt, total_overlaps)
        if len(overlap_poly) == 0:
            overlap_area.append(0)
            continue
        overlap_area.append(compute_area(overlap_poly).values[0])

    return pd.Series(overlap_area, index=overlaps.index)

print time.ctime()
overlapping_areas = compute_overlap_areas(overlaps, split_parcels)
print time.ctime()

# write it out
pd.DataFrame({"overlapping_areas": overlapping_areas}).to_csv("overlapping_areas.csv")

overlapping_areas


# #### Compute the max overlapping percent area for each building footprint - I mean, the percentage overlap for the parcel with which a building overlaps the most

# In[ ]:

overlapping_area = pd.read_csv("overlapping_areas.csv", index_col="index").overlapping_areas
overlaps["overlapping_area"] = overlapping_area
large_overlaps = overlaps[overlaps.overlapping_area.fillna(0) > .03].copy()
overlapping_area = large_overlaps.overlapping_area
overlapping_pct_area = overlapping_area / overlapping_area.groupby(overlapping_area.index).transform('sum')
large_overlaps["overlapping_pct_area"] = overlapping_pct_area
max_overlapping_pct_area = overlapping_pct_area.groupby(overlapping_pct_area.index).max()
large_overlaps["max_overlapping_pct_area"] = max_overlapping_pct_area 


# #### A pretty high proportion of building footprints touch at least two parcels - these are the "overlaps"

# In[ ]:

print len(buildings)
print len(joined_buildings.index.value_counts())
print len(large_overlaps.index.value_counts())


# #### These are the building footprints which only match one parcel - we assign them to that parcel

# In[ ]:

s = joined_buildings.index.value_counts().loc[lambda x: x == 1]
non_overlaps = joined_buildings.loc[s.index].copy()
len(non_overlaps)


# #### We then take the building footprints which match to multiple parcels, but to one parcel greater than a given threshold

# In[ ]:

threshold = .65
overlaps_greater_than_threshold = large_overlaps.query("overlapping_pct_area >= %f" % threshold)
len(overlaps_greater_than_threshold)


# #### concat the two

# In[ ]:

problematic_overlaps = large_overlaps.query("max_overlapping_pct_area < %f" % threshold)
problematic_overlaps = problematic_overlaps.sort_values(by="max_overlapping_pct_area", ascending=False)
len(problematic_overlaps.index.value_counts())


# In[ ]:

def are_these_same_parcels(parcel_overlaps):
    # this looks to see if the data on the parcels looks like multiple buildings
    # or whether it looks like a single building with 0's on the other parcels
    def majority_zero_values(s):
        return len(s[s == 0]) / float(len(s)) > .5

    return majority_zero_values(parcel_overlaps.bldg_sqft) and           majority_zero_values(parcel_overlaps.nres_sqft) and           majority_zero_values(parcel_overlaps.res_units)

def deal_with_problematic_overlap(index, building_overlaps, split_parcels):
    area = compute_area(building_overlaps.head(1)).values[0]
    # sliver threshold varies by size of the building, for small parcels we
    # want to bias towards not splitting it up, for large building it might
    # make sense to split it up more frequently
    sliver_cutoff = .25 if area < 500 else .03
    
    title = ""
    keep = building_overlaps
    building_overlaps = building_overlaps.query("overlapping_pct_area > %f" % sliver_cutoff)
    if len(building_overlaps) == 0:
        # no non-slivers, but there mostly look like apartment buildings, townhomes, and such
        # just put all the footprints back in
        building_overlaps = keep

    parcel_overlaps = split_parcels.loc[building_overlaps.index_right]
    
    if len(building_overlaps) == 1:
        title = "Single parcel"
    elif are_these_same_parcels(parcel_overlaps):
        title = "Union parcels"
    else:
        title = "Split building"
        
    return title, building_overlaps
    
problematic_overlaps["calc_area"] = compute_area(problematic_overlaps)
# drop small footprints (these are like storage sheds, believe it or not)
print "Dropping %d small footprints" %     len(problematic_overlaps[problematic_overlaps.calc_area <= 200].index.value_counts())
large_problematic_overlaps = problematic_overlaps[problematic_overlaps.calc_area > 200]

fixes = {}
cnt = 0
total_cnt = len(large_problematic_overlaps.index.unique())
for index in large_problematic_overlaps.index.unique():
    cnt += 1
    if cnt % 25 == 0:
        print "Finished %d of %d" % (cnt, total_cnt)
    overlap_type, building_overlaps =         deal_with_problematic_overlap(index, large_problematic_overlaps.loc[index],
                                      split_parcels)
    fixes.setdefault(overlap_type, [])
    fixes[overlap_type].append(building_overlaps)    


# In[ ]:

chopped_up_buildings = []
cnt = 0
total_cnt = len(fixes['Split building'])
for building_sets in fixes['Split building']:
    cnt += 1
    if cnt % 25 == 0:
        print "Finished %d of %d" % (cnt, total_cnt)
    out = gpd.overlay(
        # we go back to the original buildings set in order to drop the joined columns
        buildings.loc[building_sets.index].head(1),
        split_parcels.loc[building_sets.index_right].reset_index(),
        how='intersection')
    
    # we're splitting up building footprints, so append "-1", "-2", "-3" etc.
    out["building_id_tmp"] = out.building_id_tmp.astype("string").str.        cat(['-'+str(x) for x in range(1, len(out) + 1)])
    
    chopped_up_buildings.append(out)

chopped_up_buildings = pd.concat(chopped_up_buildings)


# In[ ]:

buildings_linked_to_parcels = gpd.GeoDataFrame(pd.concat([
    non_overlaps,
    overlaps_greater_than_threshold,
    chopped_up_buildings,
    pd.concat(fixes['Single parcel'])
    # leaving out union parcels for now because they're more complicated
]))

# these are not quite the same, but they should be close
# the 2nd number may be lower than the 1st because we drop lots of very small building footprints
# then the number is larger because we split many building footprints on parcel boundaries
# in the end, either one may be larger than the other
print len(joined_buildings.index.value_counts())
print len(buildings_linked_to_parcels)
buildings_linked_to_parcels["apn"] = buildings_linked_to_parcels.index_right
buildings_linked_to_parcels = buildings_linked_to_parcels[list(buildings.columns) + ["apn"]]

s = buildings_linked_to_parcels.apn.notnull()
assert s.value_counts()[True] == len(s)

buildings_linked_to_parcels.to_csv("buildings_linked_to_parcels.csv", index=False)


# ## Now we work towards splitting the attribute up correctly

# In[2]:

parcels = gpd.read_geocsv("split_parcels.csv", index_col="apn")
# this file contains mapping of blocks to mazs to tazs, but we want the maz to taz mapping
maz_to_taz = pd.read_csv("GeogXWalk2010_Blocks_MAZ_TAZ.csv").    drop_duplicates(subset=["MAZ_ORIGINAL"]).set_index("MAZ_ORIGINAL").TAZ_ORIGINAL
parcels["taz_id"] = parcels.maz_id.map(maz_to_taz)
buildings_linked_to_parcels = gpd.read_geocsv(
    "buildings_linked_to_parcels.csv", low_memory=False, index_col="building_id_tmp")


# In[3]:

import osmnx
berkeley = osmnx.gdf_from_places(["Berkeley, CA"])
berkeley


# In[4]:

buildings_linked_to_parcels['building:levels'] =     pd.to_numeric(buildings_linked_to_parcels['building:levels'], errors='coerce')


# In[5]:

berkeley_parcels = gpd.sjoin(parcels, berkeley)
print len(parcels)
print len(berkeley_parcels)


# In[6]:

def drop_parcel_attributes(parcels):
    # used in two place so make a function
    return parcels[['county_id', 'geometry', 'maz_id', 'taz_id', 'orig_apn']]

def assign_parcel_attributes_to_buildings(buildings, parcels):
    # attributes of the first parcel get applied to the buildings - if
    # we did this right, the attributes of all subparcels will be the
    # same - we pass in the parcels in order to set the schema for all
    # the parcels.  test this a little bit:
    for col in ['bldg_sqft', 'res_units', 'nres_sqft']:
        assert len(parcels) == 1 or parcels[col].fillna(0).describe()['std'] == 0
    # take attributes of the first parcel
    parcel = parcels.iloc[0]
        
    # drop address and amenity - they're great columns but infrequently used
    buildings = buildings[['name', 'geometry', 'apn', 'building:levels', 'building']]
    buildings = buildings.rename(columns={'building:levels': 'stories', 'building': 'osm_building_type'})
    buildings['calc_area'] = compute_area(buildings).round()
    
    # we call a building a shed if it's less than 50 meters large and it
    # doesn't get any of the parcel data
    small_buildings = buildings[buildings.calc_area < 80].copy()
    small_buildings["small_building"] = True
    large_buildings = buildings[buildings.calc_area >= 80].copy()
    large_buildings["small_building"] = False
    
    large_buildings["stories"] = large_buildings.stories.fillna(parcel.stories).fillna(1)
    large_buildings["year_built"] = parcel.year_built
    large_buildings["building_type"] = parcel.dev_type
    
    # account for height
    built_area = large_buildings.calc_area * large_buildings.stories.astype('float')
    # get built area proportion in each building footprint
    proportion_built_area = built_area / built_area.sum()
    
    large_buildings["building_sqft"] = (proportion_built_area * parcel.bldg_sqft).round()
    large_buildings["residential_units"] = (proportion_built_area * parcel.res_units).round()
    large_buildings["non_residential_sqft"] = (proportion_built_area * parcel.nres_sqft).round()
    
    return pd.concat([small_buildings, large_buildings]), drop_parcel_attributes(parcels)

def make_dummy_building(parcels):
    # when there's more than one parcel, we put the dummy building on the
    # biggest sub parcel
    parcel = parcels.sort_values(by="calc_area", ascending=False).head(1)

    if parcels.bldg_sqft.fillna(0).sum() == 0 and parcels.res_units.fillna(0).sum() == 0:
        # there's no reason to make a dummy building if the attributes aren't there
        return pd.DataFrame(), drop_parcel_attributes(parcels)

    parcel.crs = {'init': 'epsg:4326'}
    parcel = parcel.to_crs(epsg=3857) # switch to meters
    circle = parcel.centroid.buffer(15).values[0] # buffer a circle in meters
    parcel = parcel.to_crs(epsg=4326) # back to lat-lng
    building = gpd.GeoDataFrame({
        'name': ['Generated from parcel centroid'],
        'geometry': [circle],
        'apn': [parcel.index[0]],
        'building:levels': [1],
        'building': ['yes']
    })
    building.crs = {'init': 'epsg:3857'}
    building = building.to_crs(epsg=4326)
    return assign_parcel_attributes_to_buildings(building, parcels)

new_buildings_list = []
new_parcel_list = []

cnt = 0
filtered_parcels = berkeley_parcels
#filtered_parcels = parcels[parcels.taz_id == 300419]
#s = parcels.orig_apn.value_counts()[lambda x: x > 1]
#filtered_parcels = parcels[parcels.orig_apn.isin(s.index)].iloc[:1000]

grps = filtered_parcels.groupby("orig_apn")
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

new_parcels.to_csv("moved_attribute_parcels.csv")
new_buildings.to_csv("moved_attribute_buildings.csv")

open("test_parcels.geojson", "w").write(new_parcels.to_json())
open("test_buildings.geojson", "w").write(new_buildings.to_json())


# # Experimentation below this point

# In[ ]:

print len(fixes['Union parcels'])
for parcel_sets in fixes['Union parcels'][10:11]:
    print feature_to_maps_link(parcel_sets.head(1))
    print parcel_sets.head(1).name
    two_layer_map(parcel_sets, split_parcels.loc[parcel_sets.index_right])


# In[ ]:

apns = new_parcels.apn.unique()
new_parcels[new_parcels.apn == apns[0]].plot(figsize=(12, 10))


# In[ ]:

new_parcels[new_parcels.apn == apns[1]].plot(figsize=(12, 10))


# In[ ]:

new_parcels[new_parcels.apn == apns[2]].plot(figsize=(12, 10))


# In[ ]:

new_parcels[new_parcels.apn == apns[3]].plot(figsize=(12, 10))


# In[ ]:

buildings = gpd.read_geocsv("buildings.csv", low_memory=False)
neighborhoods = gpd.read_geocsv("ca_neighborhoods.csv")


# In[ ]:

downtown = neighborhoods[neighborhoods.City == "Oakland"].query("Name == 'Downtown'")
broadmoor = neighborhoods[neighborhoods.City == "San Leandro"].query("Name == 'Broadmoor'")
#downtown_buildings = gpd.sjoin(buildings, downtown)
broadmoor_buildings = gpd.sjoin(buildings, broadmoor)


# In[ ]:

parcels = gpd.read_geocsv("parcels.csv")
#downtown_parcels = gpd.sjoin(parcels, downtown)
broadmoor_parcels = gpd.sjoin(parcels, broadmoor)


# In[ ]:

ax = broadmoor_parcels.plot(color='red', figsize=(50, 50))
broadmoor_buildings.plot(ax=ax, color='green', alpha=0.5)


# In[ ]:

neighborhoods[neighborhoods.City == "San Leandro"]


# In[ ]:

parcel_building_intersections = intersect(buildings, parcels)


# In[ ]:

len(parcel_building_intersections)


# In[ ]:

s = parcel_building_intersections.apn.value_counts()
s = s[s > 1]
print len(s)
apn = s.index[0]
print apn
c = parcels[parcels.apn == apn].centroid.geometry.values[0]
print c.y, c.x
ax = parcels[parcels.apn == apn].plot(color='red', figsize=(50, 50))
parcel_building_intersections[parcel_building_intersections.apn == apn].plot(ax=ax, color='green', alpha=0.5)


# In[ ]:



