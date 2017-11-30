import geopandas as gpd
import osmnx
import time
import sys
import numpy as np

args = sys.argv[1:]
juris = args[0]

# this is nasty - these are cities without building footprints in OSM
# that crashes osmnx (at the time of this writing) - so we switch to a
# city that doesn't crash and the joins will fail in the next step
# but it gives enough for the the process to proceed
fetch_juris = juris if juris != "Ross" else "San Anselmo"

print "Fetching buildings from OSM", time.ctime()
jurises = gpd.GeoDataFrame.from_file("juris.geojson")

print "Fetching for:", juris
# I was a little worried the OSM definitions of the cities aren't the
# same as ours
# place = osmnx.gdf_from_places([args[0]])
place = jurises[jurises.NAME10 == fetch_juris]

buildings = osmnx.buildings.create_buildings_gdf(place.iloc[0].geometry)
print "Done fetching buildings", time.ctime()
print "Len buildings: %d" % len(buildings)

for col in ['addr:city', 'addr:housenumber', 'addr:postcode', 'addr:state',
            'addr:street', 'amenity', 'name']:
    if col not in buildings.columns:
        buildings[col] = ''

if "building:levels" not in buildings.columns:
    buildings["building:levels"] = np.nan

buildings.index.name = "building_id"
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
]].to_csv("cache/%s_buildings.csv" % juris, encoding='utf-8')
