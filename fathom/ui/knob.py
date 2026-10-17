"""Vlastní knob (otočný ovladač) kreslený přes wx.GraphicsContext.

Ovládání: tažení myší nahoru/dolů (se Shiftem jemně), kolečko myši,
dvojklik vrátí výchozí hodnotu.
"""

import math

import wx

from fathom.param import Param
from fathom.ui import theme

SWEEP = 1.5 * math.pi          # knob se otáčí o 270 stupňů
START_ANGLE = 0.75 * math.pi   # začátek vlevo dole (osa y ve wx míří dolů)
DRAG_PIXELS = 160              # o kolik pixelů táhnout pro celý rozsah


class Knob(wx.Control):
    def __init__(self, parent, param: Param, on_change):
        super().__init__(parent, style=wx.BORDER_NONE)
        self.param = param
        self.on_change = on_change   # funkce(key, value), volá se při změně
        self.value = param.default
        self._drag_start = None
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.SetMinSize((62, 82))
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_LEFT_DOWN, self._on_down)
        self.Bind(wx.EVT_LEFT_UP, self._on_up)
        self.Bind(wx.EVT_MOTION, self._on_motion)
        self.Bind(wx.EVT_MOUSEWHEEL, self._on_wheel)
        self.Bind(wx.EVT_LEFT_DCLICK, lambda e: self.set_value(self.param.default))

    # --- převod hodnota <-> poloha 0..1 ---

    def _to_norm(self, value: float) -> float:
        p = self.param
        if p.log:
            return math.log(value / p.lo) / math.log(p.hi / p.lo)
        return (value - p.lo) / (p.hi - p.lo)

    def _from_norm(self, norm: float) -> float:
        p = self.param
        norm = min(1.0, max(0.0, norm))
        value = p.lo * (p.hi / p.lo) ** norm if p.log else p.lo + norm * (p.hi - p.lo)
        if p.step:
            value = round(value / p.step) * p.step
        return value

    def set_value(self, value: float, notify: bool = True):
        self.value = self._from_norm(self._to_norm(value))  # oříznutí a zaokrouhlení na krok
        self.Refresh()
        if notify:
            self.on_change(self.param.key, self.value)

    # --- myš ---

    def _on_down(self, event):
        self._drag_start = (event.GetY(), self._to_norm(self.value))
        self.CaptureMouse()

    def _on_up(self, event):
        self._drag_start = None
        if self.HasCapture():
            self.ReleaseMouse()

    def _on_motion(self, event):
        if self._drag_start is None or not event.Dragging():
            return
        start_y, start_norm = self._drag_start
        pixels = DRAG_PIXELS * (5 if event.ShiftDown() else 1)
        self.set_value(self._from_norm(start_norm + (start_y - event.GetY()) / pixels))

    def _on_wheel(self, event):
        step = 1 / (len(self.param.choices) - 1) if self.param.choices else 0.02
        direction = 1 if event.GetWheelRotation() > 0 else -1
        self.set_value(self._from_norm(self._to_norm(self.value) + direction * step))

    # --- kreslení ---

    def _value_text(self) -> str:
        p = self.param
        if p.choices:
            return p.choices[int(self.value)]
        if p.unit == "Hz" and self.value >= 1000:
            return f"{self.value / 1000:.1f}k"
        if p.unit == "s" and self.value < 1:
            return f"{self.value * 1000:.0f}ms"
        if p.step or abs(self.value) >= 100:
            return f"{self.value:.0f}"
        return f"{self.value:.2f}"

    def _on_paint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(self.GetParent().GetBackgroundColour()))
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        w, h = self.GetClientSize()
        cx, cy, r = w / 2, 30, 22
        angle = START_ANGLE + SWEEP * self._to_norm(self.value)

        # dráha a hodnota jako dva oblouky
        for colour, end in ((theme.KNOB_TRACK, START_ANGLE + SWEEP), (theme.ACCENT, angle)):
            path = gc.CreatePath()
            path.AddArc(cx, cy, r, START_ANGLE, end, True)
            gc.SetPen(wx.Pen(colour, 3))
            gc.StrokePath(path)

        # tělo knobu a ukazatel
        gc.SetPen(wx.Pen(theme.PANEL_BORDER, 1))
        gc.SetBrush(wx.Brush(theme.KNOB_FACE))
        gc.DrawEllipse(cx - r + 6, cy - r + 6, 2 * (r - 6), 2 * (r - 6))
        gc.SetPen(wx.Pen(theme.TEXT, 2))
        gc.StrokeLine(cx + math.cos(angle) * 6, cy + math.sin(angle) * 6,
                      cx + math.cos(angle) * (r - 8), cy + math.sin(angle) * (r - 8))

        # popisek a hodnota
        for text, y, colour, bold in ((self.param.label, 58, theme.TEXT_DIM, True),
                                      (self._value_text(), 71, theme.TEXT, False)):
            gc.SetFont(theme.font(7, bold), colour)
            tw, _ = gc.GetTextExtent(text)
            gc.DrawText(text, (w - tw) / 2, y)
