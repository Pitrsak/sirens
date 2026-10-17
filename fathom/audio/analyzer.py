"""Analýza výstupního zvuku pro vizualizaci (a později pro světla).

Místo hotové FFT používáme vlastní banku filtrů: signál pošleme do N pásmových
propustí s logaritmicky rozloženými středy a u každé měříme obálku (Follower).
Výsledek je hrubé spektrum, které se dobře vysvětluje i kreslí.
"""

import math

from pyo import Biquad, Follower, NewTable, TableRec

BAND_COUNT = 24
F_MIN, F_MAX = 40.0, 12000.0
DB_FLOOR = -60.0  # vše tišší než -60 dB bereme jako ticho


def to_unit(amplitude: float) -> float:
    """Převod amplitudy na decibely a pak na rozsah 0..1 (0 = ticho, 1 = plná úroveň)."""
    db = 20.0 * math.log10(max(amplitude, 1e-9))
    return min(1.0, max(0.0, (db - DB_FLOOR) / -DB_FLOOR))


class Analyzer:
    def __init__(self, source):
        # Středy pásem rovnoměrně v logaritmickém měřítku (stejný poměr mezi sousedy).
        ratio = (F_MAX / F_MIN) ** (1.0 / (BAND_COUNT - 1))
        self.freqs = [F_MIN * ratio ** i for i in range(BAND_COUNT)]
        # Biquad type=2 je pásmová propust; q=4 dává zhruba třetinooktávová pásma.
        self.filters = [Biquad(source, freq=f, q=4, type=2) for f in self.freqs]
        self.followers = [Follower(f, freq=15) for f in self.filters]
        self.level_follower = Follower(source, freq=10)

        # Krátký záznam signálu pro osciloskop (cca 46 ms), nahrává se znovu každý snímek.
        self.scope_table = NewTable(length=2048 / 44100)
        self.scope_rec = TableRec(source, self.scope_table, fadetime=0)

    def bands(self) -> list[float]:
        """Aktuální energie v pásmech, každé v rozsahu 0..1."""
        return [to_unit(f.get()) for f in self.followers]

    def level(self) -> float:
        """Celková hlasitost 0..1."""
        return to_unit(self.level_follower.get())

    def scope(self) -> list[float]:
        """Vrátí poslední nahraný úsek signálu a spustí nahrávání dalšího."""
        samples = self.scope_table.getTable()
        self.scope_rec.play()
        return samples
