# cutting_board
Tools to help slice parcels according to geography and information on where buildings are within the parcel

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


#### Proposed Methodlogy (In Progress)

* Parcels that have attributes but no building footprint will be given a default geometry like a circle around the parcel centroid.
* Parcel attributes which were copied among multiple split parcels should be assigned carefully.  The attributes should be split among the building footprints associated with each of the subparcels of each parcel.
* Find non-developed parts of parcels.  Another key benefit of this approach is to identify parts of a parcel where there is not currently a building footprint.  These can be used e.g. to identify parking lots and thus areas that are more likely to develop.
* Use CoStar for non-residential space

#### Assignment

* We now have the parcel attributes assigned to building and located each within a single maz.  We can aggregate up to maz totals of residential units and non residential sqft (or jobs) and extra units to buildings based on where buildings currently exist.
  We should also take into account building records without attributes at that point (e.g. a building record with no unit count in a MAZ that needs units should target that building record), and also a building footprint with no attributes (because the parcel didn't have attributes) is also a likely candidate.
* In the end we will have building footprints assigned to sub-parcels assigned to MAZs.  The buildings will have unit counts and non residential square feet that sum to the maz unit counts and job spaces.  Some of the buildings will have geometry from OSM, and some will be circles at the parcel centroid.
