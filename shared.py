import pandas as pd
import numpy as np
import geopandas as gpd
from shapely import wkt


# someday this will be in geopandas
# setting the crs shouldn't be in here, but all my cases use it
def read_geocsv(*args, **kwargs):
    df = pd.read_csv(*args, **kwargs)
    df["geometry"] = [wkt.loads(s) for s in df["geometry"]]
    gdf = gpd.GeoDataFrame(df)
    gdf.crs = {'init': 'epsg:4326'}
    return gdf
gpd.read_geocsv = read_geocsv


# make a link to look at google maps at a lat-lng
def feature_to_maps_link(row):
    centroid = row.centroid
    return "http://www.google.com/maps/place/%f,%f" % (centroid.y, centroid.x)


# geopandas plot two layers in relation to each other
def two_layer_map(top_layer, bottom_layer, column=None):
    ax = bottom_layer.plot(figsize=(10, 8), column=column,
                           legend=(column is not None))
    return top_layer.plot(ax=ax, color='pink', alpha=0.5, edgecolor="black")


# we're in 4326, so we need to convert the crs to meters and return the area
def compute_area(gdf):
    gdf.crs = {'init': 'epsg:4326'}
    return gdf.to_crs(epsg=3395).area


# compute the percent area contained in this shape from the shapes in the df
def compute_pct_area(df, total_area):
    df["calc_area"] = compute_area(df).values
    df["pct_area"] = df["calc_area"] / total_area
    return df


def compute_overlap_areas(overlaps, overlapees):
    '''
    After a spatial join is done, this computes the actual area of the overlap.
    overlaps is the result of the spatial join (which contains geometry for the
    overlaper) overlapees is the geometry of the right side of the join
    the "index_right" column of overlaps should be the index of overlapees
    '''
    total_overlaps = len(overlaps)
    cnt = 0
    overlap_area = []
    for index, overlap in overlaps.iterrows():
        overlapee = overlapees.loc[overlap.index_right]

        try:
            overlap_poly = gpd.overlay(
                gpd.GeoDataFrame([overlap]),
                gpd.GeoDataFrame([overlapee]), how="intersection")
        except:
            overlap_area.append(np.nan)
            print "Failed:", index
            continue

        if len(overlap_poly) == 0:
            overlap_area.append(0)
            continue

        overlap_area.append(compute_area(overlap_poly).values[0])

    return pd.Series(overlap_area, index=overlaps.index)
