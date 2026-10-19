"""Bloky, ze kterých se skládá zvuk nástroje (jako moduly v syntezátoru).

Zvuk teče rackem shora dolů:
 - zdroj (SourceBlock) přičte svůj zvuk k tomu, co přitéká shora,
 - efekt (EffectBlock) zpracuje všechno, co přitéká shora.

Zdroje hrají noty: pro každý hlas nástroje (viz instrument.py) jeden signál
s výškou podle noty a hlasitostí podle obálky. Dokud se nic nehraje, mlčí.
Efekty Chorus, Delay a Reverb nejdřív sečtou všechny hlasy do jednoho
(jedna ozvěna pro všechny noty); Filter, Distortion a Bitcrush zpracují
každou notu zvlášť, pokud jsou nad nimi.

Každý druh bloku je malá třída: NAME (název), PARAMS (slidery), zdroj
v __init__ postaví pyo objekty do self.output, efekt v process(flow).
Hodnota každého slideru je pyo signál SigTo v self.values["Popisek"];
při pohybu sliderem dojede na novou hodnotu za 30 ms, takže to necvaká.

Pozor na počítání se signály operátory (a * b, a + b): pyo výsledek natrvalo
připojí k levému objektu a pravý si nepamatuje. Kdyby vlevo byl dlouho žijící
objekt (výška noty, slider) a vpravo něco, co se při přestavbě racku zahodí,
výsledek by dál běžel a četl uvolněnou paměť (pád programu), a s každou
přestavbou by přibýval (zpomalování). Proto násobíme parametrem mul=
nového objektu (Sig(x, mul=y)) a sčítáme přes Mix.
"""

import math
from pathlib import Path

from pyo import (FM, LFO, SVF, Chorus, Clip, DataTable, Delay, Freeverb, Interp, Lookup, Max, Mix,
                 NewTable, Noise, Sig, SigTo, Sine, SndTable, SuperSaw, TrigEnv)

from sirens.param import Adjustable, Choice, Param

SMOOTH_TIME = 0.03   # za jak dlouho (s) dojede signál slideru na novou hodnotu


class Block(Adjustable):
    """Společný základ všech bloků: slidery jako pyo signály."""

    NAME = ""
    IS_SOURCE = True

    def __init__(self, instrument):
        self.instrument = instrument
        self.values = {p.label: SigTo(p.default, time=SMOOTH_TIME, init=p.default)
                       for p in self.PARAMS}
        self.automation = {}    # popisek -> {takt: hodnota}, viz song.py
        self.output = None

    def get(self, label: str) -> float:
        return self.values[label].value

    def set(self, label: str, value: float):
        self.values[label].value = value

    def connect(self, flow):
        """Napojí blok na zvuk shora (flow, None = zatím nic). Vrací zvuk, který teče dál."""
        raise NotImplementedError

    def note(self) -> str:
        """Krátký text pod nadpisem bloku (např. jméno načteného souboru)."""
        return ""

    def extra(self) -> dict:
        """Data k uložení navíc ke sliderům (např. cesta k souboru)."""
        return {}

    def load_extra(self, data: dict):
        pass


# --- zdroje ---

PITCH_PARAMS = [
    Param("Octave", -3, 3, 0, step=1, help="Shift the played notes by whole octaves."),
    Param("Detune", -100, 100, 0, "ct", help="Fine tuning in cents (100 cents = one semitone)."),
]
LEVEL = Param("Level", 0, 1, 0.5, help="Loudness of this source.")


class SourceBlock(Block):
    """Zdroj zvuku: k tomu, co přitéká shora, přičte svůj zvuk (jeden signál na hlas)."""

    def __init__(self, instrument):
        super().__init__(instrument)
        self.ratio = SigTo(self._ratio(), time=SMOOTH_TIME, init=self._ratio())

    def _ratio(self) -> float:
        """Kolikrát vyšší je tón zdroje než hraná nota (podle Octave a Detune)."""
        if "Octave" not in self.values:
            return 1.0
        return 2 ** (round(self.get("Octave")) + self.get("Detune") / 1200)

    def set(self, label, value):
        super().set(label, value)
        if label in ("Octave", "Detune"):
            self.ratio.value = self._ratio()

    def freq(self):
        """Frekvence pro každý hlas: výška hrané noty krát posun zdroje."""
        return Sig(self.instrument.pitch, mul=self.ratio)

    def amp(self):
        """Hlasitost pro každý hlas: obálka noty krát Level."""
        return Sig(self.instrument.envelope, mul=self.values["Level"])

    def connect(self, flow):
        """Přičte svůj zvuk k tomu, co přitéká shora.

        Mix s tolika hlasy, kolik jich má zdroj: k-tý hlas shora + k-tý hlas zdroje.
        """
        if flow is None:
            self.flow = self.output
        else:
            self.flow = Mix([flow, self.output], voices=len(self.output))
        return self.flow


