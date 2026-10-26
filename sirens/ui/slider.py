"""Slider jako ve Flipu, kreslenej celej ručně přes wx.GraphicsContext.

Jak vypadá: tmavej pruh, vyplněná část pruhu ukazuje hodnotu, popisek je
uvnitř pruhu, vpravo je rámeček s číslem a za ním jednotka.

    [ Cutoff ███████████░░░░░░░░░ ]  [  1200 ]  Hz
      pruh (vyplněno = hodnota)      rámeček    jednotka

Ovládání:
 - kliknutí / tažení v pruhu nastaví hodnotu podle toho, kde je myš
 - kolečko myši posune hodnotu o 1 % délky pruhu
 - dvojklik v pruhu vrátí výchozí hodnotu
 - kliknutí na číslo otevře políčko, kam se dá napsat přesná hodnota (Enter potvrdí, Esc zruší)
"""

import math

import wx

from sirens.ui import theme

HEIGHT = 28        # výška celýho slideru v pixelech
BOX_WIDTH = 64     # šířka rámečku s číslem
UNIT_WIDTH = 26    # místo pro jednotku (Hz, s, ...)
GAP = 6            # mezera mezi pruhem a rámečkem
RADIUS = 4         # zaoblení rohů


def format_value(value: float, lo: float, hi: float, step: float = 0) -> str:
    """Kolik desetinnejch míst ukázat, podle toho, jak velkej je rozsah (0-2000 Hz vs. 0-1)."""
    if step and step == int(step):
        return f"{value:.0f}"          # celý čísla (oktávy, půltóny, ...)
    span = hi - lo
    if span >= 200:
        return f"{value:.0f}"
    if span >= 20:
        return f"{value:.1f}"
    if span >= 1:
        return f"{value:.2f}"
    return f"{value:.3f}"


