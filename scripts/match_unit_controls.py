import pandas as pd
import numpy as np
import geopandas as gpd
import shared
import sys

args = sys.argv[1:]
prefix = args[0] + "_" if len(args) else ""

buildings = gpd.read_geocsv(
    "cache/%smoved_attribute_buildings.csv" % prefix, index_col="building_id")
parcels = gpd.read_geocsv("cache/%smoved_attribute_parcels.csv" % prefix,
                          index_col="apn")
controls = pd.read_csv("cache/maz_unit_controls.csv", index_col="maz_id")
mazs = gpd.read_geocsv("data/mazs.csv", index_col="maz_id")
buildings["apn"] = buildings.apn.astype("str")
buildings["building_type"] = buildings.building_type.astype("str")
buildings["maz_id"] = parcels.maz_id.loc[buildings.apn].values

existing_units = buildings.groupby("maz_id").residential_units.sum()
control_units = controls.residential_units
required_new_units = control_units.sub(existing_units, fill_value=0)

mazs["existing_units"] = existing_units.reindex(mazs.index).fillna(0)
mazs["control_units"] = control_units.reindex(mazs.index).fillna(0)
mazs["required_new_units"] = required_new_units.reindex(mazs.index).fillna(0)


def random_select_respect_size(s, num):
    # we want to randomly select indexes with a size limit for each index
    # the size limits are the values in the series s
    s = s.fillna(0).astype('int')
    return s.repeat(s.values).sample(abs(num)).index.value_counts()


def random_select_with_weights(s, num):
    weights = None if s.fillna(0).sum() == 0 else s.values
    return s.sample(num, replace=True, weights=weights).index.value_counts()


# make sure residentiail buildings always have at least the minimum number of
# units
def add_units_if_no_units(buildings):
    for index, building in buildings.iterrows():
        if building.building_type == "HS" and building.residential_units == 0:
            buildings.loc[index, "residential_units"] = 1
        if building.building_type == "HT" and building.residential_units == 0:
            buildings.loc[index, "residential_units"] = 2
        if building.building_type == "HM" and building.residential_units == 0:
            buildings.loc[index, "residential_units"] = 4
    return buildings


def subtract_random_units(buildings, required_units):
    # randomly select units to subtract
    remove_units = random_select_respect_size(
        buildings.residential_units, required_units)
    buildings["residential_units"] = buildings["residential_units"].sub(
        remove_units, fill_value=0)
    return buildings


def add_random_units(buildings, required_units):
    # otherwise start randomly assigning new units, with weights according to
    # where the units are now
    new_units = random_select_with_weights(
        buildings.residential_units, required_units)
    buildings["residential_units"] = buildings["residential_units"].add(
        new_units, fill_value=0)
    return buildings


def increase_building_sqft_to_match_footprint(buildings):
    # compute floor area from building footprint size and number of stories
    floor_area = shared.compute_area(buildings) * 10.76 * buildings.stories
    # but don't include the default circle building footprints
    floor_area *= buildings.name != "Generated from parcel centroid"
    # but do set to a minimum size
    floor_area = floor_area.fillna(0).clip(1000)
    # do the max
    buildings["building_sqft"] = np.fmax(buildings.building_sqft, floor_area)
    return buildings


BUILDING_EFFICIENCY = 0.8
SQFT_PER_HM_UNIT = 800


def increase_units_to_match_buildling_sqft(buildings):
    # HS and HT units can be large, but we assume HM units should be
    # SQFT_PER_HM_UNIT or less, and make sure to have that many units
    mask = buildings.building_type == "HM"
    units_from_sqft = (buildings.building_sqft *
                       BUILDING_EFFICIENCY / SQFT_PER_HM_UNIT).astype('int')
    buildings.loc[mask, "residential_units"] = \
        np.fmax(buildings.residential_units, units_from_sqft)
    return buildings


def synthesize_unit_total(maz_id, buildings, total_units):
    if len(buildings) == 0:
        return pd.DataFrame()

    buildings = buildings.copy()
    current_units = buildings.residential_units.fillna(0).sum()
    required_units = int(total_units - current_units)

    if required_units < 0:
        buildings = subtract_random_units(buildings, required_units)

    elif required_units > 0:
        # add units to residential buildings if there are none
        buildings = add_units_if_no_units(buildings)

        # add building sqft when the footprint indicates we should have
        # more sqft
        buildings = increase_building_sqft_to_match_footprint(buildings)

        # add units when the building sqft is larger than the current
        # unit count
        buildings = increase_units_to_match_buildling_sqft(buildings)

        current_units = buildings.residential_units.fillna(0).sum()
        required_units = int(total_units - current_units)

        # if we have more units now, randomly select units to subtract
        if required_units < 0:
            buildings = subtract_random_units(buildings, required_units)
        elif required_units > 0:
            buildings = add_random_units(buildings, required_units)

    # this is our promise - make sure we keep it
    assert buildings.residential_units.fillna(0).sum() == total_units

    return buildings

buildings["base_residential_units"] = buildings.residential_units
new_buildings = pd.concat([
    synthesize_unit_total(maz_id, buildings[buildings.maz_id == maz_id],
                          row.residential_units)
    for maz_id, row in controls.iterrows()
])
new_buildings.to_csv("cache/%sbuildings_match_controls.csv" % prefix)
