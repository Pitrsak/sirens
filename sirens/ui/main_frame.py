"""Hlavní okno, tady se to celý skládá dohromady: nahoře hlavička se záložkami,
pod ní obsah tý záložky, která je zrovna vybraná.

    +---------------------------------------------------------------------------------+
    | SIRENS  [Sound] [Song] [Visual]                      [Open] [Save]  [Play]      |
    +---------------------------------------------------------------------------------+
    |  obsah záložky (SoundPage, SongPage nebo VisualPage)                            |
    +---------------------------------------------------------------------------------+

Okno drží píseň (Song), přehrávač (Player) a hraní na klávesnici (KeyboardPlayer),
a hlídá, aby všechny záložky měly vybranou stejnou stopu (jinak by Sound ukazoval
jinou stopu než Song, blbost).

Srdce je časovač, tiká 30x za sekundu a pokaždý předá záložkám nový úsek zvuku.
Každý 2 s navíc uloží stav do autosave (viz session.py), aby se po pádu nic neztratilo,
a zahodí starý zvuky, který už doprolínaly (viz Instrument.tidy).
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
from sirens.ui.sidebar import divider
from sirens.ui.song_page import SongPage
from sirens.ui.sound_page import SoundPage
from sirens.ui.visual_page import VisualPage
from sirens.ui.widgets import Caption, PillButton

FPS = 30                     # kolikrát za sekundu tikne časovač (snímky za sekundu)
AUTOSAVE_EVERY = 2 * FPS     # po kolika snímcích autosave (= 2 s)
SAVE_FOLDER = Path(__file__).resolve().parents[2] / "assets"   # výchozí složka pro Save/Open (parents[2] = ui -> sirens -> kořen projektu)
FILE_TYPES = "Sirens files (*.json)|*.json"   # filtr do dialogu, formát "popisek|maska", ukáže jen .json


# wx.Frame = okno s titulkem a křížkem, celá appka má jedno hlavní
class MainFrame(wx.Frame):
    def __init__(self, engine):
        super().__init__(None, title="Sirens", size=(1280, 820))   # None = žádnej rodič, je to hlavní okno
        self.SetMinSize((1000, 680))     # menší ne, jinak se panel se slidery nevejde
        self.engine = engine
        self.song = Song()
        self.song.add_track()            # prázdná píseň s jednou stopou, ať je na co hrát
        self.player = Player(engine, self.song)
        self.keys = KeyboardPlayer(engine)
        self.keys.on_space = self._toggle_playing   # mezerník = Play / Stop
        self.engine.play(self.song.outputs())       # výstupy všech stop pustit do enginu (mix)
        self.ticks = 0                   # počítadlo snímků od startu
        self.last_time = time.monotonic()   # kdy byl minulej tik (monotonic = hodiny, který nikdy nejdou pozpátku)
        self.last_saved = ""     # text posledního autosave, ať nezapisujeme pořád dokola to samý

        # NASTAVENÍ GUI
        # Do Frame se nekreslí napřímo, dá se do něj jeden Panel a všechno ostatní je v něm
        # (Panel umí pozadí a přeskakování tabulátorem, holej Frame ne).
        root = wx.Panel(self)
        root.SetBackgroundColour(theme.BACKGROUND)
        # vyrobí se rovnou všechny tři záložky, vidět bude jen jedna (viz _select_tab)
        self.sound_page = SoundPage(root, engine, self.song, self.keys, self.select_track)
        self.song_page = SongPage(root, engine, self.song, self.player, self.select_track, self._tracks_changed)
        self.visual_page = VisualPage(root)
        self.pages = {"Sound": self.sound_page, "Song": self.song_page,
                      "Visual": self.visual_page}

        # Sizer = neviditelnej skládač, sám spočítá, kam co dát a jak velký.
        # BoxSizer(VERTICAL) skládá pod sebe. Add(prvek, proportion, flagy):
        # proportion 0 = jen tolik místa, kolik prvek chce, 1 = vezme zbytek,
        # wx.EXPAND = roztáhne se do celý šířky.
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(self._build_header(root), 0, wx.EXPAND)
        layout.Add(divider(root), 0, wx.EXPAND)
        for page in self.pages.values():
            layout.Add(page, 1, wx.EXPAND)   # schovaný stránky sizer přeskočí, místo dostane ta vidět
        root.SetSizer(layout)
        self._load_autosave()            # když je autosave z minula, načte se
        self._select_tab("Sound")        # startuje se na Sound

        # ČASOVAČ = hlavní smyčka appky
        # wx.Timer pošle oknu každých 1000/30 = 33 ms událost EVT_TIMER.
        # Bind = "až přijde tahle událost, zavolej tuhle funkci", tady tik -> _on_tick.
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_tick, self.timer)
        self.timer.Start(int(1000 / FPS))
        self.Bind(wx.EVT_ACTIVATE, self._on_activate)   # okno dostalo / ztratilo fokus
        self.Bind(wx.EVT_CLOSE, self._on_close)         # zavírání okna, ať se stihne uklidit

    def _build_header(self, parent):
        header = wx.Panel(parent)
        header.SetBackgroundColour(theme.BACKGROUND)
        header.SetMinSize((-1, 56))      # -1 = šířka je jedno, výška aspoň 56 px
        logo = Caption(header, "Sirens", colour=theme.TEXT, size=13, spacing=4)
        logo.SetMinSize((100, 24))

        # řádek vedle sebe (HORIZONTAL); wx.LEFT, 24 = mezera 24 px zleva, ALIGN_CENTER_VERTICAL = na střed výšky
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(logo, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 24)
        row.AddSpacer(24)
        self.tabs = {}
        for name in ("Sound", "Song", "Visual"):
            # n=name: lambda si musí zapamatovat tuhle záložku, ne poslední z cyklu
            # (bez toho by všechny tlačítka přepínaly na Visual)
            self.tabs[name] = PillButton(header, name, lambda n=name: self._select_tab(n))
            row.Add(self.tabs[name], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        row.AddStretchSpacer()           # pružina, odtlačí Open / Save / Play úplně doprava
        row.Add(PillButton(header, "Open", self._open), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        row.Add(PillButton(header, "Save", self._save), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 20)
        self.play_button = PillButton(header, "Play", self._toggle_playing, primary=True)
        row.Add(self.play_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 20)
        header.SetSizer(row)
        return header

    def _select_tab(self, name: str):
        """Ukáže vybranou záložku a ostatní schová, vybraná má bílý tlačítko."""
        for tab_name, page in self.pages.items():
            page.Show(tab_name == name)
            self.tabs[tab_name].set_primary(tab_name == name)
        # page je tu poslední z cyklu, ale rodiče maj všechny stejnýho (root), takže je to jedno.
        # Layout() = ať sizer znova rozpočítá místo, jinak by se nová záložka neroztáhla.
        page.GetParent().Layout()

    # --- stopy ---

    def select_track(self, track):
        """Vybere stopu ve všech záložkách naráz, klávesnice pak hraje na její nástroj."""
        self.keys.set_channel(track.instrument.channel)
        self.sound_page.select_track(track)
        self.song_page.select_track(track)

    def _tracks_changed(self, track):
        """Po přidání nebo smazání stopy: novej mix výstupů a vybrat danou stopu."""
        self.engine.play(self.song.outputs())
        self.select_track(track)

    # --- přehrávání ---

    def _toggle_playing(self):
        self.player.toggle()
        self._show_playing()

    def _show_playing(self):
        self.play_button.set_label("Stop" if self.player.playing else "Play")
        self.play_button.GetParent().Layout()   # Stop je jinak širokej než Play, tak ať se hlavička přeskládá

    # --- ukládání ---

    def _capture(self) -> dict:
        # celej stav (píseň a obraz) jako slovník, ten jde pak do JSONu
        return session.capture(self.song, self.visual_page.painter)

    def _apply(self, data: dict):
        """Nastaví všechno podle načtenejch dat a překreslí panely."""
        self.player.stop()
        session.restore(data, self.song, self.visual_page.painter)
        self.player.set_tempo(self.song.tempo)
        self.engine.play(self.song.outputs())   # stopy jsou nový objekty, takže znova do mixu
        self.visual_page.refresh()
        self.select_track(self.song.tracks[0])
        self._show_playing()

    def _load_autosave(self):
        if not session.AUTOSAVE.exists():
            return
        try:
            self._apply(session.read(session.AUTOSAVE))
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            self._apply({})     # poškozenej soubor: začneme prostě s prázdnou písní

    def _autosave(self, data: dict):
        text = json.dumps(data)
        if text != self.last_saved:      # nic se nezměnilo = nic nezapisovat
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
                # blbej soubor: hláška místo pádu celý appky
                wx.MessageBox(f"Cannot open this file:\n{error}", "Open", wx.ICON_ERROR, self)

    # --- smyčka ---

    def _on_tick(self, event):
        # tohle volá časovač 30x za sekundu
        now = time.monotonic()
        dt, self.last_time = now - self.last_time, now   # kolik reálně uběhlo od minula (timer není přesnej)
        self.ticks += 1
        if self.ticks % AUTOSAVE_EVERY == 0:
            self._autosave(self._capture())
            # úklid: starý zvuky po přestavbě racku, který už doprolínaly, zahodit, ať se nepočítaj
            self.engine.tidy()
            self.song.tidy()
        analyzer = self.engine.analyzer
        fresh = analyzer.update()        # fresh = je hotovej novej úsek zvuku?
        # kreslí se jen záložka, která je vidět, ať se zbytečně nepálí procesor
        if self.sound_page.IsShown():
            self.sound_page.tick(analyzer, fresh)
        if self.song_page.IsShown():
            self.song_page.tick()
        if self.visual_page.IsShown() or self.visual_page.fullscreen is not None:   # fullscreen jede i z jiný záložky
            self.visual_page.tick(analyzer, dt)

    def _on_activate(self, event):
        # okno ztratilo fokus (třeba Cmd+Tab jinam): puštění klávesy by sem už nedošlo,
        # tak ať noty nevisí, řekneme to klávesnici
        if not event.GetActive():
            self.keys.focus_lost()
        event.Skip()                     # Skip = ať to zpracuje i wx sám, my jsme jen poslouchali

    def _on_close(self, event):
        # úklid před zavřením, pořadí je důležitý: nejdřív zastavit tikání, uložit, pak vypínat zvuk
        self.timer.Stop()
        self._autosave(self._capture())
        self.player.close()
        self.keys.close()
        if self.visual_page.fullscreen is not None:
            self.visual_page.fullscreen.Destroy()
        self.engine.close()
        event.Skip()                     # až teď nechat okno opravdu zavřít (bez Skip by zůstalo otevřený)
