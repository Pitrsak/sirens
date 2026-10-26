"""Záložka Song: patterny s notami, časová osa písně a automatizace.

    +-----------------------------------------+--------------------+
    |  PATTERN  editor not vybraný stopy      | PLAYBACK           |
    |  (piano roll)                           |   Loop / Song      |
    |                                         |   Tempo            |
    |                                         |   Export WAV       |
    |-----------------------------------------| TRACK              |
    |  TIMELINE  stopy x takty                |   Pattern A..H     |
    |  automatizace                           | AUTOMATION         |
    +-----------------------------------------+--------------------+

Samotný klikání do not a taktů řeší PatternView a TimelineView, tahle stránka
je jen poskládá a vpravo dá panel s nastavením (tempo, délka, mřížka, stopy...).
"""

import wx

from sirens import session
from sirens.audio.export import TAIL
from sirens.song import BEATS_PER_BAR, GRIDS, MAX_BARS, MAX_TRACKS, MIN_BARS, PATTERN_NAMES, Pattern
from sirens.ui import theme
from sirens.ui.pattern_view import PatternView
from sirens.ui.sidebar import Sidebar, divider
from sirens.ui.timeline_view import TimelineView
from sirens.ui.widgets import confirm

BAR_CHOICES = (1, 2, 4)      # jak dlouhej může bejt pattern, v taktech
GRID_NAMES = ("16ths", "8th triplets", "16th triplets")    # popisky k GRIDS (16, 12, 24)


