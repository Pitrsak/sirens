"""Hlavní okno: hlavička se záložkami a pod ní obsah vybrané záložky.

    +----------------------------------------------------------------------+
    | SIRENS  [Sound] [Song] [Visual] [Light]        [Open] [Save]  [Play] |
    +----------------------------------------------------------------------+
    |  obsah záložky (SoundPage, SongPage, VisualPage nebo LightPage)      |
    +----------------------------------------------------------------------+

Okno drží píseň (Song), přehrávač (Player) a hraní na klávesnici (KeyboardPlayer)
a stará se o to, aby všechny záložky měly vybranou stejnou stopu.
Časovač běží 30x za sekundu: předá nový úsek zvuku záložkám a každé 2 s
uloží stav do autosave (viz session.py).
"""

import json
import time
from pathlib import Path

import wx

from sirens import session
from sirens.audio.player import Player
from sirens.song import Song
from sirens.ui import theme
from sirens.ui.keys import KeyboardPlayer
from sirens.ui.light_page import LightPage
from sirens.ui.sidebar import divider
from sirens.ui.song_page import SongPage
from sirens.ui.sound_page import SoundPage
from sirens.ui.visual_page import VisualPage
from sirens.ui.widgets import Caption, PillButton

FPS = 30
AUTOSAVE_EVERY = 2 * FPS     # po kolika snímcích uložit autosave (= 2 s)
SAVE_FOLDER = Path(__file__).resolve().parents[2] / "assets"   # výchozí složka pro Save/Open
FILE_TYPES = "Sirens files (*.json)|*.json"


class MainFrame(wx.Frame):
    def __init__(self, engine):
        super().__init__(None, title="Sirens", size=(1280, 820))
        self.SetMinSize((1000, 680))
        self.engine = engine
        self.song = Song()
        self.song.add_track()
        self.player = Player(engine, self.song)
        self.keys = KeyboardPlayer(engine)
        self.keys.on_space = self._toggle_playing
        self.engine.play(self.song.outputs())
        self.ticks = 0
        self.last_time = time.monotonic()
        self.last_saved = ""     # text posledního autosave, ať nezapisujeme pořád to samé

        root = wx.Panel(self)
        root.SetBackgroundColour(theme.BACKGROUND)
        self.sound_page = SoundPage(root, engine, self.song, self.keys, self.select_track)
        self.song_page = SongPage(root, engine, self.song, self.player, self.select_track, self._tracks_changed)
        self.visual_page = VisualPage(root)
        self.light_page = LightPage(root)
        self.pages = {"Sound": self.sound_page, "Song": self.song_page,
                      "Visual": self.visual_page, "Light": self.light_page}

        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(self._build_header(root), 0, wx.EXPAND)
        layout.Add(divider(root), 0, wx.EXPAND)
        for page in self.pages.values():
            layout.Add(page, 1, wx.EXPAND)
        root.SetSizer(layout)
        self._load_autosave()
        self._select_tab("Sound")

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_tick, self.timer)
        self.timer.Start(int(1000 / FPS))
        self.Bind(wx.EVT_ACTIVATE, self._on_activate)
        self.Bind(wx.EVT_CLOSE, self._on_close)

    def _build_header(self, parent):
        header = wx.Panel(parent)
        header.SetBackgroundColour(theme.BACKGROUND)
        header.SetMinSize((-1, 56))
        logo = Caption(header, "Sirens", colour=theme.TEXT, size=13, spacing=4)
        logo.SetMinSize((140, 24))

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(logo, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 24)
        self.tabs = {}
        for name in ("Sound", "Song", "Visual", "Light"):
            # n=name: lambda si musí zapamatovat tuhle záložku, ne poslední z cyklu
            self.tabs[name] = PillButton(header, name, lambda n=name: self._select_tab(n))
            row.Add(self.tabs[name], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        row.AddStretchSpacer()
        row.Add(PillButton(header, "Open", self._open), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        row.Add(PillButton(header, "Save", self._save), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 20)
        self.play_button = PillButton(header, "Play", self._toggle_playing, primary=True)
        row.Add(self.play_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 20)
        header.SetSizer(row)
        return header

    def _select_tab(self, name: str):
        """Ukáže vybranou záložku, ostatní skryje. Vybraná má bílé tlačítko."""
        for tab_name, page in self.pages.items():
            page.Show(tab_name == name)
            self.tabs[tab_name].set_primary(tab_name == name)
        page.GetParent().Layout()

    # --- stopy ---

    def select_track(self, track):
        """Vybere stopu ve všech záložkách; klávesnice pak hraje na její nástroj."""
        self.keys.set_channel(track.instrument.channel)
        self.sound_page.select_track(track)
        self.song_page.select_track(track)

    def _tracks_changed(self, track):
        """Po přidání nebo smazání stopy: nový mix výstupů a výběr dané stopy."""
        self.engine.play(self.song.outputs())
        self.select_track(track)

    # --- přehrávání ---

    def _toggle_playing(self):
        self.player.toggle()
        self.play_button.set_label("Stop" if self.player.playing else "Play")
        self.play_button.GetParent().Layout()

    # --- ukládání ---

    def _capture(self) -> dict:
        return session.capture(self.song, self.visual_page.painter, self.light_page.rig)

    def _apply(self, data: dict):
        """Nastaví vše podle načtených dat a překreslí panely."""
        self.player.stop()
        session.restore(data, self.song, self.visual_page.painter, self.light_page.rig)
        self.player.set_tempo(self.song.tempo)
        self.engine.play(self.song.outputs())
        self.visual_page.refresh()
        self.light_page.refresh()
        self.select_track(self.song.tracks[0])

    def _load_autosave(self):
        if not session.AUTOSAVE.exists():
            return
        try:
            self._apply(session.read(session.AUTOSAVE))
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            self._apply({})     # poškozený soubor: začneme s prázdnou písní

    def _autosave(self):
        data = self._capture()
        text = json.dumps(data)
        if text != self.last_saved:
            session.write(session.AUTOSAVE, data)
            self.last_saved = text

    def _save(self):
        with wx.FileDialog(self, "Save", str(SAVE_FOLDER), "my song.json", FILE_TYPES,
                           wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                session.write(Path(dialog.GetPath()), self._capture())

    def _open(self):
        with wx.FileDialog(self, "Open", str(SAVE_FOLDER), "", FILE_TYPES,
                           wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            try:
                self._apply(session.read(Path(dialog.GetPath())))
            except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
                wx.MessageBox(f"Cannot open this file:\n{error}", "Open", wx.ICON_ERROR, self)

    # --- smyčka ---

    def _on_tick(self, event):
        now = time.monotonic()
        dt, self.last_time = now - self.last_time, now
        self.ticks += 1
        if self.ticks % AUTOSAVE_EVERY == 0:
            self._autosave()
        analyzer = self.engine.analyzer
        fresh = analyzer.update()
        if self.sound_page.IsShown():
            self.sound_page.tick(analyzer, fresh)
        if self.song_page.IsShown():
            self.song_page.tick()
        if self.visual_page.IsShown() or self.visual_page.fullscreen is not None:
            self.visual_page.tick(analyzer, dt)
        self.light_page.tick(analyzer)

    def _on_activate(self, event):
        if not event.GetActive():
            self.keys.focus_lost()
        event.Skip()

    def _on_close(self, event):
        self.timer.Stop()
        self._autosave()
        self.player.close()
        self.keys.close()
        if self.visual_page.fullscreen is not None:
            self.visual_page.fullscreen.Destroy()
        self.light_page.close()
        self.engine.close()
        event.Skip()
