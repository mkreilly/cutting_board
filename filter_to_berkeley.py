import osmnx
import geopandas as gpd
import shared

#parcels = gpd.read_geocsv("cache/moved_attribute_parcels.csv")
#buildings = gpd.read_geocsv("cache/moved_attribute_buildings.csv")
split_parcels = gpd.read_geocsv("cache/split_parcels.csv")
del split_parcels["index_right"]
print split_parcels

berkeley = osmnx.gdf_from_place("Berkeley, CA")
print berkeley

filtered = gpd.sjoin(split_parcels, berkeley)
print filtered

open("split_parcels_berkeley.json", "w").write(filtered.to_json())
#open("buildings_berkeley.json", "w").write(
#    gpd.sjoin(buildings, berkeley).to_json())
