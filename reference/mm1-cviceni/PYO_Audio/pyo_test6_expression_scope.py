"""Příklad použití výrazu v prefixové notaci pro operace se signálem.
Součet dvou sinusových signálů 500Hz a 600Hz a amplitudě -12dB."""

from pyo import *

s = Server(duplex=0)
s.setOutputDevice(pa_get_default_output())
s.boot()

expression = """
* (+ (sin (* twopi (~ 500)))
     (sin (* twopi (~ 600)))
  ) 0.25
"""

# We dont use any input with this expression (synthesis only),
# so we pass a signal filled with zeros.
input = Sig(0)

# Create the Expr object and show its expression editor. To
# re-evaluate the expression hit Ctrl+Enter when the editor
# has the focus.
expr = Expr(input, expression)
expr.editor()

# Shows the generated signal.
sc = Scope(expr)
spec = Spectrum(expr)
# Converts the mono signal to stereo and sends it to the soundcard.
pan = Pan(expr).out()

s.gui(locals())