WAVES = ("Sine", "Saw", "Square", "Triangle")
LFO_TYPES = (7, 0, 2, 3)     # čísla těchto tvarů v pyo LFO (7 s Brightness 0 = čistý sinus)


class OscillatorBlock(SourceBlock):
    """Základní oscilátor se čtyřmi tvary vlny (pásmově omezený pyo LFO)."""

    NAME = "Oscillator"
    PARAMS = [
        Choice("Wave", WAVES, 1, help="Sine is pure and soft, Saw bright and buzzy, "
                                      "Square hollow, Triangle in between."),
        *PITCH_PARAMS,
        Param("Brightness", 0, 1, 1, help="How sharp the wave is: lower = rounder, softer sound."),
        LEVEL,
    ]

    def __init__(self, instrument):
        super().__init__(instrument)
        self.osc = LFO(freq=self.freq(), sharp=self.values["Brightness"],
                       type=LFO_TYPES[round(self.get("Wave"))], mul=self.amp())
        self.output = self.osc

    def set(self, label, value):
        super().set(label, value)
        if label == "Wave":
            self.osc.type = LFO_TYPES[round(value)]


class SupersawBlock(SourceBlock):
    """Sedm mírně rozladěných pil najednou: široký, "tlustý" zvuk pro plochy a leady."""

    NAME = "Supersaw"
    PARAMS = [
        *PITCH_PARAMS,
        Param("Spread", 0, 1, 0.5, help="How far apart the seven saws are tuned: more = wider, richer."),
        Param("Center", 0, 1, 0.7, help="Balance between the middle saw and the detuned ones."),
        LEVEL,
    ]

    def __init__(self, instrument):
        super().__init__(instrument)
        self.output = SuperSaw(freq=self.freq(), detune=self.values["Spread"],
                               bal=self.values["Center"], mul=self.amp())


class FMBlock(SourceBlock):
    """Frekvenční modulace: jeden sinus rychle rozkmitává výšku druhého. Zvony, kovy, basy."""

    NAME = "FM"
    PARAMS = [
        *PITCH_PARAMS,
        Param("Ratio", 0.25, 8, 2, step=0.25, help="Speed of the modulating sine against the note. "
                                                   "Whole numbers sound musical, others metallic."),
        Param("Index", 0, 20, 4, help="How strongly it modulates: more = brighter, harsher."),
        LEVEL,
    ]

    def __init__(self, instrument):
        super().__init__(instrument)
        self.output = FM(carrier=self.freq(), ratio=self.values["Ratio"],
                         index=self.values["Index"], mul=self.amp())


class AdditiveBlock(SourceBlock):
    """Aditivní syntéza: sinusovky na násobcích tónu f, 2f, 3f... sečtené dohromady.

    S amplitudami 1, 1/2, 1/3... vznikne pila, jen s lichými (1, 3, 5, 7) skoro obdélník.
    """

    NAME = "Additive"
    COUNT = 7
    PARAMS = [*PITCH_PARAMS, LEVEL] + [Param(f"Harmonic {n}", 0, 1, round(1 / n, 3))
                                       for n in range(1, COUNT + 1)]

    def __init__(self, instrument):
        super().__init__(instrument)
        freq, amp = self.freq(), self.amp()
        # Pro každou harmonickou jeden Sine (s hlasy pro všechny noty), pak je sečteme.
        self.partials = [Sine(freq=freq * n, mul=amp * self.values[f"Harmonic {n}"])
                         for n in range(1, self.COUNT + 1)]
        total = self.partials[0]
        for partial in self.partials[1:]:
            total = total + partial
        self.output = total * 0.4      # 1 + 1/2 + ... + 1/7 je skoro 2,6, tak ztišíme


