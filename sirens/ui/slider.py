"""Slider ve stylu nástroje Flip, kreslený přes wx.GraphicsContext.

Vzhled: tmavý pruh, jehož vyplněná část ukazuje hodnotu, popisek je uvnitř
pruhu, vpravo je rámeček s číslem a za ním jednotka.

Ovládání:
 - kliknutí / tažení v pruhu nastaví hodnotu podle polohy myši
 - kolečko myši posune hodnotu o 1 % rozsahu
 - dvojklik v pruhu vrátí výchozí hodnotu
 - kliknutí na číslo otevře políčko pro zapsání přesné hodnoty (Enter potvrdí, Esc zruší)
"""

import math

import wx

from sirens.ui import theme

HEIGHT = 28        # výška celého slideru v pixelech
BOX_WIDTH = 64     # šířka rámečku s číslem
UNIT_WIDTH = 26    # místo pro jednotku (Hz, s, ...)
GAP = 6            # mezera mezi pruhem a rámečkem
RADIUS = 4         # zaoblení rohů


def format_value(value: float, lo: float, hi: float) -> str:
    """Počet desetinných míst podle velikosti rozsahu (0-2000 Hz vs. 0-1)."""
    span = hi - lo
    if span >= 200:
        return f"{value:.0f}"
    if span >= 20:
        return f"{value:.1f}"
    if span >= 1:
        return f"{value:.2f}"
    return f"{value:.3f}"


