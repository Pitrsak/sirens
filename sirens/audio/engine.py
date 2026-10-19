"""Zvukový engine: pyo server a pevný výstupní řetězec.

    nástroje všech stop (součet) -> [zásuvka] -> hlasitost -> ořez -1..1 -> obě repro
                                               \\-> analýza (osciloskop, spektrum, obraz, světlo)

Co hraje, se dá kdykoli vyměnit (po přidání nebo smazání stopy), zbytek
řetězce zůstává. Výměna proběhne s krátkým prolnutím, aby to necvaklo.
Noty dostávají nástroje jako MIDI zprávy (send_note).
"""

from pyo import Clip, InputFader, Mix, Pan, Server, Sig, SigTo

from sirens.audio.analyzer import Analyzer

FADE_TIME = 0.05   # prolnutí při výměně signálu (s)


class AudioEngine:
    def __init__(self, sample_rate: int = 44100, buffer_size: int = 512, microphone: bool = False):
        # duplex=0: jen výstup, bez mikrofonu (méně problémů se zařízeními).
        # Pro Input() (mikrofon) je potřeba microphone=True.
        self.server = Server(sr=sample_rate, nchnls=2, buffersize=buffer_size, duplex=int(microphone))
        # 99 = poslouchat všechna MIDI vstupní zařízení (připojenou MIDI klávesnici)
        self.server.setMidiInputDevice(99)
        self.server.boot()
        self.server.start()

        # pyo objekty lze vytvářet až po boot() serveru.
        self.silence = Sig(0)
        self.source = InputFader(self.silence)   # "zásuvka" pro součet nástrojů
        self.current = None                      # právě hrající signál (držíme odkaz, jinak by zanikl)
        self.retired = []                        # předchozí signály, doznívají při prolnutí

        self.volume = SigTo(0.5, time=0.05, init=0.5)
        # Ořez na -1..1 je pojistka: hodně hlasitých nástrojů najednou nepřebudí repro.
        self.safe = Clip(self.source * self.volume, min=-1, max=1)
        # Mono signál dáme doprostřed mezi levý a pravý reproduktor.
        self.output = Pan(self.safe, outs=2, pan=0.5).out()

        # Analyzujeme signál před hlasitostí, aby byl tvar vlny vidět i při tichém poslechu.
        self.analyzer = Analyzer(self.source, sample_rate)

    def play(self, signal):
        """Připojí nový signál na výstup. None = ticho.

        Mix(..., voices=1) sečte vše do jednoho kanálu, takže se sem dá poslat
        jeden objekt i seznam objektů (výstupy nástrojů všech stop).
        """
        # starý signál necháme chvíli žít, zásuvka z něj ještě prolíná (viz Instrument.play)
        self.retired = (self.retired + [self.current])[-4:]
        self.current = Mix(signal, voices=1) if signal is not None else self.silence
        self.source.setInput(self.current, fadetime=FADE_TIME)

    def send_note(self, channel: int, note: int, velocity: int):
        """Pošle notu nástrojům jako MIDI zprávu (jako by přišla z MIDI klávesnice).

        Status bajt: 0x90 = nota zapnuta, 0x80 = vypnuta; v nižších 4 bitech kanál (0 = kanál 1).
        velocity 0..127, 0 znamená puštění klávesy.
        """
        status = (0x90 if velocity > 0 else 0x80) + channel - 1
        self.server.addMidiEvent(status, note, velocity)

    def set_volume(self, value: float):
        self.volume.value = value

    def close(self):
        self.server.stop()
        self.server.shutdown()
