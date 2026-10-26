"""Export písně do WAV.

pyo má v jednom programu jen jeden server a ten hraje v reálným čase, takže
píseň nevykreslujeme "offline" (rychlejc než realtime). Prostě ji jednou
přehrajeme v režimu Song od 1. taktu do konce posledního použitýho taktu
a nahráváme výstup serveru, tedy přesně to, co jde do repro (i s hlasitostí).
Po konci písně necháme TAIL sekund doznít dozvuk a doznění not, ať se neuříznou.

Průběh (hlavní okno volá tick() 30x za sekundu):
    píseň hraje  ->  hodiny se na konci samy zastavěj (Player.once)
    dozvuk       ->  od zastavení uplyne TAIL sekund
    hotovo       ->  konec nahrávání, přehrávač dostane zpátky svůj režim
"""

import time

from sirens.song import BEATS_PER_BAR

TAIL = 3.0     # jak dlouho po konci písně ještě nahrávat (s)


def clock(seconds: float) -> str:
    """Čas jako m:ss (např. 3:07)."""
    seconds = round(seconds)
    # // = celý minuty, % = zbylý sekundy, :02d = vždycky dvě číslice (07, ne 7)
    return f"{seconds // 60}:{seconds % 60:02d}"


class Export:
    def __init__(self, engine, player, path):
        """Hned spustí export do souboru path (Path)."""
        self.engine, self.player, self.path = engine, player, path
        self.old_mode = player.mode          # po exportu se vrátí
        self.tail_end = None                 # kdy skončí dozvuk (určí se, až píseň dohraje)
        player.stop()
        player.mode = "Song"
        player.once = True
        engine.start_recording(str(path))
        self.start = time.monotonic()        # monotonic: hodiny, který nejdou pozpátku ani při změně času v systému
        player.play(from_tick=0)             # od 1. taktu, start_bar se tu nepoužije
        self.status = ""
        self.tick()                          # první text do status

    def song_seconds(self) -> float:
        """Délka písně do konce posledního použitýho taktu: takt = 4 doby po 60 / tempo s."""
        song = self.player.song
        return song.last_bar() * BEATS_PER_BAR * 60 / song.tempo

    def tick(self) -> bool:
        """Posune export dál a obnoví status. Vrátí True, když export právě skončil.

        Volá se jen z vlákna UI. Hodiny přehrávače (jiný vlákno) jen shodí
        player.playing, všechno ostatní (stop, konec nahrávání) děláme tady.
        """
        now = time.monotonic()
        if self.tail_end is None and not self.player.playing:
            self.tail_end = now + TAIL       # píseň dohrála, teď necháme doznít
        if self.tail_end is not None and now >= self.tail_end:
            self._end()
            self.status = f"Exported to {self.path.name} ({clock(now - self.start)})."
            return True
        total = self.song_seconds() + TAIL
        self.status = f"Recording {clock(now - self.start)} / {clock(total)}. Press Stop to cancel."
        return False

    def cancel(self):
        """Zrušení (Stop nebo mezerník). Co se stihlo nahrát, v souboru zůstane."""
        elapsed = time.monotonic() - self.start
        self._end()
        self.status = (f"Export cancelled at {clock(elapsed)}. "
                       f"The part recorded so far stays in {self.path.name}.")

    def _end(self):
        self.player.stop()                   # počká na hodiny a vypne znějící noty
        self.engine.stop_recording()         # tady se WAV dopíše a zavře
        self.player.once = False
        self.player.mode = self.old_mode
