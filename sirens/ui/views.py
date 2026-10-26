"""Grafy vlevo: osciloskop, spektrum, náhled obrazu a světla, kreslený přes wx.GraphicsContext.

Všechny mají stejnej rámeček (zaoblenej, tenkej okraj, nadpis vlevo nahoře,
údaj vpravo nahoře), liší se jen tím, co nakreslí dovnitř. Takže rámeček
kreslí GraphView a vnitřek si každá podtřída dodělá ve svý metodě draw().

Data se do nich dostávají přes show(...), tu volá záložka každej snímek
z časovače. show si data jen uloží a zavolá Refresh, kreslí se až v EVT_PAINT.
"""

import math

import wx

from sirens.ui import theme

MARGIN = 14        # odsazení grafu od okraje rámečku
TOP = 34           # místo nahoře pro nadpis
F_MIN, F_MAX = 20.0, 20000.0   # rozsah frekvenční osy spektra (to, co člověk slyší)
DB_MIN = -90.0                 # spodní okraj osy dB (tišší už je prostě ticho)


class GraphView(wx.Panel):
    def __init__(self, parent, title: str):
        super().__init__(parent)
        self.title = title.upper()
        self.info = ""     # text vpravo nahoře (špička, frekvence, ...)
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_SIZE, lambda e: self.Refresh())   # po změně velikosti okna překreslit celý

    def _on_paint(self, event):
        dc = wx.AutoBufferedPaintDC(self)    # kreslí se do paměti, na obrazovku až hotový = nebliká
        dc.SetBackground(wx.Brush(theme.BACKGROUND))
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        w, h = self.GetClientSize()

        # rámeček
        gc.SetPen(wx.Pen(theme.BORDER, 1))
        gc.SetBrush(wx.Brush(theme.VIEWPORT))
        gc.DrawRoundedRectangle(0.5, 0.5, w - 1, h - 1, 12)

        # nadpis vlevo, údaj zarovnanej doprava
        gc.SetFont(theme.font(9, bold=True), theme.TEXT_MUTED)
        theme.draw_spaced(gc, self.title, MARGIN, 12)
        gc.SetFont(theme.font(10), theme.TEXT_MUTED)
        tw, _ = gc.GetTextExtent(self.info)
        gc.DrawText(self.info, w - MARGIN - tw, 12)

        # vnitřní plocha grafu, tu už kreslí podtřída
        self.draw(gc, MARGIN, TOP, w - 2 * MARGIN, h - TOP - MARGIN)

    def draw(self, gc, x, y, w, h):
        """Tohle přepíše podtřída: nakreslí obsah do obdélníku x, y, w, h."""


class ScopeView(GraphView):
    """Tvar vlny v čase. Svisle -1..1, vodorovně SCOPE_VIEW vzorků."""

    def __init__(self, parent):
        super().__init__(parent, "Scope")
        self.samples = []
        self.duration_ms = 0.0

    def show(self, samples, duration_ms: float, peak_db: float):
        self.samples = samples
        self.duration_ms = duration_ms
        clip = "  CLIP" if peak_db > -0.1 else ""     # skoro 0 dB = zvuk naráží na strop
        level = f"peak {peak_db:5.1f} dB" if peak_db > DB_MIN else "silence"
        self.info = f"{level}   {duration_ms:.1f} ms{clip}"
        self.Refresh(False)     # False = nemazat předem pozadí, stejně ho přemaluju celý

    def draw(self, gc, x, y, w, h):
        mid = y + h / 2            # nula je uprostřed výšky
        scale = h / 2 * 0.9        # amplituda 1.0 = 90 % poloviny výšky

        # mřížka: vodorovně 0, +-0.5, +-1; svisle každou milisekundu
        gc.SetPen(wx.Pen(theme.GRID, 1))
        for level in (-1, -0.5, 0.5, 1):
            gc.StrokeLine(x, mid - level * scale, x + w, mid - level * scale)   # minus, protože y na obrazovce roste dolů
        if self.duration_ms > 0:
            for ms in range(1, int(self.duration_ms) + 1):
                px = x + w * ms / self.duration_ms
                gc.StrokeLine(px, y, px, y + h)
        gc.SetPen(wx.Pen(theme.BORDER, 1))
        gc.StrokeLine(x, mid, x + w, mid)   # nulová čára trochu výraznější

        n = len(self.samples)
        if n < 2:
            return                 # z jednoho bodu čára nebude
        # křivka: vzorek i -> x úměrně pořadí, hodnota -> y od středu
        path = gc.CreatePath()
        for i, s in enumerate(self.samples):
            px = x + w * i / (n - 1)
            py = mid - max(-1.1, min(1.1, float(s))) * scale   # oříznout, ať při clipu neutíká z rámečku
            if i == 0:
                path.MoveToPoint(px, py)
            else:
                path.AddLineToPoint(px, py)
        gc.SetPen(wx.Pen(theme.ACCENT, 2))
        gc.StrokePath(path)


