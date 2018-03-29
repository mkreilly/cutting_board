import os

# second phase of scripts
os.system('python scripts/merge_cities.py')
os.system('python scripts/spatial_joins.py')
os.system('python scripts/assign_households.py cache/merged_buildings.csv')
os.system('python scripts/assign_jobs.py '
          'cache/buildings_adjusted_for_households.csv')
