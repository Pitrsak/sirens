"""Pravý panel s ovládáním (jako v Event Horizon / Flip).

Volitelně nahoře pevná část (např. hlasitost výstupu), pod ní posuvná část:
skupiny s nadpisem a slidery s krátkým vysvětlením pod sebou.
Panel sám o zvuku, obrazu ani světle nic neví, jen staví ovládací prvky
a při změně volá zadané funkce.
"""

import wx

from sirens.ui import theme
from sirens.ui.slider import Slider
from sirens.ui.widgets import Caption, ChoiceRow, PillButton, TextButton

WIDTH = 340      # pevná šířka panelu
PADDING = 16     # odsazení obsahu od okrajů panelu


def divider(parent, vertical: bool = False) -> wx.Panel:
    """Tenká čára mezi skupinami (nebo svislá mezi obsahem a panelem)."""
    line = wx.Panel(parent, size=(1, -1) if vertical else (-1, 1))
    line.SetBackgroundColour(theme.BORDER)
    return line


class Sidebar(wx.Panel):
    def __init__(self, parent, with_fixed: bool = False):
        super().__init__(parent)
        self.SetBackgroundColour(theme.SIDEBAR)
        self.SetMinSize((WIDTH, -1))
        column = wx.BoxSizer(wx.VERTICAL)

        # pevná část, nemaže se při clear()
        self.fixed = self.fixed_sizer = None
        if with_fixed:
            self.fixed = wx.Panel(self)
            self.fixed.SetBackgroundColour(theme.SIDEBAR)
            self.fixed_sizer = wx.BoxSizer(wx.VERTICAL)
            self.fixed.SetSizer(self.fixed_sizer)
            column.Add(self.fixed, 0, wx.EXPAND | wx.BOTTOM, PADDING)
            column.Add(divider(self), 0, wx.EXPAND)

        # posuvná část
        self.scroll = wx.ScrolledWindow(self)
        self.scroll.SetBackgroundColour(theme.SIDEBAR)
        self.scroll.SetScrollRate(0, 12)
        self.scroll_sizer = wx.BoxSizer(wx.VERTICAL)
        self.scroll.SetSizer(self.scroll_sizer)
        column.Add(self.scroll, 1, wx.EXPAND)
        self.SetSizer(column)

    def _area(self, fixed: bool):
        return (self.fixed, self.fixed_sizer) if fixed else (self.scroll, self.scroll_sizer)

    def add_group(self, title: str, fixed: bool = False, actions=()):
        """Nadpis nové skupiny. Od předchozí skupiny ji oddělí čára.

        actions: malá textová tlačítka vpravo od nadpisu, seznam (popisek, funkce).
        """
        parent, sizer = self._area(fixed)
        if sizer.GetItemCount() > 0:
            sizer.Add(divider(parent), 0, wx.EXPAND | wx.TOP, PADDING)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(Caption(parent, title), 1, wx.ALIGN_CENTER_VERTICAL)
        for label, on_click in actions:
            row.Add(TextButton(parent, label, on_click), 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 8)
        sizer.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, PADDING)

    def add_slider(self, label, lo, hi, default, unit="", log=False, help="",
                   on_change=None, value=None, fixed=False, step=0) -> Slider:
        """Slider a pod ním (volitelně) šedé vysvětlení, co dělá.

        value: počáteční hodnota, pokud se liší od výchozí (po překreslení panelu).
        """
        parent, sizer = self._area(fixed)
        slider = Slider(parent, label, lo, hi, default, unit, log, on_change, value, step)
        sizer.AddSpacer(12)
        sizer.Add(slider, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, PADDING)
        if help:
            self._add_help(parent, sizer, help)
        return slider

    def add_params(self, owner, fixed: bool = False):
        """Slidery pro všechny PARAMS objektu owner (blok, obraz, světlo).

        Pohyb slideru zavolá owner.set(popisek, hodnota).
        """
        for p in owner.PARAMS:
            # label=p.label: lambda si musí zapamatovat tenhle popisek, ne poslední z cyklu
            on_change = lambda v, label=p.label: owner.set(label, v)
            if p.choices:
                self.add_choice(p.label, p.choices, round(owner.get(p.label)), on_change, p.help, fixed)
            else:
                self.add_slider(p.label, p.lo, p.hi, p.default, p.unit, p.log, p.help,
                                on_change=on_change, value=owner.get(p.label), fixed=fixed, step=p.step)

    def add_choice(self, label, options, index, on_change, help="", fixed=False):
        """Řada tlačítek s možnostmi (vybrat jde právě jedna)."""
        parent, sizer = self._area(fixed)
        sizer.AddSpacer(12)
        sizer.Add(ChoiceRow(parent, label, options, index, on_change), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, PADDING)
        if help:
            self._add_help(parent, sizer, help)

    def add_button(self, label: str, on_click, fixed: bool = False) -> PillButton:
        parent, sizer = self._area(fixed)
        button = PillButton(parent, label, on_click)
        sizer.Add(button, 0, wx.LEFT | wx.RIGHT | wx.TOP, PADDING)
        return button

    def add_text(self, label: str, value: str, on_change, help: str = "", fixed: bool = False):
        """Textové políčko s popiskem (např. IP adresa). on_change(text) při každé změně."""
        parent, sizer = self._area(fixed)
        field = wx.TextCtrl(parent, value=value, style=wx.BORDER_SIMPLE)
        field.SetBackgroundColour(theme.VALUE_BOX)
        field.SetForegroundColour(theme.TEXT)
        field.SetFont(theme.font(11))
        field.Bind(wx.EVT_TEXT, lambda e: on_change(field.GetValue().strip()))
        self._add_labelled(parent, sizer, label, field, help)

    def add_dropdown(self, label: str, options, index: int, on_change, help: str = "", fixed: bool = False):
        """Rozbalovací seznam s popiskem. on_change(pořadí vybrané položky)."""
        parent, sizer = self._area(fixed)
        choice = wx.Choice(parent, choices=list(options))
        if options:
            choice.SetSelection(index)
        choice.Bind(wx.EVT_CHOICE, lambda e: on_change(choice.GetSelection()))
        self._add_labelled(parent, sizer, label, choice, help)

    def _add_labelled(self, parent, sizer, label: str, control, help: str):
        """Popisek vlevo, prvek (políčko, seznam) vpravo, pod nimi vysvětlení."""
        caption = wx.StaticText(parent, label=label)
        caption.SetForegroundColour(theme.TEXT_MUTED)
        caption.SetFont(theme.font(11))
        caption.SetMinSize((60, -1))
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(caption, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row.Add(control, 1, wx.ALIGN_CENTER_VERTICAL)
        sizer.AddSpacer(12)
        sizer.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, PADDING)
        if help:
            self._add_help(parent, sizer, help)

    def _add_help(self, parent, sizer, help: str):
        text = wx.StaticText(parent, label=help)
        text.SetForegroundColour(theme.TEXT_DIM)
        text.SetFont(theme.font(10))
        text.Wrap(WIDTH - 2 * PADDING)
        sizer.AddSpacer(5)
        sizer.Add(text, 0, wx.LEFT | wx.RIGHT, PADDING)

    def add_note(self, text: str, colour=theme.TEXT_DIM) -> wx.StaticText:
        """Volný text v posuvné části (např. nápověda u prázdného racku)."""
        note = wx.StaticText(self.scroll, label=text)
        note.SetForegroundColour(colour)
        note.SetFont(theme.font(11))
        note.Wrap(WIDTH - 2 * PADDING)
        self.scroll_sizer.Add(note, 0, wx.LEFT | wx.RIGHT | wx.TOP, PADDING)
        return note

    def clear(self):
        """Smaže všechno v posuvné části (před novým vykreslením)."""
        self.scroll_sizer.Clear(delete_windows=True)

    def finish(self):
        """Po přidání prvků přepočítá rozložení a posuvník."""
        self.scroll_sizer.AddSpacer(PADDING)
        if self.fixed:
            self.fixed.Layout()
        self.scroll.Layout()
        self.scroll.FitInside()
        self.Layout()
