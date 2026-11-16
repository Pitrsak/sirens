"""Časová osa písně: řádek pro každou stopu, sloupec pro každej takt.

Takt = kus času (4 doby), celá píseň je prostě řada taktů za sebou.
Do taktu ve stopě se "namaluje" pattern (A..H) a ten tam pak hraje.

Ovládání:
 - klik na číslo taktu nahoře: odsud začne přehrávání v režimu Song
 - klik na jméno stopy: vybere ji (Sound tab pak edituje její nástroj); klik na M: ztlumí
 - klik / tažení v řádku stopy: vloží do taktů její právě editovanej pattern
   (klik na takt, kde už ten pattern je, ho naopak maže)
 - kolečko myši (nebo vodorovnej posun na touchpadu): posun v čase, když se
   celá píseň nevejde; při přehrávání se pohled posouvá s ukazatelem sám

Takt má šířku aspoň MIN_BAR_W, aby se do něj dalo kliknout. Když je taktů víc,
než se vejde, ukazuje se jen výřez od taktu first_bar.
Převod x <-> takt je v _x a _bar_at, je to zase jen násobení / dělení šířkou taktu.
"""

import wx

from sirens.song import TICKS_PER_BAR
from sirens.ui import theme

NAME_W = 130       # sloupec se jmény stop
HEADER_H = 22      # řádek s čísly taktů
ROW_H = 30         # výška řádku stopy
MIN_BAR_W = 14     # nejužší takt (px)
WHEEL_BARS = 4     # o kolik taktů posune jeden krok kolečka


