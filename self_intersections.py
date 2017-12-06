import geopandas as gpd
import pandas as pd
import shared
import sys

args = sys.argv[1:]
juris = args[0]

parcels = gpd.read_geocsv("%s_parcels.csv" % juris, low_memory=False)
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
    parcels = parcels[parcels.is_valid]

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

drop_apns = pd.concat([
    pd.Series(v) for v in fully_contained_parcels.values()])

parcels_no_contains = parcels.set_index("apn").drop(drop_apns)

parcels_no_contains.to_csv("%s_parcels_no_self_intersections.csv" % juris)

'''
buildings_centroid = buildings.copy()
buildings_centroid["geometry"] = buildings.centroid
buildings_linked_to_mazs = gpd.sjoin(buildings_centroid, mazs)

buildings["maz_id"] = buildings_linked_to_mazs["maz_id"]

maz_filter = lambda x: x.maz_id == maz_id
intersections = [
    gpd.sjoin(buildings[maz_filter], parcels_no_contains[maz_filter])
    for maz_id in parcels_no_contains.maz_id.unique()
]
df = pd.concat(intersections)
'''
