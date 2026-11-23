"""Pravej panel s ovládáním (jako v Event Horizon / Flipu).

Nahoře může bejt pevná část (třeba hlasitost výstupu), ta se neposouvá,
pod ní je posuvná část: skupiny s nadpisem a pod sebou slidery, každej
s krátkým vysvětlením.

Důležitý: panel sám o zvuku ani obrazu nic neví. Jen staví ovládací
prvky a když se něco změní, zavolá funkci, kterou mu někdo dal (on_change).
Díky tomu je stejnej pro všechny záložky.

    +----------------------+
    | OUTPUT               |  pevná část (with_fixed=True)
    | [Master ████░░] 0.50 |
    |----------------------|  divider
    | TRACK     Copy sound |  add_group s actions
    | Edit  [Track 1  v]   |  add_dropdown
    | ENVELOPE             |
    | [Attack ██░░░] 0.01 s|  add_slider / add_params
    | šedý vysvětlení ...  |  help
    | [Add block]          |  add_button
    +----------------------+  (tohle celý se posouvá)
"""

import wx

from sirens.ui import theme
from sirens.ui.slider import Slider
from sirens.ui.widgets import Caption, ChoiceRow, PillButton, TextButton

WIDTH = 340      # pevná šířka panelu
PADDING = 16     # odsazení obsahu od okrajů panelu


def divider(parent, vertical: bool = False) -> wx.Panel:
    """Tenká čára mezi skupinami (nebo svislá mezi obsahem a panelem).

    Je to vlastně jen panel 1 px širokej (nebo vysokej) s barvou okraje,
    druhej rozměr (-1) dopočítá sizer, když ho přidáme s wx.EXPAND.
    """
    line = wx.Panel(parent, size=(1, -1) if vertical else (-1, 1))
    line.SetBackgroundColour(theme.BORDER)
    return line


