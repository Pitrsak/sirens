"""Příklad použití efektu na zvukový signál načítaný ze souboru.
Třídy jsou dokumentovány a nesou sebou příklady použití. Stejný efekt, 
jako níže uvedený kód, získáte voláním dvou zakomentovaných řádků níže."""


#from pyo import *
#example(Harmonizer)

import time
from pyo import *
s = Server()
s.setOutputDevice(pa_get_default_output())
s.boot()

sf = SfPlayer(SNDS_PATH + '/transparent.aif', loop=True, mul=.3).out()
harm = Harmonizer(sf, transpo=-5, winsize=0.05).out(1)

s.gui(locals())


