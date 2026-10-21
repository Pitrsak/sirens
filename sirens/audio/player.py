"""Přehrávání písně: hodiny tikají TICKS_PER_BAR krát za takt a na každém tiku
pošlou nástrojům noty, které na něj připadají.

Tiků je 48 na takt, aby se do taktu vešly kroky všech mřížek (viz song.py):
pattern s mřížkou 16 má krok každé 3 tiky, s mřížkou 12 každé 4 tiky.

Hodiny běží ve vlastním vlákně (threading): spí do času dalšího tiku a pak
zavolá _on_tick(). Časovač okna by kolísal podle toho, jak dlouho trvá
překreslení, vlastní vlákno ne. (Pyo Metro by bylo přesnější, ale noty poslané
z jeho zpětného volání ve zvukovém vlákně pyo zahodí.)

Dva režimy:
    Loop  každá stopa dokola hraje svůj právě editovaný pattern (na zkoušení)
    Song  hraje se aranžmá z časové osy od start_bar do konce, pak znovu
          a navíc se podle časové osy mění automatizované slidery

Příznak once (pro export do WAV, viz export.py): v režimu Song se na konci
písně neopakuje, hodiny se samy zastaví.
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
        self.start_bar = 0
        self.tick = 0                 # tik, který se zahraje příště (od začátku písně / smyčky)
        self.position = 0             # tik, který právě hraje (pro ukazatel v UI)
        self.pending = []             # [zbývá_tiků, kanál, nota]: noty čekající na vypnutí
        self.thread = None
        self.once = False             # Song jen jednou: na konci se zastavit (export)

    def _tick_time(self) -> float:
        """Délka jednoho tiku v sekundách: doba = 60 / tempo, takt = 4 doby = 48 tiků."""
        return 60 / self.song.tempo * BEATS_PER_BAR / TICKS_PER_BAR

    def set_tempo(self, bpm: float):
        self.song.tempo = bpm          # hodiny si ho přečtou u dalšího tiku

    def play(self, from_tick: int | None = None):
        """Spustí hodiny. from_tick: kde začít (např. po Undo pokračovat, kde hrál);
        bez něj od začátku smyčky / od start_bar. Když je tik za koncem
        (píseň se mezitím zkrátila), _on_tick ho vrátí na začátek."""
        if self.playing:
            return
        if self.thread is not None:
            self.thread.join()         # hodiny, které skončily samy (once), můžou ještě dospávat tik
        if from_tick is not None:
            self.tick = from_tick
        else:
            self.tick = self.start_bar * TICKS_PER_BAR if self.mode == "Song" else 0
        self.playing = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.playing = False
        if self.thread is not None:
            self.thread.join()         # počkáme, až hodiny doběhnou
            self.thread = None
        for _, channel, pitch in self.pending:
            self.engine.send_note(channel, pitch, 0)
        self.pending = []

    def toggle(self):
        self.stop() if self.playing else self.play()

    def loop_ticks(self) -> int:
        """Délka smyčky v režimu Loop (v tikách): nejdelší z právě editovaných patternů."""
        return max((t.patterns[t.current].bars * TICKS_PER_BAR for t in self.song.tracks),
                   default=TICKS_PER_BAR)

    def _run(self):
        """Hodiny: tiky v pravidelných intervalech, dokud playing.

        Čas dalšího tiku se přičítá k minulému (ne k "teď"), takže se drobná
        zpoždění nesčítají a rytmus neujíždí.
        """
        next_time = time.perf_counter()
        while self.playing:
            try:
                self._on_tick()
            except Exception:
                traceback.print_exc()      # chybu vypíšeme, ale hodiny jedou dál
            next_time += self._tick_time()
            delay = next_time - time.perf_counter()
            if delay > 0:
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

        # 2) kde v písni jsme (na konci znovu od začátku)
        if self.mode == "Loop":
            self.tick %= self.loop_ticks()
        elif self.tick >= self.song.last_bar() * TICKS_PER_BAR:
            if self.once:
                self._finish()             # export: píseň dohrála, hodiny končí
                return
            self.tick = self.start_bar * TICKS_PER_BAR if self.start_bar < self.song.last_bar() else 0
        bar, tick_in_bar = divmod(self.tick, TICKS_PER_BAR)

        # 3) zahrát noty, které na tomto tiku začínají
        for track in self.song.tracks:
            if self.mode == "Loop":
                pattern = track.patterns[track.current]
                tick_in_pattern = self.tick % (pattern.bars * TICKS_PER_BAR)
            else:
                self._automate(track, bar + tick_in_bar / TICKS_PER_BAR)
                found = track.pattern_at_bar(bar)
                if found is None:
                    continue
                pattern, bar_in_pattern = found
                tick_in_pattern = bar_in_pattern * TICKS_PER_BAR + tick_in_bar
            if not track.muted:
                self._play_notes(track, pattern, tick_in_pattern)

        self.position = self.tick
        self.tick += 1

    def _finish(self):
        """Konec písně v režimu once (volá se ve vlákně hodin).

        Nesmí volat stop(): ten čeká na doběhnutí vlákna, tedy sám na sebe.
        Vypne čekající noty a shodí playing; smyčka v _run pak skončí sama.
        UI si toho všimne ve svém časovači (player.playing je False).
        """
        for _, channel, pitch in self.pending:
            self.engine.send_note(channel, pitch, 0)
        self.pending = []
        self.playing = False

    def _play_notes(self, track, pattern, tick_in_pattern: int):
        """Zahraje noty patternu, které začínají na daném tiku (tiky od začátku patternu).

        Tik, který nepadne na začátek kroku mřížky patternu, nic nespouští.
        """
        per_step = pattern.ticks_per_step()
        step, rest = divmod(tick_in_pattern, per_step)
        if rest:
            return
        channel = track.instrument.channel
        for note in list(pattern.notes):         # list(): uživatel může zrovna kreslit noty
            if note.step == step:
                self.engine.send_note(channel, note.pitch, note.velocity)
                self.pending.append([note.length * per_step, channel, note.pitch])

    def _automate(self, track, position: float):
        """Nastaví automatizované slidery stopy podle místa v písni (v taktech)."""
        for owner in track.automated_owners():
            # list(): uživatel může automatizaci zrovna kreslit (měnit slovník) v jiném vlákně
            for label, lane in list(owner.automation.items()):
                value = lane_value(lane, position)
                if value is not None and abs(value - owner.get(label)) > 1e-6:
                    owner.set(label, value)

    def close(self):
        self.stop()
