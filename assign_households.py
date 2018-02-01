
import pandas as pd
import numpy as np
import geopandas as gpd
import shared
import sys

args = sys.argv[1:]

households = pd.read_csv("households.csv", index_col="HHID")
buildings = gpd.read_geocsv(args[0], index_col="building_id")
parcels = gpd.read_geocsv(args[1], index_col="apn")
maz_controls = pd.read_csv("maz_controls.csv")

households["maz_id"] = \
    households.maz.map(maz_controls.set_index("MAZ").MAZ_ORIGINAL).values
buildings["maz_id"] = parcels.maz_id.loc[buildings.apn].values
buildings["residential_units"] = \
    buildings.residential_units.fillna(0).astype("int")

household_assignment = []
for maz_id in buildings.maz_id.unique():
    print maz_id
    maz_households = households[households.maz_id == maz_id]
    building_options = buildings[buildings.maz_id == maz_id]
    building_id_options = np.repeat(
        building_options.index, building_options.residential_units)
    assert building_options.residential_units.sum() == building_id_options.size

    cnt = len(maz_households)
    if cnt == 0:
        continue
    excess_cnt = max(cnt - building_id_options.size, 0)
    cnt -= excess_cnt

    # select w/o replacement from available units, for only those
    # households that fit
    assignment = np.random.choice(
      building_id_options, size=cnt, replace=False) if cnt else []

    # select w/ replacement from all buildings if not enough units
    if excess_cnt:
        excess_assignment = np.random.choice(
            building_options.index, size=excess_cnt, replace=True)
        assignment = np.concatenate((assignment, excess_assignment))

    s = pd.Series(assignment, index=maz_households.index)
    assert s.isnull().value_counts().get(True, None) is None
    household_assignment.append(s)

household_assignment = pd.concat(household_assignment)
households["building_id"] = household_assignment

households.to_csv("cache/households.csv", index=False)

# in theory, if our household and unit controls matched up, we would have
# enough units for households and we wouldn't need to artificially increase
# the units to fit the households.  for some reason, we sometimes have more
# households than units in a maz and therefore more households than units in
# a building, so we fix that so at least our numbers add up
buildings["residential_units"] = buildings.residential_units.combine(
    households.groupby("building_id").size(), max)

buildings.to_csv("cache/buildings_adjusted_for_households.csv")
