"""Klaviatura na obrazovce: ukazuje, co hraje, a dá se na ni hrát i myší.

Kreslí 3 oktávy od oktávy, na kterou je zrovna nastavená klávesnice počítače
(A = první C vlevo). Noty, co hrajou, jsou zvýrazněný.
Hraje se přes KeyboardPlayer z keys.py, takže myš i klávesnice dělaj to samý
a Hold platí pro obojí.
"""

import wx

from sirens.ui import theme
from sirens.ui.keys import note_name

OCTAVES = 3
WHITE_STEPS = (0, 2, 4, 5, 7, 9, 11)     # půltóny bílých kláves v oktávě (C D E F G A H), mezi E-F a H-C černá není
# za kterou bílou (pořadí) je černá a jakej má půltón
# třeba 0: 1 = za bílou č. 0 (C) je černá s půltónem 1 (C#), za E (2) a H (6) žádná není
BLACK_STEPS = {0: 1, 1: 3, 3: 6, 4: 8, 5: 10}


class PianoView(wx.Control):
    HEIGHT = 96     # výška klaviatury v px

    def __init__(self, parent, player):
        # pozor, player je tady KeyboardPlayer (keys.py), ne přehrávač písně
        super().__init__(parent, style=wx.BORDER_NONE)
        self.player = player
        self.mouse_note = None        # nota, kterou právě drží myš
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.SetMinSize((-1, self.HEIGHT))
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_LEFT_DOWN, self._on_down)
        self.Bind(wx.EVT_LEFT_UP, self._on_up)
        self.Bind(wx.EVT_MOTION, self._on_motion)

    def _first_note(self) -> int:
        # první C vlevo, stejnej vzorec jako v keys.py: 12 * (oktáva + 1), oktáva 4 -> 60
        return 12 * (self.player.octave + 1)

    def _keys(self):
        """Seznam (nota, x, y, šířka, výška, je_černá); černý až na konci, kreslí se přes bílý.

        Bílá klávesa je celá šířka / 21 (7 bílých v oktávě x 3 oktávy). Černá je
        užší (0.64 bílý), kratší (60 % výšky) a sedí přes hranici dvou bílých.
        Tenhle seznam se používá na kreslení i na to, kam se kliklo.
        """
        w, h = self.GetClientSize()
        top = 22                                 # nahoře místo pro popisek
        white_w = w / (7 * OCTAVES)
        whites, blacks = [], []
        for octave in range(OCTAVES):
            base = self._first_note() + 12 * octave       # C týhle oktávy
            # enumerate dává pořadí i hodnotu naráz: i = kolikátá bílá v oktávě, step = její půltón
            for i, step in enumerate(WHITE_STEPS):
                x = (octave * 7 + i) * white_w           # kolikátá bílá zleva krát šířka
                whites.append((base + step, x, top, white_w, h - top, False))
                if i in BLACK_STEPS:
                    # černá začne kousek před pravým okrajem bílý (0.68), takže přečuhuje na obě strany
                    bx = x + white_w * 0.68
                    blacks.append((base + BLACK_STEPS[i], bx, top, white_w * 0.64, (h - top) * 0.6, True))
        return whites + blacks

    def _note_at(self, x, y):
        # hit-test: projedu obdélníky kláves a checknu, jestli bod myši leží uvnitř
        for note, kx, ky, kw, kh, black in reversed(self._keys()):   # nejdřív černý (jsou navrchu)
            if kx <= x < kx + kw and ky <= y < ky + kh:
                return note
        return None

    def _on_down(self, event):
        self.mouse_note = self._note_at(event.GetX(), event.GetY())
        if self.mouse_note is not None:
            self.player.press(self.mouse_note)
            # CaptureMouse = myš teď patří jen sem, takže puštění tlačítka přijde sem,
            # i když mezitím ujedu myší mimo klaviaturu (jinak by nota zůstala viset)
            self.CaptureMouse()

    def _on_up(self, event):
        if self.HasCapture():
            self.ReleaseMouse()
        if self.mouse_note is not None:
            self.player.release(self.mouse_note)
            self.mouse_note = None

    def _on_motion(self, event):
        """Tažení myší po klávesách hraje jednu notu po druhý."""
        if not (event.Dragging() and self.mouse_note is not None) or self.player.hold:
            return                        # v Hold se tažením nehraje (každej stisk notu přepíná)
        note = self._note_at(event.GetX(), event.GetY())
        if note is not None and note != self.mouse_note:
            # myš je na jiný klávese: starou vypnout, novou zapnout
            self.player.note_off(self.mouse_note)
            self.mouse_note = note
            self.player.note_on(note)

    def _on_paint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(self.GetParent().GetBackgroundColour()))
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        # nahoře nápověda, jaký klávesy a kde teď je A
        gc.SetFont(theme.font(10), theme.TEXT_DIM)
        hint = "Hold: press a key again to stop it." if self.player.hold else "Or click here."
        gc.DrawText(f"Play with keys A W S E D F T G Y H U J K.   X / C = octave down / up "
                    f"(A is now {note_name(self._first_note())}).   {hint}", 0, 0)
        # klávesy: co zrovna hraje (je v player.active), je šedý, jinak normální bílá / tmavá
        for note, x, y, w, h, black in self._keys():
            playing = note in self.player.active
            if black:
                colour = theme.TEXT_MUTED if playing else theme.BACKGROUND
            else:
                colour = theme.TEXT_MUTED if playing else theme.TEXT
            gc.SetPen(wx.Pen(theme.BORDER, 1))
            gc.SetBrush(wx.Brush(colour))
            # malej posun a o pixel užší, ať jsou klávesy od sebe vidět, rohy zaoblený o 3 px
            gc.DrawRoundedRectangle(x + 0.5, y, w - 1, h, 3)
