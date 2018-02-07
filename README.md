# cutting_board

This is a set of scripts which is used to create parcels, buildings, households, and jobs datasets as inputs to MTC's UrbanSim model.  There is a rich history of practice in doing this and many examples to follow (most recently the Spandex scripts from Synthicity) - this set of scripts aims to keep things simple by 1) using only csv files as inputs and outputs 2) using geopandas instead of postgis for all spatial operations thus eliminating the need for db install, and 3) parallelizing by city for most steps, which allows multiprocessing for speed up.  The whole process takes about 40 hours in compute time but can run in about 11 hours on 4 cpus on an Amazon EC2 machine.

The main problem we're trying to solve it twofold.  First now that MTC's travel model system has a set of MAZs instead of TAZs (40k zones instead of 1.5k), there are many parcels that are larger than MAZs, and many large parcels in general.  We want to be able to locate the actual source and destinations of travel on those parcels by actually locating the buildings on the parcel, and we do that by using OpenStreetMaps significant (but not entirely complete) building footprint dataset.  This also helps us disaggregate parcel data within the parcel to buildings on the parcel.  For example, Berkeley's campus is a single parcel, but 5 or so MAZs.  Locating the building footprints on the parcel helps us know where the actual travel origins and destinations are on the campus.

The second reason for doing this is to attempt to identify parcels which are built up on one area of the parcel, but which are not on another large contiguous area, usually from being used for parking in shopping malls or corporate campuses.  Where there is a lot of pressure for development, these parking lots are ripe for redevelopment, and if we don't consider sub-parcel areas we can't know which parcels are fully covered by a short building, and which parcels have a modest height building on part of the parcel and a parking lot on the other side.

#### Proposed Methodlogy (Completed)

* Split parcel geometry by MAZ
  * Parcels with a single MAZ intersection are assigned to that MAZ
  * Parcels with no MAZ intersection are dropped
  * Parcels with multiple MAZ interesections are split into those MAZs, and "slivers" are unioned back to the main parcel
    * at this point parcels which have been split have copies of the attribute data (e.g. building sqft).  This should be split among the split parcels, but we want to use building information to do this wisely, so we need to join to buildings first.
* Assign building footprints to parcel splits
  * If a footprint intersects a majority within a single parcel (set to 70% right now), it is assigned to that parcel
  * Small footprints which overlap multiple parcels are dropped (these are shed, garages, carports, etc), and aren't important enough to worry about
  * We then assign a footprint to multiple parcels, while ignoring sliver overlaps.
    * If a footprint significantly overlaps multiple parcels, and those parcels all contain data, it is split among those parcels.  These are often townhomes which have separate parcels but share a wall.
    * If a footprint significantly overlaps multiple parcels, and only one parcel contains data, the parcels which do not have data are merged into the primary parcel.  Ikea, Kaiser, parts of Berkeley are all examples of this, where multiple parcels are now under a single owner.    
* Attributes are now moved from parcels to buildings.  At the end of this process, attributes like year_built, building_sqft, residential_units and so forth will be a part of the building dataframe, not the parcel dataframe.
  * These are assigned proportionally based on the built area (area of footprint times number of stories) of each footprint.
  * Small footprints (sheds, garages, etc) do not take these attributes.
  * Parcels that have attributes but no building footprint will be given a default geometry like a circle around the parcel centroid.
  * Parcel attributes which were copied among multiple split parcels should be assigned carefully.  The attributes should be split among the building footprints associated with each of the subparcels of each parcel.

#### Proposed Methodlogy (In Progress)

* Find non-developed parts of parcels.  Another key benefit of this approach is to identify parts of a parcel where there is not currently a building footprint.  These can be used e.g. to identify parking lots and thus areas that are more likely to develop.
* Use CoStar for non-residential space
* Add scheduled development events

#### Assignment

* We now have the parcel attributes assigned to building and located each within a single maz.  We can aggregate up to maz totals of residential units and non residential sqft (or jobs) and extra units to buildings based on where buildings currently exist.
  * We should also take into account building records without attributes at that point (e.g. a building record with no unit count in a MAZ that needs units should target that building record), and also a building footprint with no attributes (because the parcel didn't have attributes) is also a likely candidate.
  * In the end we will have building footprints assigned to sub-parcels assigned to MAZs.  The buildings will have unit counts and non residential square feet that sum to the maz unit counts and job spaces.  Some of the buildings will have geometry from OSM, and some will be circles at the parcel centroid.

#### Other Tasks from SPANDEX

* Condos and stacked detection
* Join to jurisdictions and other administrative boundaries
