"""Build a route advance PDF from one JSON file.

    python3 build_packet.py trip.json out.pdf

Page order: 1 how to read, 2 cover, 3 trip map and events check, then for each leg its map page followed by
the primary and alternate strip maps, one page per stop, medical, recon and comms, driver card, recon log,
after-move note. Image paths in the JSON are relative to the JSON file. A missing image draws a gray box
saying so, so a run without maps still builds. See ../reference/schema.md for every field.
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
FONTS = os.path.join(HERE, "..", "assets", "fonts")
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
for n in ["Regular", "Medium", "SemiBold", "Bold", "ExtraBold", "Italic"]:
    pdfmetrics.registerFont(TTFont("Inter-" + n, os.path.join(FONTS, "Inter-" + n + ".ttf")))
from reportlab.lib.fonts import addMapping
for _n in ["Inter-Regular", "Inter-Medium", "Inter-SemiBold"]:
    addMapping(_n, 0, 0, _n); addMapping(_n, 1, 0, "Inter-Bold"); addMapping(_n, 0, 1, "Inter-Italic"); addMapping(_n, 1, 1, "Inter-Bold")
from visuals import draw_qr, TEAL, Icon, Badge, Verdict, Spot, WeatherCard, StripPage, draw_icon, draw_spot, LBLUE, LGREEN
from strip import build as place_events
from reportlab.platypus import Flowable
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, NextPageTemplate,
                                TableStyle, Image, PageBreak)

NAVY = colors.HexColor("#0F1B2D"); INK = colors.HexColor("#18202B"); SLATE = colors.HexColor("#5A6577")
LINE = colors.HexColor("#DDE1E7"); AMBER = colors.HexColor("#E3A33B"); GREEN = colors.HexColor("#2F7D57")
RED = colors.HexColor("#B83A3A"); BLUE = colors.HexColor("#2E5E9E"); PALE = colors.HexColor("#F4F6F9")
AMBERPALE = colors.HexColor("#FBF1DF"); REDPALE = colors.HexColor("#F8E9E9")
NAMED = {"navy": NAVY, "blue": BLUE, "amber": AMBER, "green": GREEN, "red": RED, "purple": colors.HexColor("#7A3FA0"),
         "slate": SLATE}

H1 = ParagraphStyle("h1", fontName="Inter-ExtraBold", fontSize=20, leading=24, textColor=NAVY, spaceAfter=4)
H2 = ParagraphStyle("h2", fontName="Inter-Bold", fontSize=11.5, leading=14, textColor=NAVY, spaceBefore=6, spaceAfter=3)
KICK = ParagraphStyle("k", fontName="Inter-SemiBold", fontSize=8.5, leading=11, textColor=AMBER, spaceAfter=2)
B = ParagraphStyle("b", fontName="Inter-Regular", fontSize=9, leading=12.2, textColor=INK)
BS = ParagraphStyle("bs", parent=B, fontSize=8, leading=10.5)
SM = ParagraphStyle("sm", parent=B, fontSize=7.5, leading=9.8, textColor=SLATE)
TH = ParagraphStyle("th", fontName="Inter-SemiBold", fontSize=8, leading=10, textColor=colors.white)
BUL = ParagraphStyle("bul", parent=B, leftIndent=11, bulletIndent=0, spaceAfter=2)
FORM = ParagraphStyle("form", parent=BS, textColor=SLATE)

W = letter[0] - 1.3 * inch
VCOL = {"GREEN": "#2F7D57", "AMBER": "#B7791F", "RED": "#B83A3A"}


def P(t, s=B): return Paragraph(t, s)
def bullets(items, s=BUL): return [Paragraph(i, s, bulletText="•") for i in items]
def vtext(level, why): return '<font color="%s"><b>%s</b></font>: %s' % (VCOL[level], level, why)
def color(name): return NAMED.get(name, None) or colors.HexColor(name)


PAD = 9; GAP = 11

def panel(title, flow, width, bg=None):
    """A titled area with its own background, so each part of a page reads as one block."""
    head = Paragraph(title, ParagraphStyle("pt", fontName="Inter-Bold", fontSize=11, leading=13.5, textColor=NAVY, spaceAfter=5))
    t = Table([[[head] + list(flow)]], colWidths=[width])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg or PALE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("LEFTPADDING", (0, 0), (-1, -1), PAD), ("RIGHTPADDING", (0, 0), (-1, -1), PAD),
                           ("TOPPADDING", (0, 0), (-1, -1), PAD - 2), ("BOTTOMPADDING", (0, 0), (-1, -1), PAD),
                           ("ROUNDEDCORNERS", [6, 6, 6, 6])]))
    return t

def cols(cells, width, gap=18, split=None):
    """Two side-by-side columns with a clear gap between them."""
    a = split if split else (width - gap) / 2
    t = Table([[cells[0], "", cells[1]]], colWidths=[a, gap, width - a - gap])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                           ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return t

def no_red(D):
    """The skill gives green or amber only. Red is the team's call after the advance drive."""
    found = []
    def fix(x, path):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in ("verdict", "level") and v == "RED": x[k] = "AMBER"; found.append(path + "." + k)
                elif k == "verdict" and isinstance(v, list) and v and v[0] == "RED": v[0] = "AMBER"; found.append(path + "." + k)
                else: fix(v, path + "." + k)
        elif isinstance(x, list):
            for i, v in enumerate(x): fix(v, "%s[%d]" % (path, i))
    fix(D, "")
    if found:
        print("WARNING: RED verdicts changed to AMBER (red is the team's call after the advance drive): " + ", ".join(found))


def pages_text(a, b):
    return str(a) if a == b else "%d to %d" % (a, b)


