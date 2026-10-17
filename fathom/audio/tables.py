"""Vlastní výpočet tabulek pro syntezátor.

Vlnové tvary skládáme aditivní syntézou (součet harmonických podle Fourierovy
řady), křivku zkreslení počítáme jako funkci tanh. Výsledné seznamy čísel se
pak nahrají do pyo tabulek (DataTable), ze kterých čtou oscilátory.
"""

import math

TABLE_SIZE = 2048
HARMONICS = 32  # počet harmonických; víc = ostřejší zvuk, ale riziko aliasingu u vysokých tónů
WAVE_NAMES = ("SIN", "TRI", "SAW", "SQR")


def harmonic_amplitude(shape: int, k: int) -> float:
    """Amplituda k-té harmonické pro daný tvar vlny (k = 1 je základní tón)."""
    if shape == 0:  # sinus: pouze základní harmonická
        return 1.0 if k == 1 else 0.0
    if shape == 1:  # trojúhelník: liché harmonické, 1/k^2, střídá se znaménko
        if k % 2 == 0:
            return 0.0
        sign = 1.0 if (k // 2) % 2 == 0 else -1.0
        return sign / (k * k)
    if shape == 2:  # pila: všechny harmonické, 1/k
        return 1.0 / k
    # obdélník: liché harmonické, 1/k
    return 1.0 / k if k % 2 == 1 else 0.0


def additive_wave(shape: int, harmonics: int = HARMONICS, size: int = TABLE_SIZE) -> list[float]:
    """Jedna perioda vlny jako součet sinusovek, normalizovaná do rozsahu -1..1."""
    amps = [(k, harmonic_amplitude(shape, k)) for k in range(1, harmonics + 1)]
    amps = [(k, a) for k, a in amps if a != 0.0]  # nulové harmonické přeskočíme
    samples = []
    for i in range(size):
        phase = 2.0 * math.pi * i / size
        samples.append(sum(a * math.sin(k * phase) for k, a in amps))
    peak = max(abs(s) for s in samples)
    return [s / peak for s in samples]


def drive_curve(size: int = TABLE_SIZE, hardness: float = 2.5) -> list[float]:
    """Přenosová křivka waveshaperu: vstup -1..1 se zobrazí přes tanh.

    Malé hodnoty projdou téměř lineárně, velké se měkce ořežou -> vzniknou
    nové harmonické (zkreslení). Dělením tanh(hardness) zajistíme, že
    krajní body zůstanou na -1 a 1.
    """
    norm = math.tanh(hardness)
    curve = []
    for i in range(size):
        x = -1.0 + 2.0 * i / (size - 1)
        curve.append(math.tanh(hardness * x) / norm)
    return curve
