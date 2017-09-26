# cutting_board
Tools to help slice parcels according to geography and information on where buildings are within the parcel

#### Proposed Methodlogy

* Split parcel geometry by MAZ (making sure there are no "slivers" because of geometry errors).
* Assign building footprints to parcel splits - every footprint will be a part of a single parcel split (in order for every building to be in a single maz).  Footprints should be assigned to the parcel which has a larger land intersection (rather than containing the centroid).
* Divvy up parcel attributes after building footprints are linked.  Assign attributes to the parcel splits using the footprints as a clue.
* Now we have parcel splits with portions of the parcel attributes.  We can now take a MAZ of parcels splits and sum the units to make sure they match the unit counts from the 2010 SF1 census file.  We assign extra units to buildings based on where we currently see buildings.  We should also take into account building records without attributes at that point (e.g. a building record with no unit count in a MAZ that needs units should target that building record).
* In the end we will have parcel splits assigned to MAZs, with buildings assigned to parcel splits.  The buildings will have unit counts that sum to the maz unit counts.  Some of the buildings will have geometry from OSM, and some will be circles at the parcel centroid.