def table(header, rows, widths, style=BS, zebra=True, hdr=NAVY, extra=None):
    data = [[P(h, TH) for h in header]] + [[P(c, style) if isinstance(c, str) else c for c in r] for r in rows]
    t = Table(data, colWidths=[w * W for w in widths], repeatRows=1)
    st = [("BACKGROUND", (0, 0), (-1, 0), hdr), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LINEBELOW", (0, 1), (-1, -1), 0.4, LINE), ("LEFTPADDING", (0, 0), (-1, -1), 5),
          ("RIGHTPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 3.5),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5)]
    if zebra:
        for i in range(1, len(data)):
            if i % 2 == 0: st.append(("BACKGROUND", (0, i), (-1, i), PALE))
    if extra: st += extra
    t.setStyle(TableStyle(st))
    return t


def kv(rows, widths=(0.22, 0.78)):
    data = [[P("<b>%s</b>" % k, BS), P(v, BS)] for k, v in rows]
    t = Table(data, colWidths=[w * W for w in widths])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
                           ("LEFTPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 3),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return t


def note(text, bg=AMBERPALE, bar=AMBER, width=None):
    t = Table([[P(text, BS)]], colWidths=[width or W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("LINEBEFORE", (0, 0), (0, -1), 3, bar),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 5),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    return t


IMG_DIR = "."
def img(name, width, caption=None):
    path = os.path.join(IMG_DIR, name) if name else ""
    if path and os.path.exists(path):
        from PIL import Image as PI
        w, h = PI.open(path).size
        out = [Image(path, width=width, height=width * h / w)]
    else:
        box = Table([[P("Image not available: %s" % (name or "none given"), SM)]], colWidths=[width], rowHeights=[width * 0.5])
        box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PALE), ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                                 ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
        out = [box]
    if caption: out.append(P(caption, SM))
    return out


def legend(items):
    cells = []
    for col, label in items:
        if col == "spot": sw = Spot("1", 9)
        else:
            sw = Table([[""]], colWidths=[14], rowHeights=[5])
            sw.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), col)]))
        cells += [sw, P(label, SM)]
    t = Table([cells], colWidths=[18, None] * len(items))
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 2)]))
    return t


def icon_row(kind, text, style=None, size=11):
    ic = Spot(kind[1], size) if isinstance(kind, (tuple, list)) else Icon(kind, size)
    t = Table([[ic, P(text, style or BS)]], colWidths=[size + 6, None])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5)]))
    return t


def _notes(ns):
    out = []
    for n in ns:
        head, body, ic = n[0], n[1], (n[2] if len(n) > 2 else None)
        if isinstance(ic, list): ic = tuple(ic)
        out.append((head, body, ic))
    return out


class MiniStrip(Flowable):
    """Small worked example of the strip map: left turns above the line, right turns below, checkpoints and spots on it."""
    def __init__(self, w, h=86): Flowable.__init__(self); self.w, self.h = w, h
    def wrap(self, aw, ah): return self.w, self.h
    def draw(self):
        c = self.canv; ly = self.h / 2 - 2; x0, x1 = 14, self.w - 22
        c.setStrokeColor(INK); c.setLineWidth(2.6); c.line(x0, ly, x1, ly)
        p = c.beginPath(); p.moveTo(x1 + 10, ly); p.lineTo(x1, ly + 5); p.lineTo(x1, ly - 5); p.close(); c.setFillColor(INK); c.drawPath(p, fill=1, stroke=0)
        c.setFillColor(INK); c.circle(x0, ly, 5.5, stroke=0, fill=1)
        c.setFont("Inter-Bold", 6.8); c.drawCentredString(x0 + 2, ly - 14, "START")
        xs = [x0 + (x1 - x0) * f for f in (0.2, 0.4, 0.6, 0.8)]
        c.setStrokeColor(LBLUE); c.setLineWidth(1.6); c.line(xs[0], ly, xs[0], ly + 24); c.line(xs[0], ly + 24, xs[0] - 9, ly + 24)
        p = c.beginPath(); p.moveTo(xs[0] - 13, ly + 24); p.lineTo(xs[0] - 8, ly + 27.5); p.lineTo(xs[0] - 8, ly + 20.5); p.close(); c.setFillColor(LBLUE); c.drawPath(p, fill=1, stroke=0)
        c.setFont("Inter-Bold", 7); c.drawCentredString(xs[0], ly + 31, "Left turn")
        draw_icon(c, "cp", xs[1], ly + 14, 7); c.setFillColor(INK); c.setFont("Inter-Bold", 7); c.drawCentredString(xs[1], ly + 26, "CP2: call in")
        c.setStrokeColor(INK); c.setLineWidth(1.2); c.line(xs[1], ly - 6, xs[1], ly + 6)
        c.setStrokeColor(LGREEN); c.setLineWidth(1.6); c.line(xs[2], ly, xs[2], ly - 24); c.line(xs[2], ly - 24, xs[2] + 9, ly - 24)
        p = c.beginPath(); p.moveTo(xs[2] + 13, ly - 24); p.lineTo(xs[2] + 8, ly - 20.5); p.lineTo(xs[2] + 8, ly - 27.5); p.close(); c.setFillColor(LGREEN); c.drawPath(p, fill=1, stroke=0)
        c.setFont("Inter-Bold", 7); c.drawCentredString(xs[2], ly - 35, "Right turn")
        draw_spot(c, 2, xs[3], ly + 14, 6.5); c.setFillColor(RED); c.setFont("Inter-Bold", 7); c.drawCentredString(xs[3], ly + 26, "Spot 2")
        c.setStrokeColor(INK); c.setLineWidth(1.2); c.line(xs[3], ly - 6, xs[3], ly + 6)
        c.setFillColor(SLATE); c.setFont("Inter-Regular", 6.8); c.drawCentredString(xs[3], ly - 14, "tunnel, no turnaround")
        c.setFillColor(INK); c.setFont("Inter-Bold", 6.8)
        for a, b, t in [(x0, xs[0], "0.1"), (xs[0], xs[1], "0.5"), (xs[1], xs[2], "0.2"), (xs[2], xs[3], "0.4")]:
            c.drawCentredString((a + b) / 2, ly + 4, t)


def leg_routes(lg):
    """(label, key) for each route of a leg: primary, alternate and alternate 2 (3 routes is the default; a plan asked for 2 has no alternate 2)."""
    r = [("Primary", "primary"), ("Alternate", "alternate")]
    if lg.get("strip", {}).get("alternate2"): r.append(("Alternate 2", "alternate2"))
    return r


def maps_url(lon, lat):
    """Directions to one point. Not used on the packet since v1.1.2 (route codes cover each trip); kept for other builders."""
    return "https://www.google.com/maps/dir/?api=1&destination=%.6f,%.6f" % (lat, lon)


