"""Drawn visuals for the route advance packet: icons, verdict pills, weather card, linear strip map page."""
from reportlab.platypus import Flowable, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import simpleSplit

NAVY = colors.HexColor("#0F1B2D"); INK = colors.HexColor("#18202B"); SLATE = colors.HexColor("#5A6577")
LINE = colors.HexColor("#DDE1E7"); AMBER = colors.HexColor("#E3A33B"); GREEN = colors.HexColor("#2F7D57")
RED = colors.HexColor("#B83A3A"); BLUE = colors.HexColor("#2E5E9E"); PALE = colors.HexColor("#F4F6F9")
ORANGE = colors.HexColor("#D9772B"); LBLUE = colors.HexColor("#1F5FBF"); LGREEN = colors.HexColor("#2E8540")
VERDICT = {"GREEN": GREEN, "AMBER": AMBER, "RED": RED}

# ---------------- icons ----------------
def draw_icon(c, kind, x, y, r):
    """Draw icon centred at x,y with radius r."""
    c.saveState()
    fill = {"hospital": RED, "police": BLUE, "fire": ORANGE, "secure": GREEN, "warn": AMBER, "spot": RED,
            "rally": NAVY, "car": colors.HexColor("#8A94A6"), "cp": colors.white, "sunset": AMBER,
            "moon": colors.HexColor("#C9D3E3"), "event": colors.HexColor("#6B4FA0")}[kind]
    if kind == "warn":
        p = c.beginPath(); p.moveTo(x, y + r); p.lineTo(x + r * 1.05, y - r * 0.85); p.lineTo(x - r * 1.05, y - r * 0.85); p.close()
        c.setFillColor(fill); c.drawPath(p, fill=1, stroke=0)
        c.setFillColor(colors.white); c.setFont("Inter-ExtraBold", r * 1.2); c.drawCentredString(x, y - r * 0.6, "!")
        c.restoreState(); return
    if kind == "cp":
        c.setStrokeColor(INK); c.setLineWidth(1); c.setFillColor(colors.white); c.circle(x, y, r, stroke=1, fill=1)
        c.setFillColor(INK); c.setFont("Inter-Bold", r * 0.75); c.drawCentredString(x, y - r * 0.27, "CP")
        c.restoreState(); return
    c.setFillColor(fill); c.circle(x, y, r, stroke=0, fill=1)
    c.setFillColor(colors.white); c.setStrokeColor(colors.white)
    if kind == "hospital":
        a, b = r * 0.22, r * 0.62
        c.rect(x - a, y - b, 2 * a, 2 * b, stroke=0, fill=1); c.rect(x - b, y - a, 2 * b, 2 * a, stroke=0, fill=1)
    elif kind == "spot":
        c.setFont("Inter-ExtraBold", r * 1.3); c.drawCentredString(x, y - r * 0.45, "!")
    elif kind == "rally":
        c.setFont("Inter-ExtraBold", r * 1.15); c.drawCentredString(x, y - r * 0.4, "R")
    elif kind == "event":
        c.rect(x - r * 0.5, y - r * 0.45, r, r * 0.8, stroke=0, fill=1)
        c.setFillColor(fill); c.rect(x - r * 0.5, y + r * 0.12, r, r * 0.08, stroke=0, fill=1)
    elif kind == "police":
        p = c.beginPath(); w = r * 0.55
        p.moveTo(x - w, y + r * 0.5); p.lineTo(x + w, y + r * 0.5); p.lineTo(x + w, y - r * 0.05)
        p.curveTo(x + w, y - r * 0.45, x + r * 0.2, y - r * 0.6, x, y - r * 0.68)
        p.curveTo(x - r * 0.2, y - r * 0.6, x - w, y - r * 0.45, x - w, y - r * 0.05); p.close()
        c.drawPath(p, fill=1, stroke=0)
    elif kind == "fire":
        p = c.beginPath()
        p.moveTo(x, y + r * 0.7)
        p.curveTo(x + r * 0.55, y + r * 0.1, x + r * 0.5, y - r * 0.55, x, y - r * 0.6)
        p.curveTo(x - r * 0.5, y - r * 0.55, x - r * 0.55, y + r * 0.05, x - r * 0.15, y + r * 0.25)
        p.curveTo(x - r * 0.1, y + r * 0.05, x + r * 0.05, y + r * 0.2, x, y + r * 0.7); p.close()
        c.drawPath(p, fill=1, stroke=0)
    elif kind == "secure":
        p = c.beginPath()
        p.moveTo(x, y + r * 0.62); p.lineTo(x + r * 0.62, y + r * 0.05); p.lineTo(x + r * 0.42, y + r * 0.05)
        p.lineTo(x + r * 0.42, y - r * 0.55); p.lineTo(x - r * 0.42, y - r * 0.55); p.lineTo(x - r * 0.42, y + r * 0.05)
        p.lineTo(x - r * 0.62, y + r * 0.05); p.close(); c.drawPath(p, fill=1, stroke=0)
    elif kind == "car":
        c.roundRect(x - r * 0.62, y - r * 0.3, r * 1.24, r * 0.5, r * 0.12, stroke=0, fill=1)
        c.roundRect(x - r * 0.38, y + r * 0.1, r * 0.76, r * 0.38, r * 0.12, stroke=0, fill=1)
        c.setFillColor(fill); c.circle(x - r * 0.35, y - r * 0.32, r * 0.14, stroke=0, fill=1); c.circle(x + r * 0.35, y - r * 0.32, r * 0.14, stroke=0, fill=1)
    c.restoreState()

