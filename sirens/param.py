"""Nastavitelné parametry: popis slideru a základ pro všechno, co slidery má.

Bloky zvuku, obraz i světlo mají seznam PARAMS (jaké slidery ukázat) a hodnoty,
které slidery mění. UI je pak umí vykreslit všechny stejně (Sidebar.add_params).
"""

from dataclasses import dataclass


@dataclass
class Param:
    """Popis jednoho slideru."""
    label: str           # popisek v pruhu, např. "Frequency"
    lo: float            # nejmenší hodnota
    hi: float            # největší hodnota
    default: float       # počáteční hodnota (dvojklik na pruh ji vrátí)
    unit: str = ""       # jednotka za číslem, např. "Hz"
    log: bool = False    # logaritmický průběh (pro frekvence a časy)
    help: str = ""       # krátké vysvětlení pod sliderem


class Adjustable:
    """Něco, co se ovládá slidery: PARAMS a jejich aktuální hodnoty."""

    PARAMS: list[Param] = []

    def __init__(self):
        self.settings = {p.label: p.default for p in self.PARAMS}

    def get(self, label: str) -> float:
        return self.settings[label]

    def set(self, label: str, value: float):
        self.settings[label] = value
