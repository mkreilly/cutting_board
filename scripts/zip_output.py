import os
import datetime

os.chdir("cache")
os.system("ln buildings_adjusted_for_jobs.csv buildings.csv")
os.system("ln parcels_geography.csv parcels.csv")
today = datetime.datetime.today().strftime('%Y-%m-%d')
fname = today + "_basis_microdata.zip"
os.system("zip %s buildings.csv buildings_geometry.csv households.csv "
          "jobs.csv parcels.csv" % fname)
