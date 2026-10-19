"""Editor patternu (piano roll): mřížka, svisle výšky not, vodorovně kroky (šestnáctiny).

Ovládání:
 - klik do prázdného místa přidá notu (a přehraje ji), tažením doprava se prodlouží
 - klik na notu ji smaže
 - kolečko myši posune zobrazené výšky nahoru a dolů
"""

import wx

from sirens.song import STEPS_PER_BAR, Note
from sirens.ui import theme
from sirens.ui.keys import note_name

ROWS = 24          # zobrazené výšky (2 oktávy)
LABEL_W = 44       # místo vlevo pro názvy not
HEADER_H = 20      # místo nahoře pro čísla dob
BLACK = {1, 3, 6, 8, 10}    # půltóny černých kláves v oktávě


class PatternView(wx.Control):
    def __init__(self, parent, player, preview):
        """preview(nota): krátce zahraje notu vybrané stopy (při přidání)."""
        super().__init__(parent, style=wx.BORDER_NONE)
        self.player = player
        self.preview = preview
        self.track = None
        self.drag_note = None          # nota, kterou právě prodlužujeme tažením
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

    def _cell(self):
        w, h = self.GetClientSize()
        return (w - LABEL_W) / self.pattern().steps(), (h - HEADER_H) / ROWS

    def _at(self, x, y):
        """(krok, nota) pod myší, nebo None mimo mřížku."""
        cell_w, cell_h = self._cell()
        step = int((x - LABEL_W) // cell_w)
        row = int((y - HEADER_H) // cell_h)
        if x < LABEL_W or y < HEADER_H or not (0 <= step < self.pattern().steps()) or not (0 <= row < ROWS):
            return None
        return step, self.track.view_low + ROWS - 1 - row

    # --- myš ---

    def _on_down(self, event):
        found = self._at(event.GetX(), event.GetY())
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
        if self.drag_note is None:
            return
        cell_w, _ = self._cell()
        step = int((event.GetX() - LABEL_W) // cell_w)
        end = min(max(step, self.drag_note.step), self.pattern().steps() - 1)
        self.drag_note.length = end - self.drag_note.step + 1
        self.Refresh()

    def _on_up(self, event):
        if self.HasCapture():
            self.ReleaseMouse()
        self.drag_note = None

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

        # sloupce: slabě každý krok, víc každá doba (4 kroky), nejvíc každý takt
        for step in range(pattern.steps() + 1):
            x = LABEL_W + step * cell_w
            strong = step % STEPS_PER_BAR == 0
            gc.SetPen(wx.Pen(theme.TEXT_DIM if strong else theme.BORDER if step % 4 == 0 else theme.GRID, 1))
            gc.StrokeLine(x, HEADER_H, x, h)
            if step % 4 == 0 and step < pattern.steps():
                bar, beat = divmod(step // 4, 4)
                gc.DrawText(f"{bar + 1}.{beat + 1}", x + 3, 3)

        # ukazatel přehrávání (jen v režimu Loop, kde hraje tenhle pattern)
        if self.player.playing and self.player.mode == "Loop":
            x = LABEL_W + (self.player.position % pattern.steps()) * cell_w
            gc.SetBrush(wx.Brush(wx.Colour(255, 255, 255, 25)))
            gc.SetPen(wx.TRANSPARENT_PEN)
            gc.DrawRectangle(x, HEADER_H, cell_w, h - HEADER_H)

        # noty
        gc.SetPen(wx.Pen(theme.BACKGROUND, 1))
        gc.SetBrush(wx.Brush(theme.ACCENT))
        for note in pattern.notes:
            row = self.track.view_low + ROWS - 1 - note.pitch
            if 0 <= row < ROWS:
                gc.DrawRoundedRectangle(LABEL_W + note.step * cell_w + 1, HEADER_H + row * cell_h + 1,
                                        note.length * cell_w - 2, cell_h - 2, 3)
