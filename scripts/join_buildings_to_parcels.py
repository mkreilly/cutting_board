import pandas as pd
import geopandas as gpd
import time
import sys
from shared import compute_area, compute_overlap_areas

# This script reads in the split_parcels.csv and the buildings.csv
# and joins buildings to parcels.  Each building is assigned an apn
# and is written to buildings_linked_to_parcels.csv

args = sys.argv[1:]
prefix = args[0] + "_" if len(args) else ""

print "Reading parcels and buildings", time.ctime()
buildings = gpd.read_geocsv("cache/%sbuildings.csv" % prefix, low_memory=False,
                            index_col="building_id")
split_parcels = gpd.read_geocsv("cache/%ssplit_parcels.csv" % prefix,
                                index_col="apn", low_memory=False)
mazs = gpd.read_geocsv("data/mazs.csv")[["maz_id", "geometry"]]


def assign_maz_id_by_centroid(df, mazs):
    df_centroid = df.copy()
    df_centroid["geometry"] = df.centroid

    df_linked_to_mazs = gpd.sjoin(df_centroid, mazs)

    df["maz_id"] = df_linked_to_mazs["maz_id"]
    return df

buildings = assign_maz_id_by_centroid(buildings, mazs)


# see comment below - groups by an attribute and THEN does a spatial join
# for performance reasons
def groupby_spatial_join(groupby_attr, left, right):
    attr_filter = lambda x: x[groupby_attr] == groupby_val
    intersections = [
        gpd.sjoin(left[attr_filter], right[attr_filter])
        for groupby_val in right[groupby_attr].unique()
    ]
    return pd.concat(intersections)


# I've had a heck of a time getting San Jose parcels and buildings to finish
# joining - although I can run the entirety of alameda county with more parcels
# and more buildings, San Jose seems to never complete, even after dropping all
# the self intersection parcels that San Jose typically has.  My current
# workaround is this - to groupby maz_id and do joins for each maz one at a
# time - since parcels are already split on maz boundaries, and since we want
# every building assigned to one and only one, this seems like a fine approach
# but I'm still suspicious of geopandas for why it can't seem to do the whole
# join
def special_sjoin(left, right):
    if args[0] != "San Jose":
        return gpd.sjoin(left, right)

    return groupby_spatial_join("maz_id", left, right)

print "Joining buildings to parcels", time.ctime()
# now we have our new parcels (the split ones and want to join buildings
joined_buildings = special_sjoin(buildings, split_parcels.reset_index())
joined_buildings.index.name = "building_id"
joined_buildings["index_right"] = joined_buildings.apn

# identify overlaps of buildings and split parcels
cnts = joined_buildings.index.value_counts()
overlaps = joined_buildings.loc[cnts[cnts > 1].index].copy()

print "Computing overlapping areas", time.ctime()
overlaps["overlapping_area"] = compute_overlap_areas(overlaps, split_parcels)
print "Done computing overlapping areas", time.ctime()

# overlaps[["overlapping_area"]].to_csv("overlapping_area.csv")
'''
overlaps["overlapping_area"] = pd.read_csv(
    "overlapping_area.csv", index_col="building_id").overlapping_area.values
'''

# the percent of the total area of the building footprint that overlaps with
# each parcel
overlaps["overlapping_pct_area"] = overlaps.overlapping_area /\
    overlaps.overlapping_area.groupby(overlaps.index).transform('sum')
# find the max percent that overlaps with each parcel
overlaps["max_overlapping_pct_area"] = overlaps.overlapping_pct_area.groupby(
    overlaps.index).max()

# A pretty high proportion of building footprints touch at least two parcels -
# these are the "overlaps"

print "Len buildings:", len(buildings)
print "Len buildings that overlap a parcel or more", \
    len(joined_buildings.index.value_counts())
print "Len of buildings that overlap with 2 parcels or more",\
    len(overlaps.index.value_counts())

# These are the building footprints which only match one parcel -
# we assign them to that parcel

