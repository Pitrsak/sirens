"""Analýza zvuku, tohle krmí osciloskop a spektrum (pyo okna Scope a Spectrum nepoužívám, dělám si to sám).

Osciloskop: TableRec nahraje posledních N vzorků signálu do tabulky, nic víc.
Spektrum: vlastní DFT, přesně podle definice z přednášky

    X[k] = sum_{n=0}^{N-1} x[n] * w[n] * e^(-j * 2*pi * k * n / N)

co to jako dělá? pro každou frekvenci (koš) k se ptám, kolik takový sinusovky
v tom úseku zvuku je. x[n] je vzorek, w[n] okno (viz níž), koš = úzký pásmo
frekvencí široký sample_rate / N.
e^(-j*fi) = cos(fi) - j*sin(fi), takže reálná a imaginární část jsou prostě
součty součinů se sinusovkami (cos dá reálnou, sin imaginární). Hodnoty cos a sin
pro všechna k a n si spočítám předem do matic a DFT je pak jen násobení matice
vektorem (jeden řádek matice = jedna frekvence).
Numpy je tu jen na rychlý násobení polí, ten výpočet je náš, žádný hotový np.fft.
"""

import numpy as np
from pyo import NewTable, TableRec, TrigFunc

N = 2048          # délka úseku (~46 ms při 44,1 kHz), rozlišení spektra = 44100/2048 = 21,5 Hz na koš
SCOPE_VIEW = 512  # kolik vzorků ukáže osciloskop (~11,6 ms)
DB_FLOOR = -90.0  # cokoliv tiššího beru jako ticho
FALL_DB = 2.5     # o kolik dB smí špička ve spektru klesnout za jeden snímek spektra, tj. nový úsek (ať to nebliká)
BASS, MID, HIGH = (20, 250), (250, 2000), (2000, 20000)   # pásma v Hz, podle nich reaguje obraz a světlo


