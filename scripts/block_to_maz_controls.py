import pandas as pd

block_totals = pd.read_csv("cache/block_unit_controls.csv", index_col="fips")
block_totals = block_totals.drop(
    ["tract", "state", "county", "block"], axis=1)

maz_map = pd.read_csv(
    "data/GeogXWalk2010_Blocks_MAZ_TAZ.csv",
    dtype={
        "COUNTYFP10": "string",
        "GEOID10": "string"
    },
    index_col="GEOID10"
)

# filter blocks that don't map to mazs
maz_map = maz_map[maz_map.MAZ_ORIGINAL != 0]

mazs = {
    maz: block_totals.loc[grp.index].sum()
    for maz, grp in maz_map.groupby("MAZ_ORIGINAL")
}

ret = pd.DataFrame.from_dict(mazs, orient="index")
ret.index.name = "maz_id"
ret.to_csv("cache/maz_unit_controls.csv")
