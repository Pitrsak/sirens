"""Píseň: stopy, patterny s notama a aranžmá na časový ose.

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

Čas v patternu se počítá v krocích. Normálně 16 kroků na takt, takže jeden krok je
šestnáctinová nota (4 kroky na dobu). Takt má vždycky 4 doby.
Přehrávač ale tiká jemnějc: TICKS_PER_BAR = 48 tiků na takt, takže jeden krok
mřížky jsou 3 tiky. Pattern si ale může přepnout jemnou mřížku (Fine, 48 kroků
na takt), to je pak krok = 1 tik. Hodí se na linky hraný "od ruky", který
do šestnáctin nesednou (synth ze Sunspots).
"""

from dataclasses import dataclass

from sirens.audio.instrument import Instrument

BEATS_PER_BAR = 4
STEPS_PER_BAR = 16                          # kroků na takt: šestnáctiny, 4 na dobu
TICKS_PER_BAR = 48                          # tiky přehrávače na takt (48 / 16 = 3 tiky na krok)
GRIDS = (STEPS_PER_BAR, TICKS_PER_BAR)      # mřížky patternu: 16 kroků na takt, nebo jemná 48 (krok = tik)
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
    def __init__(self, bars: int = 1, grid: int = STEPS_PER_BAR):
        self.bars = bars
        self.grid = grid               # kroků na takt: 16 (šestnáctiny) nebo 48 (jemná mřížka)
        self.notes: list[Note] = []

    def steps(self) -> int:
        return self.bars * self.grid   # kolik kroků má celej pattern

    def ticks_per_step(self) -> int:
        """Kolik tiků přehrávače trvá jeden krok: 48 / 16 = 3, u jemný mřížky 48 / 48 = 1."""
        return TICKS_PER_BAR // self.grid

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
