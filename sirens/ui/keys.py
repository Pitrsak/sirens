"""Hraní na klávesnici počítače jako na piano.

    W E   T Y U   O P          černý klávesy (C#, D#, F#, G#, A#, ...)
   A S D F G H J K L           bílý klávesy (C, D, E, F, G, A, H, C, D)
    X = o oktávu níž, C = o oktávu výš

Každá nota je prostě číslo (MIDI číslo, 0..127), čím větší, tím vyšší tón.
+1 = o půltón výš (další klávesa na pianu, i ta černá), +12 = o oktávu výš,
a oktáva výš je fyzikálně dvakrát vyšší frekvence (A4 = 440 Hz, A5 = 880 Hz).
60 je C4, takový to "prostřední C".

Režim Hold: stisk klávesy notu zapne a nechá znít, další stisk tý samý klávesy
ji vypne. Tón tak zní dál a mezitím se dá hýbat slidery a poslouchat změnu.

Klávesy chytám filtrem událostí (wx.EventFilter), kterej vidí každej stisk
v celý aplikaci dřív než ovládací prvky, takže hraní funguje, ať je kurzor
kdekoli. Výjimka jsou textový políčka (tam se fakt píše, ne hraje).
Noty jdou do enginu jako MIDI zprávy na kanál vybranýho nástroje
(note on = klávesa dolů, note off = klávesa nahoru, u nás to je velocity 0).
"""

import wx

# klávesa -> o kolik půltónů je nad C danýho oktávy (A = C, W = C#, S = D, ...)
# K, O, L, P už lezou do další oktávy (12 = zase C, jen o oktávu výš)
NOTE_KEYS = {"A": 0, "W": 1, "S": 2, "E": 3, "D": 4, "F": 5, "T": 6, "G": 7,
             "Y": 8, "Z": 8,    # na český klávesnici je Y a Z prohozený, fungujou obě
             "H": 9, "U": 10, "J": 11, "K": 12, "O": 13, "L": 14, "P": 15}
VELOCITY = 100    # síla úhozu z klávesnice, pořád stejná (počítač nepozná, jak silně mačkám), max je 127
# názvy 12 půltónů v oktávě, pozor B je anglicky, u nás se tomu říká H
NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def note_name(note: int) -> str:
    """MIDI číslo noty jako text, např. 60 -> C4.

    note % 12 je zbytek po dělení 12 = kolikátej půltón v oktávě (0 = C),
    note // 12 je celočíselný dělení = kolikátá oktáva. -1 je tam proto, že
    MIDI čísla 0..11 jsou oktáva -1, takže C4 vychází na 60 a ne na 48.
    Příklad: 60 % 12 = 0 -> C, 60 // 12 - 1 = 4 -> C4.
    """
    return f"{NOTE_NAMES[note % 12]}{note // 12 - 1}"


