"""Download current USGS US Topo 7.5-minute GeoPDF maps for a bounding box.

Run this while you still have internet so the maps are stored offline.

Examples:
    # Boulder, CO area (west,south,east,north in decimal degrees)
    python tools/fetch_usgs_topo.py --bbox -105.35,39.95,-105.20,40.10

    # Around a point, roughly N miles in each direction
    python tools/fetch_usgs_topo.py --point 40.015,-105.27 --radius-mi 10

    # Preview without downloading
    python tools/fetch_usgs_topo.py --point 40.015,-105.27 --radius-mi 10 --dry-run

Each 7.5' quad covers ~7 x 8.5 miles and is roughly 30-60 MB. Maps are saved in
maps/offline/usgs-topo/<STATE>/ (git-ignored). Uses only the Python standard library.
API: https://tnmaccess.nationalmap.gov/api/v1/products (USGS The National Map).
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://tnmaccess.nationalmap.gov/api/v1/products"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "maps" / "offline" / "usgs-topo"


def bbox_from_point(lat: float, lon: float, radius_mi: float) -> tuple[float, float, float, float]:
    dlat = radius_mi / 69.0
    dlon = radius_mi / (69.0 * max(math.cos(math.radians(lat)), 0.01))
    return lon - dlon, lat - dlat, lon + dlon, lat + dlat


def query(bbox: tuple[float, float, float, float]) -> list[dict]:
    items, offset = [], 0
    while True:
        params = {
            "datasets": "US Topo",
            "bbox": ",".join(f"{v:.5f}" for v in bbox),
            "max": 100,
            "offset": offset,
        }
        url = f"{API}?{urllib.parse.urlencode(params)}"
        with urllib.request.urlopen(url, timeout=60) as resp:
            data = json.loads(resp.read())
        batch = data.get("items", [])
        items.extend(batch)
        offset += len(batch)
        if not batch or offset >= data.get("total", 0):
            break
    return items


def _quad_name(title: str) -> str:
    # "US Topo 7.5-minute map for Boulder, CO" / "USGS US Topo 7.5-minute map for Boulder, CO 2016"
    name = title.split("map for", 1)[-1]
    return re.sub(r"\s*\d{4}\s*$", "", name).strip().lower()


def latest_per_quad(items: list[dict]) -> list[dict]:
    """The API returns several editions per quad; keep the newest PDF of each."""
    best: dict[str, dict] = {}
    for it in items:
        if "pdf" not in (it.get("format") or "").lower():
            continue
        quad = _quad_name(it.get("title", ""))
        date = it.get("publicationDate") or ""
        if quad not in best or date > (best[quad].get("publicationDate") or ""):
            best[quad] = it
    return sorted(best.values(), key=lambda i: _quad_name(i.get("title", "")))


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url, timeout=300) as resp, tmp.open("wb") as f:
        while chunk := resp.read(1 << 20):
            f.write(chunk)
    tmp.replace(dest)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--bbox", help="west,south,east,north")
    g.add_argument("--point", help="lat,lon")
    p.add_argument("--radius-mi", type=float, default=10.0)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--max-maps", type=int, default=60, help="safety cap on number of downloads")
    args = p.parse_args()

    if args.bbox:
        bbox = tuple(float(v) for v in args.bbox.split(","))
    else:
        lat, lon = (float(v) for v in args.point.split(","))
        bbox = bbox_from_point(lat, lon, args.radius_mi)

    maps = latest_per_quad(query(bbox))
    print(f"{len(maps)} quads found for bbox {tuple(round(v, 4) for v in bbox)}")
    if len(maps) > args.max_maps:
        print(f"Refusing to download more than {args.max_maps}; raise --max-maps or shrink the area.")
        return 1
    for m in maps:
        url = m["downloadURL"]
        parts = urllib.parse.urlparse(url).path.split("/")
        state = parts[-2] if len(parts) >= 2 else "XX"
        dest = OUT / state / parts[-1]
        size_mb = (m.get("sizeInBytes") or 0) / 1e6
        status = "exists" if dest.exists() else ("would download" if args.dry_run else "downloading")
        print(f"  {m['title']}  ({size_mb:.0f} MB)  -> {status}")
        if not dest.exists() and not args.dry_run:
            try:
                download(url, dest)
            except Exception as e:  # keep going on individual failures
                print(f"    FAILED: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
