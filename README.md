# cutting_board

#### Summary

This is a set of scripts which is used to create parcels, buildings, households, and jobs datasets as inputs to MTC's UrbanSim model.  There is a rich history of practice in doing this and many examples to follow (most recently the Spandex scripts from Synthicity) - this set of scripts aims to keep things simple by 1) using only csv files as inputs and outputs 2) using geopandas instead of postgis for all spatial operations thus eliminating the need for db install, and 3) parallelizing by city for most steps, which allows multiprocessing for performance.  The whole process takes about 40 hours in compute time but can run in about 9-10 hours (overnight) on 4 cpus on an Amazon EC2 machine.

The main problems we're trying to solve are twofold.  First, now that MTC's travel model system runs using MAZs instead of TAZs (40k zones instead of 1.5k), there are many parcels that are larger than MAZs, and many large parcels in general.  We want to be able to locate the actual sources and destinations of travel on those parcels by locating the buildings on the parcel, and we do that by using OpenStreetMap's significant (but not entirely complete) building footprint dataset.  This also helps us disaggregate parcel data within the parcel to buildings on that parcel.  For example, Berkeley's campus is a single parcel, but 5 or so MAZs.  Locating the building footprints on the parcel helps us know where the actual travel origins and destinations are on campus.

The second reason for doing this is to attempt to identify parcels which are built up on one area of the parcel, but which have little to no development on another large contiguous area, usually from being used for parking - e.g. in shopping malls and corporate campuses.  Where there is a lot of pressure for development, these parking lots are ripe for redevelopment, and if we don't consider sub-parcel areas we can't know which parcels are fully covered by a short building, and which parcels have a medium height building on part of the parcel and a parking lot on the other part.

All data is included in this repo except for the parcel data, which is stored in the Basis repo.  I tried to fetch the Basis parcel files over the internet, but can't figure out how to get a web link to a LFS file from Github, thus the user has to copy parcel zip files (and unzip them) from Basis into the parcels directory here.

#### Methodlogy

* Run orchestration (run.py)
  * run.py (which does not use orca for orchestration) is responsible for reading in the list of jurisdictions and processing them one at a time.  The set of scripts which is run on each jurisdiction is decribed one a a time below.  There are three preparation steps which run before the list of jurisdictions is processed.
    1) census data (controls for unit counts) for the region is fetched using fetch_census_data.py
    2) the census data above is aggregated from block to maz usinga a block-to-maz map (block_to_maz_controls.py)
    3) the counties are run in order and jurisdictions are assigned and parcels are split by jurisdiction (a list of jurisdictions is also kept) (split_by_city.py)

* Fetch buildings from OSM (fetch_buildings.py) - we use OSMNX to fetch buildings using the Overpass api (OSM) for the shape which is the boundary of the jurisdiction (boundaries are kept in juris.geojson)

* Remove stacked parcels (self_intersections.py)
  * This script is used to identify and remove stacked parcels, which means all parcels which are fully contained or sufficiently the same as another parcel (often used for condos by county assessors).  There is logic here to merge the data from the dropped parcels as appropriate.  This creates a "cache/%sparcels_no_self_intersections.csv" file for each juris.

* Split parcel geometry by MAZ (split_parcels.py)
  * Parcels with a single MAZ intersection are assigned to that MAZ
  * Parcels with no MAZ intersection are dropped
  * Parcels with multiple MAZ interesections are split into those MAZs, and "slivers" are unioned back to the main parcel
    * at this point parcels which have been split have copies of the attribute data (e.g. building sqft).  This should be split among the split parcels, but we want to use building information to do this wisely, so we need to join to buildings first.
  * This creates a "cache/%ssplit_parcels.csv" for each juris.
    
* Assign building footprints to parcel splits (join_buildings_to_parcels.py)
  * If a footprint intersects a majority within a single parcel (set to 70% right now), it is assigned to that parcel
  * Small footprints which overlap multiple parcels are dropped (these are shed, garages, carports, etc), and aren't important enough to worry about
  * We then assign a footprint to multiple parcels, while ignoring sliver overlaps.
    * If a footprint significantly overlaps multiple parcels, and those parcels all contain data, it is split among those parcels.  These are often townhomes which have separate parcels but share a wall.
    * If a footprint significantly overlaps multiple parcels, and only one parcel contains data, the parcels which do not have data are merged into the primary parcel.  Ikea, Kaiser, parts of Berkeley are all examples of this, where multiple parcels are now under a single owner.
  * This creates a new buildings file ("cache/%sbuildings_linked_to_parcels.csv") and a new parcels file ("cache/%ssplit_parcels_unioned.csv") for each juris.
    
* Attributes are now moved from parcels to buildings.  At the end of this process, attributes like year_built, building_sqft, residential_units and so forth will be a part of the building dataframe, not the parcel dataframe. (assign_building_attributes.py)
  * These are assigned proportionally based on the built area (area of footprint times number of stories) of each footprint.
  * Small footprints (sheds, garages, etc) do not take these attributes.
  * Parcels that have attributes but no building footprint will be given a default geometry like a circle around the parcel centroid.
  * Parcel attributes which were copied among multiple split parcels should be assigned carefully.  The attributes should be split among the building footprints associated with each of the subparcels of each parcel.
  * This creates new parcels ("cache/%smoved_attribute_parcels.csv") with no attributes, and new buildings ("cache/%smoved_attribute_buildings.csv") with the new attributes.

* Impute units using the census data as controls (match_unit_controls.py)
  * We fetch census data and aggregate it from blocks to mazs (as described above)
  * We then increase/descrease the units in each building to match the controls using a random sample.  We don't add a new building in this step, we only increase and descrease the number of units.

#### Post-processing steps (mainly household and job assignment)

* These scripts are not currently executed by run.py, because their run time is short compared to what happens in run.py, and they are only run once, not once per juris.  Also they are likely to be modified and improved in the future.

* First the parcel and building data is merged for all jurisdictions (merge_cities.py), including some modifications to the building and parcel ids.  This creates "cache/merged_parcels.csv" and "cache/merged_buildings.csv"

* Assign households (assign_households.py)
  * The controls for household assignment actually come from the maz_controls.py, but the households have already been synthesized in work by another consultant.  The job here is to read in the households.csv (stored in the repo as data/households.csv.zip) and assign a building_id based on the maz_id already assigned to the household.  We don't currently use a model to assign specific households to appropriate building types, but we could (MAZs probably are more homogeneous in building types than TAZs would be, so this isn't a huge deal).  We also increase the number of units in a building if we end up with more households than units (technically this shouldn't happen as both units and household counts come from the census, but it does happen for reasons we don't yet understand).  This creates "cache/buildings_adjusted_for_households.csv" and "cache/households.csv".
  
* Assign jobs (assign_jobs.py)
  * This takes the controls from maz_controls.csv and creates records for every job and assigns a building id for each job record.  It also increases the number of job spaces in buildings that are overfull from this process (which happens a lot because non_residential_sqft is not a reliable field in the parcel data.  Right now we use our jobs dataset at the maz level as the data which controls how much non-res space to assign (rather than using CoStar).  This is so that we can publicly release all of our data as CoStar is private data and past datasets based on CoStar have had to be kept private.  This step creates "cache/buildings_adjusted_for_jobs.csv" and "cache/jobs.py"
