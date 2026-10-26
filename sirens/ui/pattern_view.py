"""Editor patternu (piano roll): mřížka, svisle výšky not, vodorovně kroky.

Řádek = jedna výška tónu (nahoře vysoký, dole hluboký), sloupec = jeden krok
v čase, nota je obdélník: kde začíná = kdy zazní, jak je dlouhá = jak dlouho zní.
Jeden krok = šestnáctinová nota, na takt jich je 16. Čísla nahoře (1.1, 1.2...)
jsou vždycky doby (takt.doba, takt má 4 doby).

Ovládání:
 - klik do prázdnýho místa přidá notu (a přehraje ji), tažením doprava se prodlouží
 - klik na notu ji smaže
 - kolečko myši posune zobrazený výšky nahoru a dolů
 - pruh "Vel" dole: síla úhozu (velocity) not; každá nota má na svým začátku
   sloupek, čím vyšší, tím hlasitějc zazní. Klik / tažení v pruhu nastaví sílu
   všem notám, který na kroku pod myší začínaj (akord se mění celej), podle výšky myši.
   Slabší noty jsou v mřížce kreslený tlumenějc.

Převod pixely <-> krok a nota je v _cell, _step_at a _at, je to vlastně jen
dělení velikostí jedný buňky.
"""

import wx

from sirens.song import BEATS_PER_BAR, STEPS_PER_BAR, Note
from sirens.ui import theme
from sirens.ui.keys import note_name

ROWS = 24          # zobrazený výšky (2 oktávy, 2 x 12 půltónů)
LABEL_W = 44       # místo vlevo pro názvy not
HEADER_H = 20      # místo nahoře pro čísla dob
VEL_H = 44         # výška pruhu se silou úhozu dole
VEL_GAP = 6        # mezera mezi mřížkou a pruhem
BLACK = {1, 3, 6, 8, 10}    # půltóny černých kláves v oktávě (C#, D#, F#, G#, A#)


