"""Definice všech parametrů syntezátoru na jednom místě.

Z tohoto seznamu se staví knoby v UI, výchozí hodnoty i ukládání presetů,
takže přidání nového parametru = jeden řádek tady + jeho použití v synth.py.
"""

from fathom.audio.tables import WAVE_NAMES
from fathom.param import Param


def _choice(key, label, choices, default_index):
    """Pomocná funkce pro přepínač: hodnota je index do seznamu popisků."""
    return Param(key, label, 0, len(choices) - 1, default_index, step=1, choices=tuple(choices))


# Sekce syntezátoru v pořadí, v jakém se zobrazí v UI.
SYNTH_SECTIONS = [
    ("OSC 1", [
        _choice("osc1_wave", "WAVE", WAVE_NAMES, 2),
        Param("osc1_level", "LEVEL", 0, 1, 0.8),
    ]),
    ("OSC 2", [
        _choice("osc2_wave", "WAVE", WAVE_NAMES, 3),
        _choice("osc2_octave", "OCTAVE", ("-2", "-1", "0", "+1", "+2"), 2),
        Param("osc2_detune", "DETUNE", -50, 50, 7, "ct"),
        Param("osc2_level", "LEVEL", 0, 1, 0.5),
    ]),
    ("NOISE", [
        Param("noise", "LEVEL", 0, 1, 0.0),
    ]),
    ("FILTER", [
        Param("cutoff", "CUTOFF", 40, 16000, 1200, "Hz", log=True),
        Param("res", "RESO", 0, 1, 0.3),
        Param("env_amt", "ENV AMT", 0, 8000, 2000, "Hz"),
        Param("lfo_rate", "LFO RATE", 0.05, 20, 0.5, "Hz", log=True),
        Param("lfo_depth", "LFO DEPTH", 0, 4000, 0, "Hz"),
    ]),
    ("AMP ENV", [
        Param("amp_a", "ATTACK", 0.001, 4, 0.005, "s", log=True),
        Param("amp_d", "DECAY", 0.001, 4, 0.2, "s", log=True),
        Param("amp_s", "SUSTAIN", 0, 1, 0.7),
        Param("amp_r", "RELEASE", 0.001, 6, 0.3, "s", log=True),
    ]),
    ("FILTER ENV", [
        Param("flt_a", "ATTACK", 0.001, 4, 0.005, "s", log=True),
        Param("flt_d", "DECAY", 0.001, 4, 0.3, "s", log=True),
        Param("flt_s", "SUSTAIN", 0, 1, 0.2),
        Param("flt_r", "RELEASE", 0.001, 6, 0.3, "s", log=True),
    ]),
    ("DIRT", [
        Param("drive", "DRIVE", 1, 40, 1, log=True),
        Param("bits", "BITS", 2, 16, 16, step=1),
    ]),
    ("DELAY", [
        Param("delay_time", "TIME", 0.01, 1.5, 0.3, "s", log=True),
        Param("delay_fb", "FEEDBACK", 0, 0.9, 0.3),
        Param("delay_mix", "MIX", 0, 1, 0.0),
    ]),
    ("MASTER", [
        Param("glide", "GLIDE", 0, 1, 0.0, "s"),
        Param("volume", "VOLUME", 0, 1, 0.5),
    ]),
]

# Plochý seznam a slovník výchozích hodnot (hodí se pro presety).
SYNTH_PARAMS = [p for _, params in SYNTH_SECTIONS for p in params]
SYNTH_DEFAULTS = {p.key: p.default for p in SYNTH_PARAMS}
