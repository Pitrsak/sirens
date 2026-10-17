from pyo import *

s = Server(duplex = 0)
s.setOutputDevice(pa_get_default_output())
s.boot()


#sine = Sine(440).out()
#sine.ctrl()

f = Sig(440)
fzakladni = f * 22000
s1 = Sine(fzakladni*1, mul = 1)
s2 = Sine(fzakladni*2, mul = 1/2)
s3 = Sine(fzakladni*3, mul = 1/3)
s4 = Sine(fzakladni*4, mul = 1/4)
s5 = Sine(fzakladni*5, mul = 1/5)
s6 = Sine(fzakladni*6, mul = 1/6)
s7 = Sine(fzakladni*7, mul = 1/7)

signal = (s1 + s2 + s3 + s4 + s5 + s6 + s7) / 6
signal.out()

f.ctrl()

scope = Scope(signal)
scope = Spectrum(signal)


s.gui()