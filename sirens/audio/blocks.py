"""BLOKY, ze kterých se skládá zvuk nástroje (jako moduly v syntezátoru, kabelama spojený pod sebou).

zvuk teče rackem shora dolů:
 - zdroj (SourceBlock) přičte svůj zvuk k tomu, co přitéká shora,
 - efekt (EffectBlock) vezme všechno, co přitéká shora, a nějak to upraví.

zdroje hrají noty: pro každý hlas nástroje (viz instrument.py) jeden signál,
výška podle noty, hlasitost podle obálky. dokud se nic nehraje, mlčí (obálka je 0).
efekty Delay a Reverb nejdřív sečtou všechny hlasy do jednoho
(jedna ozvěna pro všechny noty, jinak by to bylo 8 ozvěn a 8x víc počítání),
Filter, Distortion a Bitcrush zpracují každou notu zvlášť, pokud jsou nad nimi.

každý druh bloku je malá třída: NAME (název v menu), PARAMS (slidery), zdroj
si v __init__ postaví pyo objekty do self.output, efekt to dělá v process(flow).
hodnota každého slideru je pyo signál SigTo v self.values["Popisek"],
při pohybu sliderem k nové hodnotě dojede za 30 ms, takže to necvaká
(skok hodnoty uprostřed vlny = skok ve vlně = slyšitelný cvak).

POZOR na počítání se signály operátory (a * b, a + b): pyo výsledek natrvalo
připojí k levému objektu a pravý si nepamatuje. kdyby vlevo byl dlouho žijící
objekt (výška noty, slider) a vpravo něco, co se při přestavbě racku zahodí,
výsledek by dál běžel a četl uvolněnou paměť (pád programu), a s každou
přestavbou by jich přibývalo (zpomalování). proto násobíme parametrem mul=
nového objektu (Sig(x, mul=y)) a sčítáme přes Mix.
"""

import math
from pathlib import Path

from pyo import (LFO, SVF, Clip, DataTable, Delay, Freeverb, Interp, Lookup, Max, Mix,
                 NewTable, Noise, Sig, SigTo, Sine, SndTable, TrigEnv)

from sirens.param import Adjustable, Choice, Param

SMOOTH_TIME = 0.03   # za jak dlouho (s) dojede signál slideru na novou hodnotu

# TABULKY (křivky, zvukový soubory) se za běhu programu nikdy neuvolňujou, schválně.
# objekt, který z tabulky čte (TrigEnv, Lookup), si drží jen ukazatel na její data,
# ne tabulku samotnou. při smazání stopy Python uvolní nástroj i bloky naráz
# v libovolném pořadí, a kdyby tabulka zanikla dřív než její čtenář, zvukový vlákno
# by četlo uvolněnou paměť a program spadl. tabulek je málo, takže paměti to nevadí.
TABLES = []
SOUNDS = {}          # cesta k souboru -> načtená tabulka (stejnej soubor se načte jen jednou)


def keep(table):
    """uloží tabulku natrvalo do TABLES (proč, viz výš) a vrátí ji zpátky, ať se to dá psát na jeden řádek."""
    TABLES.append(table)
    return table


def load_sound(path: str):
    """zvukový soubor jako tabulka, každej soubor se načte jen jednou (pak se bere ze SOUNDS).

    chnl=0 = jen první kanál (levej), stereo nepotřebujem, nástroj je mono.
    """
    if path not in SOUNDS:
        SOUNDS[path] = SndTable(path, chnl=0)
    return SOUNDS[path]


