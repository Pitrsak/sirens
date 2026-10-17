"""Sestavení generátoru sinusového signálu. Vlastní spuštění se děje v grafickém rozhraní."""

from pyo import *

s = Server(duplex=0)
s.setOutputDevice(pa_get_default_output())
s.boot()
a = Sine(freq=800, mul=1).out()
s.gui(locals())


