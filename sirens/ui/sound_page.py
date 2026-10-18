"""Záložka Sound: skládání zvuku z bloků.

    +-----------------------------------------+--------------------+
    |  SCOPE (tvar vlny)                      | OUTPUT  Master     |
    |                                         | ------------------ |
    |  SPECTRUM (vlastní DFT)                 | bloky z racku      |
    |                                         | a jejich slidery   |
    |  [cesta zvuku: Sine + Noise -> Delay]   | [Add block]        |
    +-----------------------------------------+--------------------+
"""

import wx

from sirens.audio.analyzer import SCOPE_VIEW
from sirens.audio.blocks import CATALOG
from sirens.audio.rack import Rack
from sirens.ui import theme
from sirens.ui.sidebar import Sidebar, divider
from sirens.ui.views import ScopeView, SpectrumView
from sirens.ui.widgets import StatusPill


class SoundPage(wx.Panel):
    def __init__(self, parent, engine):
        super().__init__(parent)
        self.SetBackgroundColour(theme.BACKGROUND)
        self.rack = Rack(engine)

        self.scope = ScopeView(self)
        self.spectrum = SpectrumView(self)
        self.status = StatusPill(self)
        column = wx.BoxSizer(wx.VERTICAL)
        column.Add(self.scope, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 20)
        column.Add(self.spectrum, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 20)
        column.Add(self.status, 0, wx.EXPAND | wx.ALL, 20)

        self.sidebar = Sidebar(self, with_fixed=True)
        self.sidebar.add_group("Output", fixed=True)
        self.sidebar.add_slider("Master", 0, 1, 0.5, on_change=engine.set_volume, fixed=True,
                                help="Overall loudness. After it the sound is clipped to -1..1, "
                                     "so too many loud blocks cannot blast the speakers.")

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(column, 1, wx.EXPAND)
        row.Add(divider(self, vertical=True), 0, wx.EXPAND)
        row.Add(self.sidebar, 0, wx.EXPAND)
        self.SetSizer(row)
        self._show_rack()

    def _show_rack(self):
        """Překreslí pravý panel podle racku: pro každý blok skupinu se slidery."""
        self.sidebar.clear()
        for block in self.rack.blocks:
            # b=block: lambda si musí zapamatovat tenhle blok, ne poslední z cyklu
            self.sidebar.add_group(block.NAME, actions=[
                ("Up", lambda b=block: self._later(self.rack.move, b, -1)),
                ("Down", lambda b=block: self._later(self.rack.move, b, 1)),
                ("Remove", lambda b=block: self._later(self.rack.remove, b)),
            ])
            self.sidebar.add_params(block)
        if not self.rack.blocks:
            self.sidebar.add_note("Empty. Add a source (Sine, Harmonics, Sweep, Noise), "
                                  "then effects below it. Sound flows from top to bottom.")
        self.add_button = self.sidebar.add_button("Add block", self._show_add_menu)
        self.sidebar.finish()
        self.status.show(self.rack.describe() or "Silence: no blocks yet.")

    def _later(self, action, *args):
        """Provede změnu racku a překreslí panel, ale až po skončení kliknutí.

        Tlačítko, na které se kliklo, je v panelu, který se teď smaže, a okno
        nejde zrušit uprostřed jeho vlastní události. Proto wx.CallAfter.
        """
        def run():
            action(*args)
            self._show_rack()
        wx.CallAfter(run)

    def _show_add_menu(self):
        """Menu se všemi druhy bloků: nahoře zdroje, pod čarou efekty."""
        menu = wx.Menu()
        previous = None
        for block_class in CATALOG:
            if previous is not None and previous.IS_SOURCE != block_class.IS_SOURCE:
                menu.AppendSeparator()
            item = menu.Append(wx.ID_ANY, block_class.NAME)
            menu.Bind(wx.EVT_MENU, lambda e, c=block_class: self._later(self.rack.add, c), item)
            previous = block_class
        self.add_button.PopupMenu(menu, (0, self.add_button.GetSize().height))
        menu.Destroy()

    def tick(self, analyzer):
        """Zavolá hlavní okno, když je hotový nový úsek zvuku."""
        duration_ms = SCOPE_VIEW / analyzer.sample_rate * 1000
        self.scope.show(analyzer.scope(), duration_ms, analyzer.peak_level_db())
        self.spectrum.show(analyzer.freqs, analyzer.spectrum, analyzer.peak_frequency())
