"""Přehrávání písně: hodiny tikaj TICKS_PER_BAR krát za takt a na každým tiku
pošlou nástrojům noty, který na něj připadaj.

Tiků je 48 na takt, aby se do taktu vešly kroky všech mřížek (viz song.py):
pattern s mřížkou 16 má krok každý 3 tiky, s mřížkou 12 každý 4 tiky.

Hodiny běžej ve vlastním vlákně (threading): spí do času dalšího tiku a pak
zavolaj _on_tick(). Proč ne časovač okna? ten by kolísal podle toho, jak dlouho
trvá překreslení, vlastní vlákno ne. (Pyo Metro by bylo přesnější, ale noty
poslaný z jeho zpětnýho volání ve zvukovým vlákně pyo zahodí.)

Dva režimy:
    Loop  každá stopa dokola hraje svůj právě editovanej pattern (na zkoušení)
    Song  hraje se aranžmá z časový osy od start_bar do konce, pak znova,
          a navíc se podle časový osy mění automatizovaný slidery

Příznak once (pro export do WAV, viz export.py): v režimu Song se na konci
písně neopakuje, hodiny se samy zastavěj.
"""

import threading
import time
import traceback

from sirens.song import BEATS_PER_BAR, TICKS_PER_BAR, lane_value


class Player:
    def __init__(self, engine, song):
        self.engine = engine
        self.song = song
        self.mode = "Loop"
        self.playing = False
        self.start_bar = 0            # odkud hrát v režimu Song (takt, od 0)
        self.tick = 0                 # tik, kterej se zahraje příště (od začátku písně / smyčky)
        self.position = 0             # tik, kterej právě hraje (pro ukazatel v UI)
        self.pending = []             # [zbývá_tiků, kanál, nota]: noty, co čekaj na vypnutí
        self.thread = None
        self.once = False             # Song jen jednou: na konci se zastavit (export)

    def _tick_time(self) -> float:
        """Délka jednoho tiku v sekundách: doba = 60 / tempo, takt = 4 doby = 48 tiků.

        třeba tempo 120: doba 0.5 s, takt 2 s, tik 2 / 48 = asi 42 ms.
        """
        return 60 / self.song.tempo * BEATS_PER_BAR / TICKS_PER_BAR

    def set_tempo(self, bpm: float):
        self.song.tempo = bpm          # hodiny si ho přečtou u dalšího tiku, nic víc není potřeba

    def play(self, from_tick: int | None = None):
        """Spustí hodiny. from_tick: kde začít (např. po Undo pokračovat, kde to hrálo);
        bez něj od začátku smyčky / od start_bar. Když je tik za koncem
        (píseň se mezitím zkrátila), _on_tick ho vrátí na začátek."""
        if self.playing:
            return
        if self.thread is not None:
            self.thread.join()         # hodiny, co skončily samy (once), můžou ještě dospávat tik
        if from_tick is not None:
            self.tick = from_tick
        else:
            self.tick = self.start_bar * TICKS_PER_BAR if self.mode == "Song" else 0
        self.playing = True
        # daemon=True: vlákno neblokuje konec programu, když se zavře okno
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.playing = False           # tímhle se smyčka v _run zastaví
        if self.thread is not None:
            self.thread.join()         # počkáme, až hodiny doběhnou
            self.thread = None
        # všechno, co ještě zní, vypnout (velocity 0 = puštěná klávesa), jinak by to viselo
        for _, channel, pitch in self.pending:
            self.engine.send_note(channel, pitch, 0)
        self.pending = []

    def toggle(self):
        self.stop() if self.playing else self.play()

    def loop_ticks(self) -> int:
        """Délka smyčky v režimu Loop (v tikách): nejdelší z právě editovaných patternů."""
        # default: když nejsou stopy, smyčka je prostě 1 takt
        return max((t.patterns[t.current].bars * TICKS_PER_BAR for t in self.song.tracks),
                   default=TICKS_PER_BAR)

    def _run(self):
        """Hodiny: tiky v pravidelných intervalech, dokud playing.

        Čas dalšího tiku se přičítá k minulýmu (ne k "teď"), takže se drobný
        zpoždění nesčítaj a rytmus neujíždí.
        """
        next_time = time.perf_counter()        # přesný hodinky na měření krátkých časů
        while self.playing:
            try:
                self._on_tick()
            except Exception:
                traceback.print_exc()      # chybu vypíšeme, ale hodiny jedou dál
            next_time += self._tick_time()
            delay = next_time - time.perf_counter()
            if delay > 0:                  # když jsme pozadu, nespíme vůbec a dotáhneme to
                time.sleep(delay)

    def _on_tick(self):
        """Jeden tik (volá se ve vlákně hodin)."""
        # 1) vypnout noty, kterým právě skončila délka
        still = []
        for item in self.pending:
            item[0] -= 1
            if item[0] <= 0:
                self.engine.send_note(item[1], item[2], 0)
            else:
                still.append(item)
        self.pending = still

        # 2) kde v písni jsme (na konci znova od začátku)
        if self.mode == "Loop":
            self.tick %= self.loop_ticks()         # zbytek po dělení = dokola v rámci smyčky
        elif self.tick >= self.song.last_bar() * TICKS_PER_BAR:
            if self.once:
                self._finish()             # export: píseň dohrála, hodiny končej
                return
            # zpátky na start_bar, ale jen když ještě leží v písni, jinak od 0
            self.tick = self.start_bar * TICKS_PER_BAR if self.start_bar < self.song.last_bar() else 0
        # divmod = celočíselný dělení a zbytek naráz: tik 100 -> takt 2, tik 4 v taktu
        bar, tick_in_bar = divmod(self.tick, TICKS_PER_BAR)

        # 3) zahrát noty, který na tomhle tiku začínaj
        for track in self.song.tracks:
            if self.mode == "Loop":
                pattern = track.patterns[track.current]
                # kratší pattern se ve smyčce opakuje (1taktovej 4x ve 4taktový smyčce)
                tick_in_pattern = self.tick % (pattern.bars * TICKS_PER_BAR)
            else:
                # automatizace jede i u ztlumený stopy, mute jen nepouští noty
                self._automate(track, bar + tick_in_bar / TICKS_PER_BAR)
                found = track.pattern_at_bar(bar)
                if found is None:
                    continue                       # v tomhle taktu stopa nemá nic
                pattern, bar_in_pattern = found
                tick_in_pattern = bar_in_pattern * TICKS_PER_BAR + tick_in_bar
            if not track.muted:
                self._play_notes(track, pattern, tick_in_pattern)

        self.position = self.tick
        self.tick += 1

    def _finish(self):
        """Konec písně v režimu once (volá se ve vlákně hodin).

        Pozor, nesmí volat stop(): ten čeká na doběhnutí vlákna, tedy sám na sebe,
        a to nejde (join na vlastní vlákno skončí chybou). Takže jen vypne čekající noty a shodí playing,
        smyčka v _run pak skončí sama. UI si toho všimne ve svým časovači
        (player.playing je False).
        """
        for _, channel, pitch in self.pending:
            self.engine.send_note(channel, pitch, 0)
        self.pending = []
        self.playing = False

    def _play_notes(self, track, pattern, tick_in_pattern: int):
        """Zahraje noty patternu, který začínaj na daným tiku (tiky od začátku patternu).

        Tik, kterej nepadne na začátek kroku mřížky patternu, nic nespouští.
        """
        per_step = pattern.ticks_per_step()
        step, rest = divmod(tick_in_pattern, per_step)
        if rest:
            return                   # jsme mezi kroky, tady nic nezačíná
        channel = track.instrument.channel
        for note in list(pattern.notes):         # list(): uživatel může zrovna kreslit noty
            if note.step == step:
                self.engine.send_note(channel, note.pitch, note.velocity)
                # vypnutí si poznamenáme: délka v krocích převedená na tiky
                self.pending.append([note.length * per_step, channel, note.pitch])

    def _automate(self, track, position: float):
        """Nastaví automatizovaný slidery stopy podle místa v písni (v taktech)."""
        for owner in track.automated_owners():
            # list(): uživatel může automatizaci zrovna kreslit (měnit slovník) v jiným vlákně
            for label, lane in list(owner.automation.items()):
                value = lane_value(lane, position)
                # 1e-6 = skoro nula: když se hodnota nezměnila, zbytečně ji neposílat
                if value is not None and abs(value - owner.get(label)) > 1e-6:
                    owner.set(label, value)

    def close(self):
        self.stop()
