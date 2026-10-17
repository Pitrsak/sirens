"""Hlavní okno: horní lišta s presety, záložky SYNTH / SPECTRUM / VISUAL, klaviatura dole.

Časovač běží ~30x za sekundu, čte analýzu zvuku a překresluje viditelnou záložku.
"""

import time

import wx

from fathom.audio.params import SYNTH_DEFAULTS, SYNTH_SECTIONS
from fathom.presets import PresetStore
from fathom.ui import theme
from fathom.ui.keyboard import PianoStrip
from fathom.ui.panels import ImageView, KnobBoard
from fathom.visual.abstract import VISUAL_DEFAULTS, VISUAL_PARAMS, AbstractVisual
from fathom.visual.spectrum import SpectrumVisual

FPS = 30
TAB_SYNTH, TAB_SPECTRUM, TAB_VISUAL = range(3)


class MainFrame(wx.Frame):
    def __init__(self, engine):
        super().__init__(None, title="Fathom", size=(1100, 760))
        self.engine = engine
        self.synth = engine.synth
        self.presets = PresetStore()
        self.spectrum = SpectrumVisual()
        self.abstract = AbstractVisual()
        self.synth.listeners.append(self.abstract.on_note)

        root = wx.Panel(self)
        root.SetBackgroundColour(theme.BACKGROUND)
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(self._build_top_bar(root), 0, wx.EXPAND | wx.ALL, 8)

        self.tabs = wx.Notebook(root)
        self.synth_board = KnobBoard(self.tabs, SYNTH_SECTIONS, self.synth.set)
        self.spectrum_view = ImageView(self.tabs)
        self.tabs.AddPage(self.synth_board, "SYNTH")
        self.tabs.AddPage(self.spectrum_view, "SPECTRUM")
        self.tabs.AddPage(self._build_visual_tab(self.tabs), "VISUAL")
        layout.Add(self.tabs, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        layout.Add(PianoStrip(root, self.synth), 0, wx.EXPAND | wx.ALL, 8)
        root.SetSizer(layout)

        self._last_tick = time.perf_counter()
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_tick, self.timer)
        self.timer.Start(int(1000 / FPS))
        self.Bind(wx.EVT_CLOSE, self._on_close)

        names = self.presets.names()
        if names:
            self._load_preset(names[0])

    # --- stavba UI ---

    def _build_top_bar(self, parent):
        bar = wx.BoxSizer(wx.HORIZONTAL)
        title = wx.StaticText(parent, label="FATHOM")
        title.SetFont(theme.font(14, bold=True))
        title.SetForegroundColour(theme.TEXT)
        self.preset_choice = wx.Choice(parent, choices=self.presets.names())
        self.preset_choice.Bind(wx.EVT_CHOICE, lambda e: self._load_preset(self.preset_choice.GetStringSelection()))
        save = wx.Button(parent, label="Save")
        save.Bind(wx.EVT_BUTTON, self._on_save)
        save_as = wx.Button(parent, label="Save as...")
        save_as.Bind(wx.EVT_BUTTON, self._on_save_as)
        init = wx.Button(parent, label="Init")
        init.Bind(wx.EVT_BUTTON, self._on_init)
        self.octave_label = wx.StaticText(parent, label=self._octave_text(48))
        self.octave_label.SetForegroundColour(theme.TEXT_DIM)

        bar.Add(title, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 24)
        bar.Add(self.preset_choice, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        for button in (save, save_as, init):
            bar.Add(button, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        bar.AddStretchSpacer()
        bar.Add(self.octave_label, 0, wx.ALIGN_CENTER_VERTICAL)
        return bar

    def _build_visual_tab(self, parent):
        page = wx.Panel(parent)
        page.SetBackgroundColour(theme.BACKGROUND)
        self.visual_view = ImageView(page)
        self.visual_board = KnobBoard(page, [("VISUAL", VISUAL_PARAMS)], self.abstract.set)
        self.visual_board.SetMinSize((-1, 130))
        column = wx.BoxSizer(wx.VERTICAL)
        column.Add(self.visual_view, 1, wx.EXPAND)
        column.Add(self.visual_board, 0, wx.EXPAND)
        page.SetSizer(column)
        return page

    def _octave_text(self, base_note):
        return f"Keys A-L play, Z/X octave  |  octave C{base_note // 12 - 1}"

    def on_octave_change(self, base_note):
        self.octave_label.SetLabel(self._octave_text(base_note))

    # --- presety ---

    def _load_preset(self, name):
        data = self.presets.load(name)
        # Chybějící hodnoty doplníme výchozími, aby staré presety fungovaly i po přidání parametrů.
        self.synth_board.set_values({**SYNTH_DEFAULTS, **data.get("synth", {})})
        self.visual_board.set_values({**VISUAL_DEFAULTS, **data.get("visual", {})})
        self.preset_choice.SetStringSelection(name)

    def _current_preset(self):
        return {"synth": self.synth_board.get_values(), "visual": self.visual_board.get_values()}

    def _save(self, name):
        saved = self.presets.save(name, self._current_preset())
        self.preset_choice.SetItems(self.presets.names())
        self.preset_choice.SetStringSelection(saved)

    def _on_save(self, event):
        name = self.preset_choice.GetStringSelection()
        if name:
            self._save(name)
        else:
            self._on_save_as(event)

    def _on_save_as(self, event):
        name = wx.GetTextFromUser("Preset name:", "Save preset", parent=self)
        if name:
            self._save(name)

    def _on_init(self, event):
        self.synth_board.set_values(SYNTH_DEFAULTS)
        self.visual_board.set_values(VISUAL_DEFAULTS)
        self.preset_choice.SetSelection(wx.NOT_FOUND)

    # --- smyčka vykreslování ---

    def _on_tick(self, event):
        now = time.perf_counter()
        dt, self._last_tick = now - self._last_tick, now
        page = self.tabs.GetSelection()
        if page == TAB_SYNTH:
            return                    # na záložce knobů nic nepočítáme, šetříme procesor
        analyzer = self.engine.analyzer
        bands, level = analyzer.bands(), analyzer.level()
        if page == TAB_SPECTRUM:
            self.spectrum_view.show(self.spectrum.render(bands, analyzer.scope()))
        else:
            self.visual_view.show(self.abstract.render(dt, bands, level))

    def _on_close(self, event):
        self.timer.Stop()
        self.engine.close()
        event.Skip()