# ---- QR code links (v1.1.2). Each code does one job and none repeats:
#   route code (strip page)      the whole route in Google Maps, through up to 3 points on it
#   location code (trip map)     a pin on one place, not directions
#   Street View code (leg map)   the drop-off curb
def _ll(p): return "%.5f,%.5f" % (p[1], p[0])

def pin_url(lon, lat):
    return "https://www.google.com/maps/search/?api=1&query=%.5f,%.5f" % (lat, lon)

def _m(a, b):
    import math
    R = 6371000.0; la1, la2 = math.radians(a[1]), math.radians(b[1]); dl = math.radians(b[0] - a[0])
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(min(1.0, h)))

def _bearing(a, b):
    import math
    la1, la2 = math.radians(a[1]), math.radians(b[1]); dl = math.radians(b[0] - a[0])
    y = math.sin(dl) * math.cos(la2); x = math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360

def _samples(line, step=40.0):
    """Points every step metres along the line, with their distance from the start (mid-block, not on corners)."""
    out, acc = [], 0.0
    for a, b in zip(line, line[1:]):
        d = _m(a, b)
        if d <= 0: continue
        t = (step - acc % step) if acc % step else step / 2
        while t < d:
            f = t / d; out.append(((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f), acc + t)); t += step
        acc += d
    return out, acc

def _point_at(line, dist):
    acc = 0.0
    for a, b in zip(line, line[1:]):
        d = _m(a, b)
        if d > 0 and acc + d >= dist:
            f = (dist - acc) / d; return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
        acc += d
    return tuple(line[-1])

def route_waypoints(route, others, k=3):
    """Up to k points that pin the phone to this route (Google Maps opens up to 3 waypoints on a phone browser).
    Each point sits about 50 m past one of the route's turns, on the new street or ramp, so the app has to make that turn.
    When a route has more turns than that, the code keeps the turns where it parts from the leg's other routes, spread out.
    With no turns listed, points are spread along the route instead."""
    from strip import along
    line = route["line"]; _, total = _samples(line, 1000)
    cands, last = [], 0.0
    for e in route.get("events", [])[1:-1]:
        if e.get("side") not in ("L", "R") or not e.get("pt"): continue
        pos, _ = along(line, e["pt"], last); last = pos
        d = min(pos + 50, total - 60)
        if d > 60 and all(abs(d - q) > 80 for _, q in cands): cands.append((_point_at(line, d), d))
    if not cands:
        pts = [(p, d) for p, d in _samples(line)[0] if 0.1 * total < d < 0.92 * total]
        cands = [min(pts, key=lambda x: abs(x[1] - f * total)) for f in (0.25, 0.5, 0.75)] if pts else []
        cands = [c for n_, c in enumerate(cands) if c not in cands[:n_]]
    if len(cands) > k:
        # keep the turns where this route parts from the leg's other routes, spread out along the way
        def gap(p): return min(min(_m(p, q) for q in o) for o in others if o) if others else 0
        ranked = sorted(cands, key=lambda x: (-round(gap(x[0]) / 40), x[1]))
        pick = []
        for c in ranked:
            if len(pick) < k and all(abs(c[1] - q[1]) > 0.12 * total for q in pick): pick.append(c)
        for c in ranked:
            if len(pick) < k and c not in pick: pick.append(c)
        cands = pick
    return [p for p, d in sorted(cands, key=lambda x: x[1])]

def route_url(line, wps):
    u = "https://www.google.com/maps/dir/?api=1&origin=%s&destination=%s&travelmode=driving" % (_ll(line[0]), _ll(line[-1]))
    if wps: u += "&waypoints=" + "%7C".join(_ll(p) for p in wps)
    return u

def pano_url(lon, lat, heading):
    return "https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=%.5f,%.5f&heading=%d&pitch=0" % (lat, lon, round(heading) % 360)

def _last_straight(line, tol=25.0):
    """Length of the route's final straight stretch: walk back from the end while the street keeps its direction."""
    n = len(line); j = n - 2
    while j > 0 and _m(line[j], line[-1]) < 12: j -= 1
    b0 = _bearing(line[j], line[-1]); dist = _m(line[j], line[-1]); i = j
    while i > 0:
        d = _m(line[i - 1], line[i])
        if d > 0:
            db = abs((_bearing(line[i - 1], line[i]) - b0 + 180) % 360 - 180)
            if db > tol: break
            dist += d
        i -= 1
    return dist, b0

def _back_along(line, back):
    """The point `back` metres before the end of the line, measured along it (so it stays on the road)."""
    acc = 0.0
    for k in range(len(line) - 1, 0, -1):
        a, b = line[k - 1], line[k]; d = _m(a, b)
        if d > 0 and acc + d >= back:
            f = (back - acc) / d; return (b[0] + (a[0] - b[0]) * f, b[1] + (a[1] - b[1]) * f)
        acc += d
    return tuple(line[0])

def dropoff_view(lg, line, last_text=""):
    """Street View point and heading for a leg's drop-off (v1.1.3).
    Point: on the primary route's own line, so on the road beside the drop-off, set back along the final straight
    stretch (40% of it, 12 to 30 m) so it sits mid-block rather than in the intersection the route ends at.
    Heading: from that point toward dropoff_view.look_at (the venue's building or entrance, from a geocode).
    With no look_at, it looks square at the curb the arrive line names (right unless it says left).
    dropoff_view.pt and dropoff_view.heading override either part by hand."""
    dv = lg.get("dropoff_view") or {}
    L, b = _last_straight(line)
    pt = dv.get("pt") or _back_along(line, max(12.0, min(30.0, 0.4 * L)))
    if "heading" in dv: return pt, dv["heading"]
    if dv.get("look_at"): return pt, _bearing(pt, dv["look_at"])
    left = "on the left" in last_text.lower() or "left curb" in last_text.lower()
    return pt, b + (-90 if left else 90)


class MiniQR(Flowable):
    """A small QR mark for the symbols panel."""
    def __init__(self, size=12): Flowable.__init__(self); self.size = size
    def wrap(self, aw, ah): return self.size, self.size
    def draw(self): draw_qr(self.canv, "QR", 0, 0, self.size)


