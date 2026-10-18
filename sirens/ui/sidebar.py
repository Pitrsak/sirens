"""Pravý panel s ovládáním (jako v Event Horizon / Flip).

Nahoře je pevná část (výstup), pod ní posuvná část, kterou si plní kód
v sound.py: skupiny s nadpisem a slidery s krátkým vysvětlením pod sebou.
Panel sám o zvuku nic neví, jen staví ovládací prvky a volá on_change.
"""

import wx

from sirens.ui import theme
from sirens.ui.slider import Slider
from sirens.ui.widgets import Caption

WIDTH = 340      # pevná šířka panelu
PADDING = 16     # odsazení obsahu od okrajů panelu


def divider(parent, vertical: bool = False) -> wx.Panel:
    """Tenká čára mezi skupinami (nebo svislá mezi grafy a panelem)."""
    line = wx.Panel(parent, size=(1, -1) if vertical else (-1, 1))
    line.SetBackgroundColour(theme.BORDER)
    return line


class Sidebar(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        self.SetBackgroundColour(theme.SIDEBAR)
        self.SetMinSize((WIDTH, -1))

        # pevná část (hlasitost výstupu), nemaže se při novém načtení sound.py
        self.fixed = wx.Panel(self)
        self.fixed.SetBackgroundColour(theme.SIDEBAR)
        self.fixed_sizer = wx.BoxSizer(wx.VERTICAL)
        self.fixed.SetSizer(self.fixed_sizer)

        # posuvná část pro slidery ze sound.py
        self.scroll = wx.ScrolledWindow(self)
        self.scroll.SetBackgroundColour(theme.SIDEBAR)
        self.scroll.SetScrollRate(0, 12)
        self.scroll_sizer = wx.BoxSizer(wx.VERTICAL)
        self.scroll.SetSizer(self.scroll_sizer)

        column = wx.BoxSizer(wx.VERTICAL)
        column.Add(self.fixed, 0, wx.EXPAND | wx.BOTTOM, PADDING)
        column.Add(divider(self), 0, wx.EXPAND)
        column.Add(self.scroll, 1, wx.EXPAND)
        self.SetSizer(column)

    def _area(self, fixed: bool):
        return (self.fixed, self.fixed_sizer) if fixed else (self.scroll, self.scroll_sizer)

    def add_group(self, title: str, fixed: bool = False):
        """Nadpis nové skupiny. Od předchozí skupiny ji oddělí čára."""
        parent, sizer = self._area(fixed)
        if sizer.GetItemCount() > 0:
            sizer.Add(divider(parent), 0, wx.EXPAND | wx.TOP, PADDING)
        sizer.Add(Caption(parent, title), 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, PADDING)

    def add_slider(self, label, lo, hi, default, unit="", log=False, help="",
                   on_change=None, value=None, fixed=False) -> Slider:
        """Slider a pod ním (volitelně) šedé vysvětlení, co dělá.

        value: počáteční hodnota, pokud se liší od výchozí (po novém načtení sound.py).
        """
        parent, sizer = self._area(fixed)
        slider = Slider(parent, label, lo, hi, default, unit, log, on_change, value)
        sizer.AddSpacer(PADDING if fixed else 12)
        sizer.Add(slider, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, PADDING)
        if help:
            text = wx.StaticText(parent, label=help)
            text.SetForegroundColour(theme.TEXT_DIM)
            text.SetFont(theme.font(10))
            text.Wrap(WIDTH - 2 * PADDING)
            sizer.AddSpacer(5)
            sizer.Add(text, 0, wx.LEFT | wx.RIGHT, PADDING)
        return slider

    def add_note(self, text: str, colour=theme.TEXT_DIM):
        """Volný text v posuvné části (nápověda, nebo chyba v sound.py)."""
        note = wx.StaticText(self.scroll, label=text)
        note.SetForegroundColour(colour)
        note.SetFont(theme.font(11))
        note.Wrap(WIDTH - 2 * PADDING)
        self.scroll_sizer.Add(note, 0, wx.ALL, PADDING)

    def clear(self):
        """Smaže všechno v posuvné části (před novým načtením sound.py)."""
        self.scroll_sizer.Clear(delete_windows=True)

    def finish(self):
        """Po přidání prvků přepočítá rozložení a posuvník."""
        self.scroll_sizer.AddSpacer(PADDING)
        self.fixed.Layout()
        self.scroll.Layout()
        self.scroll.FitInside()
        self.Layout()
