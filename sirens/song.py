"""Píseň: stopy, patterny s notama, aranžmá na časový ose a automatizace sliderů.

    Song
     ├─ tempo (BPM), délka časový osy v taktech
     └─ Track (stopa) x až 8
         ├─ instrument   vlastní nástroj (obálka + rack bloků), hraje na svým MIDI kanálu
         ├─ patterns     A..H: noty, každej pattern 1, 2 nebo 4 takty dlouhej
         ├─ current      pattern, kterej se právě edituje (a hraje v režimu Loop)
         ├─ arrangement  takt -> pattern (časová osa); prázdnej takt = stopa mlčí
         └─ muted

takt = prostě kus času, 4 doby (doba = jedno "ťuk" při počítání do rytmu),
tempo v BPM říká, kolik dob je za minutu, takže doba trvá 60 / tempo sekund.

Čas v patternu se počítá v krocích: 16 kroků na takt, takže jeden krok je
šestnáctinová nota (4 kroky na dobu). Takt má vždycky 4 doby.
Přehrávač ale tiká jemnějc: TICKS_PER_BAR = 48 tiků na takt, takže jeden krok
mřížky jsou 3 tiky. (Dřív tu byly i trioly s jiným počtem kroků na takt,
ty jsme zahodili, ať je to jednodušší.)

Automatizace patří k nástroji a k blokům (owner.automation): pro každej slider
slovník takt -> hodnota, a mezi zadanýma taktama se hodnota plynule mění.
"""

from dataclasses import dataclass

from sirens.audio.instrument import Instrument

BEATS_PER_BAR = 4
STEPS_PER_BAR = 16                          # kroků na takt: šestnáctiny, 4 na dobu
TICKS_PER_BAR = 48                          # tiky přehrávače na takt (48 / 16 = 3 tiky na krok)
TICKS_PER_STEP = TICKS_PER_BAR // STEPS_PER_BAR
PATTERN_NAMES = "ABCDEFGH"
MAX_TRACKS = 8
MIN_BARS, MAX_BARS = 4, 512                 # rozsah délky písně v taktech


@dataclass
class Note:
    step: int      # začátek v krocích od začátku patternu
    pitch: int     # MIDI číslo noty = jak vysoko (60 = C4, +1 = o půltón výš, +12 = o oktávu výš)
    length: int    # délka v krocích
    velocity: int = 100    # síla úhozu 1..127 (MIDI velocity): jak nahlas nota zazní


class Pattern:
    def __init__(self, bars: int = 1):
        self.bars = bars
        self.notes: list[Note] = []

    def steps(self) -> int:
        return self.bars * STEPS_PER_BAR   # kolik kroků má celej pattern

    def ticks_per_step(self) -> int:
        """Kolik tiků přehrávače trvá jeden krok (pořád 3)."""
        return TICKS_PER_STEP

    def note_at(self, step: int, pitch: int):
        """Nota, která na daným kroku a výšce zní (nebo None)."""
        for note in self.notes:
            if note.pitch == pitch and note.step <= step < note.step + note.length:
                return note
        return None


class Track:
    def __init__(self, name: str, channel: int):
        self.name = name
        self.instrument = Instrument(channel)
        self.patterns = {name: Pattern() for name in PATTERN_NAMES}   # A až H, ze začátku prázdný
        self.current = "A"
        self.arrangement: dict[int, str] = {}     # číslo taktu (od 0) -> jméno patternu
        self.muted = False
        self.view_low = 48          # nejnižší nota zobrazená v editoru patternu (C3), jen pohled

    def automated_owners(self):
        """Nástroj a jeho bloky: všechno, co může mít automatizovaný slidery."""
        return [self.instrument] + self.instrument.rack.blocks

    def pattern_at_bar(self, bar: int):
        """Pattern a takt uvnitř něj, kterej stopa hraje v daným taktu písně (nebo None).

        Víc taktů za sebou se stejným patternem = pattern hraje dál (2. takt, 3. takt...).
        """
        name = self.arrangement.get(bar)
        if name is None:
            return None
        # couvám doleva, dokud je tam pořád ten samej pattern -> start = kde tenhle kus začal
        start = bar
        while self.arrangement.get(start - 1) == name:
            start -= 1
        pattern = self.patterns[name]
        # % pattern.bars: 1taktovej pattern na 3 taktech za sebou hraje 3x svůj jedinej takt
        return pattern, (bar - start) % pattern.bars


class Song:
    def __init__(self):
        self.tempo = 110                    # BPM, dob za minutu
        self.bars = 32                      # délka časový osy
        self.tracks: list[Track] = []

    def add_track(self) -> Track | None:
        """Nová stopa na volným MIDI kanálu (1-8). None, když už je jich maximum."""
        used = {track.instrument.channel for track in self.tracks}
        free = [ch for ch in range(1, MAX_TRACKS + 1) if ch not in used]
        if not free:
            return None
        track = Track(f"Track {len(self.tracks) + 1}", free[0])
        self.tracks.append(track)
        return track

    def remove_track(self, track: Track):
        track.instrument.rack.clear()       # nejdřív ztišit nástroj (rack bez bloků = ticho)
        self.tracks.remove(track)

    def last_bar(self) -> int:
        """Počet taktů do konce posledního použitýho taktu (aspoň 1).

        Takty za délkou písně se nepočítaj: po zkrácení písně zůstanou uložený,
        ale nehrajou (po prodloužení se zase vrátí).
        """
        # list(arrangement): kopie klíčů, kdyby do toho zrovna někdo kreslil z jinýho vlákna
        used = [bar for track in self.tracks for bar in list(track.arrangement) if bar < self.bars]
        return max(used) + 1 if used else 1     # +1, protože takty se číslujou od 0

    def outputs(self):
        """Výstupy všech nástrojů pro mix v enginu."""
        return [track.instrument.output for track in self.tracks]


def lane_value(lane: dict, position: float):
    """Hodnota automatizace v daným místě (v taktech, např. 3.5 = půlka 4. taktu).

    Hodnota zadaná pro takt platí na jeho začátku, mezi dvěma zadanýma taktama
    se mění lineárně (rovnou čarou), před prvním a za posledním zůstává stejná.
    Prázdná lane = None.
    """
    if not lane:
        return None
    bars = sorted(list(lane))
    if position <= bars[0]:
        return lane[bars[0]]
    # zip(bars, bars[1:]) dá dvojice sousedů: (1. a 2.), (2. a 3.)...
    for left, right in zip(bars, bars[1:]):
        if left <= position < right:
            t = (position - left) / (right - left)      # 0 = na levým bodu, 1 = na pravým
            return lane[left] + t * (lane[right] - lane[left])
    return lane[bars[-1]]
