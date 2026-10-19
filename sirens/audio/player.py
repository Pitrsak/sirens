"""Přehrávání písně: každý krok (šestnáctinu) pošle nástrojům noty, které na něj připadají.

Hodiny běží ve vlastním vlákně (threading): spí do času dalšího kroku a pak
zavolá _on_step(). Časovač okna by kolísal podle toho, jak dlouho trvá
překreslení, vlastní vlákno ne. (Pyo Metro by bylo přesnější, ale noty poslané
z jeho zpětného volání ve zvukovém vlákně pyo zahodí.)

Dva režimy:
    Loop  každá stopa dokola hraje svůj právě editovaný pattern (na zkoušení)
    Song  hraje se aranžmá z časové osy od start_bar do konce, pak znovu
          a navíc se podle časové osy mění automatizované slidery
"""

import threading
import time
import traceback

from sirens.song import STEPS_PER_BAR, lane_value

VELOCITY = 100


class Player:
    def __init__(self, engine, song):
        self.engine = engine
        self.song = song
        self.mode = "Loop"
        self.playing = False
        self.start_bar = 0
        self.step = 0                 # krok, který se zahraje příště (od začátku písně / smyčky)
        self.position = 0             # krok, který právě hraje (pro ukazatel v UI)
        self.pending = []             # [zbývá_kroků, kanál, nota]: noty čekající na vypnutí
        self.thread = None

    def _step_time(self) -> float:
        """Délka jednoho kroku v sekundách: čtvrťová nota = 60 / tempo, krok je čtvrtina z ní."""
        return 60 / self.song.tempo / 4

    def set_tempo(self, bpm: float):
        self.song.tempo = bpm          # hodiny si ho přečtou u dalšího kroku

    def play(self):
        if self.playing:
            return
        self.step = self.start_bar * STEPS_PER_BAR if self.mode == "Song" else 0
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

    def loop_steps(self) -> int:
        """Délka smyčky v režimu Loop: nejdelší z právě editovaných patternů."""
        return max((t.patterns[t.current].steps() for t in self.song.tracks), default=STEPS_PER_BAR)

    def _run(self):
        """Hodiny: kroky v pravidelných intervalech, dokud playing.

        Čas dalšího kroku se přičítá k minulému (ne k "teď"), takže se drobná
        zpoždění nesčítají a rytmus neujíždí.
        """
        next_time = time.perf_counter()
        while self.playing:
            try:
                self._on_step()
            except Exception:
                traceback.print_exc()      # chybu vypíšeme, ale hodiny jedou dál
            next_time += self._step_time()
            delay = next_time - time.perf_counter()
            if delay > 0:
                time.sleep(delay)

    def _on_step(self):
        """Jeden krok (volá se ve vlákně hodin)."""
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
            self.step %= self.loop_steps()
        elif self.step >= self.song.last_bar() * STEPS_PER_BAR:
            self.step = self.start_bar * STEPS_PER_BAR if self.start_bar < self.song.last_bar() else 0
        bar, step_in_bar = divmod(self.step, STEPS_PER_BAR)

        # 3) zahrát noty, které na tomto kroku začínají
        for track in self.song.tracks:
            if self.mode == "Loop":
                pattern = track.patterns[track.current]
                position = self.step % pattern.steps()
            else:
                self._automate(track, bar + step_in_bar / STEPS_PER_BAR)
                found = track.pattern_at_bar(bar)
                if found is None:
                    continue
                pattern, bar_in_pattern = found
                position = bar_in_pattern * STEPS_PER_BAR + step_in_bar
            if track.muted:
                continue
            channel = track.instrument.channel
            for note in pattern.notes:
                if note.step == position:
                    self.engine.send_note(channel, note.pitch, VELOCITY)
                    self.pending.append([note.length, channel, note.pitch])

        self.position = self.step
        self.step += 1

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