class Sidebar(wx.Panel):
    def __init__(self, parent, with_fixed: bool = False):
        super().__init__(parent)
        self.SetBackgroundColour(theme.SIDEBAR)
        self.SetMinSize((WIDTH, -1))
        column = wx.BoxSizer(wx.VERTICAL)

        # pevná část, ta se při clear() nemaže
        self.fixed = self.fixed_sizer = None
        if with_fixed:
            self.fixed = wx.Panel(self)
            self.fixed.SetBackgroundColour(theme.SIDEBAR)
            self.fixed_sizer = wx.BoxSizer(wx.VERTICAL)
            self.fixed.SetSizer(self.fixed_sizer)
            column.Add(self.fixed, 0, wx.EXPAND | wx.BOTTOM, PADDING)   # 0 = jen tak vysoká, jak potřebuje
            column.Add(divider(self), 0, wx.EXPAND)

        # posuvná část
        # ScrolledWindow = panel s posuvníkem, když se obsah nevejde
        self.scroll = wx.ScrolledWindow(self)
        self.scroll.SetBackgroundColour(theme.SIDEBAR)
        self.scroll.SetScrollRate(0, 12)     # vodorovně neposouvat, svisle po 12 px
        self.scroll_sizer = wx.BoxSizer(wx.VERTICAL)
        self.scroll.SetSizer(self.scroll_sizer)
        column.Add(self.scroll, 1, wx.EXPAND)    # 1 = vezme všechno místo, co zbyde
        self.SetSizer(column)

    def _area(self, fixed: bool):
        # kam přidávat: (rodič, sizer) pevný nebo posuvný části.
        # Prvek musí mít za rodiče ten samej panel, do jehož sizeru se přidává.
        return (self.fixed, self.fixed_sizer) if fixed else (self.scroll, self.scroll_sizer)

    def add_group(self, title: str, fixed: bool = False, actions=()):
        """Nadpis nový skupiny, od tý předchozí ji oddělí čára.

        actions: malý textový tlačítka vpravo od nadpisu, seznam (popisek, funkce).
        """
        parent, sizer = self._area(fixed)
        if sizer.GetItemCount() > 0:     # první skupina čáru nad sebou nemá
            sizer.Add(divider(parent), 0, wx.EXPAND | wx.TOP, PADDING)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(Caption(parent, title), 1, wx.ALIGN_CENTER_VERTICAL)   # nadpis roztáhnout, tlačítka odtlačí doprava
        for label, on_click in actions:
            row.Add(TextButton(parent, label, on_click), 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 8)
        sizer.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, PADDING)

    def add_slider(self, label, lo, hi, default, unit="", log=False, help="",
                   on_change=None, value=None, fixed=False, step=0) -> Slider:
        """Slider a pod ním (když je) šedý vysvětlení, co dělá.

        value: počáteční hodnota, když se liší od výchozí (po překreslení panelu).
        """
        parent, sizer = self._area(fixed)
        slider = Slider(parent, label, lo, hi, default, unit, log, on_change, value, step)
        sizer.AddSpacer(12)              # mezera 12 px nad sliderem
        sizer.Add(slider, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, PADDING)
        if help:
            self._add_help(parent, sizer, help)
        return slider

    def add_params(self, owner, fixed: bool = False):
        """Slidery pro všechny PARAMS objektu owner (blok zvuku, vrstva obrazu).

        Pohyb slideru zavolá owner.set(popisek, hodnota). Tohle je ten trik,
        proč panel nic neví o zvuku: jen projde seznam PARAMS a pro každej
        udělá slider (nebo řadu tlačítek, když má choices).
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
        """Řada tlačítek s možnostma (vybrat jde vždycky jen jedna)."""
        parent, sizer = self._area(fixed)
        sizer.AddSpacer(12)
        sizer.Add(ChoiceRow(parent, label, options, index, on_change), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, PADDING)
        if help:
            self._add_help(parent, sizer, help)

    def add_button(self, label: str, on_click, fixed: bool = False) -> PillButton:
        parent, sizer = self._area(fixed)
        button = PillButton(parent, label, on_click)
        sizer.Add(button, 0, wx.LEFT | wx.RIGHT | wx.TOP, PADDING)   # bez EXPAND, tlačítko má svoji šířku
        return button

    def add_text(self, label: str, value: str, on_change, help: str = "", fixed: bool = False):
        """Textový políčko s popiskem (třeba IP adresa). on_change(text) při každý změně."""
        parent, sizer = self._area(fixed)
        field = wx.TextCtrl(parent, value=value, style=wx.BORDER_SIMPLE)
        field.SetBackgroundColour(theme.VALUE_BOX)
        field.SetForegroundColour(theme.TEXT)
        field.SetFont(theme.font(11))
        # EVT_TEXT přijde po každým napsaným písmenu, strip() ořízne mezery na krajích
        field.Bind(wx.EVT_TEXT, lambda e: on_change(field.GetValue().strip()))
        self._add_labelled(parent, sizer, label, field, help)

    def add_dropdown(self, label: str, options, index: int, on_change, help: str = "", fixed: bool = False):
        """Rozbalovací seznam s popiskem. on_change(pořadí vybraný položky)."""
        parent, sizer = self._area(fixed)
        choice = wx.Choice(parent, choices=list(options))   # tady normální nativní wx prvek, kreslit to ručně by byla zbytečná práce
        if options:
            choice.SetSelection(index)
        choice.Bind(wx.EVT_CHOICE, lambda e: on_change(choice.GetSelection()))
        self._add_labelled(parent, sizer, label, choice, help)

    def _add_labelled(self, parent, sizer, label: str, control, help: str):
        """Popisek vlevo, prvek (políčko, seznam) vpravo, pod nima vysvětlení."""
        caption = wx.StaticText(parent, label=label)    # StaticText = obyčejnej text, na kterej se neklikává
        caption.SetForegroundColour(theme.TEXT_MUTED)
        caption.SetFont(theme.font(11))
        caption.SetMinSize((60, -1))     # aspoň 60 px, ať jsou políčka pod sebou zarovnaný
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(caption, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row.Add(control, 1, wx.ALIGN_CENTER_VERTICAL)   # prvek si vezme zbytek řádku
        sizer.AddSpacer(12)
        sizer.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, PADDING)
        if help:
            self._add_help(parent, sizer, help)

    def _add_help(self, parent, sizer, help: str):
        # šedej menší text pod prvkem
        text = wx.StaticText(parent, label=help)
        text.SetForegroundColour(theme.TEXT_DIM)
        text.SetFont(theme.font(10))
        text.Wrap(WIDTH - 2 * PADDING)   # zalomit na šířku panelu bez okrajů, jinak by text utekl doprava
        sizer.AddSpacer(5)
        sizer.Add(text, 0, wx.LEFT | wx.RIGHT, PADDING)

    def add_note(self, text: str, colour=theme.TEXT_DIM) -> wx.StaticText:
        """Volnej text v posuvný části (třeba nápověda u prázdnýho racku)."""
        note = wx.StaticText(self.scroll, label=text)
        note.SetForegroundColour(colour)
        note.SetFont(theme.font(11))
        note.Wrap(WIDTH - 2 * PADDING)
        self.scroll_sizer.Add(note, 0, wx.LEFT | wx.RIGHT | wx.TOP, PADDING)
        return note                      # vrací se, ať jde text pak změnit přes set_note

    def set_note(self, note: wx.StaticText, text: str):
        """Změní text poznámky z add_note (znova ho zalomí a přepočítá rozložení)."""
        note.SetLabel(text)
        note.Wrap(WIDTH - 2 * PADDING)
        self.scroll.Layout()
        self.scroll.FitInside()

    def clear(self):
        """Smaže všechno v posuvný části (než se postaví znova)."""
        # delete_windows=True: smazat i ty prvky samotný, ne jen je vyndat ze sizeru
        self.scroll_sizer.Clear(delete_windows=True)

    def finish(self):
        """Po přidání prvků přepočítá rozložení a posuvník, volat vždycky na konci."""
        self.scroll_sizer.AddSpacer(PADDING)   # kousek místa pod posledním prvkem
        if self.fixed:
            self.fixed.Layout()
        self.scroll.Layout()
        self.scroll.FitInside()          # FitInside = řekne posuvníku, jak vysokej je teď obsah
        self.Layout()
