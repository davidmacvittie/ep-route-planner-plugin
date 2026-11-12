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
from visuals import Icon, Badge, Verdict, Spot, WeatherCard, StripPage, draw_icon, draw_spot, LBLUE, LGREEN
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


def build(D, out_path):
    meta = D["meta"]; legs = D["legs"]; stops = D["stops"]
    nL, nS = len(legs), len(stops)
    p_stop0 = 4 + 3 * nL; p_med = p_stop0 + nS; p_recon = p_med + 1; p_driver = p_recon + 1; p_form = p_driver + 1

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
    HT = ParagraphStyle("ht", parent=BS, fontSize=7.7, leading=9.8)
    HTB = ParagraphStyle("htb", parent=HT, fontName="Inter-SemiBold")
    HH2 = ParagraphStyle("hh2", parent=H2, fontSize=10.5, leading=13, spaceBefore=4, spaceAfter=2)
    S += [P("START HERE", KICK), P("How to read this plan", H1),
          P("The plan follows the move in order: the whole trip first, then each leg, then each stop, then what to do when something goes wrong. "
            "Read pages 1 to 3 before the recon drive. In the car, the driver card on page %d is the one page you need." % p_driver, BS), Spacer(1, 2)]
    leg_ranges = ", ".join("leg %d is %s" % (i + 1, ("pages " if i == 0 else "") + pages_text(4 + 3 * i, 6 + 3 * i)) for i in range(nL))
    leg_ranges = leg_ranges[0].upper() + leg_ranges[1:]
    pages = [
        ("1", "How to read this plan", "This page."),
        ("2", "Cover", "The move at a glance: stops, times, the verdict for each leg and stop, weather and watch-outs."),
        ("3", "Trip map and events check", "All legs on one map, and anything in town that could block or crowd us."),
        (pages_text(4, 3 + 3 * nL), "Leg 1" if nL == 1 else "Legs 1 to %d" % nL,
         "Each leg's map view, then the linear view of the same leg: primary and alternate strip maps. %s." % leg_ranges),
        (pages_text(p_stop0, p_med - 1), "Stops", "One page per place: overhead view, curb, door, backup point, where the car waits, rally point, hand-off."),
        (str(p_med), "Medical", "Trauma center and help nearby, with the hospital run turn by turn from each stop."),
        (str(p_recon), "Recon, day-of checks, comms", "What to confirm on the recon drive, checks on the day, code words and the comms-down rule."),
        (str(p_driver), "Driver card", "The whole plan on one page for the car."),
        (pages_text(p_form, p_form + 1), "Blank forms", "Recon log (planned vs driven) and the after-move note."),
    ]
    S.append(table(["Page", "What it is", "What's on it"], [["<b>%s</b>" % a, "<b>%s</b>" % b, c] for a, b, c in pages], [0.1, 0.25, 0.65], style=HT,
                   extra=[("TOPPADDING", (0, 1), (-1, -1), 2), ("BOTTOMPADDING", (0, 1), (-1, -1), 2)]))

    def vrow(level, meaning, act):
        return [Verdict(level, 46, 13), P("<b>%s</b>" % meaning, HT), P(act, HT)]
    vt = Table([vrow("GREEN", "Go as planned", "Nothing to change. Drive the primary."),
                vrow("AMBER", "Go, with the notes", "Read the notes on that page. Usually a backup point, timing or a recon item."),
                vrow("RED", "Change the plan", "Do not drive it as written. Fix it, or move the time or the stop.")],
               colWidths=[54, 92, None])
    vt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 2), ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5), ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINE)]))
    vleft = [P("Verdicts: green, amber, red", HH2), vt,
             P("Every leg, every stop and the whole move get one. The worst leg or stop sets the overall verdict.", SM)]

    def sym(draw, label, desc): return [draw, P("<b>%s</b> %s" % (label, desc), HT)]
    def line_sw(col):
        t = Table([[""]], colWidths=[16], rowHeights=[4]); t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), col)])); return t
    syms = [
        sym(line_sw(BLUE), "Blue line:", "primary route."),
        sym(line_sw(AMBER), "Amber line:", "alternate route."),
        sym(Spot("1", 11), "Red number:", "predictable spot. Read its <b>if blocked, go</b> line."),
        sym(Icon("cp", 12), "CP1, CP2, CP3:", "checkpoints. Call each one in: rolling, call in, 2 min out."),
        sym(Badge("2", AMBER, 12), "Numbered circle:", "a stop on the timeline."),
        sym(Icon("hospital", 11), "Red cross:", "trauma center."),
        sym(Icon("police", 11), "Blue shield:", "police station."),
        sym(Icon("fire", 11), "Orange flame:", "fire station."),
        sym(Icon("secure", 11), "Green house:", "secure venue to wait in, like a hotel lobby."),
        sym(Icon("warn", 11), "Amber triangle:", "watch-out: closures, roadworks, security zones."),
        sym(Icon("event", 11), "Purple ticket:", "event that could crowd the route."),
    ]
    symt = Table(syms, colWidths=[20, None])
    symt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 1), ("TOPPADDING", (0, 0), (-1, -1), 1.2), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.2)]))
    vleft += [P("Symbols", HH2), symt,
              P("On the stop photos: <b>D</b> = where the car stops, <b>B</b> = backup point, <b>R</b> = rally point.", SM)]
    terms = D.get("terms") or [
        ("Leg", "One drive from one place to the next."),
        ("Primary / alternate", "The planned route, and a second one that shares as little road with it as possible."),
        ("Predictable spot", "A place we must pass or stop at a known time, like a curb or a tunnel. Where an attack is easiest to plan."),
        ("Choke point", "A place with no way out, like a tunnel, ramp or one-way block."),
        ("If blocked, go", "Where to go when a spot is blocked. Decide it now, not in the car."),
        ("Backup point", "A second curb if the planned one is blocked."),
        ("Rally point", "Where everyone meets if separated or comms go down."),
        ("Safe haven", "Somewhere close to get the principal inside: police, fire, hospital or a staffed lobby."),
        ("Comms-down rule", "What to do with no contact: 5 min, go to the rally point; phones down, wait 15 min, then return to the hotel."),
        ("Recon to confirm", "Could not be seen on a map. Check it on the recon drive."),
        ("Hand-off", "The drive team owns the route and the curb. The site advance owns everything past the door."),
    ]
    tt = Table([[P("<b>%s</b>" % a, HTB), P(b, HT)] for a, b in terms], colWidths=[78, None])
    tt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 2), ("TOPPADDING", (0, 0), (-1, -1), 1.8),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8), ("LINEBELOW", (0, 0), (-1, -2), 0.3, LINE)]))
    RW = W * 0.5 - 8
    vright = [P("Strip maps: how to read the line", HH2), MiniStrip(RW),
              P("Drive left to right. <font color='#1F5FBF'><b>Above the line = left turn.</b></font> <font color='#2E8540'><b>Below the line = right turn.</b></font> "
                "A tick on the line is a straight-on event like a tunnel or merge. Numbers on the line are miles between turns. Not to scale.", HT),
              P("Key terms", HH2), tt]
    two = Table([[vleft, vright]], colWidths=[W * 0.5, W * 0.5])
    two.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (0, -1), 14)]))
    S += [two, PageBreak()]

    # ---------- 2. COVER ----------
    cv = D["cover"]
    S += [P("DRIVE TEAM PACKET", KICK), P(cv["title"], H1), P(cv["intro"], SM), Spacer(1, 6)]
    S.append(kv([tuple(r) for r in cv["facts"]] + [("Overall", vtext(cv["overall"]["level"], cv["overall"]["why"]))]))
    TLS = ParagraphStyle("tl", parent=B, fontSize=8.4, leading=10.8)
    TLD = ParagraphStyle("tld", parent=SM, fontSize=7.3, leading=9.2)
    tl_rows, tst = [], [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    for i, r in enumerate(cv["timeline"]):
        stop = r.get("kind", "stop") == "stop"
        mark = Badge(r.get("badge", ""), color(r.get("badge_color", "navy"))) if stop else Icon("car", 14)
        v = r.get("verdict", "")
        tl_rows.append([mark, P(r["time"], TLS if stop else TLD), P(r["text"], TLS if stop else TLD), Verdict(v, 40, 12) if v else ""])
        if stop: tst.append(("BACKGROUND", (1, i), (-1, i), PALE))
    tlt = Table(tl_rows, colWidths=[22, 80, None, 44]); tlt.setStyle(TableStyle(tst))
    WO = ParagraphStyle("wo", parent=BS, fontSize=7.9, leading=10.2)
    watch = [icon_row(w["icon"], w["text"], WO) for w in cv["watch_outs"]]
    leftcol = [P("Timeline and verdicts", H2), tlt, Spacer(1, 4), P(cv.get("drive_times_note", ""), SM)]
    rightcol = [P("Weather and light", H2), WeatherCard(W * 0.45, D["weather"]), Spacer(1, 4), P("Watch-outs", H2)] + watch
    cov = Table([[leftcol, rightcol]], colWidths=[W * 0.53, W * 0.47])
    cov.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (0, -1), 10)]))
    S += [cov, PageBreak()]

    # ---------- 3. TRIP MAP + EVENTS ----------
    tm = D["trip_map"]; ev = D["events"]
    S += [P("TRIP MAP AND EVENTS CHECK", KICK), P(tm["title"], H1)]
    S += img(tm.get("image"), W * 0.92)
    S += [Spacer(1, 3), legend([(color(c), l) for c, l in tm["legend"]]), P(tm.get("caption", ""), SM)]
    S += [P(ev["title"], H2), P(ev.get("note", ""), SM)]
    EV = ParagraphStyle("ev", parent=BS, fontSize=7.9, leading=10.1)
    S += [table(["What", "Where", "Effect on us"], ev["rows"], [0.29, 0.31, 0.4], style=EV), PageBreak()]

    # ---------- LEGS: map page, then primary and alternate strips ----------
    LEG_LEGEND = legend([(BLUE, "Primary"), (AMBER, "Alternate"), ("spot", "Predictable spot (numbered)"), (NAVY, "Cross = trauma center")])
    bb = ParagraphStyle("bb", parent=BUL, fontSize=8, leading=10.5)
    for n, lg in enumerate(legs, start=1):
        S += [P("LEG %d  |  DEPART %s  |  MAP VIEW, LINEAR VIEW ON PAGES %d AND %d" % (n, lg["depart"], 2 + 3 * n, 3 + 3 * n), KICK), P(lg["title"], H1)]
        S += img(lg.get("map_image"), W * 0.62)
        S += [Spacer(1, 2), LEG_LEGEND, Spacer(1, 4)]
        pr, al = lg["primary"], lg["alternate"]
        S.append(table(["", "Route", "Distance", "Drive time"], [["<b>Primary</b>"] + list(pr), ["<b>Alternate</b>"] + list(al)], [0.12, 0.6, 0.11, 0.17]))
        S += [Spacer(1, 3), P(lg.get("shared", ""), SM)]
        rows, extra = [], []
        for i, (num, where, why, go) in enumerate(lg["spots"], start=1):
            rows.append([Spot(num, 11) if num else "", "<b>%s</b>" % where if num else where, why, go])
            if num: extra.append(("BACKGROUND", (0, i), (-1, i), REDPALE))
        S += [P("Predictable spots and choke points", H2),
              table(["", "Where", "Why it matters", "If blocked, go"], rows, [0.05, 0.25, 0.33, 0.37], zebra=False, extra=extra)]
        left = [P("Closures and roadworks", H2), P(lg.get("closures_source", ""), SM)] + bullets(lg["closures"], bb)
        right = [P("Leg verdict", H2), Verdict(lg["verdict"][0], 56, 15), Spacer(1, 4), P(lg["verdict"][1], BS)]
        two = Table([[left, right]], colWidths=[W * 0.62, W * 0.38])
        two.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (0, -1), 12)]))
        S.append(two)
        st = lg["strip"]
        S += [NextPageTemplate("l"), PageBreak()]
        for kind, key in (("Primary", "primary"), ("Alternate", "alternate")):
            route = st[key]
            sp = StripPage(kind, n, nL, route, place_events(route), _notes(st[key + "_notes"]), STRIP_W, STRIP_H)
            sp.map_page = 1 + 3 * n
            S.append(sp)
            S.append(PageBreak() if kind == "Primary" else NextPageTemplate("p"))
        S.append(PageBreak())

    # ---------- STOPS ----------
    hb = ParagraphStyle("hb", parent=BUL, fontSize=8.5, leading=11)
    for sd in stops:
        S += [P(sd["kicker"], KICK), P(sd["title"], H1)]
        S += img(sd.get("image"), W * 0.6, sd.get("caption"))
        S += [Spacer(1, 4), P("<b>Building overview.</b> " + sd["overview"], B), Spacer(1, 4)]
        S.append(table(["Item", "Detail", "Source"], sd["rows"] + [["Verdict", vtext(*sd["verdict"]), "Plan"]], [0.18, 0.6, 0.22]))
        if sd.get("flag"): S += [Spacer(1, 6), note(sd["flag"])]
        S += [P("Hand-off to the site advance", H2)] + bullets(sd["handoff"], hb) + [PageBreak()]

    # ---------- MEDICAL ----------
    md = D["medical"]
    S += [P("MEDICAL AND SAFE HAVENS", KICK), P("Hospital runs and help nearby", H1)]
    def _ti(t):
        k = {"Police": "police", "Fire": "fire", "Secure venue": "secure"}.get(t, "hospital" if "Trauma" in t else None)
        return icon_row(k, t, ParagraphStyle("mti", parent=BS, fontSize=8, leading=10), 9) if k else t
    ns = len(md["from"]); cw = 0.3 / ns
    S.append(table(["Place", "Type"] + ["From " + f for f in md["from"]] + ["Check"], [[r[0], _ti(r[1])] + r[2:] for r in md["rows"]],
                   [0.31, 0.19] + [cw] * ns + [0.2]))
    S += [Spacer(1, 3), P(md.get("times_note", ""), SM), P(md["runs_title"], H2)]
    HR = ParagraphStyle("hr", parent=BS, fontSize=7.8, leading=10, leftIndent=9, bulletIndent=0)
    HH = ParagraphStyle("hh", parent=BS, fontName="Inter-Bold", fontSize=8.4, leading=11, textColor=RED)
    runs = [[P(r["head"], HH), P(r["sub"], SM), Spacer(1, 2)] + [Paragraph(s, HR, bulletText="%d" % (i + 1)) for i, s in enumerate(r["steps"])] for r in md["runs"]]
    rt = Table([runs], colWidths=[W / len(runs)] * len(runs))
    rt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                            ("BACKGROUND", (0, 0), (-1, -1), PALE), ("LINEBEFORE", (1, 0), (-1, 0), 0.6, LINE),
                            ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    S += [rt, Spacer(1, 3), P(md.get("runs_note", ""), SM)]
    if md.get("kit_note"): S += [Spacer(1, 6), note(md["kit_note"], PALE, NAVY)]
    S.append(PageBreak())

    # ---------- RECON, DAY-OF, COMMS ----------
    rc = D["recon"]
    S += [P("RECON, DAY-OF CHECKS AND COMMS", KICK), P("What to check before the move", H1)]
    S += [P("Recon drive", H2), P(rc["intro"], B), Spacer(1, 4)]
    S.append(table(["#", "Where", "Confirm"], rc["rows"], [0.05, 0.3, 0.65]))
    S += [P("Day-of checks", H2)] + bullets(rc["day_of"], ParagraphStyle("dob", parent=BUL, fontSize=8.5, leading=11))
    comms_l = [P("Code words", H2), table(["Code word", "Means"], rc["code_words"], [0.17, 0.33]), Spacer(1, 3), P(rc.get("code_note", ""), SM)]
    cdr = ParagraphStyle("cdr", parent=BS, fontSize=8.2, leading=10.8, leftIndent=10, bulletIndent=0)
    comms_r = [P("If comms go down", H2)] + [Paragraph(t, cdr, bulletText="%d" % (i + 1)) for i, t in enumerate(rc["comms_down"])] + \
              [Spacer(1, 3), P(rc.get("rally_summary", ""), BS)]
    ct = Table([[comms_l, comms_r]], colWidths=[W * 0.52, W * 0.48])
    ct.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (0, -1), 12)]))
    S += [ct, P("Confidence", H2)] + bullets(rc["confidence"], ParagraphStyle("cb", parent=BUL, fontSize=8.3, leading=10.8)) + [PageBreak()]

    # ---------- DRIVER CARD ----------
    dc = D["driver_card"]
    DC = ParagraphStyle("dc", parent=B, fontSize=9.3, leading=12.2)
    M = ParagraphStyle("m", parent=B, fontSize=9.8, leading=12.8)
    S += [P("DRIVER CARD", KICK), P(dc["title"], H1)]
    S.append(table(["Time", "Move", "Primary", "Alternate"], dc["moves"], [0.12, 0.22, 0.36, 0.3], style=DC))
    S += [P("Drop-off, pick-up and rally points", H2), table(["Stop", "Car stops", "Backup", "Rally point"], dc["points"], [0.16, 0.26, 0.31, 0.27], style=DC)]
    S += [P("Medical", H2), P(dc["medical"], M), P("Code words and comms down", H2), P(dc["comms"], M), P("Red spots", H2)]
    S += bullets(dc["red_spots"], ParagraphStyle("w", parent=BUL, fontSize=9.6, leading=12.5)) + [PageBreak()]

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
    S += [P("Routes", H2), form_table(["Leg and route", "Planned min", "Driven min", "Planned mi", "Driven mi", "Traffic, closures, notes"],
                                      max(len(fm["recon_routes"]), 6), [0.22, 0.1, 0.1, 0.1, 0.1, 0.38], 24, fm["recon_routes"])]
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
