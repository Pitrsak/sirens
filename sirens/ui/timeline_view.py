"""Časová osa písně: řádek pro každou stopu, sloupec pro každý takt, dole automatizace.

Ovládání:
 - klik na číslo taktu nahoře: odtud začne přehrávání v režimu Song
 - klik na jméno stopy: vybere ji (Sound tab pak edituje její nástroj); klik na M: ztlumí
 - klik / tažení v řádku stopy: vloží do taktů její právě editovaný pattern
   (klik na takt, kde už ten pattern je, ho naopak maže)
 - spodní řádek: automatizace vybraného slideru; klik / tažení nastaví hodnotu
   v taktu podle výšky, pravé tlačítko hodnotu smaže
"""

import math

import wx

from sirens.song import STEPS_PER_BAR
from sirens.ui import theme

NAME_W = 130       # sloupec se jmény stop
HEADER_H = 22      # řádek s čísly taktů
ROW_H = 30         # výška řádku stopy
LANE_H = 80        # výška řádku automatizace


class TimelineView(wx.Control):
    def __init__(self, parent, song, player, on_select, get_lane):
        """on_select(track): výběr stopy. get_lane(): (vlastník, Param) automatizace, nebo None."""
        super().__init__(parent, style=wx.BORDER_NONE)
        self.song, self.player = song, player
        self.on_select, self.get_lane = on_select, get_lane
        self.selected = None
        self.paint_row = None        # (stopa, pattern nebo None = mazání) při tažení
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.fit()
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_LEFT_DOWN, self._on_down)
        self.Bind(wx.EVT_LEFT_UP, self._on_up)
        self.Bind(wx.EVT_MOTION, self._on_motion)
        self.Bind(wx.EVT_RIGHT_DOWN, self._on_right)
        self.Bind(wx.EVT_SIZE, lambda e: self.Refresh())

    # --- rozložení ---

    def fit(self):
        """Výška podle počtu stop: všechny řádky a automatizace se musí vejít."""
        self.SetMinSize((-1, HEADER_H + len(self.song.tracks) * ROW_H + 8 + LANE_H + 8))

    def _bar_w(self):
        return (self.GetClientSize()[0] - NAME_W) / self.song.bars

    def _lane_top(self):
        return HEADER_H + len(self.song.tracks) * ROW_H + 8

    def _bar_at(self, x):
        bar = int((x - NAME_W) // self._bar_w())
        return bar if x >= NAME_W and 0 <= bar < self.song.bars else None

    def _row_at(self, y):
        row = int((y - HEADER_H) // ROW_H)
        return self.song.tracks[row] if y >= HEADER_H and row < len(self.song.tracks) else None

    # --- automatizace: hodnota <-> výška v řádku ---

    @staticmethod
    def _to_unit(param, value):
        if param.log:
            return math.log(value / param.lo) / math.log(param.hi / param.lo)
        return (value - param.lo) / (param.hi - param.lo)

    @staticmethod
    def _from_unit(param, unit):
        unit = min(1.0, max(0.0, unit))
        if param.log:
            return param.lo * (param.hi / param.lo) ** unit
        return param.lo + unit * (param.hi - param.lo)

    def _set_lane(self, x, y):
        lane, bar = self.get_lane(), self._bar_at(x)
        if lane is None or bar is None:
            return
        owner, param = lane
        top = self._lane_top()
        unit = 1 - (y - top) / LANE_H
        owner.automation.setdefault(param.label, {})[bar] = self._from_unit(param, unit)
        self.Refresh()

    # --- myš ---

    def _on_down(self, event):
        x, y = event.GetX(), event.GetY()
        bar = self._bar_at(x)
        if y < HEADER_H:
            if bar is not None:
                self.player.start_bar = bar
                self.Refresh()
            return
        if y >= self._lane_top():
            self._set_lane(x, y)
            self.CaptureMouse()
            return
        track = self._row_at(y)
        if track is None:
            return
        if x < NAME_W:
            if x > NAME_W - 28:
                track.muted = not track.muted
                self.Refresh()
            else:
                self.on_select(track)
            return
        # klik na takt s právě editovaným patternem = mazání, jinak vkládání
        erase = track.arrangement.get(bar) == track.current
        self.paint_row = (track, None if erase else track.current)
        self._paint(bar)
        self.CaptureMouse()

    def _paint(self, bar):
        if bar is None or self.paint_row is None:
            return
        track, name = self.paint_row
        if name is None:
            track.arrangement.pop(bar, None)
        else:
            track.arrangement[bar] = name
        self.Refresh()

    def _on_motion(self, event):
        if not (event.Dragging() and self.HasCapture()):
            return
        if self.paint_row is not None:
            self._paint(self._bar_at(event.GetX()))
        else:
            self._set_lane(event.GetX(), event.GetY())

    def _on_up(self, event):
        if self.HasCapture():
            self.ReleaseMouse()
        self.paint_row = None

    def _on_right(self, event):
        lane, bar = self.get_lane(), self._bar_at(event.GetX())
        if lane and bar is not None and event.GetY() >= self._lane_top():
            owner, param = lane
            owner.automation.get(param.label, {}).pop(bar, None)
            self.Refresh()

    # --- kreslení ---

    def _on_paint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(theme.VIEWPORT))
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        w, h = self.GetClientSize()
        bar_w = self._bar_w()

        # čísla taktů a značka začátku přehrávání
        gc.SetFont(theme.font(9), theme.TEXT_DIM)
        for bar in range(self.song.bars):
            x = NAME_W + bar * bar_w
            gc.SetPen(wx.Pen(theme.GRID if bar % 4 else theme.BORDER, 1))
            gc.StrokeLine(x, HEADER_H, x, h)
            if bar % 4 == 0:
                gc.DrawText(str(bar + 1), x + 3, 4)
        sx = NAME_W + self.player.start_bar * bar_w
        gc.SetBrush(wx.Brush(theme.TEXT_MUTED))
        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.DrawRectangle(sx, HEADER_H - 4, bar_w, 3)

        # stopy
        for row, track in enumerate(self.song.tracks):
            y = HEADER_H + row * ROW_H
            if track is self.selected:
                gc.SetBrush(wx.Brush(theme.SLIDER_TRACK))
                gc.SetPen(wx.TRANSPARENT_PEN)
                gc.DrawRectangle(0, y, w, ROW_H)
            gc.SetFont(theme.font(11, bold=track is self.selected),
                       theme.TEXT_DIM if track.muted else theme.TEXT)
            gc.DrawText(track.name, 10, y + 8)
            gc.SetFont(theme.font(10, bold=True), theme.ERROR if track.muted else theme.TEXT_DIM)
            gc.DrawText("M", NAME_W - 20, y + 8)
            for bar, name in track.arrangement.items():
                if bar >= self.song.bars:
                    continue
                x = NAME_W + bar * bar_w
                continues = track.arrangement.get(bar - 1) == name     # pokračování stejného patternu
                gc.SetPen(wx.TRANSPARENT_PEN)
                gc.SetBrush(wx.Brush(theme.TEXT_DIM if track.muted else theme.SLIDER_FILL_HOT))
                gc.DrawRectangle(x + (0 if continues else 1), y + 4, bar_w - (0 if continues else 1), ROW_H - 8)
                if not continues:
                    gc.SetFont(theme.font(10, bold=True), theme.TEXT)
                    gc.DrawText(name, x + 4, y + 8)

        # automatizace
        top = self._lane_top()
        gc.SetPen(wx.Pen(theme.BORDER, 1))
        gc.StrokeLine(0, top - 4, w, top - 4)
        lane = self.get_lane()
        gc.SetFont(theme.font(10), theme.TEXT_MUTED)
        gc.DrawText("Automation" if lane is None else f"Auto: {lane[1].label}", 10, top + 4)
        if lane is not None:
            owner, param = lane
            values = owner.automation.get(param.label, {})
            # hodnota platí od začátku taktu, proto bod na jeho levém okraji
            points = [(NAME_W + bar * bar_w + 3,
                       top + LANE_H * (1 - self._to_unit(param, values[bar]))) for bar in sorted(values)]
            if len(points) > 1:
                path = gc.CreatePath()
                path.MoveToPoint(*points[0])
                for point in points[1:]:
                    path.AddLineToPoint(*point)
                gc.SetPen(wx.Pen(theme.TEXT_MUTED, 1))
                gc.StrokePath(path)
            gc.SetBrush(wx.Brush(theme.ACCENT))
            gc.SetPen(wx.TRANSPARENT_PEN)
            for px, py in points:
                gc.DrawEllipse(px - 3, py - 3, 6, 6)

        # ukazatel přehrávání v režimu Song
        if self.player.playing and self.player.mode == "Song":
            x = NAME_W + self.player.position / STEPS_PER_BAR * bar_w
            gc.SetPen(wx.Pen(theme.ACCENT, 1))
            gc.StrokeLine(x, 0, x, h)
