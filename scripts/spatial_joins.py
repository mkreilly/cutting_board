import glob
import pandas as pd
import geopandas as gpd
import shared
import numpy as np
from shapely import wkt


def read_geocsv(*args, **kwargs):
    df = pd.read_csv(*args, **kwargs)
    df.loc[df.geometry.notnull(), 'geometry'] = \
        [wkt.loads(s) for s in df.loc[df.geometry.notnull(), 'geometry']]
    gdf = gpd.GeoDataFrame(df)
    gdf.crs = {'init': 'epsg:4326'}
    return gdf
gpd.read_geocsv = read_geocsv

parcels = gpd.read_geocsv("cache/merged_parcels.csv")

dummy_pcl = parcels.loc[parcels.geometry.isnull()]
parcels = parcels.loc[parcels.geometry.notnull()]

print "Assigning old zone ids using spatial join"
old_zones = gpd.read_geocsv("data/old_zones.csv")
old_zones["old_zone_id"] = old_zones["ZONE_ID"]
old_zones = old_zones[["old_zone_id", "geometry"]]
parcels["shape_area"] = shared.compute_area(parcels)
# do a centroid join with the old tazs
parcels["real_geometry"] = parcels.geometry
parcels["geometry"] = parcels.centroid
parcels["x"] = [g.x for g in parcels.geometry]
parcels["y"] = [g.y for g in parcels.geometry]
parcels = gpd.sjoin(
    parcels, old_zones, how="left", op="intersects")
del parcels["index_right"]

parcels["old_zone_id"] = parcels.old_zone_id.fillna(-1).astype("int")
print "Done assigning old zone ids using spatial join"

print "Loading policy zones and general plan data"

# load and spatially join policy zones and general plan areas
# to parcels, selecting general plan areas with priority 1 first
# where shapes overlap
p_zones = gpd.read_file('cache/policy_zones.geojson')
genplan = gpd.read_geocsv('cache/merged_general_plan_data.csv')
genplan.rename(columns={'city': 'general_plan_city'}, inplace=True)
del genplan['id']

print "Assigning policy zone and general plan ids using spatial join"

parcels = gpd.sjoin(
    parcels, p_zones, how="left", op="intersects")
del parcels['index_right']
parcels.rename(columns={'zoningmodc': 'zoningmodcat'}, inplace=True)
parcels = gpd.sjoin(
    parcels, genplan, how="left", op="intersects")
parcels = parcels.sort_values('priority').drop_duplicates('apn')
del parcels["index_right"]

print "Done assigning policy zone and general plan ids"

parcels = parcels.sort_values('priority').drop_duplicates('apn')

parcels["geometry"] = parcels.real_geometry
del parcels["real_geometry"]

# Set spatial join values to null in dummy parcels for now
for col in parcels.columns[~parcels.columns.isin(dummy_pcl.columns)]:
    dummy_pcl[col] = np.nan

parcels = pd.concat([parcels, dummy_pcl])

parcels[['apn', 'county_id', 'geometry', 'maz_id',
         'taz_id', 'orig_apn', 'juris_name', 'shape_area',
         'x', 'y', 'old_zone_id', 'zoningmodcat', 'general_plan_city',
         'general_plan_name']].to_csv(
    "cache/parcels_geography.csv", index=False)
