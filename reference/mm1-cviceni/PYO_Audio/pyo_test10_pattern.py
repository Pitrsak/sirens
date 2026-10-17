
"""Využití dalších typů generátorů signálu. Portamento a SineLoop a dále funkce Pattern, 
která nastaví periodické volání libovolné python-funkce."""

from pyo import *

import random

s = Server(duplex=0)
s.setOutputDevice(pa_get_default_output())
s.boot()
#s.start()

fr = Sig(value=400)

p = Port(fr, risetime=0.001, falltime=0.03)
a = SineLoop(freq=p, feedback=0.08, mul=.3).out()
b = SineLoop(freq=p*1.005, feedback=0.08, mul=.3).out(1)

def pick_new_freq():
    fr.value = random.randrange(300,601,50)

pat = Pattern(function=pick_new_freq, time=0.5).play()

s.gui(locals())
