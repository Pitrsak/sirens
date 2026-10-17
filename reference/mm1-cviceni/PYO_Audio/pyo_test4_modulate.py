"""Modulace signálu. Phasor je generátor pilového signálu neboli rampy 
v každé periodě lineárně probíhající od 0 do 1 (zde je ale díky parametru 
mul rozsah od 0 do 1000). Tento signál je použit pro 
řízení frekvence harmonického signálu. """

from pyo import *

s = Server(duplex=0)
s.setOutputDevice(pa_get_default_output())
s.boot()

a = Phasor(1, mul=1000, add=0)
b = Sine(freq=a, mul=0.2).out()

sc = Scope(b)
s.gui(locals())
