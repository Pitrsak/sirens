"""Parametry, co jdou nastavit sliderem: popis jednoho slideru (Param)
a základ pro všechno, co nějaký slidery má (Adjustable).

Bloky zvuku a vrstvy obrazu mají seznam PARAMS (jaký slidery ukázat)
a k tomu hodnoty, který ty slidery mění. UI je pak umí vykreslit všechny stejně,
jednou funkcí (Sidebar.add_params), a nemusím psát panel pro každou věc zvlášť.
"""

from dataclasses import dataclass


@dataclass
class Param:
    """Popis jednoho slideru, jsou to jen data (dataclass si sama udělá __init__ z polí dole)."""
    label: str           # popisek v pruhu, např. "Frequency" (zároveň klíč v settings)
    lo: float            # nejmenší hodnota
    hi: float            # největší hodnota
    default: float       # počáteční hodnota (dvojklik na pruh ji vrátí)
    unit: str = ""       # jednotka za číslem, např. "Hz"
    log: bool = False    # logaritmickej průběh (pro frekvence a časy), ať jdou jemně i malý hodnoty
    help: str = ""       # krátký vysvětlení pod sliderem
    step: float = 0      # > 0: slider skáče po krocích (např. 1 = celá čísla), 0 = plynule
    choices: tuple = ()  # místo slideru řada tlačítek, hodnota = pořadí vybraný možnosti (0, 1, 2...)


def Choice(label: str, choices: tuple, default: int = 0, help: str = "") -> Param:
    """Parametr s pevnýma možnostma, např. tvar vlny Sine / Saw / Square.

    vlastně je to normální Param od 0 do (počet možností - 1) s krokem 1, takže
    hodnota je prostě číslo vybraný možnosti. Je to funkce, ale jméno má velkým
    jako třída, protože se používá stejně jako Param(...).
    """
    return Param(label, 0, len(choices) - 1, default, step=1, help=help, choices=choices)


class Adjustable:
    """Něco, co se ovládá slidery: má PARAMS a jejich aktuální hodnoty (settings).

    dědí z toho Instrument, Block i Layer.
    """

    PARAMS: list[Param] = []    # potomek si to přepíše svým seznamem, tady je prázdnej

    def __init__(self):
        # na začátku má každej slider svou default hodnotu, klíč je popisek
        self.settings = {p.label: p.default for p in self.PARAMS}
        self.automation = {}    # popisek -> {takt: hodnota}, viz song.py (prázdný = nic se nehýbe samo)

    def get(self, label: str) -> float:
        return self.settings[label]

    # potomek si set klidně přepíše (třeba Instrument), aby změnu poslal i do zvuku
    def set(self, label: str, value: float):
        self.settings[label] = value