def draw_spot(c, n, x, y, r=6.5):
    """Red numbered predictable spot."""
    c.saveState(); c.setFillColor(RED); c.setStrokeColor(colors.white); c.setLineWidth(1.2)
    c.circle(x, y, r, stroke=1, fill=1); c.setFillColor(colors.white); c.setFont("Inter-Bold", r * 1.15)
    c.drawCentredString(x, y - r * 0.4, str(n)); c.restoreState()

class Icon(Flowable):
    def __init__(self, kind, size=12):
        super().__init__(); self.kind, self.size = kind, size
    def wrap(self, aw, ah): return self.size, self.size
    def draw(self): draw_icon(self.canv, self.kind, self.size / 2, self.size / 2, self.size / 2)

class Spot(Flowable):
    def __init__(self, n, size=12):
        super().__init__(); self.n, self.size = n, size
    def wrap(self, aw, ah): return self.size, self.size
    def draw(self): draw_spot(self.canv, self.n, self.size / 2, self.size / 2, self.size / 2)

class Badge(Flowable):
    """Numbered stop badge."""
    def __init__(self, text, color, size=15):
        super().__init__(); self.text, self.color, self.size = text, color, size
    def wrap(self, aw, ah): return self.size, self.size
    def draw(self):
        c = self.canv; r = self.size / 2
        c.setFillColor(self.color); c.circle(r, r, r, stroke=0, fill=1)
        c.setFillColor(colors.white); c.setFont("Inter-Bold", r * 1.05); c.drawCentredString(r, r - r * 0.36, self.text)

class Verdict(Flowable):
    """Green / amber / red pill."""
    def __init__(self, level, w=46, h=13):
        super().__init__(); self.level, self.w, self.h = level, w, h
    def wrap(self, aw, ah): return self.w, self.h
    def draw(self):
        c = self.canv; col = VERDICT[self.level]
        c.setFillColor(col); c.roundRect(0, 0, self.w, self.h, self.h / 2, stroke=0, fill=1)
        c.setFillColor(colors.white if self.level != "AMBER" else INK); c.setFont("Inter-Bold", 7)
        c.drawCentredString(self.w / 2, self.h / 2 - 2.5, self.level)