class QRBox(Flowable):
    """A QR code with a label under it. The code is also a tap link in the PDF."""
    def __init__(self, url, label, sub="", size=78, width=None):
        Flowable.__init__(self); self.url, self.label, self.sub, self.size = url, label, sub, size
        self.w = width or size + 40; self.h = size + 30
    def wrap(self, aw, ah): return self.w, self.h
    def draw(self):
        c = self.canv; s = self.size; x0 = (self.w - s) / 2; y0 = 26
        draw_qr(c, self.url, x0, y0, s)
        c.setFillColor(NAVY); c.setFont("Inter-Bold", 8.5)
        lab = self.label
        while pdfmetrics.stringWidth(lab, "Inter-Bold", 8.5) > self.w and len(lab) > 4: lab = lab[:-2]
        c.drawCentredString(self.w / 2, 14, lab)
        if self.sub:
            c.setFillColor(SLATE); c.setFont("Inter-Regular", 7.2); c.drawCentredString(self.w / 2, 4, self.sub)


def qr_row(items, width, size=78):
    """items: (url, label, sub). One row of QR boxes spread across the width."""
    n = max(1, len(items)); cw = width / n
    t = Table([[QRBox(u, l, sb, size, cw - 6) for u, l, sb in items]], colWidths=[cw] * n)
    t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]))
    return t


def leg_ends(lg):
    """Short names of a leg's start and end: start_name / end_name if given, else the title split on ' to '."""
    parts = lg["title"].split(" to ")
    a = lg.get("start_name") or (parts[0] if len(parts) == 2 else "Start")
    b = lg.get("end_name") or (parts[1] if len(parts) == 2 else "Drop-off")
    return a[:1].upper() + a[1:], b[:1].upper() + b[1:]


def stop_name(sd):
    return sd.get("short_name") or sd["title"].split(",")[0]


def stops_for_legs(legs, stops):
    """Which stop overheads go on each leg map page: the leg's drop-off stop (leg n ends at stops[n mod count] on a
    round trip, or a leg's own `stop` index). A start that no leg ends at goes on leg 1 beside its drop-off."""
    out, used = [], set()
    for n, lg in enumerate(legs, start=1):
        i = lg.get("stop", n % len(stops) if len(stops) == len(legs) else min(n, len(stops) - 1))
        out.append([(stops[i], "Drop-off")]); used.add(i)
    if 0 not in used and stops:
        out[0].insert(0, (stops[0], "Start"))
    return out


