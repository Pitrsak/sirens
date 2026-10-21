"""Píseň: stopy, patterny s notami, aranžmá na časové ose a automatizace sliderů.

    Song
     ├─ tempo (BPM), délka časové osy v taktech
     └─ Track (stopa) x až 8
         ├─ instrument   vlastní nástroj (obálka + rack bloků), hraje na svém MIDI kanálu
         ├─ patterns     A..H: noty, každý pattern 1, 2 nebo 4 takty dlouhý
         ├─ current      pattern, který se právě edituje (a hraje v režimu Loop)
         ├─ arrangement  takt -> pattern (časová osa); prázdný takt = stopa mlčí
         └─ muted

Čas v patternu se počítá v krocích. Kolik kroků má takt, určuje mřížka
patternu (grid): 16 = šestnáctiny, 12 = osminové trioly (3 na dobu),
24 = šestnáctinové trioly (6 na dobu). Takt má vždy 4 doby.
Přehrávač počítá v jemnějších tikách: TICKS_PER_BAR = 48 je nejmenší číslo
dělitelné 16, 12 i 24, takže každý krok každé mřížky začíná přesně na tiku
(krok mřížky 16 = 3 tiky, mřížky 12 = 4 tiky, mřížky 24 = 2 tiky).

Automatizace patří k nástroji a k blokům (owner.automation): pro každý slider
slovník takt -> hodnota; mezi zadanými takty se hodnota plynule mění.
"""

from dataclasses import dataclass

from sirens.audio.instrument import Instrument

BEATS_PER_BAR = 4
GRIDS = (16, 12, 24)                        # možné mřížky: kroků na takt
TICKS_PER_BAR = 48                          # tiky přehrávače na takt (viz výše)
PATTERN_NAMES = "ABCDEFGH"
MAX_TRACKS = 8
MIN_BARS, MAX_BARS = 4, 512                 # rozsah délky písně v taktech


@dataclass
class Note:
    step: int      # začátek v krocích od začátku patternu
    pitch: int     # MIDI číslo noty (60 = C4)
    length: int    # délka v krocích
    velocity: int = 100    # síla úhozu 1..127 (MIDI velocity): jak hlasitě nota zazní


class Pattern:
    def __init__(self, bars: int = 1, grid: int = 16):
        self.bars = bars
        self.grid = grid               # kroků na takt (jedna z GRIDS)
        self.notes: list[Note] = []

    def steps(self) -> int:
        return self.bars * self.grid

    def ticks_per_step(self) -> int:
        """Kolik tiků přehrávače trvá jeden krok (16 -> 3, 12 -> 4, 24 -> 2)."""
        return TICKS_PER_BAR // self.grid

    def set_grid(self, grid: int):
        """Změní mřížku a přepočítá noty ve stejném poměru (krok 4 z 16 = krok 3 z 12).

        Nota, která po zaokrouhlení padne na stejné místo jako jiná (stejná výška
        i krok) nebo za konec patternu, se zahodí. Když by předchozí nota stejné
        výšky přesahovala do další, zkrátí se.
        """
        old, self.grid = self.grid, grid
        kept = []
        for note in sorted(self.notes, key=lambda n: n.step):
            # zaokrouhlení: int(x + 0.5), půlka vždy nahoru (Pythonové round(2.5) dá 2, k sudému číslu)
            step = int(note.step * grid / old + 0.5)
            length = max(1, int(note.length * grid / old + 0.5))
            if step >= self.steps() or any(n.pitch == note.pitch and n.step == step for n in kept):
                continue
            for other in kept:
                if other.pitch == note.pitch and other.step < step < other.step + other.length:
                    other.length = step - other.step
            kept.append(Note(step, note.pitch, min(length, self.steps() - step), note.velocity))
        self.notes = kept

    def note_at(self, step: int, pitch: int):
        """Nota, která na daném kroku a výšce zní (nebo None)."""
        for note in self.notes:
            if note.pitch == pitch and note.step <= step < note.step + note.length:
                return note
        return None


class Track:
    def __init__(self, name: str, channel: int):
        self.name = name
        self.instrument = Instrument(channel)
        self.patterns = {name: Pattern() for name in PATTERN_NAMES}
        self.current = "A"
        self.arrangement: dict[int, str] = {}
        self.muted = False
        self.view_low = 48          # nejnižší nota zobrazená v editoru patternu (C3)

    def automated_owners(self):
        """Nástroj a jeho bloky: všechno, co může mít automatizované slidery."""
        return [self.instrument] + self.instrument.rack.blocks

    def pattern_at_bar(self, bar: int):
        """Pattern a takt uvnitř něj, který stopa hraje v daném taktu písně (nebo None).

        Víc taktů za sebou se stejným patternem = pattern hraje dál (2. takt, 3. takt...).
        """
        name = self.arrangement.get(bar)
        if name is None:
            return None
        start = bar
        while self.arrangement.get(start - 1) == name:
            start -= 1
        pattern = self.patterns[name]
        return pattern, (bar - start) % pattern.bars


class Song:
    def __init__(self):
        self.tempo = 110
        self.bars = 32                      # délka časové osy
        self.tracks: list[Track] = []

    def add_track(self) -> Track | None:
        """Nová stopa na volném MIDI kanálu (1-8). None, když už je jich maximum."""
        used = {track.instrument.channel for track in self.tracks}
        free = [ch for ch in range(1, MAX_TRACKS + 1) if ch not in used]
        if not free:
            return None
        track = Track(f"Track {len(self.tracks) + 1}", free[0])
        self.tracks.append(track)
        return track

    def remove_track(self, track: Track):
        track.instrument.rack.clear()
        self.tracks.remove(track)

    def last_bar(self) -> int:
        """Počet taktů do konce posledního použitého taktu (aspoň 1).

        Takty za délkou písně se nepočítají: po zkrácení písně zůstanou uložené,
        ale nehrají (po prodloužení se vrátí).
        """
        used = [bar for track in self.tracks for bar in list(track.arrangement) if bar < self.bars]
        return max(used) + 1 if used else 1

    def outputs(self):
        """Výstupy všech nástrojů pro mix v enginu."""
        return [track.instrument.output for track in self.tracks]


def lane_value(lane: dict, position: float):
    """Hodnota automatizace v daném místě (v taktech, např. 3.5 = půlka 4. taktu).

    Hodnota zadaná pro takt platí na jeho začátku; mezi dvěma zadanými takty
    se mění lineárně, před prvním a za posledním zůstává stejná. Prázdná = None.
    """
    if not lane:
        return None
    bars = sorted(list(lane))
    if position <= bars[0]:
        return lane[bars[0]]
    for left, right in zip(bars, bars[1:]):
        if left <= position < right:
            t = (position - left) / (right - left)
            return lane[left] + t * (lane[right] - lane[left])
    return lane[bars[-1]]
