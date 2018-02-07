import geopandas as gpd
import numpy as np
import shared
import sys
import yaml

cities_and_counties = yaml.load(open("cities_and_counties.yaml").read())

args = sys.argv[1:]
county = args[0]
lower_county = county.replace(" ", "_").lower()

cities_in_this_county = [
    c.replace("_", " ").title()
    for c in cities_and_counties[lower_county]]

# would be nice to fetch these over the web, but can't seem to
# get a url for a lfs file
url = "%s_parcels.zip" % lower_county
parcels = gpd.read_geocsv(url, low_memory=False)
juris = gpd.GeoDataFrame.from_file("juris.geojson")

# filter to jurisdictions in this county so as not to mis-assign
# egregiously - of course we might still mis-assign within the county
juris = juris[juris.NAME10.isin(cities_in_this_county)]

print "There are %d parcels" % len(parcels)

parcels["juris"] = np.nan
BATCHSIZE = 50000

parcels["polygon_geometry"] = parcels.geometry
parcels["geometry"] = parcels.centroid

for i in range(0, len(parcels), BATCHSIZE):
    # don't want all those juris fields, just assign juris
    print "joining", i, min(i+BATCHSIZE, len(parcels)-1)
    parcels_batch = parcels.iloc[i:min(i+BATCHSIZE, len(parcels)-1)]
    parcels_joined = gpd.sjoin(parcels_batch, juris)
    parcels["juris"] = parcels.juris.fillna(parcels_joined.NAME10)
    print "done joining"

parcels["juris"] = parcels.juris.fillna("Unincorporated %s" % county)
parcels["geometry"] = parcels.polygon_geometry
del parcels["polygon_geometry"]

assert True not in parcels.juris.isnull().unique()

f = open("cache/jurislist.%s.txt" % county, "w")
for juris, juris_parcels in parcels.groupby("juris"):
    if juris_parcels.apn.value_counts().values[0] > 1:
        # duplicate apns
        print "JURIS %s HAS DUPLICATE APNs, resetting index" % juris.upper()
        juris_parcels = juris_parcels.copy()
        juris_parcels["apn"] = np.arange(len(juris_parcels)) + 1
    juris_parcels.to_csv("cache/{}_parcels.csv".format(juris), index=False)
    f.write(juris + "\n")
