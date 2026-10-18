"""Živé načítání zvuku ze souboru sirens/sound.py.

Funkce build(ui) v sound.py postaví zvuk z pyo objektů a vrátí signál,
který se má hrát. Kdykoli se sound.py uloží, načteme ho znovu
(importlib.reload) a starý zvuk vyměníme za nový, bez restartu aplikace.

Objekt `ui`, který build() dostane, je třída Controls níže: přes ui.slider()
si kód v sound.py řekne o slider a dostane zpátky pyo signál s jeho hodnotou.
To nahrazuje .ctrl() a s.gui() ze cvičení.
"""

import importlib
import os
import sys
import traceback

from pyo import SigTo

MODULE = "sirens.sound"
PATH = os.path.join(os.path.dirname(__file__), "sound.py")


class Controls:
    """Rozhraní pro sound.py: skupiny a slidery v pravém panelu."""

    def __init__(self, sidebar, memory: dict):
        self.sidebar = sidebar
        self.memory = memory   # hodnoty sliderů z minulého načtení (aby se po uložení nevracely)
        self.signals = []      # signály sliderů; držíme odkazy, jinak by je pyo zrušil

    def group(self, title: str):
        """Začne novou skupinu sliderů s nadpisem (např. ui.group("Oscillator"))."""
        self.sidebar.add_group(title)

    def slider(self, label, lo, hi, default, unit="", log=False, help=""):
        """Přidá slider a vrátí pyo signál s jeho hodnotou.

        label    popisek v pruhu, např. "Frequency"
        lo, hi   rozsah ve skutečných jednotkách, např. 20, 2000
        default  počáteční hodnota (dvojklik na pruh ji vrátí)
        unit     jednotka za číslem, např. "Hz"
        log      True = logaritmický průběh (vhodné pro frekvence a časy)
        help     krátké vysvětlení pod sliderem

        Signál je SigTo: při pohybu sliderem dojede na novou hodnotu za 30 ms,
        takže změna je plynulá a necvaká (skok hodnoty = skok ve vlně = lupnutí).
        """
        key = (label, lo, hi, default)   # stejný slider po uložení = stejný klíč
        value = self.memory.get(key, default)
        signal = SigTo(value, time=0.03, init=value)

        def on_change(new_value):
            signal.value = new_value
            self.memory[key] = new_value

        self.sidebar.add_slider(label, lo, hi, default, unit, log, help, on_change, value)
        self.signals.append(signal)
        return signal


def describe(error: Exception) -> str:
    """Chyba z sound.py jako jeden řádek: kde (číslo řádku) a co."""
    if isinstance(error, SyntaxError) and error.filename == PATH:
        return f"sound.py, line {error.lineno}: {error.msg}"
    frames = [f for f in traceback.extract_tb(error.__traceback__) if f.filename == PATH]
    where = f"sound.py, line {frames[-1].lineno}: " if frames else ""
    return f"{where}{type(error).__name__}: {error}"


class SoundLoader:
    def __init__(self, engine, sidebar):
        self.engine = engine
        self.sidebar = sidebar
        self.memory = {}
        self.controls = None
        self.mtime = None    # čas poslední úpravy souboru při posledním načtení

    def changed(self) -> bool:
        """Byl sound.py od posledního načtení uložen?"""
        return os.path.getmtime(PATH) != self.mtime

    def load(self):
        """Načte sound.py znovu a pustí nový zvuk. Vrací (text, je_chyba)."""
        self.mtime = os.path.getmtime(PATH)
        self.sidebar.clear()
        self.controls = Controls(self.sidebar, self.memory)
        try:
            if MODULE in sys.modules:
                module = importlib.reload(sys.modules[MODULE])
            else:
                module = importlib.import_module(MODULE)
            signal = module.build(self.controls)
        except Exception as error:
            self.engine.play(None)
            return describe(error), True
        self.engine.play(signal)
        if signal is None:
            return "sound.py: build() returns nothing yet, so it is silent.", False
        return "sound.py loaded. Save the file to hear changes.", False
