import geopandas as gpd
import osmnx
import time

print time.ctime()

gdf = gpd.GeoDataFrame.from_file("california.geojson")
alameda = gdf[gdf.name == "Alameda County, CA"].iloc[0]

buildings = osmnx.buildings.create_buildings_gdf(alameda.geometry)

print time.ctime()

buildings.to_csv("buildings.csv", encoding='utf-8')
print time.ctime()
