"""Vstup přes mikrofon."""

from pyo import *

s = Server(duplex=1)
s.setOutputDevice(pa_get_default_output())
s.boot()

s.start()
a = Input(chnl=0, mul=.7)
b = Delay(a, delay=.25, feedback=.5, mul=.5).out()

s.gui(locals())
