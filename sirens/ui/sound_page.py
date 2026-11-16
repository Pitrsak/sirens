"""Záložka Sound: nástroj vybraný stopy (obálka a bloky) a hraní na klávesnici.

    +-----------------------------------------+--------------------+
    |  SCOPE (tvar vlny)                      | OUTPUT  Master     |
    |                                         | ------------------ |
    |  SPECTRUM (vlastní DFT)                 | TRACK  výběr stopy |
    |                                         | PRESET Save / Load |
    |                                         | ENVELOPE           |
    |  [cesta zvuku: Oscillator -> Filter]    | bloky nástroje     |
    |  [klaviatura]                           | [Add block]        |
    +-----------------------------------------+--------------------+

Vlevo se jen kouká a hraje (grafy + klaviatura), vpravo v panelu se zvuk staví.
Horní kus panelu (Output, Master, Keys) je fixní, zbytek se celej přestaví
v refresh(), kdykoli se změní stopa nebo bloky.

Preset = zvuk jedný stopy (obálka + bloky) uloženej do vlastního souboru,
třeba assets/presets/drums/kick.json. Noty v něm nejsou, jen zvuk, takže
se dá nahrát do jakýkoli stopy. Složky (drums, bass...) si člověk dělá sám
přímo v dialogu pro uložení.
"""

from pathlib import Path

import wx

from sirens import session
from sirens.audio.analyzer import SCOPE_VIEW
from sirens.audio.blocks import CATALOG
from sirens.ui import theme
from sirens.ui.piano import PianoView
from sirens.ui.sidebar import Sidebar, divider
from sirens.ui.stack_editor import StackEditor
from sirens.ui.views import ScopeView, SpectrumView
from sirens.ui.widgets import StatusPill, confirm

# složka s presety: parents[2] = ui -> sirens -> kořen projektu
PRESET_FOLDER = Path(__file__).resolve().parents[2] / "assets" / "presets"
PRESET_TYPES = "Sound presets (*.json)|*.json"   # filtr do dialogu: ukáže jen .json


