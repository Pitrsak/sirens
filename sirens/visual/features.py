"""Co obraz ví o zvuku v jednom snímku (spočítá se jednou a pak to používaj všechny vrstvy).

    level      celková hlasitost 0..1
    bass, mid, high   síla basů, středů a výšek 0..1
    beat       1 ve chvíli úderu (prudký nárůst basů), pak to rychle klesá k 0
    wave       512 vzorků zvuku z posledního úseku (tvar vlny, od průchodu nulou jako osciloskop)
    spectrum   síla spektra 0..1 na SPECTRUM_POINTS frekvencích (40 Hz - 12 kHz, logaritmicky)
    time       čas od spuštění v sekundách

logaritmicky = body jsou rozložený tak, jak slyší ucho, každá oktáva (dvakrát vyšší
frekvence) dostane stejně bodů, jinak by se basy nacpaly do pár bodů úplně vlevo.
"""

import numpy as np

SPECTRUM_POINTS = 96    # kolik bodů spektra dostanou vrstvy (Ring, Bars)
BEAT_RISE = 1.25        # úder = basy aspoň o 25 % nad svým průměrem
BEAT_GAP = 0.18         # nejkratší čas mezi dvěma údery (s), jinak by jeden buben udělal několik úderů po sobě
BEAT_FALL = 0.85        # o kolik beat klesne za snímek: vynásobí se tímhle, takže spadne o 15 %


class Features:
    def __init__(self):
        self.level = self.bass = self.mid = self.high = self.beat = 0.0
        self.wave = np.zeros(512, dtype=np.float32)
        self.spectrum = np.zeros(SPECTRUM_POINTS, dtype=np.float32)
        self.time = 0.0
        self.bass_average = 0.0     # klouzavý průměr basů, s tím se porovnává, jestli je úder
        self.last_beat = -1.0       # kdy byl poslední úder (s), -1 ať může bejt úder hned na začátku
        # 96 frekvencí od 40 Hz do 12 kHz, každá je stejným násobkem tý předchozí (geometrická řada)
        self.freqs = np.geomspace(40, 12000, SPECTRUM_POINTS)

    def update(self, analyzer, dt: float):
        self.time += dt                     # dt = kolik sekund uběhlo od minulýho snímku
        self.bass, self.mid, self.high = analyzer.bands()
        # hlasitost ze špičky v dB, stejně jako pásma: -60 dB a míň = 0, 0 dB = 1
        self.level = min(1.0, max(0.0, (analyzer.peak_level_db() + 60) / 60))
        self.wave = analyzer.scope()
        # pro každou z mých 96 frekvencí najdu koš analyzátoru (první, kterej je na ní nebo nad ní),
        # minimum je pojistka, ať index nevyleze za konec pole
        bins = np.minimum(np.searchsorted(analyzer.freqs, self.freqs), len(analyzer.freqs) - 1)
        # dB -> 0..1 zase stejně: -60 dB = 0, 0 dB = 1, clip ořízne, co je mimo
        self.spectrum = np.clip((analyzer.spectrum[bins] + 60) / 60, 0, 1)
        self._detect_beat()

    def _detect_beat(self):
        """Vlastní detekce úderu: basy prudce vyskočí nad svůj klouzavý průměr.

        Průměr = 90 % starýho průměru + 10 % nový hodnoty (pomalu sleduje basy,
        je to vlastně jednoduchej vyhlazovací filtr). Úder je, když jsou basy aspoň
        o 25 % nad průměrem a ještě o 0.05 navíc (ať malý výkyvy potichu nedělaj
        falešný údery) a zároveň od minulýho úderu uběhlo aspoň BEAT_GAP.
        """
        rising = self.bass > self.bass_average * BEAT_RISE + 0.05
        if rising and self.time - self.last_beat > BEAT_GAP:
            self.beat = 1.0
            self.last_beat = self.time
        else:
            self.beat *= BEAT_FALL      # mezi údery beat plynule hasne
        # průměr se posune až po porovnání, jinak by do sebe napřed započítal i ten úder
        self.bass_average = 0.9 * self.bass_average + 0.1 * self.bass
