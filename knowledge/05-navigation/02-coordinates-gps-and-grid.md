---
title: Coordinate Systems, GPS, and Grid References
category: navigation
region: all
tags: [gps, coordinates, latitude-longitude, utm, mgrs, usng, datum, plss, township-range, grid-reference]
risk: low
sources: [USGS The Universal Transverse Mercator Grid, US National Grid (FGDC), BLM Public Land Survey System]
last_reviewed: 2026-11-03
---

# Coordinate Systems, GPS, and Grid References

Being able to read and communicate a position exactly is essential for rescue, radio, and group coordination.

## Latitude and longitude

- **Latitude:** degrees north of the equator (US: roughly 19°N Hawaii to 71°N Alaska).
- **Longitude:** degrees west of Greenwich (US: roughly 67°W Maine to 172°E Aleutians; written as negative in decimal form, e.g., −105.27).
- Formats: decimal degrees (40.0150, −105.2705), degrees-minutes (40°00.90′N), degrees-minutes-seconds (40°00′54″N). Agree on one format with your group.
- 1° latitude ≈ 69 miles (111 km); 1 minute ≈ 1.15 miles (1 nautical mile); 0.001° ≈ 365 ft.

## UTM / MGRS / USNG (grid systems)

The **Universal Transverse Mercator** system divides the earth into 6°-wide zones (contiguous US: zones 10–19) and gives positions in meters east and north.

- Example UTM: `13T 476500E 4429700N`.
- **US National Grid (USNG)** — used by US emergency services — and the military **MGRS** use the same grid with a 100 km square letter pair: `13T DE 76500 29700`.
- **Read right, then up:** easting first, then northing.
- Precision: 10 digits = 1 m; 8 digits = 10 m; 6 digits = 100 m; 4 digits = 1 km.
- USGS topo maps print UTM grid ticks (blue) in the margins; many have a 1 km grid overlay. A **romer** (plastic corner scale) helps read precise grid references.

Grids are easier than lat/long for field use: distances are in meters, and squares are uniform.

## Datum

The same coordinates refer to different ground positions in different datums. Old USGS maps use **NAD27**; modern maps and GPS use **NAD83/WGS84**. The difference in the US can be 10–200 meters. Set your GPS to match the map's datum.

## Public Land Survey System (PLSS)

Most land west of the original 13 colonies (except Texas) is divided into **townships** (6 × 6 miles) of 36 **sections** (1 square mile each, numbered boustrophedon from the northeast corner). Legal descriptions read like "SW¼ of Section 12, T3N, R5W, 6th P.M." Rural roads often follow section lines, spaced 1 mile apart — useful for distance estimation in the Midwest and Plains.

## GPS without cell service

- Phone GPS works without cell data or internet; it only needs a sky view. You must have **offline maps** downloaded (see *Building an Offline Map Library*).
- Airplane mode with location on dramatically extends battery life.
- Dedicated GPS units with AA batteries are more rugged and longer-lived.
- GPS may be degraded or jammed during conflict; always carry map and compass.

## Communicating a position by radio

Use an agreed format and repeat back: "Grid one-three-tango, delta echo, seven-six-five, two-nine-seven." Alternatively, use reference points: "From the water tower, 800 meters on bearing 210." Agree on code names for common locations if security is a concern.
