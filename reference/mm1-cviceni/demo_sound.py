"""
Sound Generation Demo for Multimedia 1 (MM1)
Demonstrating:
 1. Additive synthesis (harmonic chord)
 2. Frequency Modulation (FM sci-fi sweep)
 3. ADSR envelope synth melody with stereo delay
"""

import time
from pyo import *

def run_sound_demo():
    print("\n" + "=" * 55)
    print("      MULTIMEDIA 1 - PYO SOUND SYNTHESIS DEMO")
    print("=" * 55)

    s = Server(duplex=0)
    s.setOutputDevice(pa_get_default_output())
    s.boot()
    s.start()

    # --- Part 1: Additive Synthesis (Harmonics build a rich organ chord) ---
    print("\n[1/3] Playing Additive Synthesis (C-major organ with harmonics)...")
    # Base frequencies: C4 (261.63), E4 (329.63), G4 (392.00)
    freqs = [261.63, 329.63, 392.00, 523.25]
    sines = []
    for f in freqs:
        # fundamental + 2nd harmonic + 3rd harmonic
        sines.append(Sine(freq=f, mul=0.08).out())
        sines.append(Sine(freq=f * 2, mul=0.04).out())
        sines.append(Sine(freq=f * 3, mul=0.02).out())
    time.sleep(2.0)

    # Fade out part 1
    for snd in sines:
        snd.stop()
    time.sleep(0.3)

    # --- Part 2: Frequency Modulation (Sci-fi Laser / Space effect) ---
    print("[2/3] Playing FM Synthesis (Sci-fi Frequency Modulation)...")
    # LFO modulator sweeps the carrier frequency
    lfo = Sine(freq=3, mul=300, add=600)
    modulator = Sine(freq=80, mul=200)
    carrier = Sine(freq=lfo + modulator, mul=0.25).out()
    time.sleep(2.5)

    carrier.stop()
    lfo.stop()
    modulator.stop()
    time.sleep(0.3)

    # --- Part 3: ADSR Synthesizer Arpeggio with Stereo Delay ---
    print("[3/3] Playing Arpeggio with ADSR Envelopes & Stereo Delay...")
    notes = [440, 523.25, 659.25, 783.99, 880, 783.99, 659.25, 523.25]
    env = Adsr(attack=0.02, decay=0.15, sustain=0.1, release=0.1, dur=0.25, mul=0.3)
    freq_sig = Sig(value=440)
    synth = (Sine(freq_sig) * env).mix(2)
    delay = Delay(synth, delay=[0.15, 0.25], feedback=0.5, mul=0.4).out()
    synth.out()

    for note in notes * 2:
        freq_sig.value = note
        env.play()
        time.sleep(0.18)

    time.sleep(1.0)

    # Clean shutdown
    s.stop()
    s.shutdown()
    print("\n[Done] Sound demo complete!\n" + "=" * 55)

if __name__ == "__main__":
    run_sound_demo()
