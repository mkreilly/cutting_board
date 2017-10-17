import osmnx
import geopandas as gpd
import shared

parcels = gpd.read_geocsv("parcels.csv")

filter_shape = osmnx.gdf_from_place("Berkeley, CA")
print filter_shape

filtered = gpd.sjoin(parcels, filter_shape)
print filtered

parcels[parcels.index.isin(filtered.index)].to_csv(
    "cache/filtered_parcels.csv")
