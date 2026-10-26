"""Drobný kreslený prvky UI: nadpis, tlačítka a stavovej štítek.

Proč ne normální wx.Button? Nativní tlačítko na macOS barvu ani tvar změnit
nedovolí, takže by tam svítilo modrý systémový tlačítko. Proto si tlačítka
kreslíme sami, stejně jako slider.

Všechny prvky tady jedou podle stejnýho receptu:
 - dědí z wx.Control (prázdnej prvek, nic sám nekreslí)
 - SetBackgroundStyle(BG_STYLE_PAINT) + Bind(EVT_PAINT) = kreslím si sám, celý
 - _on_paint: AutoBufferedPaintDC (plátno bez blikání), smazat pozadí,
   GraphicsContext (hezký kreslení) a nakreslit
 - když se něco změní, zavolá se Refresh() a wx pak sám pošle EVT_PAINT
"""

import wx

from sirens.ui import theme


class Caption(wx.Control):
    """Malej nadpis velkejma písmenama s mezerama (třeba SCOPE, OSCILLATOR)."""

    def __init__(self, parent, text: str, colour=theme.TEXT_MUTED, size: int = 9, spacing: float = 1.5):
        super().__init__(parent, style=wx.BORDER_NONE)
        self.text = text.upper()
        self.colour, self.size, self.spacing = colour, size, spacing
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.SetMinSize((-1, size + 10))    # výška podle písma a kousek navíc
        self.Bind(wx.EVT_PAINT, self._on_paint)

    def _on_paint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(self.GetParent().GetBackgroundColour()))   # splynout s panelem pod tím
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        gc.SetFont(theme.font(self.size, bold=True), self.colour)
        theme.draw_spaced(gc, self.text, 0, 2, self.spacing)


class PillButton(wx.Control):
    """Zaoblený tlačítko. primary=True: bílý s černým textem (jako Save ve Flipu),
    jinak průhledný s tenkým okrajem."""

    def __init__(self, parent, label: str, on_click, primary: bool = False):
        super().__init__(parent, style=wx.BORDER_NONE)
        self.label, self.on_click, self.primary = label, on_click, primary
        self.hot = False                 # myš nad tlačítkem = zesvětlí se
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.SetCursor(wx.Cursor(wx.CURSOR_HAND))   # ručička, ať je jasný, že se na to dá kliknout
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_LEFT_UP, lambda e: self.on_click())   # klik = puštění levýho tlačítka
        self.Bind(wx.EVT_ENTER_WINDOW, lambda e: self._set_hot(True))
        self.Bind(wx.EVT_LEAVE_WINDOW, lambda e: self._set_hot(False))
        self.set_label(label)

    def set_label(self, label: str):
        self.label = label
        width = self.GetTextExtent(label)[0] + 32   # šířka textu + 16 px z každý strany
        self.SetMinSize((max(72, width), 30))       # ale aspoň 72 px, ať krátký tlačítka nejsou titěrný
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
            # bílá výplň bez obrysu, pod myší šedivější
            gc.SetPen(wx.TRANSPARENT_PEN)
            gc.SetBrush(wx.Brush(theme.TEXT_MUTED if self.hot else theme.ACCENT))
            text_colour = theme.BACKGROUND
        else:
            # jen obrys, bez výplně, pod myší světlejší
            gc.SetPen(wx.Pen(theme.TEXT_DIM if self.hot else theme.BORDER, 1))
            gc.SetBrush(wx.TRANSPARENT_BRUSH)
            text_colour = theme.TEXT if self.hot else theme.TEXT_MUTED
        gc.DrawRoundedRectangle(0.5, 0.5, w - 1, h - 1, 6)   # 0.5 = ostrá čára 1 px, ne rozmazaná přes dva
        gc.SetFont(theme.font(11, bold=True), text_colour)
        tw, th = gc.GetTextExtent(self.label)
        gc.DrawText(self.label, (w - tw) / 2, (h - th) / 2)   # text přesně doprostřed


class TextButton(wx.Control):
    """Malý tlačítko jen z textu (třeba Remove u bloku). Pod myší zkorálovatí."""

    def __init__(self, parent, label: str, on_click):
        super().__init__(parent, style=wx.BORDER_NONE)
        self.label, self.on_click = label, on_click
        self.hot = False
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        self.SetFont(theme.font(10))
        width, height = self.GetTextExtent(label)    # velikost podle textu (font je nastavenej o řádek výš)
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
        # error=True: okraj a text korálově
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
        _, th = gc.GetTextExtent(self.text or " ")   # " ": z prázdnýho textu by výška vyšla 0
        gc.DrawText(self.text, 14, (h - th) / 2)


class ChoiceRow(wx.Control):
    """Popisek a řada tlačítek, z nich je vybraný vždycky právě jedno (třeba Sine / Saw / Square).

    on_change(index) dostane pořadí vybraný možnosti (0, 1, 2, ...).
    """

    LABEL_WIDTH = 86     # kolik místa vlevo dostane popisek
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
        """Obdélník (x, šířka) pro každou možnost: zbytek šířky rozdělenej rovným dílem."""
        w, _ = self.GetClientSize()
        width = (w - self.LABEL_WIDTH) / len(self.options)
        return [(self.LABEL_WIDTH + i * width, width) for i in range(len(self.options))]

    def _on_down(self, event):
        # na který tlačítko se kliklo? projít obdélníky a najít ten, kde je x myši
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
            # vybraná možnost má světlejší výplň a tučnej bílej text
            gc.SetPen(wx.Pen(theme.BORDER, 1))
            gc.SetBrush(wx.Brush(theme.SLIDER_FILL_HOT if selected else theme.SLIDER_TRACK))
            gc.DrawRoundedRectangle(x + 1, 0.5, width - 2, h - 1, 4)
            gc.SetFont(theme.font(10, bold=selected), theme.TEXT if selected else theme.TEXT_MUTED)
            tw, th = gc.GetTextExtent(self.options[i])
            gc.DrawText(self.options[i], x + (width - tw) / 2, (h - th) / 2)


def confirm(parent, message: str, title: str, action: str) -> bool:
    """Zeptá se před nevratnou změnou. Tlačítka říkají, co udělají (třeba Remove / Cancel),
    protože u Yes / No se na macOS snadno klikne na modrý (výchozí) No.

    Vrátí True, když se kliklo na akci. ShowModal čeká, dokud se dialog nezavře.
    """
    with wx.MessageDialog(parent, message, title, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING) as dialog:
        dialog.SetYesNoLabels(action, "Cancel")
        return dialog.ShowModal() == wx.ID_YES