def build(D, out_path):
    no_red(D)
    meta = D["meta"]; legs = D["legs"]; stops = D["stops"]
    nL, nS = len(legs), len(stops)
    leg_map_p, p = [], 4
    for lg in legs: leg_map_p.append(p); p += 1 + len(leg_routes(lg))
    leg_stops = stops_for_legs(legs, stops)
    p_med = p; p_recon = p_med + 1; p_form = p_recon + 1

    def on_page(c, doc):
        c.saveState()
        pw, ph = c._pagesize
        c.setFillColor(NAVY); c.rect(0, ph - 0.42 * inch, pw, 0.42 * inch, fill=1, stroke=0)
        c.setFillColor(colors.white); c.setFont("Inter-Bold", 9)
        c.drawString(0.65 * inch, ph - 0.27 * inch, "ROUTE ADVANCE  |  %s  |  %s" % (meta["code_name"], meta["date_label"]))
        if meta.get("header_tag"):
            c.setFont("Inter-SemiBold", 8); c.setFillColor(AMBER)
            c.drawRightString(pw - 0.65 * inch, ph - 0.27 * inch, meta["header_tag"])
        c.setFillColor(SLATE); c.setFont("Inter-Regular", 7.5)
        c.drawString(0.65 * inch, 0.4 * inch, meta.get("footer", "Draft plan. Confirm by recon and current conditions before use.  Drive team only. Do not forward."))
        c.drawRightString(pw - 0.65 * inch, 0.4 * inch, "Page %d" % doc.page)
        c.restoreState()

    doc = BaseDocTemplate(out_path, pagesize=letter, leftMargin=0.65 * inch, rightMargin=0.65 * inch,
                          topMargin=0.65 * inch, bottomMargin=0.65 * inch,
                          title=meta.get("doc_title", "Route advance - %s" % meta["code_name"]), author=meta.get("author", "Route advance"))
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
    LW, LH = landscape(letter)
    lframe = Frame(0.65 * inch, 0.6 * inch, LW - 1.3 * inch, LH - 1.2 * inch, id="lf", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=on_page),
                          PageTemplate(id="l", frames=[lframe], onPage=on_page, pagesize=landscape(letter))])
    STRIP_W, STRIP_H = LW - 1.3 * inch, LH - 1.2 * inch
    S = []

    # ---------- 1. HOW TO READ THIS PLAN ----------
    HT = ParagraphStyle("ht", parent=BS, fontSize=8, leading=10.4)
    HTB = ParagraphStyle("htb", parent=HT, fontName="Inter-SemiBold")
    PH = ParagraphStyle("ph", parent=H2, fontSize=11, leading=13.5, spaceBefore=0, spaceAfter=5)
    IW = W - 2 * PAD          # inner width of a full-width panel
    S += [P("START HERE", KICK), P("How to read this plan", H1),
          P("A quick outline of the public information a small drive team needs for this move. It does not replace the advance drive: "
            "the team drives the routes, checks them and decides. Work through the checklist on page %d before the move." % p_recon, BS),
          Spacer(1, GAP)]

    # 1. Information needed
    inp_req = [("Locations", "Start, each stop in order, and the end."),
               ("Date", "The day of the move."),
               ("Departure time", "When the principal leaves the start.")]
    inp_opt = [("Principal code name", "ATLAS (never the real name)."),
               ("Number of cars", "1."),
               ("Routes per leg", "3. Or 2 if you ask."),
               ("Greeter at the event site", "None."),
               ("Time at each stop", "1 hour."),
               ("Risk level", "Medium. For reviewers only.")]
    def kvt(rows, w, kw=0.36):
        t = Table([[P("<b>%s</b>" % a, HTB), P(b, HT)] for a, b in rows], colWidths=[w * kw, w * (1 - kw)])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 1.6),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6), ("LINEBELOW", (0, 0), (-1, -2), 0.3, LINE)]))
        return t
    hw = (IW - 18) / 2
    req = [P("Required", HTB), Spacer(1, 2), kvt(inp_req, hw, 0.34)]
    opt = [P("Optional, with the default if left blank", HTB), Spacer(1, 2), kvt(inp_opt, hw, 0.42)]
    S += [panel("1.  Information needed to build this plan", [cols([req, opt], IW)], W), Spacer(1, GAP)]

    # 2. Symbols
    def sym(draw, label, desc): return [draw, P("<b>%s</b> %s" % (label, desc), HT)]
    def line_sw(col):
        t = Table([[""]], colWidths=[16], rowHeights=[4]); t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), col)])); return t
    syms = [
        sym(line_sw(BLUE), "Blue line:", "primary route."),
        sym(line_sw(AMBER), "Amber line:", "alternate route (teal: second alternate)."),
        sym(Spot("1", 11), "Red number:", "predictable spot."),
        sym(Icon("cp", 12), "CP1 to CP3:", "checkpoint calls."),
        sym(Badge("2", AMBER, 12), "Numbered circle:", "a stop."),
        sym(Icon("hospital", 11), "Red cross:", "trauma center."),
        sym(Icon("police", 11), "Blue shield:", "police."),
        sym(Icon("fire", 11), "Orange flame:", "fire station."),
        sym(Icon("secure", 11), "Green house:", "secure lobby."),
        sym(Icon("warn", 11), "Amber triangle:", "watch-out."),
        sym(Icon("event", 11), "Purple ticket:", "event or crowd."),
        [Badge("D", NAVY, 12), P("On stop photos: <b>D</b> car stops, <b>B</b> backup, <b>R</b> rally.", HT)],
    ]
    ncol = 3; cw = IW / ncol
    grid = []
    for r in range((len(syms) + ncol - 1) // ncol):
        row = []
        for c in range(ncol):
            k = c * ((len(syms) + ncol - 1) // ncol) + r
            if k < len(syms):
                t = Table([syms[k]], colWidths=[22, cw - 30])
                t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5)]))
                row.append(t)
            else:
                row.append("")
        grid.append(row)
    symt = Table(grid, colWidths=[cw] * ncol)
    symt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                              ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    S += [panel("2.  Symbols", [symt], W), Spacer(1, GAP)]

    # 3. Key terms
    terms = D.get("terms") or [
        ("Leg", "One drive from one place to the next."),
        ("Primary / alternates", "The planned route, and two more on different roads."),
        ("Predictable spot", "A place we must pass at a known time, like a curb."),
        ("Choke point", "No way out, like a tunnel or one-way block."),
        ("If blocked, go", "Where to go if a spot is blocked. Decided now."),
        ("Backup point", "A second curb if the planned one is blocked."),
        ("Rally point", "Where everyone meets if separated or comms fail."),
        ("Safe haven", "Police, fire, hospital or a staffed lobby nearby."),
        ("Recon to confirm", "Not visible on a map. Check it on the drive."),
        ("Hand-off", "Drive team owns route and curb; site advance owns past the door."),
    ]
    half = (len(terms) + 1) // 2
    S += [panel("3.  Key terms", [cols([[kvt(terms[:half], hw, 0.32)], [kvt(terms[half:], hw, 0.32)]], IW)], W), Spacer(1, GAP)]

    # 4. Strip map and 5. Verdicts, side by side
    PW2 = (W - GAP) / 2; IW2 = PW2 - 2 * PAD
    strip_p = panel("4.  How to read a strip map", [MiniStrip(IW2),
              P("Drive left to right. <font color='#1F5FBF'><b>Above the line = left turn.</b></font> <font color='#2E8540'><b>Below the line = right turn.</b></font> "
                "A tick on the line is a straight-on event like a tunnel or merge. Numbers on the line are miles between turns. Not to scale. "
                "<b>QR codes</b> say what they open. Each strip page's route code opens that route in Google Maps; the app may reroute in traffic.", HT)], PW2)
    def vrow(level, txt):
        return [Verdict(level, 46, 13), P(txt, HT)]
    vt = Table([vrow("GREEN", "<b>Go as planned.</b> Nothing public found that should change the plan."),
                vrow("AMBER", "<b>Go, with the notes.</b> Something public could slow or crowd you: an event, a closure, one way in, a tight closing time, weather."),
                vrow("RED", "<b>The team's call only.</b> After the advance drive, the team marks a leg or stop red if it should not be driven as written. This plan never sets red.")],
               colWidths=[54, IW2 - 54])
    vt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 3),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINE)]))
    verd_p = panel("5.  Verdicts", [vt, Spacer(1, 3), P("Every leg and stop gets green or amber with its reason, from public data. The worst one sets the overall verdict.", SM)], PW2)
    S += [cols([[strip_p], [verd_p]], W, gap=GAP), PageBreak()]

    # ---------- 2. COVER ----------
    cv = D["cover"]; inp = D.get("inputs")
    S += [P("DRIVE TEAM PACKET", KICK), P(cv["title"], H1)]
    if cv.get("intro"): S.append(P(cv["intro"], SM))
    S.append(Spacer(1, GAP))
    if inp:
        risk = inp.get("risk") or "Medium (default)"
        facts = [("Principal", "%s (code name)" % inp.get("code_name", meta["code_name"])),
                 ("Date", inp.get("date", meta["date_label"])),
                 ("Departs", inp.get("start_time", "")),
                 ("Cars", str(inp.get("cars") or "1 (default)")),
                 ("Routes per leg", str(inp.get("routes") or "3 (default)")),
                 ("Greeter at the event site", inp.get("greeter") or "None given"),
                 ("Risk level", "%s. For reviewers; the plan is the same at any level." % risk)]
        gw = (IW - 18) / 2
        half = (len(facts) + 1) // 2
        top = cols([[kvt(facts[:half], gw, 0.34)], [kvt(facts[half:], gw, 0.42)]], IW)
        stops_t = kvt([(a, b) for a, b in inp.get("stops", [])], IW, 0.14)
        S += [panel("General info", [top, Spacer(1, 6), stops_t], W), Spacer(1, GAP)]
    else:
        S += [panel("General info", [kv([tuple(r) for r in cv["facts"]])], W), Spacer(1, GAP)]

    LPW = W * 0.56; RPW = W - LPW - GAP; LIW = LPW - 2 * PAD; RIW = RPW - 2 * PAD
    TLS = ParagraphStyle("tl", parent=B, fontSize=8.6, leading=11)
    TLD = ParagraphStyle("tld", parent=SM, fontSize=8, leading=10)
    ov = cv["overall"]
    ovt = Table([[Verdict(ov["level"], 52, 15), P("<b>Overall.</b> " + ov["why"], TLS)]], colWidths=[60, LIW - 60])
    ovt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    tl_rows, tst = [], [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    for i, r in enumerate(cv["timeline"]):
        stop = r.get("kind", "stop") == "stop"
        v = r.get("verdict", "")
        if stop:
            bc = r.get("badge_color") or {"GREEN": "green", "AMBER": "amber"}.get(v, "navy")
            tl_rows.append([Badge(r.get("badge", ""), color(bc)), P(r.get("time", ""), TLS), P(r["text"], TLS), Verdict(v, 42, 12) if v else ""])
            tst.append(("BACKGROUND", (1, i), (-1, i), PALE))
        else:
            tl_rows.append([Icon("car", 13), P(r["text"], TLD), "", Verdict(v, 42, 12) if v else ""])
            tst.append(("SPAN", (1, i), (2, i)))
    tlt = Table(tl_rows, colWidths=[24, 62, LIW - 24 - 62 - 48, 48]); tlt.setStyle(TableStyle(tst))
    left_p = panel("Time and verdicts", [ovt, Spacer(1, 8), tlt, Spacer(1, 5), P(cv.get("drive_times_note", ""), SM)], LPW)
    WO = ParagraphStyle("wo", parent=BS, fontSize=8, leading=10.4)
    watch = [icon_row(w["icon"], w["text"], WO) for w in cv["watch_outs"]]
    right_p = panel("Weather and watch-outs", [WeatherCard(RIW, D["weather"]), Spacer(1, 8)] + watch, RPW)
    S += [cols([[left_p], [right_p]], W, gap=GAP, split=LPW), PageBreak()]

    # ---------- 3. TRIP MAP + EVENTS ----------
    tm = D["trip_map"]; ev = D["events"]
    S += [P("TRIP MAP", KICK), P(tm["title"], H1)]
    S += img(tm.get("image"), W * 0.86)
    S += [Spacer(1, 3), legend([(color(c), l) for c, l in tm["legend"]]), P(tm.get("caption", ""), SM), Spacer(1, 6)]
    pts = []   # start, then the end of each leg; skip an end that comes back to a place already listed
    for i, lg in enumerate(legs):
        line = lg["strip"]["primary"]["line"]; a_, b_ = leg_ends(lg)
        if i == 0: pts.append((a_, line[0]))
        if not any(abs(line[-1][0] - q[1][0]) < 0.0015 and abs(line[-1][1] - q[1][1]) < 0.0015 for q in pts):
            pts.append((b_, line[-1]))
    subs = ["Start" + (" and end" if len(pts) == nL else "")] + ["Stop %d" % k for k in range(1, len(pts))]
    if len(pts) == nL + 1: subs[-1] = "End"
    # v1.1.2: every per-place code sits here, once: a location pin and a Street View of the curb for each place.
    # The curb is where the car stops: the end of the leg that drops off there, or for the start, the pick-up point.
    views = []
    for nm, pt in pts:
        lg_in = next((lg for lg in legs if _m(lg["strip"]["primary"]["line"][-1], pt) < 160), None)
        if lg_in:
            ln = lg_in["strip"]["primary"]["line"]; ev_last = (lg_in["strip"]["primary"].get("events") or [{}])[-1]
            views.append(dropoff_view(lg_in, ln, ev_last.get("text", "")))
        else:
            ln = legs[0]["strip"]["primary"]["line"]; j = 1
            while j < len(ln) - 1 and _m(ln[0], ln[j]) < 25: j += 1
            views.append((ln[0], _bearing(ln[0], ln[j]) + 90))
    ncode = 2 * len(pts); cw = W / ncode; qs = min(66, cw - 16)
    head = []; codes = []
    for (nm, pt), sb, (vpt, vhd) in zip(pts, subs, views):
        head += [P("<b>%s</b> <font color='#5A6577'>(%s)</font>" % (nm, sb.lower()), ParagraphStyle("qh", parent=BS, fontSize=8.6, leading=10.5, alignment=1)), ""]
        codes += [QRBox(pin_url(*pt), "Location", "pin, not directions", qs, cw - 4),
                  QRBox(pano_url(vpt[0], vpt[1], vhd), "Street View", "the curb", qs, cw - 4)]
    qt = Table([head, codes], colWidths=[cw] * ncode)
    qst = [("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "TOP"),
           ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2), ("TOPPADDING", (0, 0), (-1, -1), 1)]
    for k in range(len(pts)):
        qst.append(("SPAN", (2 * k, 0), (2 * k + 1, 0)))
        if k: qst.append(("LINEBEFORE", (2 * k, 0), (2 * k, 1), 0.5, LINE))
    qt.setStyle(TableStyle(qst))
    S += [P("Place codes: a pin and a Street View for each place", H2), qt,
          P("Each route's code, which loads the whole route into Google Maps, is on its strip page.", SM)]
    key = ev.get("key") or ["<b>%s</b>: %s" % (r[0].replace("<b>", "").replace("</b>", ""), r[2]) for r in ev["rows"][:3]]
    S += [P("Events that touch the route", H2)] + [icon_row("event", k) for k in key[:3]]
    S += [Spacer(1, 3), P(ev.get("note", ""), SM), PageBreak()]

    # ---------- LEGS: map page (visual), then one strip page per route ----------
    VR = ParagraphStyle("vr", parent=BS, fontSize=9, leading=11.5)
    HTB2 = ParagraphStyle("htb2", parent=BS, fontName="Inter-SemiBold", fontSize=9, leading=11.5, textColor=NAVY, spaceAfter=2)
    for n, lg in enumerate(legs, start=1):
        routes = leg_routes(lg); mp = leg_map_p[n - 1]
        if len(routes) == 3 and int(lg.get("map_routes", 2)) < 3:
            print("WARNING: leg %d has a second alternate but its map image does not show it. Draw a fresh leg map "
                  "with all three routes (alternate 2 in teal #178A86) and set map_routes to 3." % n, file=sys.stderr)
        strip_pages = list(range(mp + 1, mp + 1 + len(routes)))
        pg = " AND ".join(", ".join(str(x) for x in strip_pages).rsplit(", ", 1))
        S += [P("LEG %d  |  DEPART %s  |  TURN BY TURN ON PAGES %s" % (n, lg["depart"], pg), KICK), P(lg["title"], H1)]
        vt = Table([[Verdict(lg["verdict"][0], 56, 15), P(lg["verdict"][1], VR)]], colWidths=[66, W - 66])
        vt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
        S += [vt, Spacer(1, 6)]
        S += img(lg.get("map_image"), W * 0.74)
        lg_items = [(BLUE, "Primary"), (AMBER, "Alternate")] + ([(TEAL, "Alternate 2")] if len(routes) == 3 else []) + \
                   [("spot", "Predictable spot"), (NAVY, "Trauma center")]
        S += [Spacer(1, 2), legend(lg_items), Spacer(1, 3)]
        times = []
        for label, key in routes:
            r = lg.get(key)
            if r: times.append("<b>%s</b> %s, %s" % (label, r[1], r[2]))
        S += [P(".&nbsp;&nbsp; ".join(times) + ".", VR), Spacer(1, 6)]
        # bottom row: overhead view of the stop(s) on this leg. No codes here since v1.1.2: place codes are on the
        # trip map page and each route's code is on its strip page, so no code appears twice.
        shown = leg_stops[n - 1]
        iw = W * 0.62 if len(shown) == 1 else W / len(shown) - 14
        cells = []
        for sd, role in shown:
            cells.append([P("<b>%s:</b> %s" % (role, stop_name(sd)), HTB2)] + img(sd.get("image"), iw) +
                         [Spacer(1, 2), P(sd.get("points") or sd.get("caption", ""), SM)])
        side = [P("<b>QR codes</b>", HTB2), P("Pin and Street View for each place: page 3.", SM), Spacer(1, 4),
                P("Route codes for this leg: pages %s, with the turns, spots, closures and where to go if blocked." % pg.lower(), SM)]
        if len(shown) == 1:
            row = Table([cells + [side]], colWidths=[iw + 14, W - iw - 14])
        else:
            row = Table([cells], colWidths=[iw + 14] * len(shown))
        row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
        S += [row] + ([Spacer(1, 3), P("QR codes: pin and Street View for each place on page 3; route codes for this leg on pages %s." % pg.lower(), SM)] if len(shown) > 1 else [])
        st = lg["strip"]
        S += [NextPageTemplate("l"), PageBreak()]
        for i, (kind, key) in enumerate(routes):
            route = st[key]
            sp = StripPage(kind, n, nL, route, place_events(route), _notes(st.get(key + "_notes", [])), STRIP_W, STRIP_H)
            sp.map_page = mp
            others = [st[k2]["line"] for _, k2 in routes if k2 != key and st.get(k2)]
            wps = route["waypoints"] if "waypoints" in route else route_waypoints(route, others)
            sp.route_qr = route_url(route["line"], wps)
            sp.route_qr_via = "%d point%s on it" % (len(wps), "" if len(wps) == 1 else "s") if wps else "no extra points"
            print("ROUTE CODE leg %d %s: %s" % (n, kind, sp.route_qr))
            S.append(sp)
            S.append(PageBreak() if i < len(routes) - 1 else NextPageTemplate("p"))
        S.append(PageBreak())

    # (stops have no pages of their own: each overhead sits on the map page of the leg that drops off there)

    # ---------- MEDICAL ----------
    md = D["medical"]
    S += [P("MEDICAL AND SAFE HAVENS", KICK), P("Hospital runs and help nearby", H1)]
    def _ti(t):
        k = {"Police": "police", "Fire": "fire", "Secure venue": "secure"}.get(t, "hospital" if "Trauma" in t else None)
        return icon_row(k, t, ParagraphStyle("mti", parent=BS, fontSize=8, leading=10), 9) if k else t
    ns = len(md["from"]); cw = 0.3 / ns
    # v1.1.3: page 1 styling. Each section is a numbered panel, with clear space between them,
    # and each hospital run sits in its own white box inside the second panel.
    IWm = W - 2 * PAD; sc = IWm / W
    WHITE = colors.white
    ht = table(["Place", "Type"] + ["From " + f for f in md["from"]] + ["Check"], [[r[0], _ti(r[1])] + r[2:] for r in md["rows"]],
               [x * sc for x in [0.31, 0.19] + [cw] * ns + [0.2]], zebra=False,
               extra=[("BACKGROUND", (0, 1), (-1, -1), WHITE)])
    S += [panel("1.  Help nearby: hospitals, police, fire and safe places", [ht, Spacer(1, 4), P(md.get("times_note", ""), SM)], W),
          Spacer(1, GAP + 7)]
    HR = ParagraphStyle("hr", parent=BS, fontSize=7.8, leading=10.2, leftIndent=9, bulletIndent=0, spaceBefore=1.5)
    HH = ParagraphStyle("hh", parent=BS, fontName="Inter-Bold", fontSize=8.6, leading=11, textColor=RED)
    nrun = len(md["runs"]); rg = 8; rw = (IWm - rg * (nrun - 1)) / nrun
    def run_box(r):
        body = [P(r["head"], HH), P(r["sub"], SM), Spacer(1, 3)] + [Paragraph(x, HR, bulletText="%d" % (i + 1)) for i, x in enumerate(r["steps"])]
        t = Table([[body]], colWidths=[rw])
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), WHITE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                               ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                               ("ROUNDEDCORNERS", [5, 5, 5, 5])]))
        return t
    row = []
    for i, r in enumerate(md["runs"]):
        if i: row.append("")
        row.append(run_box(r))
    rt = Table([row], colWidths=sum(([rg, rw] if i else [rw] for i in range(nrun)), []))
    rt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                            ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    S += [panel("2.  " + md["runs_title"], [rt, Spacer(1, 5), P(md.get("runs_note", ""), SM)], W)]
    if md.get("kit_note"): S += [Spacer(1, GAP + 7), panel("3.  Not in this packet", [P(md["kit_note"], BS)], W)]
    S.append(PageBreak())

    # ---------- CHECKLIST: RECON, DAY-OF, COMMS ----------
    rc = D["recon"]
    CK = ParagraphStyle("ck", parent=BS, fontSize=8.8, leading=11.4)
    IWc = W - 2 * PAD
    def checks(items, width=IWc):
        rows = []
        for t in items:
            bx = Table([[""]], colWidths=[9], rowHeights=[9]); bx.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.8, INK)]))
            rows.append([bx, P(t, CK)])
        t = Table(rows, colWidths=[22, width - 22])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                               ("LEFTPADDING", (0, 0), (0, -1), 7), ("LEFTPADDING", (1, 0), (1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                               ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                               ("TOPPADDING", (0, 0), (-1, 0), 6), ("BOTTOMPADDING", (0, -1), (-1, -1), 6),
                               ("LINEBELOW", (0, 0), (-1, -2), 0.3, LINE), ("ROUNDEDCORNERS", [5, 5, 5, 5])]))
        return t
    # v1.1.4: page 1 styling, as on the medical page. Each section is a numbered panel with clear space between them.
    S += [P("RECON, DAY-OF AND COMMS", KICK), P("Checklist before the move", H1)]
    if rc.get("intro_short"): S += [P(rc["intro_short"], SM), Spacer(1, 6)]
    sp = Spacer(1, GAP + 3)
    S += [panel("1.  Recon drive", [checks(["<b>%s:</b> %s" % (r[1], r[2]) for r in rc["rows"]])], W), sp]
    S += [panel("2.  Day before and day of", [checks(rc["day_of"])], W), sp]
    comms = rc.get("comms_checks") or (
        ["Code words agreed: " + ". ".join("%s = %s" % (w.replace('"', ""), m[:1].lower() + m[1:]) for w, m in rc["code_words"]) + "."] +
        ["Comms-down rule briefed: " + " ".join(rc["comms_down"])])
    S += [panel("3.  Comms", [checks(comms)], W)]
    if rc.get("confidence"):
        S += [sp, panel("4.  How sure are we", [P(c, SM) for c in rc["confidence"]], W)]
    S.append(PageBreak())

    # ---------- BLANK FORMS ----------
    def form_table(header, nrows, widths, h=22, prefill=None):
        rows = []
        for i in range(nrows):
            r = [""] * len(header)
            if prefill and i < len(prefill): r[:len(prefill[i])] = prefill[i]
            rows.append([P(c, FORM) for c in r])
        t = Table([[P(x, TH) for x in header]] + rows, colWidths=[w * W for w in widths], rowHeights=[None] + [h] * nrows)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("GRID", (0, 1), (-1, -1), 0.5, LINE),
                               ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 3)]))
        return t
    def box_list(items, cols=2):
        def cb(t):
            bx = Table([[""]], colWidths=[8], rowHeights=[8]); bx.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.8, INK)]))
            r = Table([[bx, P(t, BS)]], colWidths=[14, W / cols - 20])
            r.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
            return r
        cells = [cb(t) for t in items]
        while len(cells) % cols: cells.append("")
        t = Table([cells[i:i + cols] for i in range(0, len(cells), cols)], colWidths=[W / cols] * cols)
        t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
        return t
    fm = D["forms"]
    S += [P("FORM  |  FILL IN ON THE RECON DRIVE", KICK), P("Recon log: planned vs driven", H1),
          kv([("Driven by", ""), ("Date and time", "Same weekday and time of day as the move, if possible"), ("Vehicle", "")])]
    nr = max(len(fm["recon_routes"]), 6)   # 3 routes per leg gives more rows: keep the block the height of 10 rows so the form stays on one page
    S += [P("Routes", H2), form_table(["Leg and route", "Planned min", "Driven min", "Planned mi", "Driven mi", "Traffic, closures, notes"],
                                      nr, [0.27, 0.1, 0.1, 0.1, 0.1, 0.33], min(24, 240.0 / nr), fm["recon_routes"])]
    S += [P("Red spots and stops", H2), form_table(["Spot or stop", "What we saw", "If blocked option driven?"], max(len(fm["recon_spots"]), 6),
                                                   [0.3, 0.45, 0.25], 26, fm["recon_spots"])]
    S += [P("Day-before re-check", H2), box_list(["Closures and roadworks re-read", "Events check re-run (page 3)", "Forecast read",
          "Rally point lobbies still open late", "Changes since recon driven again", "Packet updated and re-sent"]), PageBreak()]
    S += [P("FORM  |  FILL IN WITHIN 24 HOURS OF THE MOVE", KICK), P("After-move note", H1),
          P("Two minutes, while it is fresh. It starts the next advance for this principal or these places.", SM), Spacer(1, 4),
          kv([("Move and date", ""), ("Filled in by", "")])]
    for q, h in [("What went to plan", 52), ("What changed (route, timing, curb, door)", 52), ("Red spots that were blocked, and what we did", 52),
                 ("Times driven vs planned", 40), ("Anything to fix in the next packet", 52), ("Places to add or drop (stops, havens, rally points)", 40)]:
        t = Table([[P("<b>%s</b>" % q, BS)], [""]], colWidths=[W], rowHeights=[None, h])
        t.setStyle(TableStyle([("LINEBELOW", (0, 1), (-1, 1), 0.6, LINE), ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                               ("BACKGROUND", (0, 0), (-1, 0), PALE), ("LEFTPADDING", (0, 0), (-1, -1), 6)]))
        S += [t, Spacer(1, 6)]
    S += [Spacer(1, 4), note("Draft plan. Confirm by recon and current conditions before use.")]
    doc.build(S)
    expected = p_form + 1
    if doc.page != expected:
        print("WARNING: %d pages, expected %d. A page ran over, so page numbers on page 1 are off. Shorten the text on the page that overflowed and build again." % (doc.page, expected))
    return doc.page


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: build_packet.py trip.json out.pdf")
    src = os.path.abspath(sys.argv[1])
    IMG_DIR = os.path.dirname(src)
    with open(src) as f:
        data = json.load(f)
    n = build(data, sys.argv[2])
    print("wrote %s, %d pages" % (sys.argv[2], n))
