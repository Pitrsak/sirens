"""Další ukázka na použití efektu na signál ze souboru. Tentokrát Chorus."""
from pyo import *

s = Server(duplex=0)
s.setOutputDevice(pa_get_default_output())
s.boot()
s.start()

print (f"{SNDS_PATH}/transparent.aif")
time.sleep(2)
sf = SfPlayer(SNDS_PATH + '/transparent.aif', loop=False, mul=1).out()
time.sleep(2)

sf = SfPlayer(SNDS_PATH + '/transparent.aif', loop=True, mul=.5)
chor = Chorus(sf, depth=[1.5,1.0], feedback=0.85, bal=0.5).out()

sf.out()
time.sleep(10)
s.stop()