"""Záložka Sound: nástroj vybrané stopy (obálka a bloky) a hraní na klávesnici.

    +-----------------------------------------+--------------------+
    |  SCOPE (tvar vlny)                      | OUTPUT  Master     |
    |                                         | ------------------ |
    |  SPECTRUM (vlastní DFT)                 | TRACK  výběr stopy |
    |                                         | ENVELOPE           |
    |  [cesta zvuku: Oscillator -> Filter]    | bloky nástroje     |
    |  [klaviatura]                           | [Add block]        |
    +-----------------------------------------+--------------------+
"""

import wx

from sirens.audio.analyzer import SCOPE_VIEW
from sirens.audio.blocks import CATALOG
from sirens.ui import theme
from sirens.ui.piano import PianoView
from sirens.ui.sidebar import Sidebar, divider
from sirens.ui.stack_editor import StackEditor
from sirens.ui.views import ScopeView, SpectrumView
from sirens.ui.widgets import StatusPill


class SoundPage(wx.Panel):
    def __init__(self, parent, engine, song, keys, on_track_change):
        """on_track_change(track): zavolá se, když uživatel vybere jinou stopu."""
        super().__init__(parent)
        self.SetBackgroundColour(theme.BACKGROUND)
        self.song = song
        self.keys = keys
        self.on_track_change = on_track_change
        self.track = song.tracks[0]

        self.scope = ScopeView(self)
        self.spectrum = SpectrumView(self)
        self.status = StatusPill(self)
        self.piano = PianoView(self, keys)
        column = wx.BoxSizer(wx.VERTICAL)
        column.Add(self.scope, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 20)
        column.Add(self.spectrum, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 20)
        column.Add(self.status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 20)
        column.Add(self.piano, 0, wx.EXPAND | wx.ALL, 20)

        self.sidebar = Sidebar(self, with_fixed=True)
        self.sidebar.add_group("Output", fixed=True)
        self.sidebar.add_slider("Master", 0, 1, 0.5, on_change=engine.set_volume, fixed=True,
                                help="Overall loudness of all tracks. After it the sound is clipped "
                                     "to -1..1, so nothing can blast the speakers.")
        self.sidebar.add_choice("Keys", ("Play", "Hold"), 0, lambda i: keys.set_hold(i == 1), fixed=True,
                                help="Hold: a key keeps sounding until you press it again, so you can "
                                     "move the sliders and hear the change. Envelope Sustain must be above 0.")
        self.editor = StackEditor(self.sidebar, "Add block", CATALOG, self.refresh)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(column, 1, wx.EXPAND)
        row.Add(divider(self, vertical=True), 0, wx.EXPAND)
        row.Add(self.sidebar, 0, wx.EXPAND)
        self.SetSizer(row)
        self.refresh()

    def select_track(self, track):
        self.track = track
        self.refresh()

    def _choose_track(self, index: int):
        # Seznam stop je v panelu, který se teď překreslí: až po skončení události.
        wx.CallAfter(self.on_track_change, self.song.tracks[index])

    def _rename(self, text: str):
        self.track.name = text or self.track.name

    def refresh(self):
        """Překreslí pravý panel podle vybrané stopy."""
        if self.track not in self.song.tracks:
            self.track = self.song.tracks[0]
        sidebar = self.sidebar
        sidebar.clear()
        sidebar.add_group("Track")
        names = [track.name for track in self.song.tracks]
        sidebar.add_dropdown("Edit", names, self.song.tracks.index(self.track), self._choose_track,
                           help="Each track is its own instrument. Add tracks on the Song tab.")
        sidebar.add_text("Name", self.track.name, self._rename)
        sidebar.add_group("Envelope")
        sidebar.add_params(self.track.instrument)
        self.editor.show(self.track.instrument.rack,
                         "No sound yet. Add a source (Oscillator, Supersaw, FM, ...), "
                         "then play with the keys A S D F G H J. Effects go below the source.")
        sidebar.finish()
        self.status.show(f"{self.track.name}: " + (self.track.instrument.rack.describe() or "empty"))

    def tick(self, analyzer, fresh: bool):
        """Každý snímek: klaviatura; grafy jen když je hotový nový úsek zvuku."""
        self.piano.Refresh(False)
        if fresh:
            duration_ms = SCOPE_VIEW / analyzer.sample_rate * 1000
            self.scope.show(analyzer.scope(), duration_ms, analyzer.peak_level_db())
            self.spectrum.show(analyzer.freqs, analyzer.spectrum, analyzer.peak_frequency())
