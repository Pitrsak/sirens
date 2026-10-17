"""Sestavení generátoru sinusového signálu. Vlastní 
spuštění se děje automaticky voláním metody start sound serveru.
Pozor před ukončením je potřeba zavolat čekací smyčku - zde 1s. Jinak program 
skončí hned a nic se nepřehraje."""

from pyo import *
import time
s = Server(duplex=0)
s.setOutputDevice(pa_get_default_output())
s.boot()
a = Sine(440, 0, 0.5).out()

s.start()
time.sleep(1)
s.stop()
