"""Popis jednoho ovladatelného parametru (pro syntezátor i vizualizaci)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Param:
    key: str            # klíč v presetu a v Synth.set()
    label: str          # popisek pod knobem
    lo: float           # minimum
    hi: float           # maximum
    default: float      # výchozí hodnota
    unit: str = ""      # jednotka pro zobrazení
    log: bool = False   # logaritmický průběh (frekvence a časy se tak ovládají přirozeněji)
    step: float = 0.0   # krok (0 = plynule)
    choices: tuple = () # pokud není prázdné, knob přepíná mezi těmito popisky (hodnota = index)
