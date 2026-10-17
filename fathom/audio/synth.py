"""Polyfonní subtraktivní syntezátor postavený nad pyo.

Signálový řetězec jednoho hlasu (Voice):
    OSC1 + OSC2 + šum -> filtr (MoogLP) -> zesilovač (ADSR obálka)

Společný řetězec za všemi hlasy (Synth):
    součet hlasů -> drive (vlastní waveshaper) -> bitcrusher (vlastní kvantizace)
    -> delay -> hlasitost -> výstup
"""

from pyo import (Adsr, Clip, DataTable, Delay, Lookup, Mix, MoogLP, Noise, Osc,
                 Round, Sig, Sine, SigTo, midiToHz)

from fathom.audio.params import SYNTH_DEFAULTS
from fathom.audio.tables import WAVE_NAMES, additive_wave, drive_curve

VOICE_COUNT = 6       # kolik tónů může znít současně
VOICE_GAIN = 0.25     # hlasitost jednoho hlasu, aby součet hlasů nepřebuzil výstup

# Parametry, které se mění plynule přes SigTo (bez "cvakání" při otáčení knobem).
SMOOTH_KEYS = ("osc1_level", "osc2_level", "noise", "cutoff", "res", "env_amt",
               "lfo_rate", "lfo_depth", "drive", "delay_time", "delay_fb",
               "delay_mix", "volume")

# Mapování parametrů obálek na metody pyo objektu Adsr.
ENV_SETTERS = {"a": "setAttack", "d": "setDecay", "s": "setSustain", "r": "setRelease"}


class Voice:
    """Jeden hlas syntezátoru: dva oscilátory, šum, filtr a dvě obálky."""

    def __init__(self, synth: "Synth"):
        p = synth.sig
        self.note = None  # MIDI číslo právě hrané noty (None = hlas je volný)

        # Frekvence s portamentem: SigTo plynule dojede na novou hodnotu za čas "glide".
        self.freq = SigTo(220, time=0.0, init=220)
        self.osc1 = Osc(table=synth.waves[0], freq=self.freq)
        self.osc2 = Osc(table=synth.waves[0], freq=self.freq * synth.osc2_ratio)
        source = self.osc1 * p["osc1_level"] + self.osc2 * p["osc2_level"] + synth.noise * p["noise"]

        # Obálky: amp řídí hlasitost, fenv otevírá filtr.
        self.amp = Adsr(dur=0, mul=VOICE_GAIN)
        self.fenv = Adsr(dur=0)

        # Frekvence filtru = základ + obálka + LFO, oříznutá do bezpečného rozsahu.
        cutoff = p["cutoff"] + self.fenv * p["env_amt"] + synth.lfo * p["lfo_depth"]
        self.filter = MoogLP(source, freq=Clip(cutoff, min=30, max=16000), res=p["res"])
        self.out = self.filter * self.amp

    def start(self, note: int):
        self.note = note
        self.freq.value = midiToHz(note)
        self.amp.play()
        self.fenv.play()

    def release(self):
        self.note = None
        self.amp.stop()   # stop() u Adsr spustí fázi release
        self.fenv.stop()


class Synth:
    """Celý syntezátor: správa hlasů, parametrů a společného efektového řetězce."""

    def __init__(self):
        # Vlnové tvary počítané aditivní syntézou (viz tables.py).
        self.waves = [DataTable(size=len(w), init=w) for w in
                      (additive_wave(i) for i in range(len(WAVE_NAMES)))]
        self.shaper = DataTable(size=2048, init=drive_curve())

        # Plynulé parametry jako signály, aby na ně mohly být napojené všechny hlasy.
        self.sig = {k: SigTo(SYNTH_DEFAULTS[k], time=0.03, init=SYNTH_DEFAULTS[k]) for k in SMOOTH_KEYS}
        self.osc2_ratio = Sig(1.0)  # poměr frekvence OSC2 vůči OSC1 (oktáva + rozladění)
        self.noise = Noise()
        self.lfo = Sine(freq=self.sig["lfo_rate"])

        self.voices = [Voice(self) for _ in range(VOICE_COUNT)]
        self._next_voice = 0  # pro "nejstarší hlas" při vyčerpání polyfonie

        # --- společný řetězec ---
        dry = Mix([v.out for v in self.voices], voices=1)
        # Drive: zesílíme, ořežeme na -1..1 a protáhneme přes vlastní tanh křivku.
        self.driven = Lookup(self.shaper, Clip(dry * self.sig["drive"], min=-1, max=1))
        # Bitcrusher: signál vynásobíme počtem úrovní, zaokrouhlíme a vydělíme zpět.
        # Méně bitů = hrubší schodovitý signál = digitální špína.
        self.levels = Sig(2 ** 15)
        self.inv_levels = Sig(1 / 2 ** 15)
        self.crushed = Round(self.driven * self.levels) * self.inv_levels
        self.echo = Delay(self.crushed, delay=self.sig["delay_time"],
                          feedback=self.sig["delay_fb"], maxdelay=2)
        self.output = (self.crushed + self.echo * self.sig["delay_mix"]) * self.sig["volume"]
        self.stereo = Mix(self.output, voices=2).out()

        self.listeners = []  # funkce volané při note on/off (vizualizace, klaviatura v UI)
        self.values = {}
        for key, value in SYNTH_DEFAULTS.items():
            self.set(key, value)

    # --- parametry ---

    def set(self, key: str, value: float):
        """Nastaví parametr podle klíče z params.py."""
        self.values[key] = value
        if key in self.sig:
            self.sig[key].value = value
        elif key in ("osc1_wave", "osc2_wave"):
            table = self.waves[int(value)]
            for v in self.voices:
                (v.osc1 if key == "osc1_wave" else v.osc2).setTable(table)
        elif key in ("osc2_octave", "osc2_detune"):
            octave = int(self.values.get("osc2_octave", 2)) - 2   # index 0..4 -> -2..+2
            cents = self.values.get("osc2_detune", 0)
            self.osc2_ratio.value = 2 ** (octave + cents / 1200)  # 1200 centů = 1 oktáva
        elif key[:4] in ("amp_", "flt_"):
            setter = ENV_SETTERS[key[4]]
            for v in self.voices:
                env = v.amp if key.startswith("amp_") else v.fenv
                getattr(env, setter)(value)
        elif key == "glide":
            for v in self.voices:
                v.freq.setTime(value)
        elif key == "bits":
            levels = 2 ** (int(value) - 1)  # jeden bit padne na znaménko
            self.levels.value = levels
            self.inv_levels.value = 1 / levels

    def get_values(self) -> dict:
        return dict(self.values)

    # --- noty ---

    def note_on(self, note: int):
        voice = self._find_voice(note)
        voice.start(note)
        for listener in self.listeners:
            listener(note, True)

    def note_off(self, note: int):
        for v in self.voices:
            if v.note == note:
                v.release()
        for listener in self.listeners:
            listener(note, False)

    def _find_voice(self, note: int) -> Voice:
        """Vybere hlas: stejná nota -> volný hlas -> nejstarší hlas."""
        for v in self.voices:
            if v.note == note:
                return v
        for v in self.voices:
            if v.note is None:
                return v
        voice = self.voices[self._next_voice]
        self._next_voice = (self._next_voice + 1) % len(self.voices)
        return voice
