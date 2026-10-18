"""Záložka Visual: abstraktní obraz, který reaguje na zvuk ze záložky Sound."""

import wx

from sirens.ui import theme
from sirens.ui.sidebar import Sidebar, divider
from sirens.ui.views import VisualView
from sirens.visual.painter import Painter


class VisualPage(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        self.SetBackgroundColour(theme.BACKGROUND)
        self.painter = Painter()
        self.view = VisualView(self)

        self.sidebar = Sidebar(self)
        self.sidebar.add_group("Visual")
        self.sidebar.add_note("The shape follows the sound from the Sound tab: bass makes it bigger, "
                              "the spectrum bends its outline, high notes shift the colour.")
        self.sidebar.add_params(self.painter)
        self.sidebar.finish()

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(self.view, 1, wx.EXPAND | wx.ALL, 20)
        row.Add(divider(self, vertical=True), 0, wx.EXPAND)
        row.Add(self.sidebar, 0, wx.EXPAND)
        self.SetSizer(row)

    def tick(self, analyzer):
        """Každý snímek, když je záložka vidět: spočítá a ukáže další obraz."""
        self.view.show(self.painter.render(analyzer))
