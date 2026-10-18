"""Analýza zvuku pro osciloskop a spektrum (místo pyo oken Scope a Spectrum).

Osciloskop: TableRec nahraje posledních N vzorků signálu do tabulky.
Spektrum: vlastní DFT přesně podle definice z přednášky

    X[k] = sum_{n=0}^{N-1} x[n] * w[n] * e^(-j * 2*pi * k * n / N)

e^(-j*fi) = cos(fi) - j*sin(fi), takže reálná a imaginární část jsou
součty součinů se sinusovkami. Hodnoty cos a sin pro všechna k a n si
spočítáme předem do matic a DFT je pak jen násobení matice vektorem.
Numpy používáme jen na rychlé násobení polí, výpočet je náš.
"""

import numpy as np
from pyo import NewTable, TableRec, TrigFunc

N = 2048          # délka úseku (~46 ms při 44,1 kHz), rozlišení spektra = 44100/2048 = 21,5 Hz
SCOPE_VIEW = 512  # kolik vzorků ukáže osciloskop (~11,6 ms)
DB_FLOOR = -90.0  # vše tišší bereme jako ticho
FALL_DB = 2.5     # o kolik dB za snímek smí špička ve spektru klesnout (aby neblikala)
BASS, MID, HIGH = (20, 250), (250, 2000), (2000, 20000)   # pásma v Hz pro obraz a světlo


class Analyzer:
    def __init__(self, source, sample_rate: int):
        self.sample_rate = sample_rate
        self.table = NewTable(length=N / sample_rate)
        self.size = self.table.getSize()           # skutečný počet vzorků v tabulce
        self.recorder = TableRec(source, self.table, fadetime=0).play()
        # TableRec po naplnění tabulky vyšle trigger; TrigFunc pak zavolá funkci,
        # která si poznamená, že je úsek hotový (volá se ze zvukového vlákna).
        self.ready = False
        self.on_full = TrigFunc(self.recorder["trig"], self._mark_ready)
        self.samples = np.zeros(self.size, dtype=np.float32)

        n = np.arange(self.size)
        k = np.arange(self.size // 2)[:, None]     # k jako sloupec -> matice k x n
        # Hannovo okno: úsek na krajích plynule ztlumíme, jinak by ostrý
        # začátek a konec úseku rozmazal spektrum (prosakování, leakage).
        self.window = (0.5 - 0.5 * np.cos(2 * np.pi * n / (self.size - 1))).astype(np.float32)
        self.cos = np.cos(2 * np.pi * k * n / self.size).astype(np.float32)
        self.sin = np.sin(2 * np.pi * k * n / self.size).astype(np.float32)
        self.freqs = np.arange(self.size // 2) * sample_rate / self.size   # frekvence k-tého koše
        self.spectrum = np.full(self.size // 2, DB_FLOOR, dtype=np.float32)

    def _mark_ready(self):
        self.ready = True

    def update(self) -> bool:
        """Když je nahrávání úseku hotové, vezme ho a spustí další. Vrací True, je-li nový úsek."""
        if not self.ready:
            return False
        self.ready = False
        self.samples = np.asarray(self.table.getTable(), dtype=np.float32)
        self.recorder.play()
        self._compute_spectrum()
        return True

    def _compute_spectrum(self):
        x = self.samples * self.window
        re = self.cos @ x            # sum x[n]*w[n]*cos(2*pi*k*n/N) pro každé k
        im = -(self.sin @ x)         # minus z e^(-j...)
        # Sinusovka s amplitudou A dá |X[k]| = A * sum(w) / 2, proto přepočet zpět na A:
        amplitude = 2 * np.sqrt(re * re + im * im) / self.window.sum()
        db = 20 * np.log10(np.maximum(amplitude, 1e-9))
        # Pomalé klesání: nová hodnota, nebo stará o kousek nižší (co je větší).
        self.spectrum = np.maximum(np.maximum(db, DB_FLOOR), self.spectrum - FALL_DB)

    def scope(self) -> np.ndarray:
        """Úsek pro osciloskop začínající průchodem nulou směrem nahoru (trigger).

        Bez triggeru by každý snímek začínal jinde ve vlně a obraz by ujížděl.
        """
        x = self.samples
        rising = np.nonzero((x[:-1] < 0) & (x[1:] >= 0))[0]
        rising = rising[rising < len(x) - SCOPE_VIEW]
        start = rising[0] + 1 if len(rising) else 0
        return x[start:start + SCOPE_VIEW]

    def peak_level_db(self) -> float:
        """Nejvyšší okamžitá hodnota v úseku v dB (0 dB = 1.0 = hranice ořezu)."""
        return 20 * np.log10(max(float(np.abs(self.samples).max()), 1e-9))

    def peak_frequency(self):
        """Frekvence nejsilnější složky, nebo None, když je ticho.

        Přesný vrchol leží mezi koši; dopočítáme ho parabolou proloženou
        nejsilnějším košem a jeho dvěma sousedy (jinak by 440 Hz ukázalo 430,7).
        """
        s = self.spectrum
        k = int(np.argmax(s[1:-1])) + 1
        if s[k] < -60:
            return None
        a, b, c = s[k - 1], s[k], s[k + 1]
        shift = 0.5 * (a - c) / (a - 2 * b + c) if a - 2 * b + c != 0 else 0.0
        return (k + shift) * self.sample_rate / self.size

    def band(self, lo_hz: float, hi_hz: float) -> float:
        """Síla pásma lo..hi Hz jako číslo 0..1, podle kterého reaguje obraz a světlo.

        Bereme nejsilnější složku v pásmu: -60 dB a tišší = 0, 0 dB = 1.
        """
        inside = (self.freqs >= lo_hz) & (self.freqs < hi_hz)
        db = float(self.spectrum[inside].max())
        return min(1.0, max(0.0, (db + 60) / 60))

    def bands(self) -> tuple[float, float, float]:
        """Basy, středy a výšky (0..1)."""
        return self.band(*BASS), self.band(*MID), self.band(*HIGH)
