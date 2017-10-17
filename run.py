import os

os.system('python fetch_buildings.py "Berkeley, CA"')
os.system('python filter_parcels.py "Berkeley, CA"')
os.system('python split_parcels.py')
os.system('python join_buildings_to_parcels.py')
os.system('python assign_building_attributes.py')