class PatternView(wx.Control):
    def __init__(self, parent, player, preview):
        """preview(nota): krátce zahraje notu vybraný stopy (při přidání)."""
        super().__init__(parent, style=wx.BORDER_NONE)
        self.player = player           # přehrávač písně, tady jen kvůli ukazateli, co zrovna hraje
        self.preview = preview
        self.track = None              # stopu sem dosadí SongPage, do tý doby se nekreslí nic
        self.drag_note = None          # nota, kterou právě prodlužuju tažením
        self.drag_velocity = False     # táhnu v pruhu síly úhozu
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_LEFT_DOWN, self._on_down)
        self.Bind(wx.EVT_LEFT_UP, self._on_up)
        self.Bind(wx.EVT_MOTION, self._on_motion)
        self.Bind(wx.EVT_MOUSEWHEEL, self._on_wheel)
        self.Bind(wx.EVT_SIZE, lambda e: self.Refresh())    # změna velikosti okna = překreslit celý

    def pattern(self):
        # pattern, kterej stopa zrovna edituje (A..H)
        return self.track.patterns[self.track.current]

    # --- převod poloha <-> krok a nota ---

    def _vel_top(self):
        """Horní okraj pruhu se silou úhozu (pruh je úplně dole a je VEL_H vysokej)."""
        return self.GetClientSize()[1] - VEL_H

    def _cell(self):
        # velikost jedný buňky v px: šířka = místo vpravo od názvů / počet kroků,
        # výška = místo mezi hlavičkou a pruhem Vel / 24 řádků. Je to float, ať to vyplní přesně
        w, _ = self.GetClientSize()
        grid_h = self._vel_top() - VEL_GAP - HEADER_H
        return (w - LABEL_W) / self.pattern().steps(), grid_h / ROWS

    def _step_at(self, x):
        """Krok pod myší (může bejt i mimo pattern, to si checkne ten, kdo to volá).

        x - LABEL_W = kolik px od začátku mřížky, // cell_w = kolik celejch
        buněk se tam vejde = číslo kroku. // je dělení zaokrouhlený dolů,
        s floatem dá třeba 3.0, proto ještě int().
        """
        cell_w, _ = self._cell()
        return int((x - LABEL_W) // cell_w)

    def _at(self, x, y):
        """(krok, nota) pod myší, nebo None mimo mřížku."""
        _, cell_h = self._cell()
        step = self._step_at(x)
        row = int((y - HEADER_H) // cell_h)        # stejnej trik jako u kroku, jen svisle
        # 0 <= step < n je Python zkratka pro 0 <= step and step < n
        if x < LABEL_W or y < HEADER_H or not (0 <= step < self.pattern().steps()) or not (0 <= row < ROWS):
            return None
        # řádek 0 je nahoře a to je NEJVYŠŠÍ nota (view_low + 23), proto se to otáčí
        return step, self.track.view_low + ROWS - 1 - row

    def _set_velocity(self, x, y):
        """Síla úhozu podle výšky myši v pruhu (nahoře 127, dole 1) všem notám, který začínaj na kroku pod myší."""
        step = self._step_at(x)
        # unit 0..1: 1 nahoře, 0 dole (y roste směrem dolů, proto 1 - ...), min / max to ořízne, když myš ujede
        unit = min(1.0, max(0.0, 1 - (y - self._vel_top()) / VEL_H))
        velocity = round(1 + unit * 126)       # 0..1 -> 1..127 (0 by znamenalo vypnutí noty, tak od 1)
        for note in self.pattern().notes:
            if note.step == step:
                note.velocity = velocity
        self.Refresh()

    # --- myš ---

    def _on_down(self, event):
        x, y = event.GetX(), event.GetY()
        # klik dole v pruhu Vel: nastavuju sílu úhozu, ne noty
        if x >= LABEL_W and y >= self._vel_top():
            self.drag_velocity = True
            self._set_velocity(x, y)
            self.CaptureMouse()        # ať dostávám pohyb myši, i když vyjede ven
            return
        found = self._at(x, y)
        if found is None:
            return                     # mimo mřížku, nic
        step, pitch = found
        pattern = self.pattern()
        note = pattern.note_at(step, pitch)      # zní tady nějaká nota? (i prostředek dlouhý noty se počítá)
        if note:
            pattern.notes.remove(note)            # klik na notu = smazat
        else:
            # nová nota, zatím 1 krok dlouhá, tažením (_on_motion) se natáhne
            self.drag_note = Note(step, pitch, 1)
            pattern.notes.append(self.drag_note)
            self.preview(pitch)                   # hned ji zahraju, ať slyším, co jsem dal
            self.CaptureMouse()
        self.Refresh()

    def _on_motion(self, event):
        if self.drag_velocity:
            self._set_velocity(event.GetX(), event.GetY())
            return
        if self.drag_note is None:
            return                     # jen jezdím myší, nic netáhnu
        step = self._step_at(event.GetX())
        # konec noty = krok pod myší, ale ne před její začátek (max) a ne za konec patternu (min)
        end = min(max(step, self.drag_note.step), self.pattern().steps() - 1)
        self.drag_note.length = end - self.drag_note.step + 1    # +1, protože i krok, kde začíná, se počítá
        self.Refresh()

    def _on_up(self, event):
        # pustil jsem tlačítko = konec tažení
        if self.HasCapture():
            self.ReleaseMouse()
        self.drag_note = None
        self.drag_velocity = False

    def _on_wheel(self, event):
        # kolečko nahoru = vyšší noty; view_low je nejnižší zobrazená nota, ohlídaná na 0 .. 127 - ROWS
        step = 1 if event.GetWheelRotation() > 0 else -1
        self.track.view_low = min(127 - ROWS, max(0, self.track.view_low + step))
        self.Refresh()

    # --- kreslení ---

    def _on_paint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(theme.VIEWPORT))
        dc.Clear()
        if self.track is None:
            return
        gc = wx.GraphicsContext.Create(dc)
        w, h = self.GetClientSize()
        pattern = self.pattern()
        cell_w, cell_h = self._cell()
        grid_bottom = HEADER_H + ROWS * cell_h
        vel_top = self._vel_top()

        # řádky: černý klávesy tmavší, u každýho C název (a čára, ať se vyznám v oktávách)
        gc.SetFont(theme.font(9), theme.TEXT_DIM)
        for row in range(ROWS):
            pitch = self.track.view_low + ROWS - 1 - row     # stejný otočení jako v _at
            y = HEADER_H + row * cell_h
            if pitch % 12 in BLACK:
                gc.SetBrush(wx.Brush(theme.BACKGROUND))
                gc.SetPen(wx.TRANSPARENT_PEN)
                gc.DrawRectangle(LABEL_W, y, w - LABEL_W, cell_h)
            if pitch % 12 == 0:
                gc.DrawText(note_name(pitch), 6, y + (cell_h - 12) / 2)
                gc.SetPen(wx.Pen(theme.BORDER, 1))
                gc.StrokeLine(LABEL_W, y + cell_h, w, y + cell_h)

        # sloupce: slabě každej krok, víc každá doba, nejvíc každej takt (v mřížce i v pruhu Vel)
        per_beat = STEPS_PER_BAR // BEATS_PER_BAR      # kroků na dobu: 16 / 4 = 4
        for step in range(pattern.steps() + 1):          # +1, ať je i čára na pravým konci
            x = LABEL_W + step * cell_w
            strong = step % STEPS_PER_BAR == 0           # začátek taktu
            gc.SetPen(wx.Pen(theme.TEXT_DIM if strong else theme.BORDER if step % per_beat == 0 else theme.GRID, 1))
            gc.StrokeLine(x, HEADER_H, x, grid_bottom)
            gc.StrokeLine(x, vel_top, x, h)
            if step % per_beat == 0 and step < pattern.steps():
                # divmod = celočíselný dělení a zbytek naráz: kolikátá doba -> (takt, doba v taktu)
                bar, beat = divmod(step // per_beat, BEATS_PER_BAR)
                gc.DrawText(f"{bar + 1}.{beat + 1}", x + 3, 3)    # +1, lidi počítaj od 1, ne od 0

        # pruh síly úhozu: oddělovací čára a popisek
        gc.SetPen(wx.Pen(theme.BORDER, 1))
        gc.StrokeLine(LABEL_W, vel_top, w, vel_top)
        gc.DrawText("Vel", 6, vel_top + (VEL_H - 12) / 2)

        # ukazatel přehrávání (jen v režimu Loop, kde hraje tenhle pattern); position je v tikách
        # tiky -> krok (// ticks_per_step), % steps = jakmile pattern skončí, jede se zase od začátku
        if self.player.playing and self.player.mode == "Loop":
            step = self.player.position // pattern.ticks_per_step() % pattern.steps()
            x = LABEL_W + step * cell_w
            gc.SetBrush(wx.Brush(wx.Colour(255, 255, 255, 25)))    # skoro průhledná bílá
            gc.SetPen(wx.TRANSPARENT_PEN)
            gc.DrawRectangle(x, HEADER_H, cell_w, h - HEADER_H)

        # noty: čím slabší úhoz, tím průhlednější (tlumenější)
        gc.SetPen(wx.Pen(theme.BACKGROUND, 1))
        for note in list(pattern.notes):       # list() = kopie seznamu, pro jistotu, kdyby se zrovna měnil
            alpha = 60 + round(195 * note.velocity / 127)     # průhlednost 60..255 podle velocity
            colour = wx.Colour(theme.ACCENT.Red(), theme.ACCENT.Green(), theme.ACCENT.Blue(), alpha)
            row = self.track.view_low + ROWS - 1 - note.pitch
            if 0 <= row < ROWS:                # noty mimo zobrazený výšky nekreslím
                gc.SetBrush(wx.Brush(colour))
                # +1 a -2: kousek mezery kolem, ať jsou dvě noty vedle sebe vidět zvlášť
                gc.DrawRoundedRectangle(LABEL_W + note.step * cell_w + 1, HEADER_H + row * cell_h + 1,
                                        note.length * cell_w - 2, cell_h - 2, 3)

        # sloupky síly úhozu na začátku každý noty (i not mimo zobrazený výšky)
        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.SetBrush(wx.Brush(theme.ACCENT))
        bar_w = max(2, min(6, cell_w - 2))      # šířka sloupku 2..6 px podle šířky buňky
        for note in list(pattern.notes):
            bar_h = (VEL_H - 4) * note.velocity / 127     # 127 = skoro celej pruh
            gc.DrawRectangle(LABEL_W + note.step * cell_w + 1, h - bar_h, bar_w, bar_h)
