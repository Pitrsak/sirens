"""Záložka Visual: obraz složený z vrstev, který reaguje na zvuk.

Vrstvy se přidávají a nastavují stejně jako bloky zvuku. Tlačítko Fullscreen
otevře obraz přes celou obrazovku (na projektor); Esc nebo dvojklik ho zavře.
"""

import wx

from sirens.ui import theme
from sirens.ui.sidebar import Sidebar, divider
from sirens.ui.stack_editor import StackEditor
from sirens.ui.views import VisualView
from sirens.visual.layers import CATALOG
from sirens.visual.painter import Painter


class FullscreenWindow(wx.Frame):
    """Samostatné okno přes celou obrazovku jen s obrazem.

    Je-li připojená druhá obrazovka (projektor), otevře se na ní,
    jinak na té, kde je hlavní okno.
    """

    def __init__(self, main_window, on_close):
        super().__init__(None, title="Sirens visual")
        self.on_close = on_close
        self.bitmap = None
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_CHAR_HOOK, self._on_key)
        self.Bind(wx.EVT_LEFT_DCLICK, lambda e: self.Close())
        self.Bind(wx.EVT_CLOSE, self._on_close)

        main_display = wx.Display.GetFromWindow(main_window)
        target = main_display
        for index in range(wx.Display.GetCount()):
            if index != main_display:
                target = index           # první jiná obrazovka než ta s hlavním oknem
                break
        self.SetSize(wx.Display(max(target, 0)).GetGeometry())
        # Na macOS ShowFullScreen skryté okno neukáže: nejdřív Show(), pak přes celou obrazovku.
        self.Show()
        self.ShowFullScreen(True)
        self.Raise()

    def show(self, image):
        height, width = image.shape[:2]
        self.bitmap = wx.Bitmap.FromBuffer(width, height, image)
        self.Refresh(False)

    def _on_paint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.BLACK_BRUSH)
        dc.Clear()
        if self.bitmap is None:
            return
        gc = wx.GraphicsContext.Create(dc)
        w, h = self.GetClientSize()
        bw, bh = self.bitmap.GetSize()
        scale = min(w / bw, h / bh)
        gc.DrawBitmap(self.bitmap, (w - bw * scale) / 2, (h - bh * scale) / 2, bw * scale, bh * scale)

    def _on_key(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.Close()
        else:
            event.Skip()

    def _on_close(self, event):
        self.on_close()
        event.Skip()


class VisualPage(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        self.SetBackgroundColour(theme.BACKGROUND)
        self.painter = Painter()
        self.view = VisualView(self)
        self.fullscreen = None

        self.sidebar = Sidebar(self, with_fixed=True)
        self.sidebar.add_group("Visual", fixed=True)
        self.sidebar.add_button("Fullscreen", self._open_fullscreen, fixed=True)
        self.editor = StackEditor(self.sidebar, "Add layer", CATALOG, self.refresh)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(self.view, 1, wx.EXPAND | wx.ALL, 20)
        row.Add(divider(self, vertical=True), 0, wx.EXPAND)
        row.Add(self.sidebar, 0, wx.EXPAND)
        self.SetSizer(row)
        self.refresh()

    def refresh(self):
        """Postaví panel s vrstvami podle aktuálního stavu (i po otevření souboru)."""
        self.sidebar.clear()
        self.editor.show(self.painter, "Empty: the picture is black. Add shapes (Ring, Wave, Bars, ...) "
                                       "and effects below them. Put Feedback at the top for trails.")
        self.sidebar.finish()

    def _open_fullscreen(self):
        if self.fullscreen is None:
            self.fullscreen = FullscreenWindow(self.GetTopLevelParent(), self._fullscreen_closed)
        else:
            self.fullscreen.Raise()

    def _fullscreen_closed(self):
        self.fullscreen = None

    def tick(self, analyzer, dt: float):
        """Každý snímek: spočítá další obraz a ukáže ho (v záložce i na celé obrazovce)."""
        image = self.painter.render(analyzer, dt)
        if self.IsShown():
            self.view.show(image)
        if self.fullscreen is not None:
            self.fullscreen.show(image)
