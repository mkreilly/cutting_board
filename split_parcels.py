import pandas as pd
import geopandas as gpd
import numpy as np
import time
from shared import compute_pct_area, compute_area
import sys

# This script joins parcels mazs and splits them along maz boundaries
# it reads parcels.csv and mazs.csv and writes split_parcels.csv

args = sys.argv[1:]
prefix = args[0] + "_" if len(args) else ""

print "Loading parcels and mazs"
print time.ctime()
parcels = gpd.read_geocsv("cache/%sparcels.csv" % prefix)
bad_apns = ["999 999999999"]
parcels = parcels[~parcels.apn.isin(bad_apns)]
parcels["orig_apn"] = parcels["apn"]
mazs = gpd.read_geocsv("mazs.csv")[["maz_id", "geometry"]]

# join mazs to parcels
print "Joining parcels to mazs"
print time.ctime()
joined_parcels = gpd.sjoin(parcels, mazs, how="inner", op='intersects')


# when we intersect parcels with mazs, we want to merge parcel slivers back to
# the main shape - we don't need to keep small slivers of parcels that could be
# geometric errors
def merge_slivers_back_to_shapes(shapes, slivers):
    if len(shapes) == 0:
        # we're all slivers, so just move one of the slivers to the shapes and
        # they all get merged together
        shapes = slivers.iloc[:1]
        slivers = slivers.iloc[1:]

    for label, row in slivers.iterrows():
        distances = [
            row.geometry.distance(row2.geometry)
            for _, row2 in shapes.iterrows()
        ]

        min_ind = np.argmin(distances)
        closest_shape = shapes.iloc[min_ind]
        closest_index = shapes.index[min_ind]

        union = closest_shape.geometry.union(row.geometry)
        shapes.at[closest_index, "geometry"] = union

    return shapes


# split a parcel by mazs
def split_parcel(parcel, split_shapes, dont_split_pct_cutoff=.01,
                 dont_split_size_cutoff=150, drop_not_in_maz=False):
    try:
        overlay = gpd.overlay(parcel, split_shapes.reset_index(),
                              how='identity')
    except:
        # one fails for some reason
        print "Parcel failed"
        return

    overlay = compute_pct_area(overlay, compute_area(parcel).sum())

    # now we need to make sure we don't split off very small portions
    split = overlay[
        (overlay.pct_area >= dont_split_pct_cutoff) &
        (overlay.calc_area >= dont_split_size_cutoff)
    ].copy()
    dont_split = overlay[
        (overlay.pct_area < dont_split_pct_cutoff) |
        (overlay.calc_area < dont_split_size_cutoff)
    ].copy()

    split = merge_slivers_back_to_shapes(split, dont_split)

    if drop_not_in_maz:
        split = split[~split.maz_id.isnull()]

    # have to recompute merge of slivers
    split = compute_pct_area(split, compute_area(split).sum())

    return split


# this does the parcel splits
cnt = 0
split_parcels = []
joined_parcels.set_index("apn", inplace=True)
apn_counts = joined_parcels.index.value_counts()[lambda x: x > 1]
mazs.set_index("maz_id", inplace=True)

print "Splitting parcels when there are overlaps"
print time.ctime()
for apn, count in apn_counts.iteritems():
    subset = joined_parcels.loc[apn]

    ret = split_parcel(subset.head(1).drop("maz_id", axis=1),
                       mazs[mazs.index.isin(subset.maz_id)],
                       drop_not_in_maz=True, dont_split_pct_cutoff=.03,
                       dont_split_size_cutoff=1250)

    if ret is None or len(ret) <= 1:
        # there's an error in the split parcel function, so we just
        # take the first maz intersection
        ret = subset.head(1).copy()
        ret["apn"] = apn
    else:
        # make a new unique apn when we split a parcel
        ret["apn"] = [str(apn) + "-" + str(i+1) for i in range(len(ret))]
    split_parcels.append(ret)

    cnt += 1
    if cnt % 100 == 0:
        print "Done %d of %d" % (cnt, len(apn_counts))

if "index_right" in joined_parcels.columns:
    del joined_parcels["index_right"]
joined_parcels.index.name = "apn"
joined_parcels = joined_parcels.reset_index()

print "Done splitting parcels"
print time.ctime()

if len(split_parcels) == 0:
    # for small cities there are no parcels to split
    joined_parcels.to_csv("cache/%ssplit_parcels.csv" % prefix, index=False)
    sys.exit(0)

split_parcels = pd.concat(split_parcels)

# this is a little hard to read, but the idea is that we want to take all the
# parcels and their associated maz_ids which were NOT overlaps and merge them
# with all the splits of the overlapping parcels that we just did
# after this line we should have all the parcels
split_parcels = gpd.GeoDataFrame(
    pd.concat([
        joined_parcels[~joined_parcels.apn.isin(split_parcels.orig_apn)],
        split_parcels
    ])
)

if "index_right" in split_parcels.columns:
    del split_parcels["index_right"]
split_parcels.to_csv("cache/%ssplit_parcels.csv" % prefix, index=False)