# ---------------- weather card ----------------
class WeatherCard(Flowable):
    """Packet-style day card. Fits any width from about 230 pt."""
    def __init__(self, width, data):
        super().__init__(); self.w = width; self.d = data
        tone = {"note": ("Inter-Regular", colors.white), "muted": ("Inter-Regular", colors.HexColor("#AAB3C2")),
                "impact": ("Inter-Medium", AMBER)}
        self.lines = [tone[l.get("tone", "note")] + (l["text"],) for l in data.get("lines", [])]
        tw = self.w - 28; self.wrapped = [(f, col, simpleSplit(t, f, 7.6, tw)) for f, col, t in self.lines]
        self.h = 112 + sum(len(l) * 9.6 + 4 for _, _, l in self.wrapped)
    def wrap(self, aw, ah): return self.w, self.h
    def draw(self):
        c = self.canv; w, h = self.w, self.h
        c.setFillColor(INK); c.roundRect(0, 0, w, h, 8, stroke=0, fill=1)
        c.setFillColor(colors.white); c.setFont("Inter-Medium", 8)
        c.drawString(14, h - 18, self.d.get("source", ""))
        c.setStrokeColor(colors.HexColor("#3A4556")); c.setLineWidth(0.6); c.line(0, h - 27, w, h - 27)
        c.setFillColor(colors.white); c.setFont("Inter-Bold", 13); c.drawString(14, h - 52, self.d.get("day", ""))
        c.setFont("Inter-Regular", 8); c.setFillColor(colors.HexColor("#AAB3C2")); c.drawString(14, h - 63, self.d.get("date", ""))
        cx, cy = 66, h - 52
        c.setFillColor(colors.HexColor("#E8EDF5")); c.circle(cx, cy, 13, stroke=0, fill=1)
        c.setFillColor(INK); c.circle(cx + 6.5, cy + 4.5, 11, stroke=0, fill=1)
        c.setFillColor(colors.HexColor("#E8EDF5"))
        for sx, sy in [(cx + 15, cy + 11), (cx + 19, cy - 5)]: c.circle(sx, sy, 1.1, stroke=0, fill=1)
        c.setFillColor(colors.white); c.setFont("Inter-Bold", 28); c.drawString(96, h - 63, self.d.get("high", ""))
        c.setFillColor(colors.HexColor("#8A94A6")); c.setFont("Inter-Regular", 16); c.drawString(96 + c.stringWidth(self.d.get("high", ""), "Inter-Bold", 28) + 6, h - 63, self.d.get("low", ""))
        c.setFont("Inter-SemiBold", 6.3); c.setFillColor(AMBER); c.drawString(96, h - 74, self.d.get("tag", ""))
        y = h - 92
        draw_icon(c, "sunset", 20, y + 3, 5)
        c.setFillColor(colors.white); c.setFont("Inter-Medium", 8); c.drawString(30, y, "Sunset " + self.d.get("sunset", ""))
        draw_icon(c, "moon", 112, y + 3, 5)
        c.setFillColor(colors.white); c.drawString(122, y, "Dark " + self.d.get("dark", ""))
        c.setStrokeColor(colors.HexColor("#3A4556")); c.line(0, h - 102, w, h - 102)
        y = h - 115
        for f, col, lines in self.wrapped:
            c.setFont(f, 7.6); c.setFillColor(col)
            for ln in lines: c.drawString(14, y, ln); y -= 9.6
            y -= 4

# ---------------- strip map page ----------------
SM = ParagraphStyle("vsm", fontName="Inter-Regular", fontSize=7.6, leading=9.6, textColor=INK)
SMB = ParagraphStyle("vsmb", parent=SM, fontName="Inter-Bold")
TH = ParagraphStyle("vth", fontName="Inter-SemiBold", fontSize=7.6, leading=9.5, textColor=colors.white)

def _wrap(c, text, font, size, width):
    return simpleSplit(text, font, size, width)

