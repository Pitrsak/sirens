"""Rack: bloky, ze kterých se skládá zvuk jednoho nástroje.

Uživatel přidává, maže a posouvá bloky v UI (viz stack.py); po každé změně
rack bloky znovu propojí shora dolů a výsledek předá nástroji.
"""

from sirens.stack import Stack


class Rack(Stack):
    def __init__(self, instrument):
        super().__init__()
        self.instrument = instrument

    @property
    def blocks(self):
        return self.items

    def create(self, block_class):
        return block_class(self.instrument)

    def changed(self):
        """Propojí bloky shora dolů a výsledek předá nástroji (nic = ticho)."""
        flow = None
        for block in self.blocks:
            flow = block.connect(flow)
        self.instrument.play(flow)

    def describe(self) -> str:
        """Cesta zvuku jako text, např. "Oscillator + Noise -> Filter"."""
        text = ""
        for block in self.blocks:
            if not text:
                text = block.NAME
            else:
                text += (" + " if block.IS_SOURCE else " -> ") + block.NAME
        return text