class SoundPage(wx.Panel):
    def __init__(self, parent, engine, song, keys, on_track_change):
        """on_track_change(track): zavolá se, když uživatel vybere jinou stopu.

        keys = KeyboardPlayer (hraní na klávesnici), song = celá píseň se stopama.
        """
        super().__init__(parent)
        self.SetBackgroundColour(theme.BACKGROUND)
        self.song = song
        self.keys = keys
        self.on_track_change = on_track_change
        self.track = song.tracks[0]
        self.clipboard = None     # zkopírovanej zvuk (slovník ze session.sound_of), zatím nic

        # levej sloupec: graf vlny, spektrum, štítek s cestou zvuku, klaviatura
        self.scope = ScopeView(self)
        self.spectrum = SpectrumView(self)
        self.status = StatusPill(self)
        self.piano = PianoView(self, keys)
        column = wx.BoxSizer(wx.VERTICAL)
        column.Add(self.scope, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 20)
        column.Add(self.spectrum, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 20)
        column.Add(self.status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 20)
        column.Add(self.piano, 0, wx.EXPAND | wx.ALL, 20)

        # pravej panel: fixní část nahoře (Output, Master, Keys), zbytek přes StackEditor
        self.sidebar = Sidebar(self, with_fixed=True)
        self.sidebar.add_group("Output", fixed=True)
        self.sidebar.add_slider("Master", 0, 1, 0.5, on_change=engine.set_volume, fixed=True,
                                help="Overall loudness of all tracks. After it the sound is clipped "
                                     "to -1..1, so nothing can blast the speakers.")
        # lambda = malá funkce na jeden řádek; i je pořadí vybraný možnosti (0 = Play, 1 = Hold)
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
        # volá hlavní okno, když se vybere jiná stopa (odkudkoli)
        self.track = track
        self.refresh()

    def _choose_track(self, index: int):
        # Seznam stop je v panelu, kterej se teď překreslí: tak až po skončení události.
        # (wx.CallAfter = udělej to, až se dodělá tahle událost, jinak bych mazal prvek, co ji zrovna řeší)
        wx.CallAfter(self.on_track_change, self.song.tracks[index])

    def _copy_sound(self):
        # zkopíruje jen zvuk (obálku a bloky), noty ne
        self.clipboard = session.sound_of(self.track)
        self.clipboard_name = self.track.name
        wx.CallAfter(self.refresh)          # ukáže tlačítko Paste sound

    def _paste_sound(self):
        """Nahradí zvuk vybraný stopy zkopírovaným (noty a časová osa zůstanou)."""
        if confirm(self, f"Replace the sound of {self.track.name} with the sound copied "
                         f"from {self.clipboard_name}?", "Paste sound", "Paste"):
            session.apply_sound(self.track, self.clipboard)
            wx.CallAfter(self.refresh)

    def _save_preset(self):
        """Uloží zvuk vybraný stopy do souboru (stejnej slovník jako u Copy sound)."""
        # "/" ve jménu souboru nejde (to je oddělovač složek), tak ho nahradím pomlčkou
        name = self.track.name.replace("/", "-") + ".json"
        with wx.FileDialog(self, "Save preset", str(PRESET_FOLDER), name, PRESET_TYPES,
                           wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                session.write(Path(dialog.GetPath()), session.sound_of(self.track))

    def _load_preset(self):
        """Nahradí zvuk vybraný stopy presetem ze souboru (noty a časová osa zůstanou)."""
        with wx.FileDialog(self, "Load preset", str(PRESET_FOLDER), "", PRESET_TYPES,
                           wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            try:
                data = session.read(Path(dialog.GetPath()))
            except (OSError, ValueError) as error:
                wx.MessageBox(f"Cannot open this file:\n{error}", "Load preset", wx.ICON_ERROR, self)
                return
        # preset má klíč "blocks" s bloky zvuku; celá píseň (Save na hlavní liště) ho nemá
        if not isinstance(data, dict) or "blocks" not in data:
            wx.MessageBox("This file is not a sound preset.", "Load preset", wx.ICON_ERROR, self)
            return
        session.apply_sound(self.track, data)
        wx.CallAfter(self.refresh)

    def _rename(self, text: str):
        # prázdný jméno nechci, tak když je text prázdnej, nechá se starý
        self.track.name = text or self.track.name

    def refresh(self):
        """Překreslí pravej panel podle vybraný stopy (smaže a postaví znova)."""
        if self.track not in self.song.tracks:
            self.track = self.song.tracks[0]       # stopa mezitím zmizela (smazaná, načtení souboru...), vezmu první
        sidebar = self.sidebar
        sidebar.clear()
        # skupina Track: tlačítka Copy / Paste, výběr stopy, jméno
        actions = [("Copy sound", self._copy_sound)]
        if self.clipboard is not None:
            actions.append(("Paste sound", self._paste_sound))
        sidebar.add_group("Track", actions=actions)
        names = [track.name for track in self.song.tracks]
        sidebar.add_dropdown("Edit", names, self.song.tracks.index(self.track), self._choose_track,
                           help="Each track is its own instrument. Add tracks on the Song tab.")
        sidebar.add_text("Name", self.track.name, self._rename)
        if self.clipboard is not None:
            sidebar.add_note(f"Copied sound: {self.clipboard_name}. Select another track and click Paste sound.")
        # presety: zvuk do souboru a zpátky
        sidebar.add_group("Preset", actions=[("Save", self._save_preset), ("Load", self._load_preset)])
        sidebar.add_note("Save this sound to a file (for example drums/kick) and load it into any track.")
        # obálka (Attack, Decay, Sustain, Release, Volume) = slidery nástroje
        sidebar.add_group("Envelope")
        sidebar.add_params(self.track.instrument)
        # bloky (zdroje a efekty) přes StackEditor, stejně jako vrstvy ve Visual
        self.editor.show(self.track.instrument.rack,
                         "No sound yet. Add a source (Oscillator, Noise or Sampler), "
                         "then play with the keys A S D F G H J. Effects go below the source.")
        sidebar.finish()
        self.status.show(f"{self.track.name}: " + (self.track.instrument.rack.describe() or "empty"))

    def tick(self, analyzer, fresh: bool):
        """Každej snímek: klaviatura; grafy jen když je hotovej novej úsek zvuku."""
        self.piano.Refresh(False)          # False = nemazat pozadí, kreslí se stejně celý znova
        if fresh:
            # kolik ms zvuku graf ukazuje: počet vzorků / vzorků za sekundu * 1000
            duration_ms = SCOPE_VIEW / analyzer.sample_rate * 1000
            self.scope.show(analyzer.scope(), duration_ms, analyzer.peak_level_db())
            self.spectrum.show(analyzer.freqs, analyzer.spectrum, analyzer.peak_frequency())
