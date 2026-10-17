"""Hraní na klávesnici počítače a zobrazení klaviatury na obrazovce.

Rozložení jako v běžných DAW: řada A S D F G H J K L jsou bílé klávesy,
W E T Y U O P černé. Z a X posouvají oktávu dolů a nahoru.
"""

import wx

from fathom.ui import theme

# Klávesa -> posun v půltónech od C aktuální oktávy.
KEY_TO_SEMITONE = {
    "A": 0, "W": 1, "S": 2, "E": 3, "D": 4, "F": 5, "T": 6, "G": 7,
    "Y": 8, "H": 9, "U": 10, "J": 11, "K": 12, "O": 13, "L": 14, "P": 15,
}
BLACK_KEYS = {1, 3, 6, 8, 10}  # půltóny černých kláves v oktávě


class ComputerKeyboard(wx.EventFilter):
    """Zachytává stisky kláves v celé aplikaci a posílá je syntezátoru jako noty.

    wx.EventFilter vidí všechny události dřív, než dorazí k ovladačům,
    takže hrát jde i ve chvíli, kdy má fokus třeba knob.
    """

    def __init__(self, synth, on_octave_change=None):
        super().__init__()
        self.synth = synth
        self.base_note = 48              # C3
        self.held = {}                   # klávesa -> zahraná MIDI nota
        self.on_octave_change = on_octave_change

    def FilterEvent(self, event):
        kind = event.GetEventType()
        if kind not in (wx.wxEVT_KEY_DOWN, wx.wxEVT_KEY_UP):
            return self.Event_Skip
        if isinstance(wx.Window.FindFocus(), wx.TextCtrl):
            return self.Event_Skip       # při psaní textu nehrajeme
        code = event.GetKeyCode()
        key = chr(code) if 32 <= code < 128 else ""
        if kind == wx.wxEVT_KEY_DOWN:
            handled = self._key_down(key)
        else:
            handled = self._key_up(key)
        return self.Event_Processed if handled else self.Event_Skip

    def _key_down(self, key: str) -> bool:
        if key in ("Z", "X"):
            self.base_note += -12 if key == "Z" else 12
            self.base_note = min(96, max(12, self.base_note))
            if self.on_octave_change:
                self.on_octave_change(self.base_note)
            return True
        if key not in KEY_TO_SEMITONE:
            return False
        if key not in self.held:         # držená klávesa posílá opakované události, ty ignorujeme
            note = self.base_note + KEY_TO_SEMITONE[key]
            self.held[key] = note
            self.synth.note_on(note)
        return True

    def _key_up(self, key: str) -> bool:
        note = self.held.pop(key, None)
        if note is None:
            return False
        self.synth.note_off(note)
        return True


class PianoStrip(wx.Panel):
    """Klaviatura na obrazovce: ukazuje znějící noty a dá se na ni klikat myší."""

    def __init__(self, parent, synth, octaves: int = 3):
        super().__init__(parent)
        self.synth = synth
        self.first_note = 36             # C2
        self.octaves = octaves
        self.active = set()              # právě znějící noty
        self._mouse_note = None
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.SetMinSize((-1, 70))
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_LEFT_DOWN, self._on_down)
        self.Bind(wx.EVT_LEFT_UP, self._on_up)
        synth.listeners.append(self._on_note)

    def _on_note(self, note, is_on):
        (self.active.add if is_on else self.active.discard)(note)
        self.Refresh()

    def _key_rects(self):
        """Vrátí seznam (nota, obdélník, je_černá); černé až na konci, kreslí se přes bílé."""
        w, h = self.GetClientSize()
        white_count = self.octaves * 7 + 1
        white_w = w / white_count
        whites, blacks = [], []
        index = 0
        for note in range(self.first_note, self.first_note + self.octaves * 12 + 1):
            if note % 12 in BLACK_KEYS:
                x = index * white_w - white_w * 0.3
                blacks.append((note, wx.Rect(int(x), 0, int(white_w * 0.6), int(h * 0.6)), True))
            else:
                whites.append((note, wx.Rect(int(index * white_w), 0, int(white_w) - 1, h), False))
                index += 1
        return whites + blacks

    def _note_at(self, pos):
        for note, rect, _ in reversed(self._key_rects()):   # černé mají přednost
            if rect.Contains(pos):
                return note
        return None

    def _on_down(self, event):
        self._mouse_note = self._note_at(event.GetPosition())
        if self._mouse_note is not None:
            self.synth.note_on(self._mouse_note)

    def _on_up(self, event):
        if self._mouse_note is not None:
            self.synth.note_off(self._mouse_note)
            self._mouse_note = None

    def _on_paint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(theme.BACKGROUND))
        dc.Clear()
        for note, rect, black in self._key_rects():
            if note in self.active:
                colour = theme.ACCENT
            else:
                colour = wx.Colour(20, 20, 24) if black else wx.Colour(200, 200, 205)
            dc.SetPen(wx.Pen(theme.BACKGROUND))
            dc.SetBrush(wx.Brush(colour))
            dc.DrawRectangle(rect)
