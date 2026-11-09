"""Regenerate the inlined <script id="dem"> JSON in ../index.html (bare-earth terrain, AWS Terrain Tiles / USGS 3DEP).

python3 dem_grid.py  -> downloads 9 Terrarium z15 tiles and writes dem.json: a 221x221 grid at 4 m spacing centred on the
sculpture, int16 decimetres relative to the sculpture's base, base64. Paste it into the <script id="dem"> tag.
"""
import base64, io, json, math, struct, urllib.request
from PIL import Image

LAT, LON, Z = 38.952256, -77.1457484, 15
N2 = 2 ** Z
KC = 111320 * math.cos(math.radians(LAT))
tx0 = int((LON + 180) / 360 * N2)
ty0 = int((1 - math.asinh(math.tan(math.radians(LAT))) / math.pi) / 2 * N2)
tiles = {}
for x in (tx0 - 1, tx0, tx0 + 1):
    for y in (ty0 - 1, ty0, ty0 + 1):
        url = f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{Z}/{x}/{y}.png"
        data = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "kryptos-model/1.0"})).read()
        tiles[(x, y)] = Image.open(io.BytesIO(data)).convert("RGB").load()


def raw(X, Y):
    r, g, b = tiles[(int(X // 256), int(Y // 256))][int(X % 256), int(Y % 256)]
    return r * 256 + g + b / 256 - 32768


def elev(xm, zm):
    lat, lon = LAT - zm / 111320, LON + xm / KC
    X = (lon + 180) / 360 * N2 * 256 - 0.5
    Y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * N2 * 256 - 0.5
    x0, y0 = math.floor(X), math.floor(Y)
    fx, fy = X - x0, Y - y0
    return (raw(x0, y0) * (1 - fx) * (1 - fy) + raw(x0 + 1, y0) * fx * (1 - fy)
            + raw(x0, y0 + 1) * (1 - fx) * fy + raw(x0 + 1, y0 + 1) * fx * fy)


H0, S, N = elev(0, 0), 4, 221
half = (N - 1) * S / 2
vals = [round((elev(-half + i * S, -half + j * S) - H0) * 10) for j in range(N) for i in range(N)]
json.dump({"n": N, "s": S, "d": base64.b64encode(struct.pack(f"<{len(vals)}h", *vals)).decode()}, open("dem.json", "w"))
print("range m", min(vals) / 10, max(vals) / 10)