class Block(Adjustable):
    """společnej základ všech bloků: slidery jako pyo signály.

    pozor, Adjustable.__init__ se tu schválně nevolá: blok si hodnoty nedrží
    v obyčejným slovníku settings, ale jako SigTo signály ve values (aby šly rovnou do pyo).
    proto taky přepisujem get a set.
    """

    NAME = ""
    IS_SOURCE = True
    enabled = True      # vypnutej blok rack přeskočí (viz rack.py), Stack.toggle to přepíná

    def __init__(self, instrument):
        self.instrument = instrument
        # pro každej slider jeden SigTo, který začne rovnou na výchozí hodnotě (init=)
        self.values = {p.label: SigTo(p.default, time=SMOOTH_TIME, init=p.default)
                       for p in self.PARAMS}
        self.automation = {}    # popisek -> {takt: hodnota}, viz song.py
        self.output = None

    def get(self, label: str) -> float:
        return self.values[label].value

    def set(self, label: str, value: float):
        # SigTo se sám rozjede k nový hodnotě (za SMOOTH_TIME)
        self.values[label].value = value

    def connect(self, flow):
        """napojí blok na zvuk shora (flow, None = zatím nic nepřitéká). vrací zvuk, který teče dál dolů.

        každej potomek (zdroj, efekt) si to dělá po svým.
        """
        raise NotImplementedError

    def note(self) -> str:
        """krátkej text pod nadpisem bloku (třeba jméno načteného souboru), prázdnej = nic."""
        return ""

    def extra(self) -> dict:
        """data k uložení navíc ke sliderům (třeba cesta k souboru), většina bloků nic nemá."""
        return {}

    def load_extra(self, data: dict):
        pass


# ---- ZDROJE ----

# slidery na výšku, který má skoro každej zdroj (proto společnej seznam)
PITCH_PARAMS = [
    Param("Octave", -3, 3, 0, step=1, help="Shift the played notes by whole octaves."),
    Param("Detune", -100, 100, 0, "ct", help="Fine tuning in cents (100 cents = one semitone)."),
    Param("Pitch drop", 0, 48, 0, "st", step=1, help="Each note starts this many semitones higher and "
                                                     "quickly falls to its pitch. Kick drums, toms, lasers."),
    Param("Drop time", 0.01, 1, 0.06, "s", log=True, help="How fast the pitch falls back to the note."),
]
LEVEL = Param("Level", 0, 1, 0.5, help="Loudness of this source.")


DROP_POINTS = 512   # z kolika bodů je křivka poklesu výšky (víc = hladší, 512 bohatě stačí)


def drop_curve() -> list:
    """tvar poklesu výšky: z 1 rychle k 0 (exponenciálně, jako tlumenej kmit blány bubnu).

    e^(-6x) klesne na konci skoro k nule, ale ne úplně (asi 0,0025), takže od toho
    odečtem ten konec a vydělíme, aby to končilo přesně v 0, jinak by
    po doběhnutí nota zůstala trošku rozladěná.
    """
    end = math.exp(-6)
    return [(math.exp(-6 * i / (DROP_POINTS - 1)) - end) / (1 - end) for i in range(DROP_POINTS)]


class SourceBlock(Block):
    """zdroj zvuku: k tomu, co přitéká shora, přičte svůj zvuk (jeden signál na hlas)."""

    def __init__(self, instrument):
        super().__init__(instrument)
        # ratio = kolikrát výš/níž hraje tenhle zdroj než nota (Octave + Detune), taky plynule
        self.ratio = SigTo(self._ratio(), time=SMOOTH_TIME, init=self._ratio())
        if "Pitch drop" in self.values:
            # pokles výšky: při každým stisku (trigger) proběhne křivka 1 -> 0 za Drop time.
            # výška = nota * (1 + amount * křivka): na začátku nota * 2^(drop/12), pak už jen nota.
            self.curve = keep(DataTable(size=DROP_POINTS, init=drop_curve()))
            self.drop = TrigEnv(instrument.trigger, self.curve, dur=self.values["Drop time"],
                                interp=1)    # bez interpolace: ta by na konci křivky skočila zpět k 1
            self.amount = SigTo(self._amount(), time=SMOOTH_TIME, init=self._amount())
            self.bend = Sig(self.drop, mul=self.amount, add=1)   # 1 + amount * křivka

    def _amount(self) -> float:
        """o kolik víc (krát) než nota začíná tón: 12 půltónů = 2x výš, tedy amount 1.

        proč 2 na něco? výška je frekvence a o oktávu výš = dvojnásobná frekvence,
        oktáva má 12 půltónů, takže 1 půltón = 2^(1/12) krát. mínus 1, protože
        se to pak přičítá k 1 (viz bend).
        """
        return 2 ** (round(self.get("Pitch drop")) / 12) - 1

    def _ratio(self) -> float:
        """kolikrát vyšší je tón zdroje než hraná nota (podle Octave a Detune).

        Detune je v centech, 100 centů = půltón, 1200 = oktáva, proto / 1200.
        zdroje bez slideru Octave (Noise, Sampler) mají prostě 1.
        """
        if "Octave" not in self.values:
            return 1.0
        return 2 ** (round(self.get("Octave")) + self.get("Detune") / 1200)

    def set(self, label, value):
        super().set(label, value)
        # ratio a amount jsou spočítaný z víc sliderů, tak je musíme přepočítat ručně
        if label in ("Octave", "Detune"):
            self.ratio.value = self._ratio()
        if label == "Pitch drop":
            self.amount.value = self._amount()

    def freq(self):
        """frekvence pro každej hlas: výška hraný noty krát posun zdroje (krát pokles výšky).

        vždycky nový Sig s mul=, ne operátor *, viz POZOR nahoře.
        """
        shifted = Sig(self.instrument.pitch, mul=self.ratio)
        if "Pitch drop" not in self.values:
            return shifted
        return Sig(shifted, mul=self.bend)

    def amp(self):
        """hlasitost pro každej hlas: obálka noty krát Level (obálka 0 = ticho, mezi notama nic nehraje)."""
        return Sig(self.instrument.envelope, mul=self.values["Level"])

    def connect(self, flow):
        """přičte svůj zvuk k tomu, co přitéká shora.

        Mix s tolika hlasy, kolik jich má zdroj: k-tej hlas shora + k-tej hlas zdroje
        (takže noty zůstanou pořád oddělený, efekt pod tím je může zpracovat každou zvlášť).
        """
        if flow is None:
            self.flow = self.output   # nahoře nic není, tak teče dál jen můj zvuk
        else:
            self.flow = Mix([flow, self.output], voices=len(self.output))
        return self.flow


