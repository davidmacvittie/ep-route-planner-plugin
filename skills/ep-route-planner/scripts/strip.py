"""Places strip-map events along a route line and scales cumulative miles to the routing distance.
Turn positions are placed on the route geometry; cumulative miles are scaled so the leg total matches Mapbox's distance.
v3: events can carry red=N, a numbered predictable spot (curb, only way in or out, single approach). Each red spot has an
"if blocked, go" line on the leg page and in the strip notes.
"""
import math

def hav(a, b):
    R = 6371000.0
    la1, la2 = math.radians(a[1]), math.radians(b[1])
    dla = la2 - la1; dlo = math.radians(b[0] - a[0])
    h = math.sin(dla / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dlo / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))

def along(line, pt, start_m=0.0):
    """Distance along line (m) of the projection of pt, searching from start_m onward."""
    best = None; cum = 0.0
    kx = math.cos(math.radians(pt[1]))
    for a, b in zip(line, line[1:]):
        seg = hav(a, b)
        ax, ay = a[0] * kx, a[1]; bx, by = b[0] * kx, b[1]; px, py = pt[0] * kx, pt[1]
        dx, dy = bx - ax, by - ay
        t = 0.0 if dx == dy == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
        proj = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
        d = hav(proj, pt); pos = cum + t * seg
        if pos >= start_m - 1 and (best is None or d < best[0] - 0.5):
            best = (d, pos)
        cum += seg
    return best[1], cum

def build(route):
    line = route["line"]; total_api = route["meters"]
    _, total_line = along(line, line[-1])
    scale = total_api / total_line
    out = []; last = 0.0
    for ev in route["events"]:
        if ev.get("at") == "start": pos = 0.0
        elif ev.get("at") == "end": pos = total_line
        else: pos, _ = along(line, ev["pt"], last)
        last = pos
        e = dict(ev); e["mi"] = pos * scale / 1609.344
        out.append(e)
    return out


def bearing(a, b):
    kx = math.cos(math.radians((a[1] + b[1]) / 2))
    return math.degrees(math.atan2((b[0] - a[0]) * kx, b[1] - a[1])) % 360

def turns(line, min_deg=35, min_seg=15):
    """Turn points read from the route geometry, for routing tools that give turn text but no turn coordinates.
    Returns [{"pt": [lon, lat], "side": "L" or "R", "deg": change}]. Segments shorter than min_seg metres are merged,
    so a jog at a corner reads as one turn. Match each one to the routing tool's turn list in order."""
    pts = [line[0]]
    for p in line[1:]:
        if hav(pts[-1], p) >= min_seg or p is line[-1]:
            pts.append(p)
    out = []
    for a, b, c in zip(pts, pts[1:], pts[2:]):
        d = (bearing(b, c) - bearing(a, b) + 540) % 360 - 180
        if abs(d) < 20:
            continue
        side = "R" if d > 0 else "L"
        if out and out[-1]["side"] == side and hav(out[-1]["pt"], b) < 40:
            out[-1]["deg"] += round(d)   # one corner drawn as two bends
        else:
            out.append({"pt": b, "side": side, "deg": round(d)})
    return [t for t in out if abs(t["deg"]) >= min_deg]
