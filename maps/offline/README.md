# Offline map storage

This folder holds the map files themselves (GeoPDFs, MBTiles, OSM extracts). Everything here except this README is git-ignored because the files are large.

Recommended layout:

```
maps/offline/
  usgs-topo/<STATE>/*.pdf      # tools/fetch_usgs_topo.py
  osm/<region>.osm.pbf         # Geofabrik extracts (download.geofabrik.de)
  organic-maps/ or osmand/     # phone app offline packs (back up the .mwm/.obf files)
  paper-scans/                 # photos of your printed, annotated maps
```

See `knowledge/04-maps/00-offline-map-sources.md` for what to download and how. Print your most important maps (home area, evacuation routes, rally points). Electronics fail; paper doesn't need batteries.
