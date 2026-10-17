
"""Modulace sinusového signálu dvěma fázově posunutými funkcemi po jedné do každého kanálu L a R."""

from pyo import *

s = Server(duplex=0)
s.setOutputDevice(pa_get_default_output())
s.boot()
s.start()

# Tangent panning function

import math

src = Sine(mul=.3)

a = Phasor(freq=1, mul=90, add=-45)

b = Tan(Abs(a*math.pi/180))

b1 = 1.0 - b

oL = src * b

oR = src * b1

oL.out()

oR.out(1)

s.gui(locals())