class NoiseBlock(SourceBlock):
    """Bílý šum: náhodné vzorky, všechny frekvence. S filtrem dělá vítr, hi-hat, šum vln."""

    NAME = "Noise"
    PARAMS = [LEVEL]

    def __init__(self, instrument):
        super().__init__(instrument)
        self.output = Noise(mul=self.amp())


ROOT_HZ = 261.63    # nota C4: na ní hraje Sampler zvuk v původní výšce


class SamplerBlock(SourceBlock):
    """Přehraje zvukový soubor (bicí, hlas, smyčku) při každé notě.

    Na C4 v původní výšce, o oktávu výš dvakrát rychleji (a výš), níž pomaleji.
    Hraje vždy celý soubor, puštění klávesy ho neutne (vhodné pro bicí).
    """

    NAME = "Sampler"
    PARAMS = [Param("Pitch", -24, 24, 0, "st", step=1, help="Shift in semitones."), LEVEL]

    def __init__(self, instrument):
        super().__init__(instrument)
        self.path = ""
        self.table = NewTable(0.1)                  # zatím prázdná = ticho
        self.shift = SigTo(1.0, time=SMOOTH_TIME)
        self._build()

    def _build(self):
        """Přehrávač pro aktuální tabulku se zvukem.

        Doba přehrání: delší soubor = déle, vyšší nota = kratší (rychlejší).
        """
        speed = Max(self.instrument.pitch, 1) / ROOT_HZ * self.shift
        self.player = TrigEnv(self.instrument.trigger, self.table, dur=self.table.getDur() / speed,
                              mul=self.values["Level"])
        self.output = self.player

    def set(self, label, value):
        super().set(label, value)
        if label == "Pitch":
            self.shift.value = 2 ** (round(value) / 12)

    def load(self, path: str):
        """Načte soubor (WAV, AIFF, ...), bere jen první kanál.

        Pro nový soubor postavíme nový přehrávač a rack znovu propojíme. Výměna tabulky
        za běhu (setTable) by mohla uvolnit starý zvuk, zatímco ho zvukové vlákno čte.
        """
        self.table = SndTable(path, chnl=0)
        self.path = path
        self._build()
        self.instrument.rack.changed()

    def note(self):
        return Path(self.path).name if self.path else "No sound file yet: click Load."

    def extra(self):
        return {"file": self.path}

    def load_extra(self, data):
        if data.get("file") and Path(data["file"]).exists():
            self.load(data["file"])


# --- efekty ---

class EffectBlock(Block):
    """Efekt: zpracuje zvuk, který přitéká shora. Když nic nepřitéká, mlčí."""

    IS_SOURCE = False

    def connect(self, flow):
        # Při každé změně racku se efekt postaví znovu s novým vstupem.
        self.output = self.process(flow) if flow is not None else None
        return self.output

    def process(self, flow):
        raise NotImplementedError


FILTER_MODES = ("Low-pass", "Band-pass", "High-pass")


class FilterBlock(EffectBlock):
    """Filtr s rezonancí (pyo SVF). Cutoff může otevírat obálka noty a rozhoupat LFO (wobble)."""

    NAME = "Filter"
    PARAMS = [
        Choice("Mode", FILTER_MODES, 0, help="Low-pass keeps the lows (darker), High-pass the highs "
                                             "(thinner), Band-pass a band around the cutoff."),
        Param("Cutoff", 20, 20000, 1200, "Hz", log=True, help="Where the filter starts cutting."),
        Param("Resonance", 0.5, 10, 1, help="Boost right at the cutoff: higher = sharper, whistling."),
        Param("Envelope", 0, 1, 0, help="Each note opens the filter and lets it close again (pluck, wah)."),
        Param("Wobble", 0, 0.9, 0, help="An LFO moving the cutoff up and down."),
        Param("Wobble rate", 0.1, 16, 2, "Hz", log=True, help="How fast it wobbles."),
    ]

    def __init__(self, instrument):
        super().__init__(instrument)
        self.mode = SigTo(self.get("Mode") / 2, time=SMOOTH_TIME)   # SVF: 0 = LP, 0.5 = BP, 1 = HP
        # o kolik obálka otevře filtr: 1 + Envelope * 8 * obálka (pro každý hlas zvlášť)
        self.env_amount = Sig(self.values["Envelope"], mul=8)
        self.opening = Sig(self.instrument.envelope, mul=self.env_amount, add=1)

    def set(self, label, value):
        super().set(label, value)
        if label == "Mode":
            self.mode.value = round(value) / 2

    def process(self, flow):
        # LFO kolem 1 (např. 0.5..1.5), kterým se násobí Cutoff
        self.lfo = Sine(freq=self.values["Wobble rate"], mul=self.values["Wobble"], add=1)
        self.moving = Sig(self.lfo, mul=self.values["Cutoff"])
        cutoff = self.moving
        if len(flow) == len(self.instrument.envelope):
            # zvlášť pro každou notu: obálka posune cutoff až 9x výš
            self.opened = Sig(self.moving, mul=self.opening)
            cutoff = self.opened
        self.cutoff = Clip(cutoff, 20, 18000)
        return SVF(flow, freq=self.cutoff, q=self.values["Resonance"], type=self.mode)


