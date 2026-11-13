import argparse
import json
import math
import runpy
from itertools import pairwise
from pathlib import Path

parser = argparse.ArgumentParser(
    description="Rebuild geographic rail assets from public GIS/API JSON exports."
)
parser.add_argument("--stations", type=Path, required=True)
parser.add_argument("--rail", type=Path, required=True)
parser.add_argument("--extension", type=Path, required=True)
parser.add_argument("--schematic-shapes", type=Path, required=True)
parser.add_argument("--anchors", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
ROOT = args.output
(ROOT / "www").mkdir(parents=True, exist_ok=True)
stations = {s["Code"]: s for s in json.loads(args.stations.read_text())}
features = json.loads(args.rail.read_text())["features"]
features += json.loads(args.extension.read_text())["features"]
names = {
    "red": "RD",
    "blue": "BL",
    "orange": "OR",
    "green": "GR",
    "yellow": "YL",
    "silver": "SV",
}
paths = [
    (
        names[(f["attributes"].get("NAME") or "silver").lower()],
        p[::5] + [p[-1]] if len(p) > 10000 else p,
    )
    for f in features
    for p in f["geometry"]["paths"]
]


def project(point, path):
    best = (float("inf"), None, None)
    for i, (a, b) in enumerate(pairwise(path)):
        dx = (b[0] - a[0]) * 0.78
        dy = b[1] - a[1]
        px = (point[0] - a[0]) * 0.78
        py = point[1] - a[1]
        t = max(0, min(1, (px * dx + py * dy) / (dx * dx + dy * dy))) if dx or dy else 0
        d = math.hypot(px - t * dx, py - t * dy) * 111000
        if d < best[0]:
            best = (d, i + t, [a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])])
    return best


shapes = {}
maxerr = 0
for key in json.loads(args.schematic_shapes.read_text()):
    line, a, b = key.split("/")
    start = [stations[a]["Lon"], stations[a]["Lat"]]
    end = [stations[b]["Lon"], stations[b]["Lat"]]
    choices = []
    for color, path in paths:
        pa, pb = project(start, path), project(end, path)
        choices.append(
            (max(pa[0], pb[0]) + (0 if color == line else 150), pa, pb, path)
        )
    _, pa, pb, path = min(choices, key=lambda c: c[0])
    assert max(pa[0], pb[0]) < 500, (key, pa[0], pb[0])
    maxerr = max(maxerr, pa[0], pb[0])
    reverse = pa[1] > pb[1]
    if reverse:
        pa, pb = pb, pa
    curve = [pa[2]] + path[int(pa[1]) + 1 : int(pb[1]) + 1] + [pb[2]]
    if reverse:
        curve.reverse()
    # Resample by geographic distance for approximately uniform circuit intervals.
    ds = [0]
    for x, y in pairwise(curve):
        ds.append(ds[-1] + math.hypot((y[0] - x[0]) * 0.78, y[1] - x[1]) * 111000)
    result = []
    i = 0
    count = max(2, int(ds[-1] / 25) + 1)
    for j in range(count):
        distance = ds[-1] * j / (count - 1)
        while i < len(ds) - 2 and ds[i + 1] < distance:
            i += 1
        t = (distance - ds[i]) / (ds[i + 1] - ds[i]) if ds[i + 1] > ds[i] else 0
        result.append(
            [
                round(x + (y - x) * t, 7)
                for x, y in zip(curve[i], curve[i + 1], strict=True)
            ]
        )
    shapes[key] = result
(ROOT / "geo_shapes.json").write_text(json.dumps(shapes, separators=(",", ":")))
(ROOT / "www/geo_routes.json").write_text(
    json.dumps(
        {
            "paths": [
                {"line": k.split("/")[0], "points": p} for k, p in shapes.items()
            ],
            "stations": [
                {"code": c, "name": s["Name"], "point": [s["Lon"], s["Lat"]]}
                for c, s in stations.items()
            ],
            "source": "WMATA public GIS rail lines and Dulles extension; OpenStreetMap basemap",
        },
        separators=(",", ":"),
    )
)
anchors = runpy.run_path(str(args.anchors))["STATIONS"]
route_file = ROOT / "www/geo_routes.json"
data = json.loads(route_file.read_text())
for station in data["stations"]:
    station["diagram_point"] = anchors.get(station["code"])
route_file.write_text(json.dumps(data, separators=(",", ":")))
print(
    "Segments",
    len(shapes),
    "maximum station projection distance (metres)",
    round(maxerr),
)
