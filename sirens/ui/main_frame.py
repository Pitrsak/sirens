"""Hlavní okno, tady se to celý skládá dohromady: nahoře hlavička se záložkami,
pod ní obsah tý záložky, která je zrovna vybraná (Undo / Redo jsou šipky hned za logem).

    +---------------------------------------------------------------------------------+
    | SIRENS  [Undo] [Redo]  [Sound] [Song] [Visual] [Light]    [Open] [Save]  [Play] |
    +---------------------------------------------------------------------------------+
    |  obsah záložky (SoundPage, SongPage, VisualPage nebo LightPage)                 |
    +---------------------------------------------------------------------------------+

Okno drží píseň (Song), přehrávač (Player) a hraní na klávesnici (KeyboardPlayer),
a hlídá, aby všechny záložky měly vybranou stejnou stopu (jinak by Sound ukazoval
jinou stopu než Song, blbost).

Srdce je časovač, tiká 30x za sekundu a pokaždý předá záložkám nový úsek zvuku.
Každou 1/3 s navíc zachytí stav pro Undo / Redo (viz history.py) a každý 2 s ho
uloží do autosave (viz session.py). Undo a Redo jsou v menu Edit (Cmd+Z,
Cmd+Shift+Z, na Windows Ctrl+Z, Ctrl+Y) a taky jako šipky v hlavičce.

Export WAV (tlačítko je v záložce Song) řídí taky okno, přes Export (viz export.py).
Pozor na to, co se děje během exportu: tlačítko Play ukazuje Stop, Stop i mezerník
export zruší, a Undo, Redo a Open nejdou, aby se píseň uprostřed nahrávání nezměnila.
"""

import json
import time
from pathlib import Path

import wx

from sirens import session
from sirens.audio.export import Export
from sirens.audio.player import Player
from sirens.history import History, change_key
from sirens.song import Song
from sirens.ui import theme
from sirens.ui.keys import KeyboardPlayer
from sirens.ui.light_page import LightPage
from sirens.ui.sidebar import divider
from sirens.ui.song_page import SongPage
from sirens.ui.sound_page import SoundPage
from sirens.ui.visual_page import VisualPage
from sirens.ui.widgets import ArrowButton, Caption, PillButton

