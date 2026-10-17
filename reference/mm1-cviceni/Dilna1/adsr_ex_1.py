from pyo import *

server = Server(duplex=0)
#server.setOutputDevice(11)
server.boot()

#s.start()

f = Adsr(attack=.01, decay=.5, sustain=.05, release=.05, dur=1, mul=.5)
a = Phasor(freq=440).mix(2)

y = f*a



def repeat():
    f.play()

y.out()

f.ctrl()

pat = Pattern(function=repeat, time=2).play()

server.gui(locals())
