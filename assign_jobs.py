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
  'ed_other', 'health', 'serv_soc', 'art_rec', 'hotel', 'eat', 'gov',
  'mis']
maz_controls = pd.read_csv("maz_controls.csv", index_col="MAZ_ORIGINAL")
buildings = gpd.read_geocsv(args[0], index_col="building_id")


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
for maz_id in buildings.maz_id.unique():
    maz_control = maz_controls.loc[maz_id]
    building_options = buildings[buildings.maz_id == maz_id]
    building_id_options = np.repeat(
        building_options.index, building_options.job_spaces)
    assert building_options.job_spaces.sum() == building_id_options.size

    np.random.shuffle(sectors)
    cnts = [maz_control.get(sector, 0) for sector in sectors]
    sectors_fanned_out = np.repeat(sectors, cnts)

    cnt = sectors_fanned_out.size
    if cnt == 0:
        continue
    excess_cnt = max(cnt - building_id_options.size, 0)
    cnt -= excess_cnt

    # select w/o replacement from available job spaces, for only those
    # jobs that fit
    assignment = np.random.choice(
      building_id_options, size=cnt, replace=False) if cnt else []

    # select w/ replacement from all building if not enough job spaces
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