class TimelineView(wx.Control):
    def __init__(self, parent, song, player, on_select):
        """on_select(track): výběr stopy (klik na jméno)."""
        super().__init__(parent, style=wx.BORDER_NONE)
        self.song, self.player = song, player
        self.on_select = on_select
        self.selected = None
        self.paint_row = None        # (stopa, pattern nebo None = mazání) při tažení
        self.first_bar = 0           # první viditelnej takt (posun v čase)
        self.wheel = 0               # nasčítaný otočení kolečka (touchpad posílá malý kroky)
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.fit()
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_LEFT_DOWN, self._on_down)
        self.Bind(wx.EVT_LEFT_UP, self._on_up)
        self.Bind(wx.EVT_MOTION, self._on_motion)
        self.Bind(wx.EVT_MOUSEWHEEL, self._on_wheel)
        self.Bind(wx.EVT_SIZE, lambda e: self.Refresh())

    # --- rozložení ---

    def fit(self):
        """Výška podle počtu stop: všechny řádky se musí vejít (+ 8 px mezera dole)."""
        self.SetMinSize((-1, HEADER_H + len(self.song.tracks) * ROW_H + 8))

    def _bar_w(self):
        # šířka taktu: místo vpravo od jmen / počet taktů, ale nikdy míň než MIN_BAR_W
        return max(MIN_BAR_W, (self.GetClientSize()[0] - NAME_W) / self.song.bars)

    def _visible_bars(self) -> int:
        """Kolik celejch taktů se vejde na šířku."""
        return max(1, int((self.GetClientSize()[0] - NAME_W) / self._bar_w()))

    def _scroll_to(self, bar: int):
        """Posune výřez tak, aby začínal taktem bar (ne ale za konec písně)."""
        self.first_bar = max(0, min(bar, self.song.bars - self._visible_bars()))

    def _x(self, bar: float) -> float:
        """Vodorovná pozice začátku taktu na obrazovce (bar může bejt i desetinnej, třeba 3.5)."""
        return NAME_W + (bar - self.first_bar) * self._bar_w()

    def _bar_at(self, x):
        # opak _x: pixely -> číslo taktu (// = kolik celejch taktů), None když je to mimo
        bar = self.first_bar + int((x - NAME_W) // self._bar_w())
        return bar if x >= NAME_W and 0 <= bar < self.song.bars else None

    def _row_at(self, y):
        # pixely -> stopa: každá stopa je ROW_H vysoká, pod hlavičkou
        row = int((y - HEADER_H) // ROW_H)
        return self.song.tracks[row] if y >= HEADER_H and row < len(self.song.tracks) else None

    # --- myš ---

    def _on_down(self, event):
        x, y = event.GetX(), event.GetY()
        bar = self._bar_at(x)
        # 1) hlavička s čísly taktů = odkud začne Song
        if y < HEADER_H:
            if bar is not None:
                self.player.start_bar = bar
                self.Refresh()
            return
        # 2) řádek nějaký stopy
        track = self._row_at(y)
        if track is None:
            return
        if x < NAME_W:
            # vlevo jména: posledních 28 px je M (mute), zbytek = výběr stopy
            if x > NAME_W - 28:
                track.muted = not track.muted
                self.Refresh()
            else:
                self.on_select(track)
            return
        # klik na takt s právě editovaným patternem = mazání, jinak vkládání
        # (co se rozhodne na začátku, platí pro celý tažení)
        erase = track.arrangement.get(bar) == track.current
        self.paint_row = (track, None if erase else track.current)
        self._paint(bar)
        self.CaptureMouse()

    def _paint(self, bar):
        # "malování" patternu do taktu (nebo mazání, když je name None)
        if bar is None or self.paint_row is None:
            return
        track, name = self.paint_row
        if name is None:
            track.arrangement.pop(bar, None)     # pop s None nespadne, když tam nic není
        else:
            track.arrangement[bar] = name
        self.Refresh()

    def _on_motion(self, event):
        if not (event.Dragging() and self.HasCapture()):
            return
        # tažení = malování patternu do dalších taktů
        self._paint(self._bar_at(event.GetX()))

    def _on_up(self, event):
        if self.HasCapture():
            self.ReleaseMouse()
        self.paint_row = None

    def _on_wheel(self, event):
        """Kolečko posouvá v čase: dolů / doprava = dál v písni.

        Otočení se sčítá do self.wheel a posune se, až je ho dost na jeden celej
        "cvak" (GetWheelDelta), protože touchpad posílá spoustu malejch kousků.
        """
        rotation = event.GetWheelRotation()
        if event.GetWheelAxis() == wx.MOUSE_WHEEL_VERTICAL:
            rotation = -rotation                     # otočení dolů má zápornou hodnotu
        self.wheel += rotation
        steps = int(self.wheel / event.GetWheelDelta())
        if steps:
            self.wheel -= steps * event.GetWheelDelta()    # spotřebovaný cvaky odečíst, zbytek si nechat
            self._scroll_to(self.first_bar + steps * WHEEL_BARS)
            self.Refresh()

    # --- kreslení ---

    def _on_paint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(theme.VIEWPORT))
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        w, h = self.GetClientSize()
        bar_w = self._bar_w()
        playing = self.player.playing and self.player.mode == "Song"

        # při přehrávání pohled sleduje ukazatel (když uteče z výřezu, otočí se stránka)
        visible = self._visible_bars()
        if playing:
            play_bar = self.player.position // TICKS_PER_BAR      # tiky -> takt (48 tiků = 1 takt)
            if not self.first_bar <= play_bar < self.first_bar + visible:
                self._scroll_to(play_bar)
        self._scroll_to(self.first_bar)              # po zkrácení písně nebo změně šířky okna
        # takty, co jsou vidět (+1, ať se dokreslí i ten useknutej na kraji)
        bars = range(self.first_bar, min(self.song.bars, self.first_bar + visible + 1))

        # zvýraznění vybraný stopy přes celou šířku
        # enumerate dá pořadí (row) i stopu naráz, pořadí potřebuju na y
        for row, track in enumerate(self.song.tracks):
            if track is self.selected:
                gc.SetBrush(wx.Brush(theme.SLIDER_TRACK))
                gc.SetPen(wx.TRANSPARENT_PEN)
                gc.DrawRectangle(0, HEADER_H + row * ROW_H, w, ROW_H)

        # všechno, co patří k taktům, se kreslí jen vpravo od sloupce se jmény
        # (Clip = co je mimo ten obdélník, se prostě nenakreslí)
        gc.Clip(NAME_W, 0, w - NAME_W, h)

        # čísla taktů a značka začátku přehrávání; číslo a výraznější čára jen u každýho 4. taktu
        gc.SetFont(theme.font(9), theme.TEXT_DIM)
        for bar in bars:
            x = self._x(bar)
            gc.SetPen(wx.Pen(theme.GRID if bar % 4 else theme.BORDER, 1))
            gc.StrokeLine(x, HEADER_H, x, h)
            if bar % 4 == 0:
                gc.DrawText(str(bar + 1), x + 3, 4)      # takty počítám od 0, lidi od 1
        gc.SetBrush(wx.Brush(theme.TEXT_MUTED))
        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.DrawRectangle(self._x(self.player.start_bar), HEADER_H - 4, bar_w, 3)

        # patterny ve stopách
        for row, track in enumerate(self.song.tracks):
            y = HEADER_H + row * ROW_H
            for bar, name in list(track.arrangement.items()):
                if bar not in bars:
                    continue
                x = self._x(bar)
                # pokračování stejnýho patternu (na začátku výřezu ale jméno ukážu)
                # pokračování se kreslí bez mezery a bez písmenka, ať to vypadá jako jeden dlouhej blok
                continues = track.arrangement.get(bar - 1) == name and bar > self.first_bar
                gc.SetPen(wx.TRANSPARENT_PEN)
                gc.SetBrush(wx.Brush(theme.TEXT_DIM if track.muted else theme.SLIDER_FILL_HOT))
                gc.DrawRectangle(x + (0 if continues else 1), y + 4, bar_w - (0 if continues else 1), ROW_H - 8)
                if not continues:
                    gc.SetFont(theme.font(10, bold=True), theme.TEXT)
                    gc.DrawText(name, x + 4, y + 8)

        # ukazatel přehrávání v režimu Song
        if playing:
            gc.SetPen(wx.Pen(theme.ACCENT, 1))
            x = self._x(self.player.position / TICKS_PER_BAR)     # position je v tikách, / dá desetinnej takt
            gc.StrokeLine(x, 0, x, h)
        gc.ResetClip()

        # posuvník nahoře: jakou část písně výřez ukazuje
        if visible < self.song.bars:
            span = w - NAME_W
            gc.SetBrush(wx.Brush(theme.TEXT_DIM))
            gc.SetPen(wx.TRANSPARENT_PEN)
            gc.DrawRectangle(NAME_W + span * self.first_bar / self.song.bars, 0,
                             span * visible / self.song.bars, 2)

        # jména stop a M (ztlumení)
        for row, track in enumerate(self.song.tracks):
            y = HEADER_H + row * ROW_H
            gc.SetFont(theme.font(11, bold=track is self.selected),
                       theme.TEXT_DIM if track.muted else theme.TEXT)
            gc.DrawText(track.name, 10, y + 8)
            gc.SetFont(theme.font(10, bold=True), theme.ERROR if track.muted else theme.TEXT_DIM)
            gc.DrawText("M", NAME_W - 20, y + 8)
