"""Hlavní okno, rozložení jako v Event Horizon / Flip:

    +--------------------------------------------------------------+
    | SIRENS                                     [Reload]  [Stop]  |
    +-----------------------------------------+--------------------+
    |  SCOPE (tvar vlny)                      | OUTPUT             |
    |                                         |   Master           |
    |  SPECTRUM (vlastní DFT)                 | ------------------ |
    |                                         | slidery ze         |
    |  [stav: načteno / chyba v sound.py]     | sound.py           |
    +-----------------------------------------+--------------------+

Časovač běží 30x za sekundu: překreslí grafy a dvakrát za sekundu se
podívá, jestli se sound.py neuložil (pak ho načte znovu).
"""

import wx

from sirens.audio.analyzer import SCOPE_VIEW
from sirens.live import SoundLoader
from sirens.ui import theme
from sirens.ui.sidebar import Sidebar, divider
from sirens.ui.views import ScopeView, SpectrumView
from sirens.ui.widgets import Caption, PillButton, StatusPill

FPS = 30
WATCH_EVERY = 15   # po kolika snímcích kontrolovat sound.py (15 = 2x za sekundu)


class MainFrame(wx.Frame):
    def __init__(self, engine):
        super().__init__(None, title="Sirens", size=(1240, 800))
        self.SetMinSize((900, 600))
        self.engine = engine
        self.playing = True
        self.ticks = 0

        root = wx.Panel(self)
        root.SetBackgroundColour(theme.BACKGROUND)
        self.sidebar = Sidebar(root)

        workspace = wx.BoxSizer(wx.HORIZONTAL)
        workspace.Add(self._build_viewport(root), 1, wx.EXPAND)
        workspace.Add(divider(root, vertical=True), 0, wx.EXPAND)
        workspace.Add(self.sidebar, 0, wx.EXPAND)

        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(self._build_header(root), 0, wx.EXPAND)
        layout.Add(divider(root), 0, wx.EXPAND)
        layout.Add(workspace, 1, wx.EXPAND)
        root.SetSizer(layout)

        # pevná skupina OUTPUT: celková hlasitost
        self.sidebar.add_group("Output", fixed=True)
        self.sidebar.add_slider("Master", 0, 1, 0.5, on_change=engine.set_volume, fixed=True,
                                help="Overall loudness. After it the signal is clipped to -1..1, "
                                     "so a mistake in sound.py cannot blast the speakers.")

        self.loader = SoundLoader(engine, self.sidebar)
        self._reload()

        # Cmd+R (na Windows/Linuxu Ctrl+R) = načíst sound.py znovu
        reload_id = wx.NewIdRef()
        self.Bind(wx.EVT_MENU, lambda e: self._reload(), id=reload_id)
        self.SetAcceleratorTable(wx.AcceleratorTable([(wx.ACCEL_CMD, ord("R"), reload_id)]))

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_tick, self.timer)
        self.timer.Start(int(1000 / FPS))
        self.Bind(wx.EVT_CLOSE, self._on_close)

    # --- stavba UI ---

    def _build_header(self, parent):
        header = wx.Panel(parent)
        header.SetBackgroundColour(theme.BACKGROUND)
        header.SetMinSize((-1, 56))
        logo = Caption(header, "Sirens", colour=theme.TEXT, size=13, spacing=4)
        logo.SetMinSize((140, 24))
        reload_button = PillButton(header, "Reload", self._reload)
        self.play_button = PillButton(header, "Stop", self._toggle_playing, primary=True)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(logo, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 24)
        row.AddStretchSpacer()
        row.Add(reload_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        row.Add(self.play_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 20)
        header.SetSizer(row)
        return header

    def _build_viewport(self, parent):
        self.scope = ScopeView(parent)
        self.spectrum = SpectrumView(parent)
        self.status = StatusPill(parent)
        column = wx.BoxSizer(wx.VERTICAL)
        column.Add(self.scope, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 20)
        column.Add(self.spectrum, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 20)
        column.Add(self.status, 0, wx.EXPAND | wx.ALL, 20)
        return column

    # --- akce ---

    def _reload(self):
        text, error = self.loader.load()
        if self.sidebar.scroll_sizer.GetItemCount() == 0:
            hint = "Fix the error in sound.py and save again." if error else \
                   "Sliders from sound.py appear here (ui.slider)."
            self.sidebar.add_note(hint)
        self.sidebar.finish()
        self.status.show(text, error)

    def _toggle_playing(self):
        self.playing = not self.playing
        self.engine.set_playing(self.playing)
        self.play_button.set_label("Stop" if self.playing else "Play")
        self.play_button.GetParent().Layout()

    # --- smyčka ---

    def _on_tick(self, event):
        self.ticks += 1
        if self.ticks % WATCH_EVERY == 0 and self.loader.changed():
            self._reload()

        analyzer = self.engine.analyzer
        if analyzer.update():
            duration_ms = SCOPE_VIEW / analyzer.sample_rate * 1000
            self.scope.show(analyzer.scope(), duration_ms, analyzer.peak_level_db())
            self.spectrum.show(analyzer.freqs, analyzer.spectrum, analyzer.peak_frequency())

    def _on_close(self, event):
        self.timer.Stop()
        self.engine.close()
        event.Skip()
