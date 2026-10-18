"""Bloky, ze kterých se v aplikaci skládá zvuk (jako moduly v syntezátoru).

Zvuk teče rackem shora dolů:
 - zdroj (SourceBlock) přičte svůj zvuk k tomu, co přitéká shora,
 - efekt (EffectBlock) zpracuje všechno, co přitéká shora.
Takže např. Sine, Noise, Low-pass = (sinus + šum) přes dolní propust.

Každý druh bloku je malá třída:
 - NAME     název v menu "Add block" a v nadpisu skupiny
 - PARAMS   jaké má slidery
 - zdroj v __init__ postaví pyo objekty a zvuk uloží do self.output,
   efekt v process(flow) zpracuje přitékající zvuk a vrátí výsledek

Hodnota každého slideru je pyo signál SigTo v self.values["Popisek"].
Dá se použít všude, kde by bylo číslo, např. Sine(freq=self.values["Frequency"]).
Při pohybu sliderem SigTo dojede na novou hodnotu za 30 ms, takže to necvaká.
"""

import math

from pyo import ButHP, ButLP, Clip, DataTable, Delay, Interp, Lookup, Mix, Noise, Phasor, SigTo, Sine

from sirens.param import Adjustable, Param

SMOOTH_TIME = 0.03   # za jak dlouho (s) dojede signál slideru na novou hodnotu


class Block(Adjustable):
    """Společný základ všech bloků: slidery jako pyo signály."""

    NAME = ""
    IS_SOURCE = True

    def __init__(self):
        self.values = {p.label: SigTo(p.default, time=SMOOTH_TIME, init=p.default)
                       for p in self.PARAMS}
        self.output = None

    def get(self, label: str) -> float:
        return self.values[label].value

    def set(self, label: str, value: float):
        self.values[label].value = value

    def connect(self, flow):
        """Napojí blok na zvuk shora (flow, None = zatím nic). Vrací zvuk, který teče dál."""
        raise NotImplementedError


class SourceBlock(Block):
    """Zdroj zvuku: k tomu, co přitéká shora, přičte svůj zvuk."""

    def connect(self, flow):
        self.flow = self.output if flow is None else flow + self.output
        return self.flow


class EffectBlock(Block):
    """Efekt: zpracuje zvuk, který přitéká shora. Když nic nepřitéká, mlčí."""

    IS_SOURCE = False

    def connect(self, flow):
        # Při každé změně racku se efekt postaví znovu s novým vstupem.
        self.output = self.process(flow) if flow is not None else None
        return self.output

    def process(self, flow):
        raise NotImplementedError


# --- zdroje ---

class SineBlock(SourceBlock):
    """Jeden sinusový tón: nejjednodušší zvuk, jen jedna frekvence (cv3.py)."""

    NAME = "Sine"
    PARAMS = [
        Param("Frequency", 20, 2000, 440, "Hz", log=True,
              help="How high the tone is: how many waves per second."),
        Param("Amplitude", 0, 1, 0.3, help="How loud: the wave is multiplied by this number."),
    ]

    def __init__(self):
        super().__init__()
        self.output = Sine(freq=self.values["Frequency"], mul=self.values["Amplitude"])


class HarmonicsBlock(SourceBlock):
    """Aditivní syntéza (cv3.py): sinusovky na násobcích základní frekvence f, 2f, 3f...

    S amplitudami 1, 1/2, 1/3... vznikne pilovitý průběh, jen s lichými (1, 3, 5, 7)
    se blíží obdélníku. Barva zvuku = jak silné jsou jednotlivé harmonické.
    """

    NAME = "Harmonics"
    COUNT = 7
    PARAMS = [
        Param("Frequency", 20, 2000, 110, "Hz", log=True,
              help="Base tone f. The other sines play at 2f, 3f, 4f..."),
        Param("Amplitude", 0, 1, 0.3, help="Overall loudness of the block."),
    ] + [Param(f"Harmonic {n}", 0, 1, round(1 / n, 3)) for n in range(1, COUNT + 1)]
    PARAMS[-1].help = "1, 1/2, 1/3... makes a sawtooth. Only odd harmonics (1, 3, 5, 7) make it square-like."

    def __init__(self):
        super().__init__()
        f = self.values["Frequency"]
        numbers = range(1, self.COUNT + 1)
        # Jeden Sine se seznamem frekvencí = 7 sinusovek najednou.
        self.partials = Sine(freq=[f * n for n in numbers],
                             mul=[self.values[f"Harmonic {n}"] for n in numbers])
        # Sečteme je do jednoho kanálu. Polovina, protože 1 + 1/2 + ... + 1/7 je skoro 2,6.
        self.output = Mix(self.partials, voices=1, mul=self.values["Amplitude"] * 0.5)


class SweepBlock(SourceBlock):
    """Sinus, jehož frekvenci pořád dokola rozjíždí Phasor (cv2.py)."""

    NAME = "Sweep"
    PARAMS = [
        Param("Rate", 0.05, 20, 0.5, "Hz", log=True, help="How many sweeps per second."),
        Param("From", 20, 5000, 200, "Hz", log=True, help="Frequency where each sweep starts."),
        Param("To", 20, 5000, 1200, "Hz", log=True, help="Frequency where it ends and jumps back."),
        Param("Amplitude", 0, 1, 0.3),
    ]

    def __init__(self):
        super().__init__()
        low, high = self.values["From"], self.values["To"]
        # Phasor jde pořád dokola 0 -> 1; mul a add z něj udělají From -> To.
        self.ramp = Phasor(freq=self.values["Rate"], mul=high - low, add=low)
        self.output = Sine(freq=self.ramp, mul=self.values["Amplitude"])


