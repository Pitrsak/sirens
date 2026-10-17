from pyo import *

s = Server()
#s.setMidiInputDevice(3)
#s.setMidiOutputDevice(2)
#s.setOutputDevice(11)
s.boot()

#s.start()

notes = Notein(poly=1, scale=1, mul=.5)
#p = Port(notes['velocity'], .001, .5)
p = MidiAdsr(notes['velocity'],attack=0.05,decay=0.1,sustain=0.7,release=0.5,mul=0.5)
b = Sine(freq=notes['pitch'], mul=p).out()
c = Sine(freq=notes['pitch'] * 0.997, mul=p).out()
d = Sine(freq=notes['pitch'] * 1.005, mul=p).out()

#s.ctlout(ctlnum=0,value=50)
notes.keyboard()

scop = Scope([b,c,d])

s.gui(locals())
