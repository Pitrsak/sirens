"""Drobné kreslené prvky UI: nadpis, tlačítko a stavový štítek.

Nativní wx.Button na macOS barvu ani tvar změnit nedovolí, proto si
tlačítka kreslíme sami (stejně jako slider).
"""

import wx

from sirens.ui import theme


class Caption(wx.Control):
    """Malý nadpis velkými písmeny s rozestupem (např. SCOPE, OSCILLATOR)."""

    def __init__(self, parent, text: str, colour=theme.TEXT_MUTED, size: int = 9, spacing: float = 1.5):
        super().__init__(parent, style=wx.BORDER_NONE)
        self.text = text.upper()
        self.colour, self.size, self.spacing = colour, size, spacing
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.SetMinSize((-1, size + 10))
        self.Bind(wx.EVT_PAINT, self._on_paint)

    def _on_paint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(self.GetParent().GetBackgroundColour()))
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        gc.SetFont(theme.font(self.size, bold=True), self.colour)
        theme.draw_spaced(gc, self.text, 0, 2, self.spacing)


class PillButton(wx.Control):
    """Zaoblené tlačítko. primary=True: bílé s černým textem (jako Save ve Flipu),
    jinak průhledné s tenkým okrajem."""

    def __init__(self, parent, label: str, on_click, primary: bool = False):
        super().__init__(parent, style=wx.BORDER_NONE)
        self.label, self.on_click, self.primary = label, on_click, primary
        self.hot = False
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_LEFT_UP, lambda e: self.on_click())
        self.Bind(wx.EVT_ENTER_WINDOW, lambda e: self._set_hot(True))
        self.Bind(wx.EVT_LEAVE_WINDOW, lambda e: self._set_hot(False))
        self.set_label(label)

    def set_label(self, label: str):
        self.label = label
        width = self.GetTextExtent(label)[0] + 32
        self.SetMinSize((max(72, width), 30))
        self.Refresh()

    def set_primary(self, primary: bool):
        """Přepne vzhled (u záložek: vybraná záložka je bílá)."""
        self.primary = primary
        self.Refresh()

    def _set_hot(self, hot: bool):
        self.hot = hot
        self.Refresh()

    def _on_paint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(self.GetParent().GetBackgroundColour()))
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        w, h = self.GetClientSize()
        if self.primary:
            gc.SetPen(wx.TRANSPARENT_PEN)
            gc.SetBrush(wx.Brush(theme.TEXT_MUTED if self.hot else theme.ACCENT))
            text_colour = theme.BACKGROUND
        else:
            gc.SetPen(wx.Pen(theme.TEXT_DIM if self.hot else theme.BORDER, 1))
            gc.SetBrush(wx.TRANSPARENT_BRUSH)
            text_colour = theme.TEXT if self.hot else theme.TEXT_MUTED
        gc.DrawRoundedRectangle(0.5, 0.5, w - 1, h - 1, 6)
        gc.SetFont(theme.font(11, bold=True), text_colour)
        tw, th = gc.GetTextExtent(self.label)
        gc.DrawText(self.label, (w - tw) / 2, (h - th) / 2)


class TextButton(wx.Control):
    """Malé tlačítko jen z textu (např. Remove u bloku). Pod myší zkorálovatí."""

    def __init__(self, parent, label: str, on_click):
        super().__init__(parent, style=wx.BORDER_NONE)
        self.label, self.on_click = label, on_click
        self.hot = False
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        self.SetFont(theme.font(10))
        width, height = self.GetTextExtent(label)
        self.SetMinSize((width + 4, height + 4))
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_LEFT_UP, lambda e: self.on_click())
        self.Bind(wx.EVT_ENTER_WINDOW, lambda e: self._set_hot(True))
        self.Bind(wx.EVT_LEAVE_WINDOW, lambda e: self._set_hot(False))

    def _set_hot(self, hot: bool):
        self.hot = hot
        self.Refresh()

    def _on_paint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(self.GetParent().GetBackgroundColour()))
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        gc.SetFont(theme.font(10), theme.ERROR if self.hot else theme.TEXT_DIM)
        gc.DrawText(self.label, 2, 2)


class StatusPill(wx.Control):
    """Štítek se stavem dole pod grafy (co je v racku, nápověda)."""

    def __init__(self, parent):
        super().__init__(parent, style=wx.BORDER_NONE)
        self.text, self.error = "", False
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.SetMinSize((-1, 34))
        self.Bind(wx.EVT_PAINT, self._on_paint)

    def show(self, text: str, error: bool = False):
        self.text, self.error = text, error
        self.Refresh()

    def _on_paint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(self.GetParent().GetBackgroundColour()))
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        w, h = self.GetClientSize()
        gc.SetPen(wx.Pen(theme.ERROR if self.error else theme.BORDER, 1))
        gc.SetBrush(wx.Brush(theme.VIEWPORT))
        gc.DrawRoundedRectangle(0.5, 0.5, w - 1, h - 1, 8)
        gc.SetFont(theme.font(11), theme.ERROR if self.error else theme.TEXT_MUTED)
        _, th = gc.GetTextExtent(self.text or " ")
        gc.DrawText(self.text, 14, (h - th) / 2)
