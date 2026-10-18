"""Zvukový engine: pyo server a pevný výstupní řetězec.

    signál ze sound.py -> [zásuvka] -> hlasitost -> zap/vyp -> ořez -1..1 -> obě repro
                                  \\-> analýza (osciloskop, spektrum)

Signál ze sound.py se dá kdykoli vyměnit (po uložení souboru), zbytek
řetězce zůstává. Výměna proběhne s krátkým prolnutím, aby to necvaklo.
"""

from pyo import Clip, InputFader, Mix, Pan, Server, Sig, SigTo

from sirens.audio.analyzer import Analyzer

FADE_TIME = 0.05   # prolnutí při výměně signálu (s)


class AudioEngine:
    def __init__(self, sample_rate: int = 44100, buffer_size: int = 512, microphone: bool = False):
        # duplex=0: jen výstup, bez mikrofonu (méně problémů se zařízeními).
        # Pro Input() (mikrofon, krok s delayem z cv2.py) je potřeba microphone=True.
        self.server = Server(sr=sample_rate, nchnls=2, buffersize=buffer_size, duplex=int(microphone))
        self.server.boot()
        self.server.start()

        # pyo objekty lze vytvářet až po boot() serveru.
        self.silence = Sig(0)
        self.source = InputFader(self.silence)   # "zásuvka" pro signál ze sound.py
        self.current = None                      # právě hrající signál (držíme odkaz, jinak by zanikl)

        self.volume = SigTo(0.5, time=0.05, init=0.5)
        self.on = SigTo(1, time=0.05, init=1)    # tlačítko Stop/Play: 0 = ticho, 1 = hraje
        # Ořez na -1..1 je pojistka: chyba v kódu (např. mul=100) nepřebudí repro.
        self.safe = Clip(self.source * self.volume * self.on, min=-1, max=1)
        # Mono signál dáme doprostřed mezi levý a pravý reproduktor.
        self.output = Pan(self.safe, outs=2, pan=0.5).out()

        # Analyzujeme signál před hlasitostí, aby byl tvar vlny vidět i při tichém poslechu.
        self.analyzer = Analyzer(self.source, sample_rate)

    def play(self, signal):
        """Připojí nový signál na výstup. None = ticho.

        Mix(..., voices=1) sečte vše do jednoho kanálu, takže sound.py může
        vrátit jeden objekt, víc kanálů (Sine([440, 660])) i seznam objektů.
        """
        self.current = Mix(signal, voices=1) if signal is not None else self.silence
        self.source.setInput(self.current, fadetime=FADE_TIME)

    def set_volume(self, value: float):
        self.volume.value = value

    def set_playing(self, playing: bool):
        self.on.value = 1 if playing else 0

    def close(self):
        self.server.stop()
        self.server.shutdown()