class SpectrumView(GraphView):
    """Spektrum: vodorovně frekvence (logaritmicky 20 Hz - 20 kHz), svisle dB."""

    def __init__(self, parent):
        super().__init__(parent, "Spectrum")
        self.freqs, self.levels = [], []

    def show(self, freqs, levels_db, peak_hz):
        self.freqs, self.levels = freqs, levels_db
        self.info = f"strongest {peak_hz:.1f} Hz" if peak_hz else "silence"
        self.Refresh(False)

    @staticmethod
    def _x_of(freq, x, w):
        """Logaritmická osa: každá dekáda (20-200, 200-2000, ...) má stejnou šířku.

        Stejnej vzorec jako u log slideru, jen místo 0..1 vyjde rovnou pixel.
        """
        return x + w * math.log(freq / F_MIN) / math.log(F_MAX / F_MIN)

    def draw(self, gc, x, y, w, h):
        y_of = lambda db: y + h * (db / DB_MIN)    # 0 dB nahoře, DB_MIN dole

        # mřížka s popiskama: frekvence dole, dB vlevo
        # (popisek jen u 100, 1k, 10k, ostatní čáry jsou tmavší a bez textu)
        gc.SetFont(theme.font(9), theme.TEXT_DIM)
        for freq, label in ((50, ""), (100, "100"), (200, ""), (500, ""), (1000, "1k"),
                            (2000, ""), (5000, ""), (10000, "10k")):
            px = self._x_of(freq, x, w)
            gc.SetPen(wx.Pen(theme.BORDER if label else theme.GRID, 1))
            gc.StrokeLine(px, y, px, y + h)
            if label:
                gc.DrawText(label, px + 3, y + h - 14)
        for db in (-20, -40, -60, -80):
            gc.SetPen(wx.Pen(theme.GRID, 1))
            gc.StrokeLine(x, y_of(db), x + w, y_of(db))
            gc.DrawText(f"{db}", x + 3, y_of(db) + 2)

        if len(self.levels) < 2:
            return
        # body křivky; koš k=0 (stejnosměrná složka) a všechno pod 20 Hz se vynechá
        # (log(0) by stejně nešel), dB se ořízne do rozsahu osy
        points = [(self._x_of(f, x, w), y_of(max(DB_MIN, min(0.0, float(db)))))
                  for f, db in zip(self.freqs, self.levels) if F_MIN <= f <= F_MAX]
        if len(points) < 2:
            return
        line = gc.CreatePath()
        line.MoveToPoint(*points[0])
        for point in points[1:]:
            line.AddLineToPoint(*point)
        # výplň = ta samá křivka, jen uzavřená dolů k ose
        area = gc.CreatePath()
        area.AddPath(line)
        area.AddLineToPoint(points[-1][0], y + h)
        area.AddLineToPoint(points[0][0], y + h)
        area.CloseSubpath()

        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.SetBrush(wx.Brush(wx.Colour(255, 255, 255, 18)))   # jemná výplň pod křivkou (4. číslo = průhlednost, 18 z 255)
        gc.FillPath(area)
        gc.SetPen(gc.CreatePen(wx.GraphicsPenInfo(theme.ACCENT).Width(1.5)))   # wx.Pen umí jen celý pixely, tohle i 1.5
        gc.StrokePath(line)


class VisualView(GraphView):
    """Obraz z Painteru, zvětšenej do rámečku tak, aby se nezdeformoval (poměr stran zůstane)."""

    def __init__(self, parent):
        super().__init__(parent, "Visual")
        self.bitmap = None

    def show(self, image):
        """image: pole výška x šířka x 3 (RGB, 0..255) z Painter.render()."""
        height, width = image.shape[:2]
        # z pole čísel udělá wx.Bitmap, to už se dá nakreslit
        self.bitmap = wx.Bitmap.FromBuffer(width, height, image)
        self.info = f"{width} x {height}"
        self.Refresh(False)

    def draw(self, gc, x, y, w, h):
        if self.bitmap is None:
            return
        bw, bh = self.bitmap.GetSize()
        scale = min(w / bw, h / bh)          # celej obraz se musí vejít, tak menší z obou zvětšení
        dw, dh = bw * scale, bh * scale
        gc.DrawBitmap(self.bitmap, x + (w - dw) / 2, y + (h - dh) / 2, dw, dh)   # na střed


class LightView(GraphView):
    """Náhled světla: kruh v barvě, kterou světlo právě svítí, a čísla R, G, B."""

    def __init__(self, parent):
        super().__init__(parent, "Light")
        self.rgb = (0, 0, 0)

    def show(self, rgb, address: int):
        self.rgb = tuple(rgb)
        r, g, b = self.rgb
        # address = první DMX kanál světla, R, G, B jsou tři kanály za sebou
        self.info = f"R {r}   G {g}   B {b}   channels {address}-{address + 2}"
        self.Refresh(False)

    def draw(self, gc, x, y, w, h):
        radius = min(w, h) * 0.35
        cx, cy = x + w / 2, y + h / 2
        gc.SetPen(wx.Pen(theme.BORDER, 1))
        gc.SetBrush(wx.Brush(wx.Colour(*self.rgb)))
        gc.DrawEllipse(cx - radius, cy - radius, 2 * radius, 2 * radius)   # elipsa ve čtverci = kruh
