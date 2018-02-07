import pandas as pd
import numpy as np
import geopandas as gpd
import shared
import sys

args = sys.argv[1:]
sectors = [
  'ag', 'natres', 'util', 'constr', 'man_lgt', 'man_hvy', 'man_bio',
  'man_tech', 'logis', 'ret_reg', 'ret_loc', 'transp', 'info', 'fire',
  'serv_pers', 'lease', 'prof', 'serv_bus', 'ed_k12', 'ed_high',
  'ed_oth', 'health', 'serv_soc', 'art_rec', 'hotel', 'eat', 'gov']
maz_controls = pd.read_csv("data/maz_controls.csv", index_col="MAZ_ORIGINAL")
buildings = gpd.read_geocsv(args[0], index_col="building_id")


# there are at least 2 reasons right now to have a dummy building per maz which
# does not technically have a parcel link - 1) for group quarters and 2) for
# jobs in mazs which have no building.  instead of just randomly selecting a
# parcel to add a building record to, we leave them associated with each maz
def add_dummy_buildings_per_maz(buildings):
    dummy_df = pd.DataFrame({"maz_id": maz_controls.index})
    dummy_df["name"] = "MAZ-level dummy building"
    dummy_df.index = ["MAZBLDG-" + str(d) for d in dummy_df.maz_id.values]
    df = pd.concat([buildings, dummy_df])
    df.index.name = "building_id"
    return df

buildings = add_dummy_buildings_per_maz(buildings)
    

sqft_per_job = {
  "HS": 400,
  "HT": 400,
  "HM": 400,
  "OF": 355,
  "HO": 1161,
  "SC": 470,
  "IL": 661,
  "IW": 960,
  "IH": 825,
  "RS": 445,
  "RB": 445,
  "MR": 383,
  "MT": 383,
  "ME": 383
}
buildings["sqft_per_job"] = buildings.building_type.map(sqft_per_job).\
    reindex(buildings.index).fillna(400)
buildings["job_spaces"] = (
    buildings.non_residential_sqft / buildings.sqft_per_job).\
    round().fillna(0).astype("int")


new_jobs = []
for maz_id in maz_controls.index:
    maz_control = maz_controls.loc[maz_id]

    np.random.shuffle(sectors)
    cnts = [maz_control.get(sector, 0) for sector in sectors]
    sectors_fanned_out = np.repeat(sectors, cnts)

    cnt = sectors_fanned_out.size
    if cnt == 0:
        continue

    building_options = buildings[buildings.maz_id == maz_id]
    building_id_options = np.repeat(
        building_options.index, building_options.job_spaces)
    assert building_options.job_spaces.sum() == building_id_options.size

    excess_cnt = max(cnt - building_id_options.size, 0)
    cnt -= excess_cnt

    # select w/o replacement from available job spaces, for only those
    # jobs that fit
    assignment = np.random.choice(
      building_id_options, size=cnt, replace=False) if cnt else []

    # select w/ replacement from all buildings if not enough job spaces
    if excess_cnt:
        excess_assignment = np.random.choice(
            building_options.index, size=excess_cnt, replace=True)
        assignment = np.concatenate((assignment, excess_assignment))

    new_jobs.append(pd.DataFrame({
        "sector": sectors_fanned_out,
        "building_id": assignment
    }))
new_jobs = pd.concat(new_jobs)
new_jobs["job_id"] = new_jobs.index + 1
print "New jobs by sector"
print new_jobs.sector.value_counts()


# we want to move this to the maz or probably taz level, but for
# now we use a regional number
REGIONAL_VACANCY_RATE = .05

# adjust the unit counts so that the number of job spaces is on average
# equal to the vacancy rate
buildings["job_spaces"] = (new_jobs.building_id.value_counts() *
                           (1 + REGIONAL_VACANCY_RATE)).round().astype("int")


new_jobs.to_csv("cache/jobs.csv", index=False)
buildings.to_csv("cache/buildings_adjusted_for_jobs.csv")