non_overlaps = joined_buildings.loc[cnts[cnts == 1].index].copy()
print "Len of non-overlaps:", len(non_overlaps)

# We then take the building footprints which match to multiple parcels,
# but to one parcel greater than a given threshold

SINGLE_PARCEL_THRESHOLD = .65
overlaps_greater_than_threshold = overlaps.query(
    "overlapping_pct_area >= %f" % SINGLE_PARCEL_THRESHOLD)
print "Len parcels that overlap enough to map to a single parcel:",\
    len(overlaps_greater_than_threshold)

problematic_overlaps = overlaps.query(
    "max_overlapping_pct_area < %f" % SINGLE_PARCEL_THRESHOLD).copy()
print "Len parcels which overlap significantly with 2 or more parcels:",\
    len(problematic_overlaps.index.value_counts())


def are_these_same_parcels(parcel_overlaps):
    # this looks to see if the data on the parcels looks like multiple
    # buildings or whether it looks like a single building with 0's on the
    # other parcels
    def majority_zero_values(s):
        return len(s[s == 0]) / float(len(s)) > .5

    return majority_zero_values(parcel_overlaps.bldg_sqft) and \
        majority_zero_values(parcel_overlaps.nres_sqft) and \
        majority_zero_values(parcel_overlaps.res_units)


def find_master_parcel(parcel_overlaps):
    # similar to the above, but returns the parcel to keep - keep the largest
    # building sqft, or units, or nres_sqft value
    keep_apn = parcel_overlaps.sort_values(
        by=["bldg_sqft", "res_units", "nres_sqft"], ascending=False)\
        .apn.values[0]
    dropped_apns = set(parcel_overlaps.apn)
    dropped_apns.remove(keep_apn)
    return keep_apn, list(dropped_apns)


def union_parcels(split_parcels, keep_apn, dropped_apns):
    # given the parcel set, union the geometry among the keep_apn (single apn)
    # and dropped_apns (list of apns) and then drop the parcels in dropped_apns
    all_apns = [keep_apn] + dropped_apns
    assert keep_apn not in dropped_apns
    new_geometry = split_parcels.loc[all_apns].geometry.unary_union

    # ok this is stupid but there's something really weird where you can't set
    # the geometry value with a multigeometry
    geometry = split_parcels.geometry.copy()
    index = split_parcels.index.get_loc(keep_apn)
    geometry[index] = new_geometry
    split_parcels["geometry"] = geometry

    return split_parcels.drop(dropped_apns)


def deal_with_problematic_overlap(index, building_overlaps, split_parcels):
    area = compute_area(building_overlaps.head(1)).values[0]
    # sliver threshold varies by size of the building, for small parcels we
    # want to bias towards not splitting it up, for large building it might
    # make sense to split it up more frequently
    sliver_cutoff = .25 if area < 500 else .03

    title = ""
    keep = building_overlaps
    building_overlaps = building_overlaps.query(
        "overlapping_pct_area > %f" % sliver_cutoff)

    if len(building_overlaps) == 0:
        # no non-slivers, but there mostly look like apartment buildings,
        # townhomes, and such just put all the footprints back in
        building_overlaps = keep

    parcel_overlaps = split_parcels.loc[building_overlaps.apn]

    if len(building_overlaps) == 1:
        title = "Single parcel"
    elif are_these_same_parcels(parcel_overlaps):
        title = "Union parcels"
    else:
        title = "Split building"

    return title, building_overlaps


problematic_overlaps["calc_area"] = compute_area(problematic_overlaps)

# drop small footprints (these are like storage sheds, believe it or not)
large_problematic_overlaps = \
    problematic_overlaps[problematic_overlaps.calc_area > 200]
print "Dropped %d small overlapping footprints" %\
    (len(problematic_overlaps) - len(large_problematic_overlaps))


