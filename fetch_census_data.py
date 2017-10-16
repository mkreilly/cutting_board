import pandas as pd
from census import Census

# this script fetch unit totals from the census api and writes
# is as maz_unit_controls.csv

c = Census("f70721eba51f14bac9808503e8261b3be5884396")

# a good census lookup table (for variable names) is here
# https://wagda.lib.washington.edu/data/type/census/geodb/metadata/SF1qkRef_2010.pdf

dfs = []
# iterate over county fips codes in the MTC region
for county in ['001', '013', '041', '055', '075', '081', '085', '095', '097']:
    print "Fetching county %s" % county

    df = pd.DataFrame().from_dict(
        c.sf1.get(
            ['H00010001', 'H0030003', 'H0040004'],
            geo={
                'for': 'block:*',
                'in': 'state:06 county:%s' % county
            }
        )
    )

    df["fips"] = df.state + df.county + df.tract + df.block

    df.rename(columns={
        'H00010001': 'residential_units',
        'H0030003': 'vacant_units',
        'H0040004': 'rental_units'
    }, inplace=True)

    dfs.append(df)

df = pd.concat(dfs)
df.to_csv("cache/block_unit_controls.csv", index=False)
