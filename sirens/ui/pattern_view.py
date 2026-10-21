"""Editor patternu (piano roll): mřížka, svisle výšky not, vodorovně kroky.

Kolik kroků má takt, určuje mřížka patternu (16 = šestnáctiny, 12 nebo 24 = trioly),
sloupce se jí přizpůsobí. Čísla nahoře (1.1, 1.2...) jsou vždy doby.

Ovládání:
 - klik do prázdného místa přidá notu (a přehraje ji), tažením doprava se prodlouží
 - klik na notu ji smaže
 - kolečko myši posune zobrazené výšky nahoru a dolů
 - pruh "Vel" dole: síla úhozu (velocity) not; každá nota má na svém začátku
   sloupek, čím vyšší, tím hlasitěji zazní. Klik / tažení v pruhu nastaví sílu
   všem notám, které na kroku pod myší začínají (akord se mění celý), podle výšky myši.
   Slabší noty jsou v mřížce kreslené tlumeněji.
"""

import wx

from sirens.song import BEATS_PER_BAR, Note
from sirens.ui import theme
from sirens.ui.keys import note_name

ROWS = 24          # zobrazené výšky (2 oktávy)
LABEL_W = 44       # místo vlevo pro názvy not
HEADER_H = 20      # místo nahoře pro čísla dob
VEL_H = 44         # výška pruhu se silou úhozu dole
VEL_GAP = 6        # mezera mezi mřížkou a pruhem
BLACK = {1, 3, 6, 8, 10}    # půltóny černých kláves v oktávě


