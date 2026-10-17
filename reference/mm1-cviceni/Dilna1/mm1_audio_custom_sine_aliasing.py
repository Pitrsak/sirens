import pyo

# Lehce upravená třída na generování sinusovky
# přidal jsem tu možnost nastavit max nastavitelnou frekvenci
class TweakedSine(pyo.Sine):
    """
    A simple sine wave oscillator.

    :Parent: :py:class:`PyoObject`

    :Args:

        freq: float or PyoObject, optional
            Frequency in cycles per second. Defaults to 1000.
        phase: float or PyoObject, optional
            Phase of sampling, expressed as a fraction of a cycle (0 to 1).
            Defaults to 0.

    .. seealso::

        :py:class:`Osc`, :py:class:`Phasor`

    >>> s = Server().boot()
    >>> s.start()
    >>> sine = Sine(freq=[400,500], mul=.2).out()

    """

    def __init__(self, freq=1000, phase=0, mul=1, add=0, max=44100):
        super().__init__(freq, phase, mul, add)
        self.max = max


    def reset(self):
        """
        Resets current phase to 0.

        """
        [obj.reset() for i, obj in enumerate(self._base_objs)]


    def control(self, map_list=None, title=None, wxnoserver=False):
        self._map_list = [pyo.SLMap(1.0, self.max, "lin", "freq", self._freq, "float", 0.025), pyo.SLMapPhase(self._phase), pyo.SLMapMul(self._mul)]
        pyo.PyoObject.ctrl(self, map_list, title, wxnoserver)

if __name__ == '__main__':

    server = pyo.Server(duplex=0)
    #server.setOutputDevice(6)
    server.boot()

    a = TweakedSine(400, 0, 0.5)
    b = TweakedSine(36000, 0, 0.5, max=80000)

    a.control(title="Params of sine a")
    b.control(title="Params of sine b")

    # a = pyo.Sine(400, 0, 0.5)
    # b = pyo.Sine(36000, 0, 0.5)

    # a.ctrl(title="Params of sine a")
    # b.ctrl(title="Params of sine b")

    scope = pyo.Scope([a, b])

    spectrum = pyo.Spectrum([a,b])

    a.out(0) # audio kanál
    b.out(1) # audio kanál

    # sp.setHighFreq(5000)
    # sp.setHighbound(0.1)

    # print(sp.getHighfreq())
    # print(sp.highbound)

    server.gui(locals())