class Slider(wx.Control):
    def __init__(self, parent, label, lo, hi, default, unit="", log=False, on_change=None, value=None):
        super().__init__(parent, style=wx.BORDER_NONE)
        if log and lo <= 0:
            raise ValueError(f"Slider '{label}': logaritmický slider musí začínat nad nulou")
        self.label, self.lo, self.hi, self.default = label, lo, hi, default
        self.unit, self.log = unit, log
        self.on_change = on_change   # funkce(hodnota), volá se při každé změně
        self.value = default if value is None else value
        self.hot = False             # je myš nad sliderem? (pruh se trochu zesvětlí)
        self.editor = None           # textové políčko při psaní hodnoty

        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.SetMinSize((-1, HEIGHT))
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_LEFT_DOWN, self._on_down)
        self.Bind(wx.EVT_LEFT_UP, self._on_up)
        self.Bind(wx.EVT_MOTION, self._on_motion)
        self.Bind(wx.EVT_MOUSEWHEEL, self._on_wheel)
        self.Bind(wx.EVT_LEFT_DCLICK, self._on_double_click)
        self.Bind(wx.EVT_ENTER_WINDOW, lambda e: self._set_hot(True))
        self.Bind(wx.EVT_LEAVE_WINDOW, lambda e: self._set_hot(False))

    # --- převod hodnota <-> poloha 0..1 ---
    # Logaritmický průběh: stejný kus pruhu = stejný poměr hodnot (20->200 Hz
    # je stejně dlouhé jako 200->2000 Hz). Tak slyšíme výšku tónu.

    def _to_pos(self, value: float) -> float:
        if self.log:
            return math.log(value / self.lo) / math.log(self.hi / self.lo)
        return (value - self.lo) / (self.hi - self.lo)

    def _from_pos(self, pos: float) -> float:
        pos = min(1.0, max(0.0, pos))
        if self.log:
            return self.lo * (self.hi / self.lo) ** pos
        return self.lo + pos * (self.hi - self.lo)

    def set_value(self, value: float):
        self.value = min(self.hi, max(self.lo, value))
        self.Refresh()
        if self.on_change:
            self.on_change(self.value)

    # --- rozložení: pruh | rámeček s číslem | jednotka ---

    def _bar_rect(self):
        w, h = self.GetClientSize()
        return 0, 0, max(10, w - BOX_WIDTH - UNIT_WIDTH - GAP), h

    def _box_rect(self):
        bx, _, bw, h = self._bar_rect()
        return bx + bw + GAP, 0, BOX_WIDTH, h

    def _in_box(self, x: int) -> bool:
        return x >= self._box_rect()[0]

    # --- myš ---

    def _set_hot(self, hot: bool):
        self.hot = hot
        self.Refresh()

    def _set_from_mouse(self, x: int):
        bx, _, bw, _ = self._bar_rect()
        self.set_value(self._from_pos((x - bx) / bw))

    def _on_down(self, event):
        if self._in_box(event.GetX()):
            self._start_edit()
            return
        self._set_from_mouse(event.GetX())
        self.CaptureMouse()

    def _on_up(self, event):
        if self.HasCapture():
            self.ReleaseMouse()

    def _on_motion(self, event):
        # Kurzor napoví, co se dá dělat: šipky = táhnout, I = psát.
        self.SetCursor(wx.Cursor(wx.CURSOR_IBEAM if self._in_box(event.GetX()) else wx.CURSOR_SIZEWE))
        if event.Dragging() and self.HasCapture():
            self._set_from_mouse(event.GetX())

    def _on_wheel(self, event):
        direction = 1 if event.GetWheelRotation() > 0 else -1
        self.set_value(self._from_pos(self._to_pos(self.value) + direction * 0.01))

    def _on_double_click(self, event):
        if not self._in_box(event.GetX()):
            self.set_value(self.default)

    # --- zápis přesné hodnoty ---

    def _start_edit(self):
        if self.editor:
            return
        x, y, w, h = self._box_rect()
        self.editor = wx.TextCtrl(self, value=format_value(self.value, self.lo, self.hi),
                                  pos=(x + 4, y + 5), size=(w - 8, h - 10),
                                  style=wx.TE_PROCESS_ENTER | wx.TE_RIGHT | wx.BORDER_NONE)
        self.editor.SetBackgroundColour(theme.VALUE_BOX)
        self.editor.SetForegroundColour(theme.TEXT)
        self.editor.SetFont(theme.font(11, bold=True))
        self.editor.Bind(wx.EVT_TEXT_ENTER, lambda e: self._finish_edit(True))
        self.editor.Bind(wx.EVT_KILL_FOCUS, lambda e: self._finish_edit(True))
        self.editor.Bind(wx.EVT_CHAR_HOOK, self._on_editor_key)
        self.editor.SelectAll()
        self.editor.SetFocus()

    def _on_editor_key(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self._finish_edit(False)
        else:
            event.Skip()

    def _finish_edit(self, commit: bool):
        editor, self.editor = self.editor, None
        if editor is None:      # už ukončeno (Enter i ztráta fokusu přijdou oba)
            return
        text = editor.GetValue().replace(",", ".")   # povolíme i českou čárku
        wx.CallAfter(editor.Destroy)  # políčko nelze zrušit uvnitř jeho vlastní události
        if commit:
            try:
                self.set_value(float(text))
            except ValueError:
                pass            # nesmysl ignorujeme, hodnota zůstane
        self.Refresh()

    # --- kreslení ---

    def _on_paint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(self.GetParent().GetBackgroundColour()))
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        gc.SetPen(wx.TRANSPARENT_PEN)

        # pruh: nejdřív celá dráha, přes ni vyplněná část podle hodnoty
        bx, by, bw, bh = self._bar_rect()
        gc.SetBrush(wx.Brush(theme.SLIDER_TRACK))
        gc.DrawRoundedRectangle(bx, by, bw, bh, RADIUS)
        fill = bw * self._to_pos(self.value)
        if fill > 1:
            gc.SetBrush(wx.Brush(theme.SLIDER_FILL_HOT if self.hot else theme.SLIDER_FILL))
            gc.DrawRoundedRectangle(bx, by, fill, bh, min(RADIUS, fill / 2))
            if 2 * RADIUS < fill < bw - RADIUS:
                gc.DrawRectangle(bx + fill - RADIUS, by, RADIUS, bh)  # pravý okraj výplně rovně
        gc.SetFont(theme.font(11), theme.TEXT_MUTED)
        _, th = gc.GetTextExtent(self.label)
        gc.DrawText(self.label, bx + 10, by + (bh - th) / 2)

        # rámeček s číslem (když se zrovna píše, číslo kreslí textové políčko)
        x, y, w, h = self._box_rect()
        gc.SetPen(wx.Pen(theme.BORDER, 1))
        gc.SetBrush(wx.Brush(theme.VALUE_BOX))
        gc.DrawRoundedRectangle(x + 0.5, y + 0.5, w - 1, h - 1, RADIUS)
        if not self.editor:
            text = format_value(self.value, self.lo, self.hi)
            gc.SetFont(theme.font(11, bold=True), theme.TEXT)
            tw, th = gc.GetTextExtent(text)
            gc.DrawText(text, x + w - tw - 8, y + (h - th) / 2)

        # jednotka
        gc.SetFont(theme.font(10), theme.TEXT_DIM)
        _, th = gc.GetTextExtent(self.unit or " ")
        gc.DrawText(self.unit, x + w + 5, y + (h - th) / 2)
