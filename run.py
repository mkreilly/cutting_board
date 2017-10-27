import os

os.system('python fetch_buildings.py "Emeryville, CA"')
os.system('python filter_parcels.py "Emeryville, CA"')
os.system('python split_parcels.py')
os.system('python join_buildings_to_parcels.py')
os.system('python assign_building_attributes.py')
os.system('python fetch_census_data.py')
os.system('python block_to_maz_controls.py')
os.system('python match_unit_controls.py')
