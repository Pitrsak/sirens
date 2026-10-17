from pyo import *

s = Server(duplex = 0)
s.setOutputDevice(pa_get_default_output())
s.boot()

s.start()

a = Input(chnl=0, mul=0.7)
b = Delay(a, delay=.25, feedback=.5, mul=.5).out()


phasor_signal = Phasor(1, mul=1000)
sin_signal = Sine(phasor_signal).out()
sin_signal.ctrl()


sc = Scope(sin_signal)
sp = Spectrum(sin_signal)

n = Noise()
lp = ButLP(n, freq = 200).out(0)
hp = ButHP(n, freq = 1200).out(0)



s.gui()