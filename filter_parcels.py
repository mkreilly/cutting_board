import osmnx
import geopandas as gpd
import shared

args = sys.argv[1:]

parcels = gpd.read_geocsv("parcels.csv")

filter_shape = osmnx.gdf_from_place(args[0])
print filter_shape

filtered = gpd.sjoin(parcels, filter_shape)

parcels[parcels.index.isin(filtered.index)].to_csv(
    "cache/filtered_parcels.csv", index=False)
