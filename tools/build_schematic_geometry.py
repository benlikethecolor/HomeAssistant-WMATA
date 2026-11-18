import argparse
import hashlib
import json
import runpy
from itertools import pairwise
from pathlib import Path

import numpy as np
import pymupdf as pdf
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree
from skimage.graph import route_through_array
from skimage.morphology import skeletonize

parser = argparse.ArgumentParser(
    description="Trace station segments from the verified WMATA PDF artwork."
)
parser.add_argument("--pdf", type=Path, required=True)
parser.add_argument("--anchors", type=Path, required=True)
parser.add_argument("--routes", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
EXPECTED_PDF_SHA256 = "a8067f85b1fabbe0140e2838bd7fb0d4609ac2e08f733c4f535169ca769b2804"
if hashlib.sha256(args.pdf.read_bytes()).hexdigest() != EXPECTED_PDF_SHA256:
    raise ValueError(
        "PDF artwork changed. Review the route drawing IDs before rebuilding the schematic."
    )
stations = runpy.run_path(str(args.anchors))["STATIONS"]
draws = pdf.open(args.pdf)[0].get_drawings()
routes = dict(json.loads(args.routes.read_text()))
out = {}
for line, ids in {
    "BL": [632, 633, 634],
    "GR": [664, 665, 666],
    "OR": [650, 651, 652, 653],
    "RD": [671],
    "SV": [639, 640, 641, 642, 643],
    "YL": [658, 659, 660, 661],
}.items():
    img = Image.new("1", (988, 1200))
    draw = ImageDraw.Draw(img)
    for idx in ids:
        pts = []
        for item in draws[idx]["items"]:
            if item[0] == "l":
                pts.extend(item[1:])
            elif item[0] == "c":
                a, b, c, d = item[1:]
                pts.extend(
                    a * (1 - t) ** 3
                    + b * (3 * t * (1 - t) ** 2)
                    + c * (3 * t * t * (1 - t))
                    + d * t**3
                    for t in np.linspace(0, 1, 31)
                )
            else:
                raise ValueError(item)
        draw.polygon([(p.x * 988 / 1080, p.y * 1200 / 1312) for p in pts], fill=1)
    mask = np.array(img)
    center = skeletonize(mask, method="lee")
    spine = np.argwhere(center)
    tree = cKDTree(spine)
    cost = (
        1
        + 200 * distance_transform_edt(~center) ** 2
        + 10000 * distance_transform_edt(~mask) ** 2
    )
    codes = routes[line]
    for a, b in pairwise(codes):
        start, end = [spine[tree.query(stations[k][::-1])[1]] for k in [a, b]]
        lo = np.maximum(np.minimum(start, end) - 85, 0)
        hi = np.maximum(start, end) + 86
        path, _ = route_through_array(
            cost[lo[0] : hi[0], lo[1] : hi[1]], start - lo, end - lo
        )
        xy = (np.array(path) + lo)[:, ::-1]
        ds = np.r_[0, np.cumsum(np.linalg.norm(np.diff(xy, axis=0), axis=1))]
        samples = np.linspace(0, ds[-1], max(2, int(ds[-1] / 1.5) + 1))
        out[f"{line}/{a}/{b}"] = np.round(
            np.array([np.interp(samples, ds, col) for col in xy.T]).T, 1
        ).tolist()
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(out, separators=(",", ":")))
print(len(out), "segments")