WAVES = ("Sine", "Saw", "Square", "Triangle")
LFO_TYPES = (7, 0, 2, 3)     # čísla těchto tvarů v pyo LFO (7 s Brightness 0 = čistej sinus)


class OscillatorBlock(SourceBlock):
    """základní oscilátor, čtyři tvary vlny (pyo LFO, je pásmově omezenej, takže nepíská aliasing).

    tvar vlny = barva tónu: sinus je jen jeden čistej tón, pila má všechny vyšší
    harmonický (ostrá, bzučí), obdélník a trojúhelník jen ty lichý.
    """

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
        # freq a mul jsou vícehlasý signály, takže LFO má taky tolik hlasů (pro každou notu jeden)
        self.osc = LFO(freq=self.freq(), sharp=self.values["Brightness"],
                       type=LFO_TYPES[round(self.get("Wave"))], mul=self.amp())
        self.output = self.osc

    def set(self, label, value):
        super().set(label, value)
        # type není signál, jen číslo, tak ho přepnem přímo na oscilátoru
        if label == "Wave":
            self.osc.type = LFO_TYPES[round(value)]


class NoiseBlock(SourceBlock):
    """bílej šum: náhodný vzorky, všechny frekvence najednou (není to tón, nemá výšku).

    s filtrem dělá vítr, hi-hat, šum vln. výška noty ho nezajímá, jen obálka (kdy a jak hlasitě).
    """

    NAME = "Noise"
    PARAMS = [LEVEL]

    def __init__(self, instrument):
        super().__init__(instrument)
        self.output = Noise(mul=self.amp())


ROOT_HZ = 261.63    # nota C4: na ní hraje Sampler zvuk v původní výšce


