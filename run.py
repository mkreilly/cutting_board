import os

os.system('python fetch_buildings.py "Alameda County, CA"')
os.system('python split_parcels.py')
os.system('python join_buildings_to_parcels.py')
os.system('python assign_building_attributes.py')
