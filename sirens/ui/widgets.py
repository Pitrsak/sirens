"""Drobné kreslené prvky UI: nadpis, tlačítka (i ikony Undo / Redo) a stavový štítek.

Nativní wx.Button na macOS barvu ani tvar změnit nedovolí, proto si
tlačítka kreslíme sami (stejně jako slider).
"""

import math

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


class ArrowButton(wx.Control):
    """Ikona Undo (zahnutá šipka doleva) nebo Redo (zrcadlově doprava).

    Bez textu, jako v hlavičce většiny programů. Když není co vracet,
    je tmavá a nereaguje (vypnutý prvek wx nedostává kliknutí).
    """

    SIZE = 28

    def __init__(self, parent, redo: bool, on_click, tip: str):
        super().__init__(parent, style=wx.BORDER_NONE)
        self.redo, self.on_click = redo, on_click
        self.hot = False
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        self.SetMinSize((self.SIZE, self.SIZE))
        self.SetToolTip(tip)
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_LEFT_UP, lambda e: self.on_click())
        self.Bind(wx.EVT_ENTER_WINDOW, lambda e: self._set_hot(True))
        self.Bind(wx.EVT_LEAVE_WINDOW, lambda e: self._set_hot(False))

    def set_enabled(self, enabled: bool):
        """Zapne / vypne tlačítko; překreslí se jen při změně (volá se 3x za sekundu)."""
        if enabled != self.IsEnabled():
            self.Enable(enabled)
            self.Refresh()

    def _set_hot(self, hot: bool):
        self.hot = hot
        self.Refresh()

    def _on_paint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(self.GetParent().GetBackgroundColour()))
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        if not self.IsEnabled():
            colour = theme.TEXT_DIM
        else:
            colour = theme.TEXT if self.hot else theme.TEXT_MUTED
        gc.SetPen(wx.Pen(colour, 2, wx.PENSTYLE_SOLID))
        gc.SetBrush(wx.TRANSPARENT_BRUSH)
        if self.redo:
            gc.Translate(self.SIZE, 0)     # Redo = Undo zrcadlově: osa x obrácená
            gc.Scale(-1, 1)
        # šipka: hrot vlevo nahoře, čára doprava, oblouk dolů a kousek zpátky doleva
        path = gc.CreatePath()
        path.MoveToPoint(8, 11)
        path.AddLineToPoint(16, 11)
        path.AddArc(16, 15.5, 4.5, -math.pi / 2, math.pi / 2, True)
        path.AddLineToPoint(12, 20)
        path.MoveToPoint(11.5, 7.5)        # hrot
        path.AddLineToPoint(8, 11)
        path.AddLineToPoint(11.5, 14.5)
        gc.StrokePath(path)

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


class ChoiceRow(wx.Control):
    """Popisek a řada tlačítek, z nichž je vybrané právě jedno (např. Sine / Saw / Square).

    on_change(index) dostane pořadí vybrané možnosti (0, 1, 2, ...).
    """

    LABEL_WIDTH = 86
    HEIGHT = 26

    def __init__(self, parent, label: str, options, index: int, on_change):
        super().__init__(parent, style=wx.BORDER_NONE)
        self.label, self.options, self.index, self.on_change = label, list(options), index, on_change
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.SetMinSize((-1, self.HEIGHT))
        self.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_LEFT_DOWN, self._on_down)

    def _option_rects(self):
        """Obdélník (x, šířka) pro každou možnost: zbytek šířky rozdělený rovným dílem."""
        w, _ = self.GetClientSize()
        width = (w - self.LABEL_WIDTH) / len(self.options)
        return [(self.LABEL_WIDTH + i * width, width) for i in range(len(self.options))]

    def _on_down(self, event):
        for i, (x, width) in enumerate(self._option_rects()):
            if x <= event.GetX() < x + width:
                self.index = i
                self.Refresh()
                self.on_change(i)

    def _on_paint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(self.GetParent().GetBackgroundColour()))
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        _, h = self.GetClientSize()
        gc.SetFont(theme.font(11), theme.TEXT_MUTED)
        _, th = gc.GetTextExtent(self.label)
        gc.DrawText(self.label, 0, (h - th) / 2)
        for i, (x, width) in enumerate(self._option_rects()):
            selected = i == self.index
            gc.SetPen(wx.Pen(theme.BORDER, 1))
            gc.SetBrush(wx.Brush(theme.SLIDER_FILL_HOT if selected else theme.SLIDER_TRACK))
            gc.DrawRoundedRectangle(x + 1, 0.5, width - 2, h - 1, 4)
            gc.SetFont(theme.font(10, bold=selected), theme.TEXT if selected else theme.TEXT_MUTED)
            tw, th = gc.GetTextExtent(self.options[i])
            gc.DrawText(self.options[i], x + (width - tw) / 2, (h - th) / 2)


def confirm(parent, message: str, title: str, action: str) -> bool:
    """Zeptá se před nevratnou změnou. Tlačítka říkají, co udělají (např. Remove / Cancel),
    protože u Yes / No se na macOS snadno klikne na modré (výchozí) No.
    """
    with wx.MessageDialog(parent, message, title, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING) as dialog:
        dialog.SetYesNoLabels(action, "Cancel")
        return dialog.ShowModal() == wx.ID_YES