# wx.Control = prázdnej ovládací prvek, nic sám nekreslí, všechno (vzhled i myš) si dělám sám
class Slider(wx.Control):
    def __init__(self, parent, label, lo, hi, default, unit="", log=False, on_change=None, value=None,
                 step=0):
        super().__init__(parent, style=wx.BORDER_NONE)
        if log and lo <= 0:
            # logaritmus z nuly nejde, tak radši hned spadnout s jasnou hláškou
            raise ValueError(f"Slider '{label}': logaritmický slider musí začínat nad nulou")
        self.label, self.lo, self.hi, self.default = label, lo, hi, default
        self.unit, self.log = unit, log
        self.step = step             # > 0: hodnota skáče po krocích (např. celý oktávy)
        self.on_change = on_change   # funkce(hodnota), volá se při každý změně
        self.value = default if value is None else value
        self.hot = False             # je myš nad sliderem? (pruh se trochu zesvětlí)
        self.editor = None           # textový políčko, když se zrovna píše hodnota

        # BG_STYLE_PAINT = pozadí si mažu sám v _on_paint, ať wx nemaže zvlášť a nebliká to
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.SetMinSize((-1, HEIGHT))    # šířku určí sizer v panelu, výška je pevná
        # napojení událostí: EVT_PAINT = "nakresli se", ostatní je myš
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_LEFT_DOWN, self._on_down)
        self.Bind(wx.EVT_LEFT_UP, self._on_up)
        self.Bind(wx.EVT_MOTION, self._on_motion)
        self.Bind(wx.EVT_MOUSEWHEEL, self._on_wheel)
        self.Bind(wx.EVT_LEFT_DCLICK, self._on_double_click)
        self.Bind(wx.EVT_ENTER_WINDOW, lambda e: self._set_hot(True))    # myš vjela nad slider
        self.Bind(wx.EVT_LEAVE_WINDOW, lambda e: self._set_hot(False))   # a zase odjela

    # --- převod hodnota <-> poloha 0..1 ---
    # Poloha 0 = úplně vlevo, 1 = úplně vpravo.
    # Lineárně: poloha = kolik procent rozsahu je od lo k hodnotě.
    # Logaritmicky: stejnej kus pruhu = stejnej poměr hodnot (20->200 Hz je stejně
    # dlouhý jako 200->2000 Hz). Tak totiž slyšíme výšku tónu, jinak by celá
    # spodní půlka slyšitelnýho pásma byla namačkaná na kraji pruhu.

    def _to_pos(self, value: float) -> float:
        if self.log:
            return math.log(value / self.lo) / math.log(self.hi / self.lo)
        return (value - self.lo) / (self.hi - self.lo)

    def _from_pos(self, pos: float) -> float:
        # opačnej směr než _to_pos, poloha se nejdřív ořízne do 0..1 (myš může bejt mimo pruh)
        pos = min(1.0, max(0.0, pos))
        if self.log:
            return self.lo * (self.hi / self.lo) ** pos
        return self.lo + pos * (self.hi - self.lo)

    def set_value(self, value: float):
        # sem vede všechno: myš, kolečko, dvojklik i napsaný číslo
        if self.step:
            # zaokrouhlit na nejbližší krok počítanej od lo (třeba 4, 8, 12, ...)
            value = self.lo + round((value - self.lo) / self.step) * self.step
        self.value = min(self.hi, max(self.lo, value))   # nikdy mimo rozsah
        self.Refresh()     # Refresh nekreslí hned, jen řekne "tohle je potřeba překreslit", pak přijde EVT_PAINT
        if self.on_change:
            self.on_change(self.value)

    # --- rozložení: pruh | rámeček s číslem | jednotka ---
    # obdélníky jako (x, y, šířka, výška); počítá se pokaždý znova, protože se okno dá roztáhnout

    def _bar_rect(self):
        w, h = self.GetClientSize()
        return 0, 0, max(10, w - BOX_WIDTH - UNIT_WIDTH - GAP), h   # pruh = zbytek po rámečku a jednotce

    def _box_rect(self):
        bx, _, bw, h = self._bar_rect()
        return bx + bw + GAP, 0, BOX_WIDTH, h

    def _in_box(self, x: int) -> bool:
        return x >= self._box_rect()[0]   # cokoli vpravo od začátku rámečku se bere jako rámeček

    # --- myš ---

    def _set_hot(self, hot: bool):
        self.hot = hot
        self.Refresh()

    def _set_from_mouse(self, x: int):
        # x myši (v pixelech od levýho kraje slideru) -> poloha 0..1 v pruhu -> hodnota
        bx, _, bw, _ = self._bar_rect()
        self.set_value(self._from_pos((x - bx) / bw))

    def _on_down(self, event):
        if self._in_box(event.GetX()):
            self._start_edit()
            return
        self._set_from_mouse(event.GetX())
        # CaptureMouse = posílej mi pohyby myši, i když vyjede ze slideru ven,
        # dokud ji nepustím (jinak by se tažení zaseklo, jakmile myš ujede kousek vedle)
        self.CaptureMouse()

    def _on_up(self, event):
        if self.HasCapture():
            self.ReleaseMouse()    # capture se musí zase pustit, jinak by si slider myš držel dál

    def _on_motion(self, event):
        # Kurzor napoví, co se dá dělat: šipky = táhnout, I = psát.
        self.SetCursor(wx.Cursor(wx.CURSOR_IBEAM if self._in_box(event.GetX()) else wx.CURSOR_SIZEWE))
        if event.Dragging() and self.HasCapture():   # táhne se jen tehdy, když to začalo v pruhu
            self._set_from_mouse(event.GetX())

    def _on_wheel(self, event):
        # posun o 1 % polohy, ne hodnoty, takže u log slideru je krok taky "logaritmickej"
        direction = 1 if event.GetWheelRotation() > 0 else -1
        self.set_value(self._from_pos(self._to_pos(self.value) + direction * 0.01))

    def _on_double_click(self, event):
        if not self._in_box(event.GetX()):
            self.set_value(self.default)

    # --- psaní přesný hodnoty ---
    # Na chvíli se přes rámeček položí opravdový wx.TextCtrl, po Enteru zase zmizí.

    def _start_edit(self):
        if self.editor:
            return
        x, y, w, h = self._box_rect()
        # TE_PROCESS_ENTER = Enter pošle EVT_TEXT_ENTER, TE_RIGHT = číslo zarovnaný doprava jako v rámečku
        self.editor = wx.TextCtrl(self, value=format_value(self.value, self.lo, self.hi, self.step),
                                  pos=(x + 4, y + 5), size=(w - 8, h - 10),
                                  style=wx.TE_PROCESS_ENTER | wx.TE_RIGHT | wx.BORDER_NONE)
        self.editor.SetBackgroundColour(theme.VALUE_BOX)
        self.editor.SetForegroundColour(theme.TEXT)
        self.editor.SetFont(theme.font(11, bold=True))
        self.editor.Bind(wx.EVT_TEXT_ENTER, lambda e: self._finish_edit(True))
        self.editor.Bind(wx.EVT_KILL_FOCUS, lambda e: self._finish_edit(True))   # kliknutí jinam = taky potvrdit
        # CHAR_HOOK chytí klávesu dřív než políčko samo, jinak by se Esc nedal zachytit
        self.editor.Bind(wx.EVT_CHAR_HOOK, self._on_editor_key)
        self.editor.SelectAll()
        self.editor.SetFocus()     # fokus = kam jdou klávesy, ať se dá hned psát

    def _on_editor_key(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self._finish_edit(False)
        else:
            event.Skip()            # ostatní klávesy normálně do políčka

    def _finish_edit(self, commit: bool):
        editor, self.editor = self.editor, None
        if editor is None:      # už je hotovo (Enter i ztráta fokusu přijdou oba, druhej se ignoruje)
            return
        text = editor.GetValue().replace(",", ".")   # povolíme i českou čárku
        wx.CallAfter(editor.Destroy)  # políčko nejde zrušit uvnitř jeho vlastní události, CallAfter = až po ní
        if commit:
            try:
                self.set_value(float(text))
            except ValueError:
                pass            # nesmysl ignorujeme, hodnota zůstane jak byla
        self.Refresh()

    # --- kreslení ---
    # Volá se při EVT_PAINT, pokaždý se nakreslí celej slider od nuly.

    def _on_paint(self, event):
        # DC (device context) = "plátno", na který se kreslí. AutoBuffered = kreslí se nejdřív
        # do paměti a na obrazovku až hotový obrázek, takže to nebliká.
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(self.GetParent().GetBackgroundColour()))   # pozadí stejný jako panel pod tím
        dc.Clear()
        # GraphicsContext = lepší kreslení nad DC: vyhlazený hrany, zaoblený rohy, desetinný souřadnice
        gc = wx.GraphicsContext.Create(dc)
        gc.SetPen(wx.TRANSPARENT_PEN)      # pen = obrys, brush = výplň; tady obrys žádnej

        # pruh: nejdřív celá dráha, přes ni vyplněná část podle hodnoty
        bx, by, bw, bh = self._bar_rect()
        gc.SetBrush(wx.Brush(theme.SLIDER_TRACK))
        gc.DrawRoundedRectangle(bx, by, bw, bh, RADIUS)
        fill = bw * self._to_pos(self.value)   # kolik pixelů je vyplněno
        if fill > 1:
            gc.SetBrush(wx.Brush(theme.SLIDER_FILL_HOT if self.hot else theme.SLIDER_FILL))
            gc.DrawRoundedRectangle(bx, by, fill, bh, min(RADIUS, fill / 2))   # u malý výplně menší zaoblení, jinak by se rozbila
            if 2 * RADIUS < fill < bw - RADIUS:
                gc.DrawRectangle(bx + fill - RADIUS, by, RADIUS, bh)  # pravej okraj výplně rovně, ne kulatě
        gc.SetFont(theme.font(11), theme.TEXT_MUTED)
        _, th = gc.GetTextExtent(self.label)
        gc.DrawText(self.label, bx + 10, by + (bh - th) / 2)   # popisek svisle na střed

        # rámeček s číslem (když se zrovna píše, číslo kreslí textový políčko, ne my)
        x, y, w, h = self._box_rect()
        gc.SetPen(wx.Pen(theme.BORDER, 1))
        gc.SetBrush(wx.Brush(theme.VALUE_BOX))
        gc.DrawRoundedRectangle(x + 0.5, y + 0.5, w - 1, h - 1, RADIUS)   # +0.5 = čára 1 px přesně na pixel, jinak je rozmazaná
        if not self.editor:
            text = format_value(self.value, self.lo, self.hi, self.step)
            gc.SetFont(theme.font(11, bold=True), theme.TEXT)
            tw, th = gc.GetTextExtent(text)
            gc.DrawText(text, x + w - tw - 8, y + (h - th) / 2)   # zarovnaný doprava

        # jednotka
        gc.SetFont(theme.font(10), theme.TEXT_DIM)
        _, th = gc.GetTextExtent(self.unit or " ")   # " ": u prázdný jednotky by výška vyšla 0
        gc.DrawText(self.unit, x + w + 5, y + (h - th) / 2)
