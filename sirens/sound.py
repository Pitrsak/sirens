"""Tady vzniká zvuk. Tenhle soubor píšu sám, krok po kroku podle cvičení.

Jak to funguje:
 - Píšu normální pyo kód jako na cvičení (cv2.py, cv3.py), jen uvnitř funkce build(ui).
 - Server neřeším, ten už běží (Server, boot, start a s.gui() dělá aplikace).
 - Místo sig.ctrl() si řeknu o slider ve skutečných jednotkách:

       freq = ui.slider("Frequency", 20, 2000, 440, unit="Hz", log=True,
                        help="Jak vysoký je tón.")

   freq je pyo signál, dá se použít všude, kde by bylo číslo: Sine(freq=freq).
   (Na cvičení f.ctrl() dalo slider 0..1, proto tam bylo f * 22000.)
 - ui.group("Oscillator") začne v pravém panelu novou skupinu s nadpisem.
 - Na konci vrátím signál, který chci slyšet: return signal
   (.out() nepíšu, výstup, hlasitost, osciloskop a spektrum řeší aplikace).
 - Po uložení souboru se zvuk hned načte znovu. Když udělám chybu, aplikace
   napíše dole pod grafy číslo řádku a co je špatně.

Plán kroků (podle cv3.py a cv2.py):
 1. Jeden sinus: slidery pro frekvenci a amplitudu (mul).
 2. Aditivní syntéza: 7 harmonických f, 2f, 3f... s amplitudami 1, 1/2, 1/3...,
    každá se svým sliderem -> sledovat, jak se ze sinusu stává pila.
 3. Modulace: Phasor, který rozjíždí frekvenci sinusu (cv2.py).
 4. Šum do dolní a horní propusti (Noise, ButLP, ButHP) se slidery na frekvenci.
 5. Mikrofon do delaye (Input, Delay) s časem a zpětnou vazbou.
"""

from pyo import *


def build(ui):
    # Krok 1: jeden sinus.
    # a) slider "Frequency" 20-2000 Hz, výchozí 440, logaritmický
    # b) slider "Amplitude" 0-1, výchozí 0.3 (mul = násobí vlnu, tedy jak je silná)
    # c) Sine(...) s těmito slidery jako freq a mul
    # d) vrátit ho: return ...
    return None