class ShaperBlock(EffectBlock):
    """Vlastní operace se signálem (waveshaping): každý vzorek x projde křivkou y = curve(x).

    Křivku si spočítáme sami do tabulky (TABLE_SIZE bodů pro x od -1 do 1)
    a pyo Lookup pak pro každý vzorek jen najde hodnotu v tabulce.
    Mix prolíná původní (0) a upravený (1) zvuk.
    """

    SHAPE = ""          # popisek slideru, který mění tvar křivky
    TABLE_SIZE = 4096

    def __init__(self, instrument):
        super().__init__(instrument)
        self.table = DataTable(self.TABLE_SIZE)
        self._draw_curve()

    def set(self, label, value):
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
        Param("Bits", 1, 12, 4, step=1, help="Fewer bits, fewer allowed levels (2 to the bits): "
                                             "more broken, digital sound."),
        Param("Mix", 0, 1, 1, help="0 = original sound, 1 = fully crushed."),
    ]

    def curve(self, x, bits):
        levels = 2 ** round(bits) / 2       # úrovní na každou stranu od nuly
        return round(x * levels) / levels   # zaokrouhlení na nejbližší povolenou úroveň


class ChorusBlock(EffectBlock):
    """Několik lehce zpožděných a rozhoupaných kopií: zvuk je širší a "živější"."""

    NAME = "Chorus"
    PARAMS = [
        Param("Depth", 0, 5, 1, help="How much the copies wander in pitch."),
        Param("Mix", 0, 1, 0.5, help="0 = original sound only, 1 = copies only."),
    ]

    def process(self, flow):
        self.mixed = Mix(flow, voices=1)
        return Chorus(self.mixed, depth=self.values["Depth"], feedback=0.25, bal=self.values["Mix"])


class DelayBlock(EffectBlock):
    """Ozvěna: zpožděná kopie zvuku, část se vrací zpět a opakuje se."""

    NAME = "Delay"
    PARAMS = [
        Param("Time", 0.02, 2, 0.25, "s", log=True, help="Time between echoes."),
        Param("Feedback", 0, 0.95, 0.4, help="How much of each echo comes back again."),
        Param("Mix", 0, 1, 0.4, help="How loud the echoes are next to the original."),
    ]

    def process(self, flow):
        self.mixed = Mix(flow, voices=1)
        self.echo = Delay(self.mixed, delay=self.values["Time"], feedback=self.values["Feedback"],
                          maxdelay=2)
        return self.mixed + self.echo * self.values["Mix"]


class ReverbBlock(EffectBlock):
    """Dozvuk místnosti: zvuk se rozplyne jako v sále."""

    NAME = "Reverb"
    PARAMS = [
        Param("Size", 0, 1, 0.8, help="Size of the room: bigger = longer tail."),
        Param("Damping", 0, 1, 0.5, help="How quickly the high frequencies die out in the tail."),
        Param("Mix", 0, 1, 0.3, help="0 = dry, 1 = only the reverb."),
    ]

    def process(self, flow):
        self.mixed = Mix(flow, voices=1)
        return Freeverb(self.mixed, size=self.values["Size"], damp=self.values["Damping"],
                        bal=self.values["Mix"])


# Bloky, které nabízí menu "Add block", v tomto pořadí (zdroje, pak efekty).
CATALOG = [OscillatorBlock, SupersawBlock, FMBlock, AdditiveBlock, NoiseBlock, SamplerBlock,
           FilterBlock, DistortionBlock, BitcrushBlock, ChorusBlock, DelayBlock, ReverbBlock]
