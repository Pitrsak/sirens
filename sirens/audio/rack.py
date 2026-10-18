"""Rack: seznam bloků, ze kterých se právě skládá zvuk.

Aplikace začíná s prázdným rackem (ticho). Uživatel přidává, maže a posouvá
bloky v UI; po každé změně rack bloky znovu propojí shora dolů a výsledek
pošle do enginu.
"""

from sirens.audio.blocks import Block


class Rack:
    def __init__(self, engine):
        self.engine = engine
        self.blocks: list[Block] = []

    def add(self, block_class) -> Block:
        """Vytvoří nový blok daného druhu a přidá ho na konec (dolů)."""
        block = block_class()
        self.blocks.append(block)
        self._connect()
        return block

    def remove(self, block: Block):
        self.blocks.remove(block)
        self._connect()

    def move(self, block: Block, step: int):
        """Posune blok o step míst (-1 = nahoru, +1 = dolů)."""
        i = self.blocks.index(block)
        j = i + step
        if 0 <= j < len(self.blocks):
            self.blocks[i], self.blocks[j] = self.blocks[j], self.blocks[i]
            self._connect()

    def describe(self) -> str:
        """Cesta zvuku jako text, např. "Sine + Noise -> Low-pass"."""
        text = ""
        for block in self.blocks:
            if not text:
                text = block.NAME
            else:
                text += (" + " if block.IS_SOURCE else " -> ") + block.NAME
        return text

    def _connect(self):
        """Propojí bloky shora dolů a výsledek pošle do enginu (nic = ticho)."""
        flow = None
        for block in self.blocks:
            flow = block.connect(flow)
        self.engine.play(flow)
