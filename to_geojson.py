import geopandas as gpd
import shared
import sys


def convert(from_name, to_name):
    gdf = gpd.read_geocsv(from_name)
    open(to_name, "w").write(gdf.to_json())

for arg in sys.argv[1:]:
    print "Converting", arg
    convert(arg, arg.replace(".csv", ".geojson"))
