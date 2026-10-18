"""Hlavní okno: hlavička se záložkami a pod ní obsah vybrané záložky.

    +--------------------------------------------------------------+
    | SIRENS   [Sound] [Visual] [Light]                    [Stop]  |
    +--------------------------------------------------------------+
    |  obsah záložky (SoundPage, VisualPage nebo LightPage)        |
    +--------------------------------------------------------------+

Časovač běží 30x za sekundu: vezme nový úsek zvuku z analyzátoru
a předá ho záložkám. Zvuk i světlo běží pořád, obraz se počítá jen
na záložce Visual (jinak by zbytečně zatěžoval počítač).
"""

import wx

from sirens.ui import theme
from sirens.ui.light_page import LightPage
from sirens.ui.sidebar import divider
from sirens.ui.sound_page import SoundPage
from sirens.ui.visual_page import VisualPage
from sirens.ui.widgets import Caption, PillButton

FPS = 30


class MainFrame(wx.Frame):
    def __init__(self, engine):
        super().__init__(None, title="Sirens", size=(1240, 800))
        self.SetMinSize((900, 600))
        self.engine = engine
        self.playing = True

        root = wx.Panel(self)
        root.SetBackgroundColour(theme.BACKGROUND)
        self.sound_page = SoundPage(root, engine)
        self.visual_page = VisualPage(root)
        self.light_page = LightPage(root)
        self.pages = {"Sound": self.sound_page, "Visual": self.visual_page, "Light": self.light_page}

        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(self._build_header(root), 0, wx.EXPAND)
        layout.Add(divider(root), 0, wx.EXPAND)
        for page in self.pages.values():
            layout.Add(page, 1, wx.EXPAND)
        root.SetSizer(layout)
        self._select("Sound")

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_tick, self.timer)
        self.timer.Start(int(1000 / FPS))
        self.Bind(wx.EVT_CLOSE, self._on_close)

    def _build_header(self, parent):
        header = wx.Panel(parent)
        header.SetBackgroundColour(theme.BACKGROUND)
        header.SetMinSize((-1, 56))
        logo = Caption(header, "Sirens", colour=theme.TEXT, size=13, spacing=4)
        logo.SetMinSize((140, 24))

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(logo, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 24)
        self.tabs = {}
        for name in ("Sound", "Visual", "Light"):
            # n=name: lambda si musí zapamatovat tuhle záložku, ne poslední z cyklu
            self.tabs[name] = PillButton(header, name, lambda n=name: self._select(n))
            row.Add(self.tabs[name], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        row.AddStretchSpacer()
        self.play_button = PillButton(header, "Stop", self._toggle_playing)
        row.Add(self.play_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 20)
        header.SetSizer(row)
        return header

    def _select(self, name: str):
        """Ukáže vybranou záložku, ostatní skryje. Vybraná má bílé tlačítko."""
        for tab_name, page in self.pages.items():
            page.Show(tab_name == name)
            self.tabs[tab_name].set_primary(tab_name == name)
        page.GetParent().Layout()

    def _toggle_playing(self):
        self.playing = not self.playing
        self.engine.set_playing(self.playing)
        self.play_button.set_label("Stop" if self.playing else "Play")
        self.play_button.GetParent().Layout()

    def _on_tick(self, event):
        analyzer = self.engine.analyzer
        if analyzer.update() and self.sound_page.IsShown():
            self.sound_page.tick(analyzer)
        if self.visual_page.IsShown():
            self.visual_page.tick(analyzer)
        self.light_page.tick(analyzer)

    def _on_close(self, event):
        self.timer.Stop()
        self.light_page.close()
        self.engine.close()
        event.Skip()
