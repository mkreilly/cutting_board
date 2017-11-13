import geopandas as gpd

gdf = gpd.GeoDataFrame.from_file("est10_esri_gt1.shp")
gdf = gdf.to_crs(epsg=4326)

fname_map = {
    'Duns_Numbe': 'duns_number',
    'Business_N': 'business_name',
    'Emp_Total': 'total_employment',
    'Emp_Here': 'local_employment',
    'Year_Start': 'start_year',
    'sixcat': 'PBA_category',
    'remi70': 'REMI_category',
    'steelhead': 'steelhead_category',
    'naics2': 'NAICS'
}
out_gdf = gdf[['Duns_Numbe', 'Business_N', 'geometry', 'Emp_Total', 'Emp_Here',
               'Year_Start', 'sixcat', 'remi70', 'steelhead',  'naics2']].\
    rename(columns=fname_map)

# see the bigger establishments
out_gdf.sort_values('total_employment', ascending=False)

out_gdf.to_csv("jobs.csv", index=False)
