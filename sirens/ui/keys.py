"""Hraní na klávesnici počítače jako na piano.

    W E   T Y U   O P          černé klávesy (C#, D#, F#, G#, A#, ...)
   A S D F G H J K L           bílé klávesy (C, D, E, F, G, A, H, C, D)
    X = o oktávu níž, C = o oktávu výš

Klávesy se chytají filtrem událostí (wx.EventFilter), který vidí každý stisk
v celé aplikaci dřív než ovládací prvky, takže hraní funguje, ať je kurzor
kdekoli. Výjimkou jsou textová políčka (tam se píše).
Noty jdou do enginu jako MIDI zprávy na kanál vybraného nástroje.
"""

import wx

# klávesa -> o kolik půltónů nad C dané oktávy
NOTE_KEYS = {"A": 0, "W": 1, "S": 2, "E": 3, "D": 4, "F": 5, "T": 6, "G": 7,
             "Y": 8, "Z": 8,    # na české klávesnici je Y a Z prohozené, fungují obě
             "H": 9, "U": 10, "J": 11, "K": 12, "O": 13, "L": 14, "P": 15}
VELOCITY = 100
NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def note_name(note: int) -> str:
    """MIDI číslo noty jako text, např. 60 -> C4."""
    return f"{NOTE_NAMES[note % 12]}{note // 12 - 1}"


class KeyboardPlayer(wx.EventFilter):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.channel = 1          # MIDI kanál nástroje, na který se hraje
        self.octave = 4           # A = C4 (MIDI nota 60)
        self.held = {}            # držená klávesa -> nota (aby opakovaný stisk nespouštěl notu znovu)
        self.active = set()       # noty, které právě znějí (pro zvýraznění na pianu)
        self.on_space = None      # co dělá mezerník (spuštění / zastavení písně)
        wx.EvtHandler.AddFilter(self)

    def note_on(self, note: int):
        self.engine.send_note(self.channel, note, VELOCITY)
        self.active.add(note)

    def note_off(self, note: int):
        self.engine.send_note(self.channel, note, 0)
        self.active.discard(note)

    def release_all(self):
        """Pustí všechny noty (např. když okno ztratí fokus a puštění klávesy by nepřišlo)."""
        for note in list(self.active):
            self.note_off(note)
        self.held.clear()

    def set_channel(self, channel: int):
        self.release_all()
        self.channel = channel

    def FilterEvent(self, event):
        kind = event.GetEventType()
        if kind not in (wx.wxEVT_KEY_DOWN, wx.wxEVT_KEY_UP):
            return self.Event_Skip
        if isinstance(event.GetEventObject(), wx.TextCtrl) or event.HasAnyModifiers():
            return self.Event_Skip          # psaní do políčka nebo zkratka (Cmd+Q, ...)
        code = event.GetKeyCode()
        key = chr(code) if 32 <= code < 128 else ""

        if kind == wx.wxEVT_KEY_UP:
            if key in self.held:
                self.note_off(self.held.pop(key))
                return self.Event_Processed
            return self.Event_Skip

        if key in NOTE_KEYS:
            if key not in self.held:        # držená klávesa posílá opakované stisky, ty ignorujeme
                note = 12 * (self.octave + 1) + NOTE_KEYS[key]
                self.held[key] = note
                self.note_on(note)
            return self.Event_Processed
        if key in ("X", "C"):
            self.release_all()
            self.octave = max(1, self.octave - 1) if key == "X" else min(7, self.octave + 1)
            return self.Event_Processed
        if key == " " and self.on_space:
            self.on_space()
            return self.Event_Processed
        return self.Event_Skip

    def close(self):
        self.release_all()
        wx.EvtHandler.RemoveFilter(self)
