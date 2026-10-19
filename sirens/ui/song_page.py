"""Záložka Song: patterny s notami, časová osa písně a automatizace.

    +-----------------------------------------+--------------------+
    |  PATTERN  editor not vybrané stopy      | PLAYBACK           |
    |  (piano roll)                           |   Loop / Song      |
    |                                         |   Tempo            |
    |-----------------------------------------| TRACK              |
    |  TIMELINE  stopy x takty                |   Pattern A..H     |
    |  automatizace                           | AUTOMATION         |
    +-----------------------------------------+--------------------+
"""

import wx

from sirens.song import MAX_BARS, MAX_TRACKS, MIN_BARS, PATTERN_NAMES, STEPS_PER_BAR, Pattern
from sirens.ui import theme
from sirens.ui.pattern_view import PatternView
from sirens.ui.sidebar import Sidebar, divider
from sirens.ui.timeline_view import TimelineView

BAR_CHOICES = (1, 2, 4)


class SongPage(wx.Panel):
    def __init__(self, parent, engine, song, player, on_track_change, on_tracks_changed):
        """on_track_change(track): výběr stopy. on_tracks_changed(track): stopa přidána / smazána."""
        super().__init__(parent)
        self.SetBackgroundColour(theme.BACKGROUND)
        self.engine, self.song, self.player = engine, song, player
        self.on_track_change, self.on_tracks_changed = on_track_change, on_tracks_changed
        self.track = song.tracks[0]
        self.lane = None                  # (vlastník, Param) automatizace v časové ose

        self.pattern_view = PatternView(self, player, self._preview)
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
        if track is not self.track:
            self.lane = None
        self.track = track
        self.pattern_view.track = track
        self.timeline.selected = track
        self.refresh()

    def _select_from_timeline(self, track):
        self.on_track_change(track)

    # --- pravý panel ---

    def refresh(self):
        if self.track not in self.song.tracks:
            self.track = self.song.tracks[0]
            self.pattern_view.track = self.timeline.selected = self.track
        s = self.sidebar
        s.clear()
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
        self.duration = s.add_note("")
        self._show_duration()

        mute = "Unmute" if self.track.muted else "Mute"
        s.add_group(self.track.name, actions=[(mute, self._toggle_mute), ("Remove", self._remove_track)])
        s.add_choice("Pattern", tuple(PATTERN_NAMES), PATTERN_NAMES.index(self.track.current), self._set_pattern,
                     help="Click in the grid to add a note, drag to make it longer, click a note to delete it. "
                          "Mouse wheel scrolls the pitch.")
        pattern = self.track.patterns[self.track.current]
        s.add_choice("Length", tuple(f"{b} bar" for b in BAR_CHOICES), BAR_CHOICES.index(pattern.bars),
                     self._set_length)
        s.add_button("Clear pattern", self._clear_pattern)
        if len(self.song.tracks) < MAX_TRACKS:
            s.add_button("Add track", self._add_track)

        s.add_group("Automation")
        self.lane_options = [(owner, p) for owner in self.track.automated_owners()
                             for p in owner.PARAMS if not p.choices]
        names = ["None"] + [f"{self._owner_name(owner)}: {p.label}" for owner, p in self.lane_options]
        index = 0
        if self.lane in self.lane_options:
            index = self.lane_options.index(self.lane) + 1
        s.add_dropdown("Slider", names, index, self._set_lane,
                       help="Draw how it changes over the song in the bottom row of the timeline "
                            "(click or drag; right-click removes a point). Plays in Song mode.")
        s.add_note("Click the bar numbers above the timeline to choose where Song mode starts.")
        s.finish()
        self.timeline.fit()
        self.Layout()
        self.pattern_view.Refresh()
        self.timeline.Refresh()

    def _owner_name(self, owner) -> str:
        if owner is self.track.instrument:
            return "Envelope"
        blocks = self.track.instrument.rack.blocks
        same = [b for b in blocks if b.NAME == owner.NAME]
        return owner.NAME if len(same) == 1 else f"{owner.NAME} {same.index(owner) + 1}"

    # --- akce (změny, které překreslí panel, až po skončení kliknutí: wx.CallAfter) ---

    def _set_tempo(self, bpm):
        self.player.set_tempo(bpm)
        self._show_duration()

    def _set_bars(self, bars):
        self.song.bars = int(bars)
        self.player.start_bar = min(self.player.start_bar, self.song.bars - 1)
        self._show_duration()
        self.timeline.Refresh()

    def _show_duration(self):
        """Délka písně v minutách: takt = 16 kroků po 60 / tempo / 4 sekundách."""
        seconds = round(self.song.bars * STEPS_PER_BAR * 60 / self.song.tempo / 4)
        self.duration.SetLabel(f"{self.song.bars} bars at {self.song.tempo:.0f} bpm = "
                               f"{seconds // 60}:{seconds % 60:02d} min")

    def _set_mode(self, index):
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

    def _clear_pattern(self):
        self.track.patterns[self.track.current] = Pattern(self.track.patterns[self.track.current].bars)
        self.pattern_view.Refresh()

    def _toggle_mute(self):
        self.track.muted = not self.track.muted
        wx.CallAfter(self.refresh)

    def _add_track(self):
        track = self.song.add_track()
        if track is not None:
            wx.CallAfter(self.on_tracks_changed, track)

    def _remove_track(self):
        if len(self.song.tracks) == 1:
            wx.MessageBox("The song needs at least one track.", "Remove track")
            return
        answer = wx.MessageBox(f"Remove {self.track.name} with its instrument and patterns?", "Remove track",
                               wx.YES_NO | wx.NO_DEFAULT)
        if answer == wx.YES:
            self.song.remove_track(self.track)
            wx.CallAfter(self.on_tracks_changed, self.song.tracks[0])

    def _set_lane(self, index):
        self.lane = self.lane_options[index - 1] if index > 0 else None
        self.timeline.Refresh()

    def _preview(self, pitch: int):
        """Krátce zahraje notu vybrané stopy (při přidání do patternu)."""
        channel = self.track.instrument.channel
        self.engine.send_note(channel, pitch, 100)
        wx.CallLater(200, self.engine.send_note, channel, pitch, 0)

    def tick(self):
        if self.player.playing:
            self.pattern_view.Refresh(False)
            self.timeline.Refresh(False)
