"""Tvarování signálu obálkou. Práce s MIDI vstupem."""

from pyo import *

# Inicializace serveru
s = Server(duplex=1)
s.setOutputDevice(pa_get_default_output())
s.boot()

# Nastavení Notein pro zachycení MIDI not (virtuální klávesnice)
notes = Notein(poly=1, scale=1)
notes.keyboard()

# Map MIDI na frekvenci v rozsahu 150 Hz až 350 Hz
freq = Scale(notes['pitch'], outmin=150, outmax=350)

# Krátká a ostrá obálka
p = MidiAdsr(notes['velocity'], attack=0.001, decay=0.05, sustain=0, release=0.1, mul=1.0)

# Bílý šum
noise = Noise(1)


# filt_drum = p*MoogLP(input=noise, freq=freq, res=1.2)
filt_drum = p*Biquadx(input=noise, freq=freq, type=2, q=2)
filt_drum.out()

# Osciloskop pro vizualizaci vlnového tvaru
scop = Spectrum(filt_drum)

# Spuštění GUI
s.gui(locals())
