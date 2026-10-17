"""Příklad součtové a rozdílové syntézy."""

from pyo import *

s = Server(sr=44100)
#s.setMidiInputDevice(3)
s.setMidiOutputDevice(pm_get_default_output())
s.setOutputDevice(pa_get_default_output())
s.boot()


notes = Notein(poly=10, scale=1, mul=.5)
notes.keyboard(title="KEYBOARD")

# Sound bank
folder = "../snds/"
sounds = ["1.mp3", "2.mp3", "3.mp3", "4.mp3","1.mp3", "2.mp3", "3.mp3", "4.mp3"]

tables = [SndTable(folder+sounds[i]) for i in range(8)]
l = Looper(tables[0],mode=0,mul=1.5)
#l.ctrl()


'''Aditivní syntéza s deseti harmonickými'''

nastroje = {
'sinus':        [1  , 0  , 0  , 0  , 0  , 0  , 0   , 0  , 0  , 0  ],
'obdélník':     [1  , 0  , 1/3, 0  , 1/5, 0  , 1/7 , 0  , 1/9, 0  ],
'trojúhelník':  [1  , 0  , 1/9, 0  , 1/25, 0  , 1/49, 0  , 1/81, 0  ],
'pila':         [1  , 1/2, 1/3, 1/4, 1/5, 1/6, 1/7 , 1/8, 1/9, 1/10],
'trubka':       [0.17, 0.63, 0.57, 0.98, 0.56, 0.68, 0.02, 0.05, 0  , 0  ],
'harmonika':    [8.60, 0.45, 3.40, 0.50, 0.42, 0.13, 0.13, 0.16, 0.04, 0.35],
'flétna':       [2.54, 0.25, 0.01, 0  , 0  , 0  , 0   , 0  , 0  , 0  ],
'klarinet':     [1.00, 0.00, 0.07, 0.00, 0.50, 0.00, 0.14, 0.50, 0.00, 0.12],
'hoboj':        [0.02, 0.20, 1.00, 0.37, 0.36, 0.46, 0.10, 0.06, 0.03, 0.02],
'piano':        [0.32, 0.20, 0.08, 0.07, 0.06, 0  , 0   , 0  , 0  , 0  ],
'housle':       [0.39, 0.30, 0.17, 0.01, 0.11, 0  , 0   , 0  , 0  , 0  ],
'hlas':         [0.43, 0.08, 0.01, 0  , 0  , 0  , 0   , 0  , 0  , 0  ],
}

amp = nastroje['harmonika']

a = Sine(freq=notes["pitch"] * 1.0, mul=notes["velocity"]*amp[0])
b = Sine(freq=notes['pitch'] * 2.0, mul=notes["velocity"]*amp[1])
c = Sine(freq=notes['pitch'] * 3.0, mul=notes["velocity"]*amp[2])
d = Sine(freq=notes['pitch'] * 4.0, mul=notes["velocity"]*amp[3])
e = Sine(freq=notes['pitch'] * 5.0, mul=notes["velocity"]*amp[4])
f = Sine(freq=notes['pitch'] * 6.0, mul=notes["velocity"]*amp[5])
g = Sine(freq=notes['pitch'] * 7.0, mul=notes["velocity"]*amp[6])
h = Sine(freq=notes['pitch'] * 8.0, mul=notes["velocity"]*amp[7])
i = Sine(freq=notes['pitch'] * 9.0, mul=notes["velocity"]*amp[8])
j = Sine(freq=notes['pitch'] * 10.0, mul=notes["velocity"]*amp[9])

'''Zakomentujte pokud používáte rozdílovou syntézu'''
sig = (a + b + c + d + e + f + g + h + i + j)/10


'''Subtraktivní syntéza s využitím generátoru šumu.'''

sumswistu = Noise()
envelope = MidiAdsr(notes["velocity"],sustain=0)
lp = ButLP(sumswistu,freq=100)
envelope.ctrl()

'''Zakomentujte pokud používáte součtovou syntézu'''
#sig = envelope * lp * 10


sig.out()
spc = Spectrum(sig)

def noteon(voice):
    hz = notes["pitch"].get(all=True)[voice]
    pit = int(hzToMidi(hz))
    vel = int(notes["velocity"].get(all=True)[voice] * 127)
    if pit<8:
        l.setTable(tables[pit])
        l.out()

    print("Noteon: voice = %d, pitch = %d, velocity = %d, freq = %d " % (voice, pit, vel, hz))

def noteoff(voice):
    pit = int(hzToMidi(notes["pitch"].get(all=True)[voice]))
    vel = int(notes["velocity"].get(all=True)[voice] * 127)
    print("Noteoff: voice = %d, pitch = %d, velocity = %d" % (voice, pit, vel))
    l.stop()
    
tfon = TrigFunc(notes["trigon"], noteon, arg=list(range(10)))
tfoff = TrigFunc(notes["trigoff"], noteoff, arg=list(range(10)))

s.gui(locals())
