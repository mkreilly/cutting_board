import pandas as pd

# Load the data to DataFrames
buildings = pd.read_csv('../data/buildings_adjusted_for_jobs.csv')
hh = pd.read_csv('../data/households.csv')
jobs = pd.read_csv('../data/jobs.csv')
pcl = pd.read_csv('../data/merged_parcels.csv')
ctrl = pd.read_csv('../maz_controls.csv').set_index('MAZ')


# Check buildings for APNs not found in parcel table
no_pcl_bldg = buildings.apn[(~buildings.apn.isin(pcl.apn)) &
                            (buildings.name!='MAZ-level dummy building')]

if len(no_pcl_bldg) > 0:
    print("{0} buildings are linked to APNs not found in parcel table".format(len(no_pcl_bldg)))
    no_pcl_bldg.to_csv('../data/parcel-less_buildings.csv')


# Join maz_id to jobs
bldg2maz = buildings.loc[buildings.name!='MAZ-level dummy building', ['building_id', 'maz_id']]
bldg2maz.building_id = bldg2maz.building_id.astype('int')

jobs = jobs[~jobs.building_id.str.contains('MAZBLDG')]
jobs.building_id = jobs.building_id.astype('int')

jobs = pd.merge(jobs, bldg2maz, left_on='building_id', right_on='building_id')


# Check all job sectors in jobs table against MAZ controls
for sector in jobs.sector.unique():
    sc = ctrl[['MAZ_ORIGINAL', sector]].set_index('MAZ_ORIGINAL')
    jobs_sum = jobs.loc[jobs.sector==sector, ['maz_id','sector']].groupby('maz_id').count()
    jobs_comp = sc[sector] - jobs_sum.reindex(sc.index).fillna(0).sector
    if len(jobs_comp[jobs_comp!=0]):
        print("{0} MAZs do not match job controls for sector {1}".format(len(jobs_comp[jobs_comp!=0]), sector))
        jobs_comp.to_csv('../data/jobs_comp_{0}.csv'.format(sector))


# Drop group quarters households from hh table
hh = hh[hh.GQFlag==0]


# Check parcel APNs for duplicate values
pcl_dupes = pcl.apn.value_counts()[pcl.apn.value_counts() > 1]
if len(pcl_dupes) > 0:
    print '{0} parcel APN values are repeated'.format(pcl_dupes)
    pcl[pcl.apn.isin(pcl_dupes)].to_csv('../data/repeated_parcel_apns.csv', index=False)


# Check households against MAZ hh controls. Negative values mean more households per MAZ in hh table than in controls.
maz_hh = ctrl.HH - hh.maz.value_counts()

maz_hh_pos = maz_hh[maz_hh > 0]
maz_hh_neg = maz_hh[maz_hh < 0]

if len(maz_hh_pos) > 0:
    print("{0} MAZs have fewer households than specified in the controls".format(len(maz_hh_pos)))
    maz_hh_pos.to_csv('../data/maz_hh_overallocated.csv')

if len(maz_hh_neg) > 0:
    print("{0} MAZs have more households than specified in the controls".format(len(maz_hh_neg)))
    maz_hh_neg.to_csv('../data/maz_hh_underallocated.csv')


# Check for negative building vacancies
bldg_vac = (buildings.set_index('building_id').residential_units.fillna(0) - hh.building_id.value_counts()).fillna(0)

neg_vac = bldg_vac[bldg_vac < 0]

if len(neg_vac) > 0:
    print("{0} buildings have negative vacancy".format(len(neg_vac)))
    buildings.loc[building_id.isin(neg_vac)].to_csv('../data/negative_vacancy_buildings.csv', index=False)


# Check for unallocated non-GQ households
print("{0} households are unallocated to buildings".format(len(hh.index[hh.building_id.isnull()])))


# Grab non-dummy building ids
bldg_ids = buildings.building_id[~(buildings.name=='MAZ-level dummy building')].astype('int')


# Check for non-null building ids in households that are not in the buildings table
missing_hh_bids = hh.building_id.dropna()[~hh.building_id.dropna().astype('int').isin(bldg_ids)]

if len(missing_hh_bids) > 0:
    print("{0} households have building ids not found in buildings table".format(len(missing_hh_bids)))
    missing_hh_bids.to_csv('../data/building-less_households.csv')


# Check jobs not in dummy buildings against valid building id list

no_bldg_jobs = jobs[~jobs.building_id.astype('int').isin(bldg_ids)]

if len(no_bldg_jobs) > 0:
    print("{0} jobs have building ids not found in buildings table".format(len(no_bldg_jobs)))
    no_bldg_jobs.to_csv('../data/building-less_households.csv')