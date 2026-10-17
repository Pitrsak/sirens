"""Panely UI: sekce s knoby, panel syntezátoru a zobrazení obrazu z OpenCV."""

import cv2
import wx

from fathom.ui import theme
from fathom.ui.knob import Knob


class Section(wx.Panel):
    """Pojmenovaná skupina knobů (např. FILTER: cutoff, reso, ...)."""

    def __init__(self, parent, title, params, on_change, knobs: dict):
        super().__init__(parent)
        self.SetBackgroundColour(theme.PANEL)
        caption = wx.StaticText(self, label=title)
        caption.SetForegroundColour(theme.ACCENT)
        caption.SetFont(theme.font(8, bold=True))
        row = wx.BoxSizer(wx.HORIZONTAL)
        for param in params:
            knob = Knob(self, param, on_change)
            knobs[param.key] = knob      # zaregistrujeme knob, aby šel nastavit z presetu
            row.Add(knob, 0, wx.ALL, 2)
        column = wx.BoxSizer(wx.VERTICAL)
        column.Add(caption, 0, wx.LEFT | wx.TOP, 8)
        column.Add(row, 0, wx.ALL, 4)
        self.SetSizer(column)


class KnobBoard(wx.ScrolledWindow):
    """Mřížka sekcí s knoby. Drží slovník knobů podle klíče parametru."""

    def __init__(self, parent, sections, on_change, columns=3):
        super().__init__(parent)
        self.SetBackgroundColour(theme.BACKGROUND)
        self.SetScrollRate(0, 10)
        self.knobs = {}
        grid = wx.WrapSizer(wx.HORIZONTAL)
        for title, params in sections:
            grid.Add(Section(self, title, params, on_change, self.knobs), 0, wx.ALL, 5)
        self.SetSizer(grid)

    def set_values(self, values: dict):
        """Nastaví knoby (a přes jejich callback i engine) podle presetu."""
        for key, value in values.items():
            if key in self.knobs:
                self.knobs[key].set_value(value)

    def get_values(self) -> dict:
        return {key: knob.value for key, knob in self.knobs.items()}


class ImageView(wx.Panel):
    """Zobrazí OpenCV obraz (BGR numpy pole) roztažený na velikost panelu."""

    def __init__(self, parent):
        super().__init__(parent)
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.bitmap = None
        self.Bind(wx.EVT_PAINT, self._on_paint)

    def show(self, frame):
        w, h = self.GetClientSize()
        if w < 2 or h < 2:
            return
        frame = cv2.resize(frame, (w, h), interpolation=cv2.INTER_LINEAR)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)   # wx chce RGB, OpenCV pracuje v BGR
        self.bitmap = wx.Bitmap.FromBuffer(w, h, rgb.tobytes())
        self.Refresh(False)

    def _on_paint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(wx.BLACK))
        dc.Clear()
        if self.bitmap:
            dc.DrawBitmap(self.bitmap, 0, 0)