# engine si ho vyrobí jednou a GUI se ho pak každej snímek ptá, co je novýho
class Analyzer:
    def __init__(self, source, sample_rate: int):
        self.sample_rate = sample_rate
        # NewTable chce délku v sekundách, ne ve vzorcích, proto N / sample_rate
        self.table = NewTable(length=N / sample_rate)
        # skutečný počet vzorků v tabulce (radši se zeptám, než spoléhat na N)
        self.size = self.table.getSize()
        # TableRec nahrává zvuk do tabulky, fadetime=0 = žádný stmívání na krajích, chci to surový
        self.recorder = TableRec(source, self.table, fadetime=0).play()
        # TableRec po naplnění tabulky vyšle trigger, TrigFunc pak zavolá funkci,
        # která si jen poznamená, že je úsek hotový (pozor, volá se to ze zvukového vlákna,
        # takže tam nic složitýho, jen příznak, a GUI si to vyzvedne v update())
        self.ready = False
        self.on_full = TrigFunc(self.recorder["trig"], self._mark_ready)
        self.samples = np.zeros(self.size, dtype=np.float32)

        # PŘÍPRAVA NA DFT, počítá se jen jednou při startu
        n = np.arange(self.size)                   # čísla vzorků 0..N-1
        k = np.arange(self.size // 2)[:, None]     # k jako sloupec -> matice k x n
        # (stačí půlka košů, u reálnýho signálu je druhá půlka spektra jen zrcadlo)
        # Hannovo okno: úsek na krajích plynule ztlumím, jinak by ostrý
        # začátek a konec úseku rozmazal spektrum (prosakování, leakage).
        # tvarem je to jeden kopeček z cosinusu, na krajích 0, uprostřed 1
        self.window = (0.5 - 0.5 * np.cos(2 * np.pi * n / (self.size - 1))).astype(np.float32)
        # matice cos a sin: řádek k = sinusovka, která se do úseku vejde přesně k-krát
        self.cos = np.cos(2 * np.pi * k * n / self.size).astype(np.float32)
        self.sin = np.sin(2 * np.pi * k * n / self.size).astype(np.float32)
        self.freqs = np.arange(self.size // 2) * sample_rate / self.size   # frekvence k-tého koše v Hz
        self.spectrum = np.full(self.size // 2, DB_FLOOR, dtype=np.float32)   # na začátku všude ticho

    def _mark_ready(self):
        # tohle volá TrigFunc ze zvukovýho vlákna, jen nastaví příznak
        self.ready = True

    def update(self) -> bool:
        """Když je úsek nahranej, vezme ho a pustí nahrávání dalšího. Vrací True, když je nový úsek.

        Volá se každej snímek GUI, ale úsek trvá ~46 ms, takže dost často to vrátí
        False a nic se nepočítá (spektrum zůstane z minula).
        """
        if not self.ready:
            return False
        self.ready = False
        self.samples = np.asarray(self.table.getTable(), dtype=np.float32)
        self.recorder.play()    # znova nahrávat od začátku tabulky
        self._compute_spectrum()
        return True

    def _compute_spectrum(self):
        x = self.samples * self.window   # vzorky krát okno, to je x[n] * w[n] ze vzorce
        re = self.cos @ x            # sum x[n]*w[n]*cos(2*pi*k*n/N) pro každý k (@ = matice krát vektor)
        im = -(self.sin @ x)         # minus z e^(-j...)
        # sinusovka s amplitudou A dá |X[k]| = A * sum(w) / 2, proto přepočet zpátky na A
        # (|X| = délka komplexního čísla = odmocnina z re^2 + im^2, Pythagoras)
        amplitude = 2 * np.sqrt(re * re + im * im) / self.window.sum()
        # na decibely: 20*log10(A), takže 1.0 = 0 dB, 0.1 = -20 dB, 0.01 = -40 dB...
        # 1e-9 je pojistka, logaritmus z nuly nejde
        db = 20 * np.log10(np.maximum(amplitude, 1e-9))
        # pomalý klesání: nová hodnota, nebo ta stará o kousek nižší (co je větší),
        # nahoru to skočí hned, dolů padá max o FALL_DB, takže to neposkakuje
        self.spectrum = np.maximum(np.maximum(db, DB_FLOOR), self.spectrum - FALL_DB)

    def scope(self) -> np.ndarray:
        """Úsek pro osciloskop, začíná tam, kde jde vlna přes nulu nahoru (trigger).

        Bez triggeru by každej snímek začínal jinde ve vlně a obraz by ujížděl,
        takhle vlna stojí na místě (stejně to dělaj normální osciloskopy).
        """
        x = self.samples
        # indexy, kde je vzorek pod nulou a ten další už na nule nebo nad = průchod nulou nahoru
        rising = np.nonzero((x[:-1] < 0) & (x[1:] >= 0))[0]
        # beru jen ty, za kterými je ještě aspoň SCOPE_VIEW vzorků, ať se to celý vejde
        rising = rising[rising < len(x) - SCOPE_VIEW]
        # +1 = první vzorek už nad nulou; když žádnej průchod není (třeba ticho), tak prostě od 0
        start = rising[0] + 1 if len(rising) else 0
        return x[start:start + SCOPE_VIEW]

    def peak_level_db(self) -> float:
        """Nejvyšší okamžitá hodnota v úseku v dB (0 dB = 1.0 = hranice, kde už se ořezává)."""
        return 20 * np.log10(max(float(np.abs(self.samples).max()), 1e-9))

    def peak_frequency(self):
        """Frekvence nejsilnější složky, nebo None, když je ticho (všechno pod -60 dB).

        Přesnej vrchol většinou leží někde mezi koši, takže ho dopočítám parabolou
        proloženou nejsilnějším košem a jeho dvěma sousedy (jinak by 440 Hz ukázalo
        430,7, protože koše jdou po 21,5 Hz).
        """
        s = self.spectrum
        # nejsilnější koš, krajní vynechám (potřebuju oba sousedy), +1 vrací index zpátky do celýho pole
        k = int(np.argmax(s[1:-1])) + 1
        if s[k] < -60:
            return None
        a, b, c = s[k - 1], s[k], s[k + 1]      # levej soused, vrchol, pravej soused
        # vrchol paraboly přes ty 3 body, vyjde posun -0.5..0.5 koše od k
        # (jmenovatel 0 = všechny tři stejně, pak žádnej posun)
        shift = 0.5 * (a - c) / (a - 2 * b + c) if a - 2 * b + c != 0 else 0.0
        return (k + shift) * self.sample_rate / self.size     # číslo koše (i s desetinou) krát šířka koše = Hz

    def band(self, lo_hz: float, hi_hz: float) -> float:
        """Síla pásma lo..hi Hz jako číslo 0..1, podle kterýho pak reaguje obraz a světlo.

        Beru nejsilnější složku v pásmu (ne průměr): -60 dB a tišší = 0, 0 dB = 1,
        mezi tím rovnoměrně v dB.
        """
        inside = (self.freqs >= lo_hz) & (self.freqs < hi_hz)    # maska, True u košů v pásmu
        db = float(self.spectrum[inside].max())
        return min(1.0, max(0.0, (db + 60) / 60))     # -60..0 dB -> 0..1, a oříznout, ať to nevyleze ven

    def bands(self) -> tuple[float, float, float]:
        """Basy, středy a výšky (každý 0..1), přesně takhle to chce obraz i světlo."""
        return self.band(*BASS), self.band(*MID), self.band(*HIGH)
