"""Co obraz ví o zvuku v jednom snímku (počítá se jednou, používají všechny vrstvy).

    level      celková hlasitost 0..1
    bass, mid, high   síla basů, středů a výšek 0..1
    beat       1 ve chvíli úderu (prudký nárůst basů), pak rychle klesá k 0
    wave       posledních 512 vzorků zvuku (tvar vlny)
    spectrum   síla spektra 0..1 na SPECTRUM_POINTS frekvencích (40 Hz - 12 kHz, logaritmicky)
    time       čas od spuštění v sekundách
"""

import numpy as np

SPECTRUM_POINTS = 96
BEAT_RISE = 1.25        # úder = basy aspoň o 25 % nad svým průměrem
BEAT_GAP = 0.18         # nejkratší čas mezi dvěma údery (s)
BEAT_FALL = 0.85        # o kolik beat klesne za snímek


class Features:
    def __init__(self):
        self.level = self.bass = self.mid = self.high = self.beat = 0.0
        self.wave = np.zeros(512, dtype=np.float32)
        self.spectrum = np.zeros(SPECTRUM_POINTS, dtype=np.float32)
        self.time = 0.0
        self.bass_average = 0.0
        self.last_beat = -1.0
        self.freqs = np.geomspace(40, 12000, SPECTRUM_POINTS)

    def update(self, analyzer, dt: float):
        self.time += dt
        self.bass, self.mid, self.high = analyzer.bands()
        self.level = min(1.0, max(0.0, (analyzer.peak_level_db() + 60) / 60))
        self.wave = analyzer.scope()
        bins = np.minimum(np.searchsorted(analyzer.freqs, self.freqs), len(analyzer.freqs) - 1)
        self.spectrum = np.clip((analyzer.spectrum[bins] + 60) / 60, 0, 1)
        self._detect_beat()

    def _detect_beat(self):
        """Vlastní detekce úderu: basy prudce vyskočí nad svůj klouzavý průměr.

        Průměr = 90 % starého průměru + 10 % nové hodnoty (pomalu sleduje basy).
        """
        rising = self.bass > self.bass_average * BEAT_RISE + 0.05
        if rising and self.time - self.last_beat > BEAT_GAP:
            self.beat = 1.0
            self.last_beat = self.time
        else:
            self.beat *= BEAT_FALL
        self.bass_average = 0.9 * self.bass_average + 0.1 * self.bass