class NoiseBlock(SourceBlock):
    """Bílý šum: náhodné vzorky, všechny frekvence stejně silné (cv2.py)."""

    NAME = "Noise"
    PARAMS = [Param("Amplitude", 0, 1, 0.2, help="Random samples: every frequency at once. "
                                                 "Shape it with Low-pass and High-pass below.")]

    def __init__(self):
        super().__init__()
        self.output = Noise(mul=self.values["Amplitude"])


# --- efekty ---

class LowPassBlock(EffectBlock):
    NAME = "Low-pass"
    PARAMS = [Param("Cutoff", 20, 20000, 1000, "Hz", log=True,
                    help="Frequencies above this get quieter: the sound gets darker.")]

    def process(self, flow):
        return ButLP(flow, freq=self.values["Cutoff"])


class HighPassBlock(EffectBlock):
    NAME = "High-pass"
    PARAMS = [Param("Cutoff", 20, 20000, 500, "Hz", log=True,
                    help="Frequencies below this get quieter: the sound gets thinner.")]

    def process(self, flow):
        return ButHP(flow, freq=self.values["Cutoff"])


class DelayBlock(EffectBlock):
    """Ozvěna (cv2.py): zpožděná kopie zvuku, část se vrací zpět a opakuje se."""

    NAME = "Delay"
    PARAMS = [
        Param("Time", 0.02, 2, 0.25, "s", log=True, help="Time between echoes."),
        Param("Feedback", 0, 0.95, 0.5, help="How much of each echo comes back again."),
        Param("Mix", 0, 1, 0.5, help="How loud the echoes are next to the original."),
    ]

    def process(self, flow):
        self.echo = Delay(flow, delay=self.values["Time"], feedback=self.values["Feedback"], maxdelay=2)
        return flow + self.echo * self.values["Mix"]


class ShaperBlock(EffectBlock):
    """Vlastní operace se signálem (waveshaping): každý vzorek x projde křivkou y = curve(x).

    Křivku si spočítáme sami do tabulky (TABLE_SIZE bodů pro x od -1 do 1)
    a pyo Lookup pak pro každý vzorek jen najde hodnotu v tabulce.
    Mix prolíná původní (0) a upravený (1) zvuk.
    """

    SHAPE = ""          # popisek slideru, který mění tvar křivky
    TABLE_SIZE = 4096

    def __init__(self):
        super().__init__()
        self.table = DataTable(self.TABLE_SIZE)
        self._draw_curve()

    def set(self, label: str, value: float):
        super().set(label, value)
        if label == self.SHAPE:
            self._draw_curve()

    def _draw_curve(self):
        amount = self.get(self.SHAPE)
        xs = [2 * i / (self.TABLE_SIZE - 1) - 1 for i in range(self.TABLE_SIZE)]
        self.table.replace([self.curve(x, amount) for x in xs])

    def curve(self, x: float, amount: float) -> float:
        raise NotImplementedError

    def process(self, flow):
        self.shaped = Lookup(self.table, index=Clip(flow, -1, 1))
        return Interp(flow, self.shaped, interp=self.values["Mix"])


class DistortionBlock(ShaperBlock):
    """Zkreslení: tanh zaobleně ořízne vrcholy vlny, přibudou vyšší harmonické."""

    NAME = "Distortion"
    SHAPE = "Drive"
    PARAMS = [
        Param("Drive", 1, 50, 5, log=True, help="How hard the wave is pushed into the curve: "
                                                "more drive, flatter tops, rougher sound."),
        Param("Mix", 0, 1, 1, help="0 = original sound, 1 = fully distorted."),
    ]

    def curve(self, x, drive):
        # Dělení tanh(drive) zajistí, že x = 1 dá zase 1 (hlasitost se nezmění).
        return math.tanh(drive * x) / math.tanh(drive)


class BitcrushBlock(ShaperBlock):
    """Snížení bitové hloubky: vlna smí mít jen pár úrovní, vznikají schody."""

    NAME = "Bitcrush"
    SHAPE = "Bits"
    PARAMS = [
        Param("Bits", 1, 12, 4, help="Fewer bits, fewer allowed levels (2 to the bits), "
                                     "more broken and digital sound."),
        Param("Mix", 0, 1, 1, help="0 = original sound, 1 = fully crushed."),
    ]

    def curve(self, x, bits):
        levels = 2 ** round(bits) / 2       # úrovní na každou stranu od nuly
        return round(x * levels) / levels   # zaokrouhlení na nejbližší povolenou úroveň


# Bloky, které nabízí menu "Add block", v tomto pořadí.
CATALOG = [SineBlock, HarmonicsBlock, SweepBlock, NoiseBlock,
           LowPassBlock, HighPassBlock, DelayBlock, DistortionBlock, BitcrushBlock]
