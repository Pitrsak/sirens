"""Seřazenej seznam prvků, který uživatel skládá pod sebe: bloky zvuku, vrstvy obrazu.

Umí přidat, smazat, vyprázdnit, posunout a vypnout / zapnout prvek. Po každý změně
zavolá changed(), kde si potomek zařídí, co je potřeba (rack třeba znovu propojí zvuk).
Prvky se tvoří přes create(), protože blok potřebuje svůj nástroj a vrstva ne,
takže si to každej potomek udělá po svým.
"""


class Stack:
    def __init__(self):
        self.items = []     # pořadí = pořadí na obrazovce, shora dolů

    # potomek přepíše, když prvek potřebuje něco do začátku (Rack dává bloku nástroj)
    def create(self, item_class):
        return item_class()

    # tady nic, potomek si to přepíše (Rack tu znovu propojí bloky)
    def changed(self):
        pass

    def add(self, item_class):
        """Vytvoří novej prvek daného druhu a přidá ho na konec (dolů)."""
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

    def toggle(self, item):
        """Vypne nebo zapne prvek. Vypnutej zůstane v seznamu i s nastavením, jen se přeskakuje."""
        item.enabled = not item.enabled
        self.changed()

    def move(self, item, step: int):
        """Posune prvek o step míst (-1 = nahoru, +1 = dolů)."""
        i = self.items.index(item)
        j = i + step
        if 0 <= j < len(self.items):      # na kraji už není kam, tak nic
            # prohození dvou prvků naráz (vpravo se nejdřív vyrobí dvojice, pak se přiřadí)
            self.items[i], self.items[j] = self.items[j], self.items[i]
            self.changed()
