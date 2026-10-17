"""Přehrávání zvuku z tabulky pomocí Oscilátoru"""

from pyo import *


s = Server(duplex=0)
s.setOutputDevice(pa_get_default_output())
s.boot()

s.start()
#t = TriangleTable().normalize()
t = SquareTable().normalize()
rate = t.getRate()
size = t.getSize()
bsize = t.getBufferSize()
dur = t.getDur()
sr = t.getSamplingRate()


print(f"rate: {rate}\nsize: {size}\nbuffer size: {bsize}\nduration: {dur}\nsampling rate: {sr}")

a = Osc(table=t, freq=300, mul=.5).out()

s.gui(locals())