class SamplerBlock(SourceBlock):
    """přehraje zvukovej soubor (bicí, hlas, smyčku) při každý notě.

    na C4 v původní výšce, o oktávu výš dvakrát rychlejc (a výš), níž pomalejc.
    hraje vždycky celej soubor, puštění klávesy ho neutne (dobrý pro bicí),
    obálku nástroje ani sílu úhozu nepoužívá, jen Level.
    """

    NAME = "Sampler"
    PARAMS = [Param("Pitch", -24, 24, 0, "st", step=1, help="Shift in semitones."), LEVEL]

    def __init__(self, instrument):
        super().__init__(instrument)
        self.path = ""
        self.table = keep(NewTable(0.1))            # zatím prázdná (0,1 s) = ticho
        self.shift = SigTo(1.0, time=SMOOTH_TIME)   # posun slideru Pitch jako násobek rychlosti
        self._build()

    def _build(self):
        """přehrávač pro aktuální tabulku se zvukem.

        trik: TrigEnv normálně přehrává obálku, ale tabulka může být klidně celej zvuk,
        takže ho prostě přehraje při každým stisku. rychlost přehrání určuje dur:
        delší soubor = déle, vyšší nota = kratší (rychlejc a tím i výš, jako gramofon).
        Max(pitch, 1): než se zahraje první nota, je pitch 0 a dělit nulou nechceme.
        """
        speed = Max(self.instrument.pitch, 1) / ROOT_HZ * self.shift
        self.player = TrigEnv(self.instrument.trigger, self.table, dur=self.table.getDur() / speed,
                              mul=self.values["Level"])
        self.output = self.player

    def set(self, label, value):
        super().set(label, value)
        if label == "Pitch":
            # půltóny -> násobek rychlosti, stejně jako u _amount (12 = 2x rychlejc)
            self.shift.value = 2 ** (round(value) / 12)

    def load(self, path: str):
        """načte soubor (WAV, AIFF, ...), bere jen první kanál.

        pro novej soubor postavíme novej přehrávač a rack znovu propojíme. výměna tabulky
        za běhu (setTable) by mohla uvolnit starej zvuk, zatímco ho zvukový vlákno čte.
        """
        self.table = load_sound(path)
        self.path = path
        self._build()
        self.instrument.rack.changed()

    def note(self):
        return Path(self.path).name if self.path else "No sound file yet: click Load."

    def extra(self):
        return {"file": self.path}

    def load_extra(self, data):
        # při otevření uloženýho projektu: soubor načteme, jen když pořád existuje
        if data.get("file") and Path(data["file"]).exists():
            self.load(data["file"])


# ---- EFEKTY ----

class EffectBlock(Block):
    """efekt: zpracuje zvuk, který přitéká shora. když nic nepřitéká, mlčí."""

    IS_SOURCE = False

    def connect(self, flow):
        # při každý změně racku se efekt postaví znovu s novým vstupem
        # (starej řetězec se zahodí, drží ho jen nástroj v retired, než doprolíná)
        self.output = self.process(flow) if flow is not None else None
        return self.output

    def process(self, flow):
        raise NotImplementedError


FILTER_MODES = ("Low-pass", "Band-pass", "High-pass")


class FilterBlock(EffectBlock):
    """filtr s rezonancí (pyo SVF). Cutoff může otevírat obálka noty a rozhoupat LFO (wobble).

    filtr nechá projít jen část frekvencí: Low-pass hloubky (zvuk ztmavne),
    High-pass výšky (zeslábne), Band-pass jen pásmo kolem Cutoff.
    """

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
        # o kolik obálka otevře filtr: 1 + Envelope * 8 * obálka (pro každej hlas zvlášť)
        # tohle se staví jednou tady, ne v process, protože obálka nástroje se nemění
        self.env_amount = Sig(self.values["Envelope"], mul=8)
        self.opening = Sig(self.instrument.envelope, mul=self.env_amount, add=1)

    def set(self, label, value):
        super().set(label, value)
        if label == "Mode":
            self.mode.value = round(value) / 2   # 0, 1, 2 -> 0, 0.5, 1

    def process(self, flow):
        # LFO kolem 1 (třeba 0.5..1.5 při Wobble 0.5), kterým se násobí Cutoff
        self.lfo = Sine(freq=self.values["Wobble rate"], mul=self.values["Wobble"], add=1)
        self.moving = Sig(self.lfo, mul=self.values["Cutoff"])
        cutoff = self.moving
        # má zvuk shora stejně hlasů jako obálka? pak jsou noty pořád oddělený (žádnej Delay/Reverb nad tím)
        if len(flow) == len(self.instrument.envelope):
            # zvlášť pro každou notu: obálka posune cutoff až 9x výš
            self.opened = Sig(self.moving, mul=self.opening)
            cutoff = self.opened
        # pojistka, ať se cutoff nedostane mimo rozumný rozsah (SVF by mohl blbnout)
        self.cutoff = Clip(cutoff, 20, 18000)
        return SVF(flow, freq=self.cutoff, q=self.values["Resonance"], type=self.mode)


