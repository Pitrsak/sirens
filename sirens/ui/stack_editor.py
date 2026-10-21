"""Úprava seznamu bloků nebo vrstev v pravém panelu (stejně pro zvuk i obraz).

Pro každý prvek skupina: nadpis s tlačítky Off / Up / Down / Remove (a případně
Load u Sampleru), pod ním jeho slidery. Off prvek vypne (zůstane i s nastavením),
On ho zase zapne. Na konci tlačítko pro přidání
s menu všech druhů (nahoře zdroje / tvary, pod čarou efekty).
"""

import wx


class StackEditor:
    def __init__(self, sidebar, add_label: str, catalog, on_change):
        """on_change: co udělat po změně seznamu (stránka překreslí panel)."""
        self.sidebar = sidebar
        self.add_label = add_label
        self.catalog = catalog
        self.on_change = on_change
        self.stack = None
        self.add_button = None

    def show(self, stack, empty_hint: str):
        """Přidá do panelu skupiny pro všechny prvky a tlačítko pro přidání."""
        self.stack = stack
        for item in stack.items:
            # i=item: lambda si musí zapamatovat tenhle prvek, ne poslední z cyklu
            actions = [("Off" if item.enabled else "On", lambda i=item: self._later(stack.toggle, i)),
                       ("Up", lambda i=item: self._later(stack.move, i, -1)),
                       ("Down", lambda i=item: self._later(stack.move, i, 1)),
                       ("Remove", lambda i=item: self._later(stack.remove, i))]
            if hasattr(item, "load"):
                actions.insert(0, ("Load", lambda i=item: self._load_file(i)))
            self.sidebar.add_group(item.NAME if item.enabled else f"{item.NAME} (off)", actions=actions)
            note = item.note() if hasattr(item, "note") else ""
            if note:
                self.sidebar.add_note(note)
            self.sidebar.add_params(item)
        if not stack.items:
            self.sidebar.add_note(empty_hint)
        self.add_button = self.sidebar.add_button(self.add_label, self._show_menu)

    def _later(self, action, *args):
        """Provede změnu a překreslí panel, ale až po skončení kliknutí.

        Tlačítko, na které se kliklo, je v panelu, který se teď smaže, a okno
        nejde zrušit uprostřed jeho vlastní události. Proto wx.CallAfter.
        """
        def run():
            action(*args)
            self.on_change()
        wx.CallAfter(run)

    def _show_menu(self):
        menu = wx.Menu()
        previous = None
        for item_class in self.catalog:
            if previous is not None and previous.IS_SOURCE != item_class.IS_SOURCE:
                menu.AppendSeparator()
            entry = menu.Append(wx.ID_ANY, item_class.NAME)
            menu.Bind(wx.EVT_MENU, lambda e, c=item_class: self._later(self.stack.add, c), entry)
            previous = item_class
        self.add_button.PopupMenu(menu, (0, self.add_button.GetSize().height))
        menu.Destroy()

    def _load_file(self, item):
        with wx.FileDialog(self.sidebar, "Load sound", wildcard="Sound files (*.wav;*.aif;*.aiff;*.flac)|"
                           "*.wav;*.aif;*.aiff;*.flac", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            try:
                item.load(dialog.GetPath())
            except Exception as error:      # pyo hlásí nečitelný soubor různými výjimkami
                wx.MessageBox(f"Cannot load this file:\n{error}", "Load", wx.ICON_ERROR)
                return
        wx.CallAfter(self.on_change)     # panel s tlačítkem Load se překreslí až po kliknutí
