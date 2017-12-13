import geopandas as gpd
import pandas as pd
import numpy as np
import shared
import sys

args = sys.argv[1:]
prefix = args[0] + "_" if len(args) else ""

parcels = gpd.read_geocsv("cache/%sparcels.csv" % prefix, low_memory=False)
mazs = gpd.read_geocsv("mazs.csv")

parcels_centroid = parcels.copy()
parcels_centroid["geometry"] = parcels.centroid
parcels_linked_to_mazs = gpd.sjoin(parcels_centroid, mazs)

parcels["maz_id"] = parcels_linked_to_mazs["maz_id"]


# takes a list of parcels and returns a dictionary where keys are parcel ids
# and values are lists of parcel ids which are fully contained in the key
# parcel id
def find_fully_contained_parcels(parcels):
    # next operation fails for invalid parcels, of which there are a few
    parcels = parcels[parcels.is_valid].copy()

    # this is because condos are often "cut out" of their parent parcel - we
    # want to drop the "cut out" part when doing the contains below
    # convex hull might not be precisely what we want here, but it
    # is close and I can't think of any major side effects
    parcels["geometry"] = parcels.convex_hull

    if not len(parcels):
        # no valid parcels in this maz, causes an error in the sjoin
        return {}

    # find intersections
    intersections = gpd.sjoin(parcels, parcels.copy(), op="contains")
    # filter to non-self-intersections
    non_self_intersections = intersections[
        intersections.index != intersections.index_right]

    if len(non_self_intersections) == 0:
        return {}

    d = {}
    for index, row in non_self_intersections.iterrows():
        d.setdefault(row.apn_left, [])
        d[row.apn_left].append(row.apn_right)
    return d


def merge_dicts(L):
    return {k: v for d in L for k, v in d.items()}

# iterate over mazs because the sjoin is too slow without going to
# small geography
fully_contained_parcels = merge_dicts(
    find_fully_contained_parcels(grouped_parcels)
    for index, grouped_parcels in parcels.groupby("maz_id"))


def merge_parcel_attributes(parcels, drop_list):
    new_parcels = parcels.copy()

    # iterate over the parcels we're going to merge and merge
    # attributes across parent and children
    for parent_apn, child_apns in drop_list.iteritems():
        parent = parcels.loc[parent_apn]
        children = parcels.loc[child_apns]
        both = children.append(parent)

        # sum these up
        for attr in ["bldg_sqft", "nres_sqft", "res_units"]:
            new_parcels.loc[parent_apn, attr] = both[attr].sum()

        # take most frequent occurring for these
        for attr in ["dev_type", "stories", "year_built"]:
            mode = both[attr].mode()
            mode = mode.values[0] if len(mode) else np.nan
            new_parcels.loc[parent_apn, attr] = mode

    return new_parcels

parcels.set_index("apn", inplace=True)
parcels = merge_parcel_attributes(parcels, fully_contained_parcels)

if len(fully_contained_parcels):
    drop_apns = pd.concat([
        pd.Series(v) for v in fully_contained_parcels.values()])
else:
    drop_apns = []

parcels_no_contains = parcels.drop(drop_apns)
del parcels_no_contains["maz_id"]

num_intersections = len(parcels) - len(parcels_no_contains)
print "%d parcels dropped because of self-intersections" % num_intersections
parcels_no_contains.to_csv(
    "cache/%sparcels_no_self_intersections.csv" % prefix)
