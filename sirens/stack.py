"""Seřazený seznam prvků, které uživatel skládá pod sebe: bloky zvuku, vrstvy obrazu.

Umí přidat, smazat, vyprázdnit a posunout prvek. Po každé změně zavolá
changed(), kde si potomek zařídí, co je potřeba (rack znovu propojí zvuk).
Prvky se tvoří přes create(), protože blok potřebuje svůj nástroj a vrstva ne.
"""


class Stack:
    def __init__(self):
        self.items = []

    def create(self, item_class):
        return item_class()

    def changed(self):
        pass

    def add(self, item_class):
        """Vytvoří nový prvek daného druhu a přidá ho na konec (dolů)."""
        item = self.create(item_class)
        self.items.append(item)
        self.changed()
        return item

    def remove(self, item):
        self.items.remove(item)
        self.changed()

    def clear(self):
        self.items = []
        self.changed()

    def move(self, item, step: int):
        """Posune prvek o step míst (-1 = nahoru, +1 = dolů)."""
        i = self.items.index(item)
        j = i + step
        if 0 <= j < len(self.items):
            self.items[i], self.items[j] = self.items[j], self.items[i]
            self.changed()