class SongPage(wx.Panel):
    def __init__(self, parent, engine, song, player, on_track_change, on_tracks_changed, on_export):
        """on_track_change(track): výběr stopy. on_tracks_changed(track): stopa přidaná / smazaná.
        on_export(): tlačítko Export WAV (export řídí hlavní okno)."""
        super().__init__(parent)
        self.SetBackgroundColour(theme.BACKGROUND)
        self.engine, self.song, self.player = engine, song, player
        self.on_track_change, self.on_tracks_changed = on_track_change, on_tracks_changed
        self.on_export = on_export
        # text pod tlačítkem Export WAV: nápověda, během exportu průběh, pak výsledek
        self.export_text = ("Export WAV records the song from bar 1 to the end of the last used bar, "
                            f"plus {TAIL:.0f} s to ring out. It plays in real time.")
        self.track = song.tracks[0]
        self.lane = None                  # (vlastník, Param) automatizace v časový ose, None = žádná

        self.pattern_view = PatternView(self, player, self._preview)
        # lambda: self.lane = funkce, která pokaždý vrátí AKTUÁLNÍ self.lane,
        # timeline si to tak zjistí sama, kdykoli kreslí, a nemusím jí to pořád posílat
        self.timeline = TimelineView(self, song, player, self._select_from_timeline, lambda: self.lane)
        column = wx.BoxSizer(wx.VERTICAL)
        column.Add(self.pattern_view, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 20)
        column.Add(self.timeline, 0, wx.EXPAND | wx.ALL, 20)     # výška podle počtu stop

        self.sidebar = Sidebar(self)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(column, 1, wx.EXPAND)
        row.Add(divider(self, vertical=True), 0, wx.EXPAND)
        row.Add(self.sidebar, 0, wx.EXPAND)
        self.SetSizer(row)
        self.select_track(self.track)

    # --- výběr stopy ---

    def select_track(self, track):
        # jiná stopa = automatizace tý minulý tu nemá co dělat, takže pryč
        if track is not self.track:
            self.lane = None
        self.track = track
        self.pattern_view.track = track
        self.timeline.selected = track
        self.refresh()

    def _select_from_timeline(self, track):
        # klik na jméno v timeline -> hlavní okno -> vybere stopu všude (i v Sound a klávesnici)
        self.on_track_change(track)

    # --- pravej panel ---

    def refresh(self):
        # celej pravej panel smazat a postavit znova podle vybraný stopy
        if self.track not in self.song.tracks:
            self.track = self.song.tracks[0]
            self.pattern_view.track = self.timeline.selected = self.track
        s = self.sidebar
        s.clear()
        # Playback: Loop / Song, tempo, délka písně, export
        s.add_group("Playback")
        s.add_choice("Mode", ("Loop", "Song"), 0 if self.player.mode == "Loop" else 1, self._set_mode,
                     help="Loop repeats the pattern each track is editing. Song plays the timeline. "
                          "Space starts and stops.")
        s.add_slider("Tempo", 40, 200, self.song.tempo, "bpm", step=1, on_change=self._set_tempo,
                     value=self.song.tempo)
        s.add_slider("Song length", MIN_BARS, MAX_BARS, 32, "bars", step=4, on_change=self._set_bars,
                     value=self.song.bars,
                     help="How many bars the timeline has. If they don't fit, the mouse wheel "
                          "over the timeline scrolls in time.")
        self.duration = s.add_note("")      # text s délkou v minutách, vyplní _show_duration
        self._show_duration()
        s.add_button("Export WAV", self.on_export)
        self.export_note = s.add_note(self.export_text)

        # skupina se jménem stopy: Mute / Duplicate / Remove, pattern, délka, mřížka
        mute = "Unmute" if self.track.muted else "Mute"
        s.add_group(self.track.name, actions=[(mute, self._toggle_mute), ("Duplicate", self._duplicate_track),
                                              ("Remove", self._remove_track)])
        s.add_choice("Pattern", tuple(PATTERN_NAMES), PATTERN_NAMES.index(self.track.current), self._set_pattern,
                     help="Click in the grid to add a note, drag to make it longer, click a note to delete it. "
                          "Mouse wheel scrolls the pitch. Drag in the Vel strip below the grid to make notes "
                          "louder (higher bar) or softer.")
        pattern = self.track.patterns[self.track.current]
        s.add_choice("Length", tuple(f"{b} bar" for b in BAR_CHOICES), BAR_CHOICES.index(pattern.bars),
                     self._set_length)
        s.add_choice("Grid", GRID_NAMES, GRIDS.index(pattern.grid), self._set_grid,
                     help="How finely each beat is split. 16ths: 4 equal parts. Triplets split each "
                          "beat into 3 (or 6) equal parts instead of 4: the rolling, swung feel. "
                          "Changing it moves existing notes to the nearest new column.")
        s.add_button("Clear pattern", self._clear_pattern)
        if len(self.song.tracks) < MAX_TRACKS:
            s.add_button("Add track", self._add_track)

        # Automation: dropdown se všema sliderama nástroje a bloků (bez přepínačů, ty automatizovat nejde)
        s.add_group("Automation")
        # dvojitej for v jednom řádku: pro každýho vlastníka (obálka, bloky) každej jeho slider
        self.lane_options = [(owner, p) for owner in self.track.automated_owners()
                             for p in owner.PARAMS if not p.choices]
        names = ["None"] + [f"{self._owner_name(owner)}: {p.label}" for owner, p in self.lane_options]
        # v dropdownu je navíc "None" na začátku, proto + 1
        index = 0
        if self.lane in self.lane_options:
            index = self.lane_options.index(self.lane) + 1
        s.add_dropdown("Slider", names, index, self._set_lane,
                       help="Draw how it changes over the song in the bottom row of the timeline "
                            "(click or drag; right-click removes a point). Plays in Song mode.")
        s.add_note("Click the bar numbers above the timeline to choose where Song mode starts.")
        s.finish()
        self.timeline.fit()            # počet stop se mohl změnit, takže jiná výška
        self.Layout()
        self.pattern_view.Refresh()
        self.timeline.Refresh()

    def _owner_name(self, owner) -> str:
        # jméno do dropdownu: obálka = "Envelope", blok = jeho jméno,
        # a když jsou dva stejný (dva Oscillatory), tak s číslem "Oscillator 2"
        if owner is self.track.instrument:
            return "Envelope"
        blocks = self.track.instrument.rack.blocks
        same = [b for b in blocks if b.NAME == owner.NAME]
        return owner.NAME if len(same) == 1 else f"{owner.NAME} {same.index(owner) + 1}"

    # --- akce (změny, který překreslí panel, až po skončení kliknutí: wx.CallAfter) ---
    # (tlačítko, na který se kliklo, je v panelu, kterej by se jinak smazal uprostřed svý vlastní události)

    def _set_tempo(self, bpm):
        self.player.set_tempo(bpm)
        self._show_duration()

    def _set_bars(self, bars):
        self.song.bars = int(bars)
        # začátek přehrávání nesmí zůstat za koncem zkrácený písně
        self.player.start_bar = min(self.player.start_bar, self.song.bars - 1)
        self._show_duration()
        self.timeline.Refresh()

    def _show_duration(self):
        """Délka písně v minutách: takt = 4 doby po 60 / tempo sekundách.

        Tempo je v bpm = doby za minutu, takže jedna doba trvá 60 / tempo sekund.
        Pak sekundy // 60 = celý minuty, % 60 = zbylý sekundy (:02d = vždycky dvě číslice, 2:05).
        """
        seconds = round(self.song.bars * BEATS_PER_BAR * 60 / self.song.tempo)
        self.duration.SetLabel(f"{self.song.bars} bars at {self.song.tempo:.0f} bpm = "
                               f"{seconds // 60}:{seconds % 60:02d} min")

    def show_export(self, text: str):
        """Novej text pod tlačítkem Export WAV (při exportu se mění jednou za sekundu)."""
        if text != self.export_text:
            self.export_text = text
            self.sidebar.set_note(self.export_note, text)

    def _set_mode(self, index):
        if self.player.once:             # export nahrává v režimu Song, ten se měnit nesmí
            wx.CallAfter(self.refresh)   # v panelu zase ukázat Song
            return
        # přepnutí za běhu: zastavit, přepnout, a když hrálo, zase pustit
        was_playing = self.player.playing
        self.player.stop()
        self.player.mode = ("Loop", "Song")[index]
        if was_playing:
            self.player.play()

    def _set_pattern(self, index):
        self.track.current = PATTERN_NAMES[index]
        wx.CallAfter(self.refresh)

    def _set_length(self, index):
        pattern = self.track.patterns[self.track.current]
        pattern.bars = BAR_CHOICES[index]
        pattern.notes = [n for n in pattern.notes if n.step < pattern.steps()]   # noty za koncem pryč
        self.pattern_view.Refresh()

    def _set_grid(self, index):
        """Jiná mřížka: noty se přepočítaj na nejbližší nový kroky (viz Pattern.set_grid)."""
        self.track.patterns[self.track.current].set_grid(GRIDS[index])
        self.pattern_view.Refresh()

    def _clear_pattern(self):
        # novej prázdnej pattern se stejnou délkou a mřížkou místo starýho
        old = self.track.patterns[self.track.current]
        self.track.patterns[self.track.current] = Pattern(old.bars, old.grid)
        self.pattern_view.Refresh()

    def _toggle_mute(self):
        self.track.muted = not self.track.muted
        wx.CallAfter(self.refresh)

    def _add_track(self):
        # add_track vrátí None, když už je stop maximum
        track = self.song.add_track()
        if track is not None:
            wx.CallAfter(self.on_tracks_changed, track)

    def _duplicate_track(self):
        """Kopie stopy (zvuk i patterny); na časový ose se umístí ručně."""
        copy = session.duplicate(self.song, self.track)
        if copy is None:
            wx.MessageBox(f"The song can have at most {MAX_TRACKS} tracks.", "Duplicate track")
            return
        wx.CallAfter(self.on_tracks_changed, copy)

    def _remove_track(self):
        # poslední stopu smazat nejde, píseň musí mít aspoň jednu
        if len(self.song.tracks) == 1:
            wx.MessageBox("The song needs at least one track.", "Remove track")
            return
        if confirm(self, f"Remove {self.track.name} with its instrument and patterns?", "Remove track", "Remove"):
            self.song.remove_track(self.track)
            wx.CallAfter(self.on_tracks_changed, self.song.tracks[0])

    def _set_lane(self, index):
        # index 0 je "None", ostatní jsou o jedna posunutý oproti lane_options
        self.lane = self.lane_options[index - 1] if index > 0 else None
        self.timeline.Refresh()

    def _preview(self, pitch: int):
        """Krátce zahraje notu vybraný stopy (při přidání do patternu).

        Note on hned, note off (velocity 0) za 200 ms přes wx.CallLater,
        ten zavolá funkci za daný počet ms a mezitím nic neblokuje.
        """
        channel = self.track.instrument.channel
        self.engine.send_note(channel, pitch, 100)
        wx.CallLater(200, self.engine.send_note, channel, pitch, 0)

    def tick(self):
        # každej snímek: když něco hraje, překreslit, ať se hejbe ukazatel
        if self.player.playing:
            self.pattern_view.Refresh(False)
            self.timeline.Refresh(False)