class ShaperBlock(EffectBlock):
    """vlastní operace se signálem (waveshaping): každej vzorek x projde křivkou y = curve(x).

    křivku si spočítáme sami do tabulky (TABLE_SIZE bodů pro x od -1 do 1)
    a pyo Lookup pak pro každej vzorek jen najde hodnotu v tabulce
    (počítat tanh 44100x za vteřinu pro každej hlas v Pythonu by nestíhalo, tabulka jo).
    Mix prolíná původní (0) a upravenej (1) zvuk.
    potomek (Distortion, Bitcrush) jen řekne, jakou má křivku.
    """

    SHAPE = ""          # popisek slideru, kterej mění tvar křivky
    TABLE_SIZE = 4096

    def __init__(self, instrument):
        super().__init__(instrument)
        self.table = keep(DataTable(self.TABLE_SIZE))
        self._draw_curve()

    def set(self, label, value):
        super().set(label, value)
        if label == self.SHAPE:
            self._draw_curve()   # jinej tvar = přepočítat celou tabulku

    def _draw_curve(self):
        amount = self.get(self.SHAPE)
        # x rovnoměrně od -1 do 1 (bod 0 = -1, poslední bod = 1)
        xs = [2 * i / (self.TABLE_SIZE - 1) - 1 for i in range(self.TABLE_SIZE)]
        self.table.replace([self.curve(x, amount) for x in xs])

    def curve(self, x: float, amount: float) -> float:
        raise NotImplementedError

    def process(self, flow):
        # Clip, protože Lookup bere index jen -1..1, hlasitější vzorky by koukaly mimo tabulku
        self.shaped = Lookup(self.table, index=Clip(flow, -1, 1))
        return Interp(flow, self.shaped, interp=self.values["Mix"])


class DistortionBlock(ShaperBlock):
    """zkreslení: tanh zaobleně ořízne vrcholy vlny, přibudou vyšší harmonický (zvuk je drsnější)."""

    NAME = "Distortion"
    SHAPE = "Drive"
    PARAMS = [
        Param("Drive", 1, 50, 5, log=True, help="How hard the wave is pushed into the curve: "
                                                "more drive, flatter tops, rougher sound."),
        Param("Mix", 0, 1, 1, help="0 = original sound, 1 = fully distorted."),
    ]

    def curve(self, x, drive):
        # tanh malý čísla skoro nemění, velký zaobleně stáhne k ±1, takže drive * x = jak moc se vlna "přepálí".
        # dělení tanh(drive) zajistí, že x = 1 dá zase 1 (hlasitost se nezmění).
        return math.tanh(drive * x) / math.tanh(drive)


class BitcrushBlock(ShaperBlock):
    """snížení bitový hloubky: vlna smí mít jen pár úrovní, vznikaj schody (zní to rozbitě, digitálně)."""

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


class DelayBlock(EffectBlock):
    """ozvěna: zpožděná kopie zvuku, část se vrací zpátky a opakuje se (pokaždý slabší)."""

    NAME = "Delay"
    PARAMS = [
        Param("Time", 0.02, 2, 0.25, "s", log=True, help="Time between echoes."),
        Param("Feedback", 0, 0.95, 0.4, help="How much of each echo comes back again."),
        Param("Mix", 0, 1, 0.4, help="How loud the echoes are next to the original."),
    ]

    def process(self, flow):
        self.mixed = Mix(flow, voices=1)
        # maxdelay=2: na kolik sekund si Delay připraví buffer, víc než 2 s nejde (proto max Time 2)
        # Feedback max 0.95, při 1 by se ozvěna nikdy neztišila
        self.echo = Delay(self.mixed, delay=self.values["Time"], feedback=self.values["Feedback"],
                          maxdelay=2)
        # původní zvuk + ozvěny ztlumený Mixem (vlevo jsou nový objekty, takže operátory vpoho)
        return self.mixed + self.echo * self.values["Mix"]


class ReverbBlock(EffectBlock):
    """dozvuk místnosti: zvuk se rozplyne jako v sále (spousta hustých odrazů, který doznívaj)."""

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


# bloky, který nabízí menu "Add block", v tomhle pořadí (zdroje, pak efekty, mezi nima čára)
CATALOG = [OscillatorBlock, NoiseBlock, SamplerBlock,
           FilterBlock, DistortionBlock, BitcrushBlock, DelayBlock, ReverbBlock]