FPS = 30                     # kolikrát za sekundu tikne časovač (snímky za sekundu)
SNAPSHOT_EVERY = 10          # po kolika snímcích zachytit stav pro Undo (10 snímků = 1/3 s)
AUTOSAVE_EVERY = 2 * FPS     # po kolika snímcích autosave (= 2 s), musí to být násobek SNAPSHOT_EVERY, jinak by se to netrefilo
SAVE_FOLDER = Path(__file__).resolve().parents[2] / "assets"   # výchozí složka pro Save/Open (parents[2] = ui -> sirens -> kořen projektu)
FILE_TYPES = "Sirens files (*.json)|*.json"   # filtr do dialogu, formát "popisek|maska", ukáže jen .json
WAV_TYPES = "WAV files (*.wav)|*.wav"


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
        self.history = History()
        self.export = None       # běžící Export WAV, jinak None

        # NASTAVENÍ GUI
        # Do Frame se nekreslí napřímo, dá se do něj jeden Panel a všechno ostatní je v něm
        # (Panel umí pozadí a přeskakování tabulátorem, holej Frame ne).
        root = wx.Panel(self)
        root.SetBackgroundColour(theme.BACKGROUND)
        # vyrobí se rovnou všechny čtyři záložky, vidět bude jen jedna (viz _select_tab)
        self.sound_page = SoundPage(root, engine, self.song, self.keys, self.select_track)
        self.song_page = SongPage(root, engine, self.song, self.player, self.select_track, self._tracks_changed,
                                  self._export_wav)
        self.visual_page = VisualPage(root)
        self.light_page = LightPage(root)
        self.pages = {"Sound": self.sound_page, "Song": self.song_page,
                      "Visual": self.visual_page, "Light": self.light_page}

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
        self._build_menu()
        self._load_autosave()            # když je autosave z minula, načte se
        data = self._capture()
        self.history.record(json.dumps(data), change_key(data))   # výchozí stav, ke kterýmu se dá vrátit
        self._update_menu()
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
        key = "Cmd" if wx.Platform == "__WXMAC__" else "Ctrl"   # jen do bublinky s nápovědou
        self.undo_button = ArrowButton(header, False, self.undo, f"Undo ({key}+Z)")
        self.redo_button = ArrowButton(header, True, self.redo, f"Redo ({key}+Shift+Z)")

        # řádek vedle sebe (HORIZONTAL); wx.LEFT, 24 = mezera 24 px zleva, ALIGN_CENTER_VERTICAL = na střed výšky
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(logo, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 24)
        row.Add(self.undo_button, 0, wx.ALIGN_CENTER_VERTICAL)
        row.Add(self.redo_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 24)
        self.tabs = {}
        for name in ("Sound", "Song", "Visual", "Light"):
            # n=name: lambda si musí zapamatovat tuhle záložku, ne poslední z cyklu
            # (bez toho by všechny tlačítka přepínaly na Light)
            self.tabs[name] = PillButton(header, name, lambda n=name: self._select_tab(n))
            row.Add(self.tabs[name], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        row.AddStretchSpacer()           # pružina, odtlačí Open / Save / Play úplně doprava
        row.Add(PillButton(header, "Open", self._open), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        row.Add(PillButton(header, "Save", self._save), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 20)
        self.play_button = PillButton(header, "Play", self._toggle_playing, primary=True)
        row.Add(self.play_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 20)
        header.SetSizer(row)
        return header

    def _build_menu(self):
        """Menu Edit s Undo a Redo. "Ctrl" v zkratce si wx na macOS sám přeloží na Cmd.

        Text za tabulátorem v názvu položky je klávesová zkratka (accelerator),
        wx ji hlídá sám a při stisku pošle EVT_MENU, jako by se kliklo v menu.
        Pozor, Z je zároveň nota, ale filtr kláves (keys.py) stisky s Cmd/Ctrl
        propouští, takže dojdou až sem.
        """
        edit = wx.Menu()
        self.undo_item = edit.Append(wx.ID_ANY, "Undo\tCtrl+Z")   # ID_ANY = ať si wx vymyslí číslo samo
        self.redo_item = edit.Append(wx.ID_ANY, "Redo\tCtrl+Shift+Z")
        self.redo_item.AddExtraAccel(wx.AcceleratorEntry(wx.ACCEL_CTRL, ord("Y")))   # druhá zkratka Ctrl+Y, zvyk z Windows
        menu_bar = wx.MenuBar()
        menu_bar.Append(edit, "Edit")
        self.SetMenuBar(menu_bar)
        # lambda e: událost zahodí, undo() ji nepotřebuje; poslední argument = jen pro tuhle položku
        self.Bind(wx.EVT_MENU, lambda e: self.undo(), self.undo_item)
        self.Bind(wx.EVT_MENU, lambda e: self.redo(), self.redo_item)
        self._update_menu()

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
        if self.export is not None:
            self._cancel_export()        # Stop / mezerník během exportu = zrušit export
        else:
            self.player.toggle()
        self._show_playing()

    def _show_playing(self):
        busy = self.player.playing or self.export is not None
        self.play_button.set_label("Stop" if busy else "Play")
        self.play_button.GetParent().Layout()   # Stop je jinak širokej než Play, tak ať se hlavička přeskládá

    # --- export WAV ---

    def _export_wav(self):
        """Tlačítko Export WAV: zeptá se, kam to uložit, a spustí export."""
        if self.export is not None:
            return
        # je na časový ose aspoň jeden pattern před koncem písně? jinak není co nahrávat
        if not any(bar < self.song.bars for track in self.song.tracks for bar in track.arrangement):
            wx.MessageBox("The timeline is empty. Put some patterns on it first.", "Export WAV",
                          wx.ICON_INFORMATION, self)
            return
        # with = dialog se po zavření sám zničí; FD_OVERWRITE_PROMPT = zeptá se, když soubor už existuje
        with wx.FileDialog(self, "Export WAV", str(SAVE_FOLDER), "my song.wav", WAV_TYPES,
                           wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as dialog:
            # ShowModal čeká, dokud uživatel dialog nezavře, a vrátí ID_OK nebo ID_CANCEL
            if dialog.ShowModal() != wx.ID_OK:
                return
            path = Path(dialog.GetPath())
        self.start_export(path)

    def start_export(self, path: Path):
        """Spustí export do souboru (píseň se jednou přehraje a nahraje, viz export.py)."""
        self.keys.release_all()          # držený klávesy by se nahrály taky
        self.export = Export(self.engine, self.player, path)
        self._export_changed()

    def _export_tick(self):
        """Každej snímek: jak daleko je export, do poznámky v záložce Song."""
        finished = self.export.tick()
        self.song_page.show_export(self.export.status)
        if finished:
            self.export = None
            self._export_changed()

    def _cancel_export(self):
        self.export.cancel()
        self.song_page.show_export(self.export.status)
        self.export = None
        self._export_changed()

    def _export_changed(self):
        """Export začal nebo skončil: přepsat text, režim v panelu, tlačítko Play a menu."""
        if self.export is not None:
            self.song_page.show_export(self.export.status)
        self.song_page.refresh()
        self._show_playing()
        self._update_menu()

    # --- ukládání ---

    def _capture(self) -> dict:
        # celej stav (píseň, obraz, světlo) jako slovník, ten jde pak do JSONu
        return session.capture(self.song, self.visual_page.painter, self.light_page.rig)

    def _apply(self, data: dict):
        """Nastaví všechno podle načtenejch dat a překreslí panely."""
        self.player.stop()
        session.restore(data, self.song, self.visual_page.painter, self.light_page.rig)
        self.player.set_tempo(self.song.tempo)
        self.engine.play(self.song.outputs())   # stopy jsou nový objekty, takže znova do mixu
        self.visual_page.refresh()
        self.light_page.refresh()
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
        if self.export is not None:
            return                       # během exportu se píseň nemění
        with wx.FileDialog(self, "Open", str(SAVE_FOLDER), "", FILE_TYPES,
                           wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            try:
                self._apply(session.read(Path(dialog.GetPath())))
            except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
                # blbej soubor: hláška místo pádu celý appky
                wx.MessageBox(f"Cannot open this file:\n{error}", "Open", wx.ICON_ERROR, self)

    # --- undo / redo ---

    def _snapshot(self):
        """Zachytí stav: zapíše ho do historie a jednou za 2 s i do autosave."""
        data = self._capture()
        mouse = wx.GetMouseState()
        if not (mouse.LeftIsDown() or mouse.RightIsDown() or mouse.MiddleIsDown()):
            # Při tažení (slider, nota) se čeká na puštění myši, celý tažení = jeden krok Undo.
            self.history.record(json.dumps(data), change_key(data))
            self._update_menu()
        if self.ticks % AUTOSAVE_EVERY == 0:
            self._autosave(data)

    def _update_menu(self):
        """Undo / Redo v menu a šipky v hlavičce jsou zapnutý jen tehdy, když je co vracet."""
        idle = self.export is None       # během exportu se píseň nemění
        self.undo_item.Enable(self.history.can_undo and idle)
        self.redo_item.Enable(self.history.can_redo and idle)
        self.undo_button.set_enabled(self.history.can_undo and idle)
        self.redo_button.set_enabled(self.history.can_redo and idle)

    def undo(self):
        if self.export is not None:
            return
        data = self._capture()           # aktuální stav, ať se na něj dá pak dát Redo
        self._go_to(self.history.undo(json.dumps(data), change_key(data)))

    def redo(self):
        if self.export is not None:
            return
        data = self._capture()
        self._go_to(self.history.redo(json.dumps(data), change_key(data)))

    def _go_to(self, text):
        """Obnoví stav z historie přes _apply (to postaví všechno znova).

        Záložka zůstane, stopa se vybere podle pořadí (objekty jsou nový, tak
        podle pořadí, ne podle objektu), a přehrávání jede dál od místa, kde bylo
        (player.tick: _apply přehrávač jen zastaví, pozici nechá).
        """
        self._update_menu()
        if text is None:
            return                      # není kam jít
        # zapamatovat si, co bylo vybraný, než se to celý přestaví
        track = self.song_page.track
        index = self.song.tracks.index(track) if track in self.song.tracks else 0
        lane = self._lane_place()
        playing = self.player.playing
        self._apply(json.loads(text))
        tracks = self.song.tracks
        self.select_track(tracks[min(index, len(tracks) - 1)])   # min, kdyby stop teď bylo míň
        self._show_lane(lane)
        if playing:
            self.player.play(from_tick=self.player.tick)
            self._show_playing()

    def _lane_place(self):
        """Automatizace ukázaná na časový ose jako (pořadí vlastníka, popisek), nebo None.

        Objekty se při obnovení vyrobí znova, takže si nejde pamatovat objekt,
        ale pořadí a popisek zůstanou stejný.
        """
        owners = self.song_page.track.automated_owners()
        if self.song_page.lane is None or self.song_page.lane[0] not in owners:
            return None
        owner, param = self.song_page.lane
        return owners.index(owner), param.label

    def _show_lane(self, place):
        """Po obnovení zase ukáže tu samou automatizaci (pokud vlastník pořád existuje)."""
        if place is None:
            return
        index, label = place
        owners = self.song_page.track.automated_owners()
        if index < len(owners):
            for param in owners[index].PARAMS:
                if param.label == label and not param.choices:
                    self.song_page.lane = (owners[index], param)
                    self.song_page.refresh()

    # --- smyčka ---

    def _on_tick(self, event):
        # tohle volá časovač 30x za sekundu
        now = time.monotonic()
        dt, self.last_time = now - self.last_time, now   # kolik reálně uběhlo od minula (timer není přesnej)
        self.ticks += 1
        if self.ticks % SNAPSHOT_EVERY == 0:
            self._snapshot()
        if self.export is not None:
            self._export_tick()
        analyzer = self.engine.analyzer
        fresh = analyzer.update()        # fresh = je hotovej novej úsek zvuku?
        # kreslí se jen záložka, která je vidět, ať se zbytečně nepálí procesor
        if self.sound_page.IsShown():
            self.sound_page.tick(analyzer, fresh)
        if self.song_page.IsShown():
            self.song_page.tick()
        if self.visual_page.IsShown() or self.visual_page.fullscreen is not None:   # fullscreen jede i z jiný záložky
            self.visual_page.tick(analyzer, dt)
        self.light_page.tick(analyzer)   # světlo svítí pořád, ať se díváš kamkoli

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
        if self.export is not None:
            self.export.cancel()         # dopsat soubor, než se server zastaví
        self.player.close()
        self.keys.close()
        if self.visual_page.fullscreen is not None:
            self.visual_page.fullscreen.Destroy()
        self.light_page.close()
        self.engine.close()
        event.Skip()                     # až teď nechat okno opravdu zavřít (bez Skip by zůstalo otevřený)
