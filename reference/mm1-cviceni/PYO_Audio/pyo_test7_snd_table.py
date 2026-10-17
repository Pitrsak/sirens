"""Přehrávání zvuku z tabulky iniciované ze zvukového souboru."""

from pyo import *

s = Server(duplex=0)
s.setOutputDevice(pa_get_default_output())
s.boot()

path = SNDS_PATH + "/transparent.aif"


# Loads the sound file in RAM. Beginning and ending points
# can be controlled with "start" and "stop" arguments.
t = SndTable(path)
t.view()

# Gets the frequency relative to the table length.
freq = t.getRate()

print(f"frequency {freq}\n")

# Simple stereo looping playback (right channel is 180 degrees out-of-phase).
osc = Osc(table=t, freq=freq, phase=[0, 0.5], mul=0.4).out()

s.gui(locals())