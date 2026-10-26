"""RACK: bloky, ze kterých se skládá zvuk jednoho nástroje, pěkně pod sebou.

uživatel přidává, maže a posouvá bloky v UI (viz stack.py), a po každý změně
rack bloky znovu propojí shora dolů a výsledek předá nástroji.
přidávání, mazání, posun a vypínání umí už Stack, tady je jen to, co je speciální pro zvuk.
"""

from sirens.stack import Stack


class Rack(Stack):
    def __init__(self, instrument):
        super().__init__()
        self.instrument = instrument

    @property
    def blocks(self):
        # jen hezčí jméno pro self.items (rack.blocks se čte líp než rack.items)
        return self.items

    def create(self, block_class):
        # blok potřebuje vědět, čí je (bere si od nástroje pitch, obálku, trigger)
        return block_class(self.instrument)

    def changed(self):
        """propojí zapnutý bloky shora dolů a výsledek předá nástroji (nic = ticho).

        flow = to, co zrovna teče rackem. každej blok dostane flow shora a vrátí,
        co teče dál (zdroj něco přičte, efekt to upraví).
        """
        flow = None
        for block in self.blocks:
            if block.enabled:
                flow = block.connect(flow)
            elif not block.IS_SOURCE:
                block.output = None     # vypnutej efekt: jeho starej řetězec zahodíme, ať se nepočítá
        self.instrument.play(flow)

    def describe(self) -> str:
        """cesta zvuku jako text, např. "Oscillator + Noise -> Filter" (ukazuje se pod spektrem)."""
        text = ""
        for block in self.blocks:
            if not block.enabled:
                continue
            if not text:
                text = block.NAME
            else:
                # zdroj se přičítá (+), efekt zpracovává všechno nad sebou (->)
                text += (" + " if block.IS_SOURCE else " -> ") + block.NAME
        return text
