---
title: Building an Offline Map Library (US Sources)
category: maps
region: all
tags: [maps, offline, usgs, topo, openstreetmap, geopdf, organic-maps, osmand, gazetteer, printing, evacuation-routes]
risk: low
sources: [USGS The National Map, USGS topoView, OpenStreetMap / Geofabrik, US Forest Service, BLM, NOAA]
last_reviewed: 2026-11-03
---

# Building an Offline Map Library

When cell networks and the internet are down, online maps vanish. Build your library **now**, store it in several formats, and print the essentials.

## What to collect (priority order)

1. **Home area** (20–30 mile radius): USGS 7.5-minute topo quads, printed and laminated or in plastic sleeves.
2. **Evacuation routes** to at least two destinations in different directions, including back roads.
3. **State road atlas** (paper, e.g., a DeLorme/Garmin Gazetteer-type atlas with topographic detail and backroads).
4. **Water sources:** springs, wells, rivers, reservoirs marked on topo maps.
5. **Public lands:** National Forest (USFS) and BLM maps show roads, trails, and campsites.
6. **Utilities and hazards:** pipelines, dams (flood paths), chemical plants, rail lines, nuclear plants (10- and 50-mile emergency zones).
7. **Coastal/marine:** NOAA nautical charts if on the coast or Great Lakes.

## Sources

### USGS (free)
- **US Topo** (current 7.5-minute quads, GeoPDF) — use `tools/fetch_usgs_topo.py` in this repo, or the National Map Downloader (apps.nationalmap.gov/downloader).
- **Historical Topographic Map Collection** (topoView, ngmdb.usgs.gov/topoview) — older maps show springs, mines, old trails, and structures that newer editions dropped.
- GeoPDFs open in any PDF reader; in the Avenza Maps phone app they show your live GPS position offline.

### OpenStreetMap (free)
- **Phone apps with offline downloads:** Organic Maps, OsmAnd. Download state packs while online; they route offline using GPS, which works without cell service.
- **Raw data:** Geofabrik (download.geofabrik.de/north-america/us.html) provides state extracts (.osm.pbf) for desktop GIS (QGIS).

### Government agencies
- **USFS** Motor Vehicle Use Maps and forest visitor maps.
- **BLM** surface management maps (land ownership).
- **NOAA** charts (charts.noaa.gov) — free PDF and raster nautical charts.
- **FEMA** flood maps (msc.fema.gov) — know which areas flood.
- **State DOT** maps — official road maps, often free.

### Other
- Local county GIS sites: parcel maps, hydrants, wells, culverts.
- Gazetteers: list place names with coordinates — useful for radio communications.

## Storage strategy

- **Paper:** most important maps printed, in waterproof sleeves, in each vehicle and go-bag.
- **Phone/tablet:** offline map apps plus GeoPDFs. Keep a charged power bank and a small solar charger.
- **Laptop/Raspberry Pi:** this repository plus `maps/offline/` and QGIS.
- **USB drives:** at least two copies, one stored off-site; consider a Faraday container (metal box, insulated inside).

## Annotate your maps

Mark: rally points (primary, secondary), water sources, caches, safe houses of friends/family, hospitals/clinics, pharmacies, fuel, bridges (and alternate crossings), chokepoints, high ground for radio. Use pencil — plans change. Use a consistent legend and date each annotation.

## Map scale cheat sheet

- **1:24,000** (USGS 7.5'): 1 inch = 2,000 ft. Best for foot navigation.
- **1:100,000:** 1 inch ≈ 1.6 miles. Regional vehicle planning.
- **1:250,000:** 1 inch ≈ 4 miles. Big-picture planning.