print "Analyzing problematic overlaps"
fixes = {}
cnt = 0
total_cnt = len(large_problematic_overlaps.index.unique())
for index in large_problematic_overlaps.index.unique():
    cnt += 1
    if cnt % 25 == 0:
        print "Finished %d of %d" % (cnt, total_cnt)
    overlap_type, building_overlaps = deal_with_problematic_overlap(
        index, large_problematic_overlaps.loc[index], split_parcels)
    fixes.setdefault(overlap_type, [])
    fixes[overlap_type].append(building_overlaps)


print "Splitting building footprints where appropriate"
chopped_up_buildings = []
cnt = 0
total_cnt = len(fixes.get('Split building', []))
for building_sets in fixes.get('Split building', []):
    cnt += 1
    if cnt % 25 == 0:
        print "Finished %d of %d" % (cnt, total_cnt)

    out = gpd.overlay(
        # we go back to the original buildings set in order to drop the joined
        # columns
        buildings.loc[building_sets.index].head(1).reset_index(),
        split_parcels.loc[building_sets.apn].reset_index(),
        how='intersection')

    # this is super weird but I'm seeing the need for different code on
    # different os-es presumably because of different version of pandas
    # or geopandas
    out_index = out.building_id if "building_id" in out.columns\
        else out.index_left
    # we're splitting up building footprints, so append "-1", "-2", "-3" etc.
    out.index = out_index.astype("string").str.\
        cat(['-'+str(x) for x in range(1, len(out) + 1)])

    chopped_up_buildings.append(out)

chopped_up_buildings = pd.concat(chopped_up_buildings)\
    if len(chopped_up_buildings)\
    else pd.DataFrame()


print "Union parcels where appropriate"
unioned_buildings = []

mapped_apns = {}  # need to keep track of parcels we dropped


def get_mapped_apn(apn):
    # needs to be recursive
    if apn in mapped_apns:
        mapped_apn = mapped_apns[apn]
        if apn == mapped_apn:
            return apn
        return get_mapped_apn(mapped_apn)
    return apn

cnt = 0
total_cnt = len(fixes.get('Union parcels', []))
for building_sets in fixes.get('Union parcels', []):
    cnt += 1
    if cnt % 25 == 0:
        print "Finished %d of %d" % (cnt, total_cnt)

    keep_apn, dropped_apns = find_master_parcel(building_sets)

    # this code does an iterative union, if parcels are joined to
    # parcels that have already been joined
    keep_apn = get_mapped_apn(keep_apn)
    dropped_apns = set([get_mapped_apn(apn) for apn in dropped_apns])
    dropped_apns.discard(keep_apn)
    dropped_apns = list(dropped_apns)

    for dropped_apn in dropped_apns:
        mapped_apns[dropped_apn] = keep_apn

    split_parcels = union_parcels(split_parcels, keep_apn, dropped_apns)

    # assign the building to the one master parcel
    keep_building = building_sets[lambda row: row.apn == keep_apn]

    unioned_buildings.append(keep_building)

unioned_buildings = pd.concat(unioned_buildings)\
    if len(unioned_buildings)\
    else pd.DataFrame()


buildings_linked_to_parcels = gpd.GeoDataFrame(pd.concat([
    non_overlaps,
    overlaps_greater_than_threshold,
    chopped_up_buildings,
    pd.concat(fixes.get('Single parcel', [pd.DataFrame()])),
    unioned_buildings
]))

del buildings["maz_id"]
# don't keep all the columns
buildings_linked_to_parcels = \
    buildings_linked_to_parcels[list(buildings.columns) + ["apn"]]

# only keep footprints that have been joined to a parcel
buildings_linked_to_parcels = buildings_linked_to_parcels[
    buildings_linked_to_parcels.apn.notnull()]

if len(buildings_linked_to_parcels):
    assert buildings_linked_to_parcels.index.value_counts().values[0] == 1

buildings_linked_to_parcels.index.name = "building_id"
buildings_linked_to_parcels.to_csv(
    "cache/%sbuildings_linked_to_parcels.csv" % prefix)

split_parcels.index.name = "apn"
split_parcels.to_csv("cache/%ssplit_parcels_unioned.csv" % prefix)