class StripPage(Flowable):
    """notes: list of (head, body, icon) where icon may be a kind string or ("spot", n)."""
    def __init__(self, kind, leg_no, legs_total, route, events, notes, width, height):
        super().__init__()
        self.kind, self.leg_no, self.legs_total, self.route, self.ev, self.notes = kind, leg_no, legs_total, route, events, notes
        self.w, self.h = width, height
    def wrap(self, aw, ah): return self.w, self.h - 2
    def draw(self):
        c = self.canv; w, h = self.w, self.h - 2
        accent = BLUE if self.kind == "Primary" else ORANGE
        c.setFillColor(accent); c.setFont("Inter-ExtraBold", 17)
        t = "%s Route  |  Leg %d of %d: %s" % (self.kind, self.leg_no, self.legs_total, self.route["title"].split(": ", 1)[1])
        c.drawString(0, h - 16, t)
        if getattr(self, "map_page", None):  # v5: say which map page this strip is the linear view of
            c.setFillColor(SLATE); c.setFont("Inter-SemiBold", 9)
            c.drawRightString(w, h - 15, "Linear view of the leg %d map on page %d" % (self.leg_no, self.map_page))
        r = self.route; total = self.ev[-1]["mi"]
        c.setFillColor(SLATE); c.setFont("Inter-Regular", 8.5)
        c.drawString(0, h - 30, "Depart %s, arrive %s.  %.1f mi / about %d min (Mapbox, typical traffic for that time).  Not to scale; miles between turns on the line.  %s" %
                     (r["depart"], r["arrive"], total, r["minutes"], r.get("source", "")))
        # legend box
        by = h - 72
        c.setFillColor(PALE); c.setStrokeColor(LINE); c.roundRect(0, by, w, 32, 5, stroke=1, fill=1)
        c.setFont("Inter-Bold", 8.5); c.setFillColor(LBLUE); c.drawString(12, by + 19, "ABOVE THE LINE = LEFT TURN")
        c.setFillColor(LGREEN); c.drawString(12, by + 7, "BELOW THE LINE = RIGHT TURN")
        draw_icon(c, "cp", 214, by + 16, 9); c.setFillColor(INK); c.setFont("Inter-Regular", 8.5); c.drawString(228, by + 13, "Checkpoint (call it in)")
        c.setStrokeColor(INK); c.setLineWidth(1.2); c.line(342, by + 16, 354, by + 16); c.line(348, by + 10, 348, by + 22)
        c.drawString(360, by + 13, "Straight-on event (tunnel, merge)")
        draw_spot(c, 1, 520, by + 16, 7); c.setFillColor(RED); c.setFont("Inter-Bold", 8.5)
        c.drawString(532, by + 13, "Predictable spot: if blocked, see notes")
        # strip
        ly = h - 190
        x0, x1 = 34, w - 40
        n = len(self.ev); sp = (x1 - x0 - 30) / (n - 1)
        xs = [x0 + i * sp for i in range(n)]
        c.setStrokeColor(INK); c.setLineWidth(3.2); c.line(x0, ly, x1, ly)
        p = c.beginPath(); p.moveTo(x1 + 12, ly); p.lineTo(x1, ly + 6); p.lineTo(x1, ly - 6); p.close(); c.setFillColor(INK); c.drawPath(p, fill=1, stroke=0)
        c.setFont("Inter-Bold", 8); c.setFillColor(INK)
        for i in range(1, n):
            d = self.ev[i]["mi"] - self.ev[i - 1]["mi"]
            c.drawCentredString((xs[i - 1] + xs[i]) / 2, ly + 5, ("%.2f" % d) if d < 0.1 else ("%.1f" % d))
        lw = sp * 1.75
        flipL = flipR = 0
        for i, (e, x) in enumerate(zip(self.ev, xs)):
            side = e["side"]
            c.setFillColor(INK)
            if i == 0:
                c.setFillColor(INK); c.circle(x, ly, 7, stroke=0, fill=1)
                c.setFont("Inter-Bold", 7.5); c.drawString(x - 12, ly + 12, "START")
                c.setFont("Inter-Bold", 8); c.drawCentredString(x, ly - 20, e["label"])
                c.setFont("Inter-Regular", 7); c.setFillColor(SLATE); c.drawCentredString(x, ly - 30, e["sub"])
            elif i == n - 1:
                c.setFillColor(LBLUE); c.setFont("Inter-Bold", 8)
                yy = ly - 22
                for ln in [e["label"]] + _wrap(c, e["sub"], "Inter-Bold", 8, 60):
                    c.drawCentredString(x1 + 6, yy, ln); yy -= 10
            elif side == "L":
                tall = 34 + 30 * (flipL % 2); flipL += 1
                c.setStrokeColor(LBLUE); c.setLineWidth(1.6); c.line(x, ly + 4, x, ly + tall)
                c.line(x, ly + tall, x - 9, ly + tall)
                pp = c.beginPath(); pp.moveTo(x - 13, ly + tall); pp.lineTo(x - 8, ly + tall + 3.5); pp.lineTo(x - 8, ly + tall - 3.5); pp.close()
                c.setFillColor(LBLUE); c.drawPath(pp, fill=1, stroke=0)
                lines = _wrap(c, e["label"], "Inter-Bold", 8, lw)
                yy = ly + tall + 8 + 10 * (len(lines) - 1)
                c.setFont("Inter-Bold", 8)
                for ln in lines: c.drawCentredString(x, yy, ln); yy -= 10
                if e["sub"]:
                    c.setFont("Inter-Regular", 6.8); c.setFillColor(SLATE)
                    c.drawCentredString(x, ly + tall + 10 + 10 * len(lines), e["sub"])
            elif side == "R":
                tall = 34 + 30 * (flipR % 2); flipR += 1
                c.setStrokeColor(LGREEN); c.setLineWidth(1.6); c.line(x, ly - 4, x, ly - tall)
                c.line(x, ly - tall, x + 9, ly - tall)
                pp = c.beginPath(); pp.moveTo(x + 13, ly - tall); pp.lineTo(x + 8, ly - tall + 3.5); pp.lineTo(x + 8, ly - tall - 3.5); pp.close()
                c.setFillColor(LGREEN); c.drawPath(pp, fill=1, stroke=0)
                lines = _wrap(c, e["label"], "Inter-Bold", 8, lw)
                yy = ly - tall - 12
                c.setFont("Inter-Bold", 8)
                for ln in lines: c.drawCentredString(x, yy, ln); yy -= 10
                if e["sub"]:
                    c.setFont("Inter-Regular", 6.8); c.setFillColor(SLATE); c.drawCentredString(x, yy - 1, e["sub"])
            else:
                c.setStrokeColor(INK); c.setLineWidth(1.4); c.line(x, ly - 8, x, ly + 8)
                c.setFillColor(INK); c.setFont("Inter-Bold", 7.5)
                lines = _wrap(c, e["label"], "Inter-Bold", 7.5, lw)
                yy = ly - 18
                for ln in lines: c.drawCentredString(x, yy, ln); yy -= 9
                if e["sub"]:
                    c.setFont("Inter-Regular", 6.8); c.setFillColor(SLATE); c.drawCentredString(x, yy, e["sub"])
            if e.get("cp") and i > 0:
                draw_icon(c, "cp", x - 13, ly + 15 if side != "L" else ly - 15, 8)
            elif e.get("cp") and i == 0:
                draw_icon(c, "cp", x, ly + 32, 8)
            if e.get("red"):
                if i == n - 1: draw_spot(c, e["red"], x1 + 6, ly + 16)
                elif i == 0: draw_spot(c, e["red"], x + 19, ly + 32)
                else: draw_spot(c, e["red"], x + 12, ly + (-15 if side == "L" else 15))
        # cumulative miles
        cy = ly - 106
        c.setFillColor(SLATE); c.setFont("Inter-SemiBold", 7); c.drawString(0, cy + 10, "Cumulative miles:")
        c.setFont("Inter-Regular", 7.2)
        for e, x in zip(self.ev, xs): c.drawCentredString(x, cy, "%.1f" % e["mi"] if e["mi"] >= 0.1 or e["mi"] == 0 else "%.2f" % e["mi"])
        c.setStrokeColor(LINE); c.setLineWidth(0.6); c.line(0, cy - 8, w, cy - 8)
        # step table
        rows = [[Paragraph("#", TH), Paragraph("Mile", TH), Paragraph("Turn", TH), Paragraph("Instruction", TH), Paragraph("Call in", TH)]]
        for i, e in enumerate(self.ev):
            turn = {"L": '<font color="#1F5FBF"><b>LEFT</b></font>', "R": '<font color="#2E8540"><b>RIGHT</b></font>'}.get(e["side"], "")
            mi = "%.2f" % e["mi"] if 0 < e["mi"] < 0.1 else "%.1f" % e["mi"]
            txt = e["text"]
            if e.get("red"): txt = '<font color="#B83A3A"><b>Spot %d.</b></font> ' % e["red"] + txt
            rows.append([Paragraph(str(i + 1), SMB), Paragraph(mi, SM), Paragraph(turn, SM), Paragraph(txt, SM), Paragraph(e.get("cp", ""), SM)])
        tw = w * 0.6
        t = Table(rows, colWidths=[tw * 0.05, tw * 0.08, tw * 0.1, tw * 0.6, tw * 0.17])
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("LINEBELOW", (0, 1), (-1, -1), 0.3, LINE), ("TOPPADDING", (0, 0), (-1, -1), 1.6),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6), ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]))
        tw_, th_ = t.wrapOn(c, tw, cy - 14)
        c.setFillColor(accent); c.setFont("Inter-Bold", 9); c.drawString(0, cy - 22, "STEP BY STEP: %s" % self.route["title"].split(":")[0].upper())
        t.drawOn(c, 0, cy - 28 - th_)
        # notes
        nx = tw + 18; nw = w - nx
        c.setStrokeColor(LINE); c.line(nx - 9, cy - 16, nx - 9, 0)
        c.setFillColor(accent); c.setFont("Inter-Bold", 9); c.drawString(nx, cy - 22, "NOTES FOR THIS ROUTE")
        yy = cy - 36
        for head, body, icon in self.notes:
            if isinstance(icon, tuple):
                draw_spot(c, icon[1], nx + 5, yy + 3, 5.5); tx = nx + 14; hc = RED
            elif icon:
                draw_icon(c, icon, nx + 5, yy + 3, 5); tx = nx + 14; hc = INK
            else: tx = nx; hc = INK
            c.setFillColor(hc); c.setFont("Inter-Bold", 7.8); c.drawString(tx, yy, head); yy -= 10
            for ln in simpleSplit(body, "Inter-Regular", 7.4, nw - (tx - nx)):
                c.setFont("Inter-Regular", 7.4); c.setFillColor(SLATE); c.drawString(tx, yy, ln); yy -= 9.2
            yy -= 4