class PatternView(wx.Control):
    def __init__(self, parent, player, preview):
        """preview(nota): krátce zahraje notu vybrané stopy (při přidání)."""
        super().__init__(parent, style=wx.BORDER_NONE)
        self.player = player
        self.preview = preview
        self.track = None
        self.drag_note = None          # nota, kterou právě prodlužujeme tažením
        self.drag_velocity = False     # táhneme v pruhu síly úhozu
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_LEFT_DOWN, self._on_down)
        self.Bind(wx.EVT_LEFT_UP, self._on_up)
        self.Bind(wx.EVT_MOTION, self._on_motion)
        self.Bind(wx.EVT_MOUSEWHEEL, self._on_wheel)
        self.Bind(wx.EVT_SIZE, lambda e: self.Refresh())

    def pattern(self):
        return self.track.patterns[self.track.current]

    # --- převod poloha <-> krok a nota ---

    def _vel_top(self):
        """Horní okraj pruhu se silou úhozu."""
        return self.GetClientSize()[1] - VEL_H

    def _cell(self):
        w, _ = self.GetClientSize()
        grid_h = self._vel_top() - VEL_GAP - HEADER_H
        return (w - LABEL_W) / self.pattern().steps(), grid_h / ROWS

    def _step_at(self, x):
        """Krok pod myší (může být i mimo pattern, kontroluje volající)."""
        cell_w, _ = self._cell()
        return int((x - LABEL_W) // cell_w)

    def _at(self, x, y):
        """(krok, nota) pod myší, nebo None mimo mřížku."""
        _, cell_h = self._cell()
        step = self._step_at(x)
        row = int((y - HEADER_H) // cell_h)
        if x < LABEL_W or y < HEADER_H or not (0 <= step < self.pattern().steps()) or not (0 <= row < ROWS):
            return None
        return step, self.track.view_low + ROWS - 1 - row

    def _set_velocity(self, x, y):
        """Síla úhozu podle výšky myši v pruhu (nahoře 127, dole 1) všem notám začínajícím na kroku pod myší."""
        step = self._step_at(x)
        unit = min(1.0, max(0.0, 1 - (y - self._vel_top()) / VEL_H))
        velocity = round(1 + unit * 126)
        for note in self.pattern().notes:
            if note.step == step:
                note.velocity = velocity
        self.Refresh()

    # --- myš ---

    def _on_down(self, event):
        x, y = event.GetX(), event.GetY()
        if x >= LABEL_W and y >= self._vel_top():
            self.drag_velocity = True
            self._set_velocity(x, y)
            self.CaptureMouse()
            return
        found = self._at(x, y)
        if found is None:
            return
        step, pitch = found
        pattern = self.pattern()
        note = pattern.note_at(step, pitch)
        if note:
            pattern.notes.remove(note)
        else:
            self.drag_note = Note(step, pitch, 1)
            pattern.notes.append(self.drag_note)
            self.preview(pitch)
            self.CaptureMouse()
        self.Refresh()

    def _on_motion(self, event):
        if self.drag_velocity:
            self._set_velocity(event.GetX(), event.GetY())
            return
        if self.drag_note is None:
            return
        step = self._step_at(event.GetX())
        end = min(max(step, self.drag_note.step), self.pattern().steps() - 1)
        self.drag_note.length = end - self.drag_note.step + 1
        self.Refresh()

    def _on_up(self, event):
        if self.HasCapture():
            self.ReleaseMouse()
        self.drag_note = None
        self.drag_velocity = False

    def _on_wheel(self, event):
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

        # řádky: černé klávesy tmavší, u každého C název
        gc.SetFont(theme.font(9), theme.TEXT_DIM)
        for row in range(ROWS):
            pitch = self.track.view_low + ROWS - 1 - row
            y = HEADER_H + row * cell_h
            if pitch % 12 in BLACK:
                gc.SetBrush(wx.Brush(theme.BACKGROUND))
                gc.SetPen(wx.TRANSPARENT_PEN)
                gc.DrawRectangle(LABEL_W, y, w - LABEL_W, cell_h)
            if pitch % 12 == 0:
                gc.DrawText(note_name(pitch), 6, y + (cell_h - 12) / 2)
                gc.SetPen(wx.Pen(theme.BORDER, 1))
                gc.StrokeLine(LABEL_W, y + cell_h, w, y + cell_h)

        # sloupce: slabě každý krok, víc každá doba, nejvíc každý takt (v mřížce i v pruhu Vel)
        per_beat = pattern.grid // BEATS_PER_BAR        # kroků na dobu: 4, 3 nebo 6
        for step in range(pattern.steps() + 1):
            x = LABEL_W + step * cell_w
            strong = step % pattern.grid == 0
            gc.SetPen(wx.Pen(theme.TEXT_DIM if strong else theme.BORDER if step % per_beat == 0 else theme.GRID, 1))
            gc.StrokeLine(x, HEADER_H, x, grid_bottom)
            gc.StrokeLine(x, vel_top, x, h)
            if step % per_beat == 0 and step < pattern.steps():
                bar, beat = divmod(step // per_beat, BEATS_PER_BAR)
                gc.DrawText(f"{bar + 1}.{beat + 1}", x + 3, 3)

        # pruh síly úhozu: oddělovací čára a popisek
        gc.SetPen(wx.Pen(theme.BORDER, 1))
        gc.StrokeLine(LABEL_W, vel_top, w, vel_top)
        gc.DrawText("Vel", 6, vel_top + (VEL_H - 12) / 2)

        # ukazatel přehrávání (jen v režimu Loop, kde hraje tenhle pattern); position je v tikách
        if self.player.playing and self.player.mode == "Loop":
            step = self.player.position // pattern.ticks_per_step() % pattern.steps()
            x = LABEL_W + step * cell_w
            gc.SetBrush(wx.Brush(wx.Colour(255, 255, 255, 25)))
            gc.SetPen(wx.TRANSPARENT_PEN)
            gc.DrawRectangle(x, HEADER_H, cell_w, h - HEADER_H)

        # noty: čím slabší úhoz, tím průhlednější (tlumenější)
        gc.SetPen(wx.Pen(theme.BACKGROUND, 1))
        for note in list(pattern.notes):
            alpha = 60 + round(195 * note.velocity / 127)
            colour = wx.Colour(theme.ACCENT.Red(), theme.ACCENT.Green(), theme.ACCENT.Blue(), alpha)
            row = self.track.view_low + ROWS - 1 - note.pitch
            if 0 <= row < ROWS:
                gc.SetBrush(wx.Brush(colour))
                gc.DrawRoundedRectangle(LABEL_W + note.step * cell_w + 1, HEADER_H + row * cell_h + 1,
                                        note.length * cell_w - 2, cell_h - 2, 3)

        # sloupky síly úhozu na začátku každé noty (i not mimo zobrazené výšky)
        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.SetBrush(wx.Brush(theme.ACCENT))
        bar_w = max(2, min(6, cell_w - 2))
        for note in list(pattern.notes):
            bar_h = (VEL_H - 4) * note.velocity / 127
            gc.DrawRectangle(LABEL_W + note.step * cell_w + 1, h - bar_h, bar_w, bar_h)
