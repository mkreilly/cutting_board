import geopandas as gpd
import osmnx
import time
import sys

args = sys.argv[1:]

print "Fetching buildings from OSM", time.ctime()
print "Fetching for:", args[0]
alameda = osmnx.gdf_from_places([args[0]]).iloc[0]
buildings = osmnx.buildings.create_buildings_gdf(alameda.geometry)
print "Done fetching buildings", time.ctime()

buildings.index.name = "osm_id"
buildings[[
	"addr:city",
	"addr:housenumber",
	"addr:postcode",
	"addr:state",
	"addr:street",
	"amenity",
	"building",
	"building:levels",
	"geometry",
	"name"
]].to_csv("buildings.csv", encoding='utf-8')