# KeyboardPlayer = to, co mění klávesy na noty. Dědí z wx.EventFilter,
# takže wx mu dá každou událost dřív než komukoli jinýmu (viz FilterEvent dole).
class KeyboardPlayer(wx.EventFilter):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.channel = 1          # MIDI kanál nástroje, na kterej se hraje (každá stopa má svůj)
        self.octave = 4           # A = C4 (MIDI nota 60), X / C to posouvá
        self.held = {}            # držená klávesa -> nota (aby opakovanej stisk nespouštěl notu znova)
        self.active = set()       # noty, který právě zní (pro zvýraznění na pianu), set = každá max jednou
        self.on_space = None      # co dělá mezerník (spuštění / zastavení písně), nastaví hlavní okno
        self.hold = False         # režim Hold: noty zní, dokud se znova nestisknou
        wx.EvtHandler.AddFilter(self)   # tady se filtr přihlásí do wx, od teď vidí všechny klávesy

    def note_on(self, note: int):
        # note on: nástroj začne hrát tuhle notu
        self.engine.send_note(self.channel, note, VELOCITY)
        self.active.add(note)

    def note_off(self, note: int):
        # note off = ta samá zpráva, jen s velocity 0 (engine z toho udělá vypnutí)
        self.engine.send_note(self.channel, note, 0)
        self.active.discard(note)       # discard nespadne, když tam nota není (remove by spadl)

    def press(self, note: int):
        """Stisk klávesy, je jedno jestli na počítači nebo myší na klaviatuře."""
        if self.hold and note in self.active:
            self.note_off(note)           # v Hold druhej stisk notu vypne
        else:
            self.note_on(note)

    def release(self, note: int):
        """Puštění klávesy: v Hold nota zní dál, takže se nic neděje."""
        if not self.hold:
            self.note_off(note)

    def set_hold(self, hold: bool):
        # při přepnutí Play / Hold radši všechno umlčím, ať nic nezůstane viset
        self.release_all()
        self.hold = hold

    def focus_lost(self):
        """Okno ztratilo fokus (třeba Cmd+Tab jinam): puštění klávesy by nepřišlo,
        takže držený noty radši vypnu, jinak by zněly furt.
        V Hold noty na puštění kláves nezávisí, takže zní dál, jen zapomenu, co bylo držený."""
        if self.hold:
            self.held.clear()
        else:
            self.release_all()

    def release_all(self):
        """Pustí všechny noty (např. když okno ztratí fokus a puštění klávesy by nepřišlo)."""
        # list() = kopie, protože note_off z množiny maže a přes množinu, co se mění, se jet nedá
        for note in list(self.active):
            self.note_off(note)
        self.held.clear()

    def set_channel(self, channel: int):
        # jiná stopa = jinej kanál, starý noty vypnout, ať nezůstanou znít na minulým nástroji
        self.release_all()
        self.channel = channel

    def FilterEvent(self, event):
        # tohle wx volá pro KAŽDOU událost v appce (klik, pohyb myši, klávesy...)
        # vracím Event_Skip = nech to jít dál normálně, Event_Processed = vyřídil jsem to já, dál už ne
        kind = event.GetEventType()
        if kind not in (wx.wxEVT_KEY_DOWN, wx.wxEVT_KEY_UP):
            return self.Event_Skip          # nejsou to klávesy, nezajímá mě to
        if isinstance(event.GetEventObject(), wx.TextCtrl) or event.HasAnyModifiers():
            return self.Event_Skip          # psaní do políčka nebo zkratka (Cmd+Q, ...)
        code = event.GetKeyCode()
        # kód klávesy -> znak; písmena chodí jako velký (A = 65), cokoli mimo běžný znaky = ""
        key = chr(code) if 32 <= code < 128 else ""

        # puštění klávesy: řeším jen ty, co hrajou notu, ostatní nechám jít dál
        if kind == wx.wxEVT_KEY_UP:
            if key in self.held:
                self.release(self.held.pop(key))    # pop vrátí notu a zároveň ji ze slovníku vyhodí
                return self.Event_Processed
            return self.Event_Skip

        # stisk klávesy s notou
        if key in NOTE_KEYS:
            if key not in self.held:        # držená klávesa posílá opakovaný stisky, ty ignoruju
                # C danýho oktávy je 12 * (oktáva + 1), oktáva 4 -> 60, k tomu posun klávesy (S = +2 = D)
                note = 12 * (self.octave + 1) + NOTE_KEYS[key]
                self.held[key] = note
                self.press(note)
            return self.Event_Processed
        # X / C = oktáva dolů / nahoru
        if key in ("X", "C"):
            if not self.hold:             # v Hold nechám znít i noty z předchozí oktávy
                self.release_all()
            # ohlídaný na 1..7 (max / min), ať to neuteče mimo rozsah
            self.octave = max(1, self.octave - 1) if key == "X" else min(7, self.octave + 1)
            return self.Event_Processed
        # mezerník = play / stop, ale jen když ho hlavní okno nastavilo
        if key == " " and self.on_space:
            self.on_space()
            return self.Event_Processed
        return self.Event_Skip

    def close(self):
        # při zavírání appky: všechno umlčet a odhlásit filtr z wx
        self.release_all()
        wx.EvtHandler.RemoveFilter(self)
