"""ZVUKOVEJ ENGINE: pyo server a pevnej výstupní řetězec, kterým jde všechno do repráků.

    nástroje všech stop (součet) -> [zásuvka] -> hlasitost -> ořez -1..1 -> obě repro
                                               \\-> analýza (osciloskop, spektrum, obraz, světlo)

co hraje, se dá kdykoli vyměnit (po přidání nebo smazání stopy), zbytek
řetězce zůstává. výměna proběhne s krátkým prolnutím, aby to necvaklo.
noty dostávaj nástroje jako MIDI zprávy (send_note).
"""

from pyo import Clip, InputFader, Mix, Pan, Server, Sig, SigTo

from sirens.audio.analyzer import Analyzer

FADE_TIME = 0.05   # prolnutí při výměně signálu (s)


class AudioEngine:
    """jeden na celou appku, vzniká v __main__.py ještě před oknem."""

    def __init__(self, sample_rate: int = 44100, buffer_size: int = 512, microphone: bool = False):
        # sample_rate = kolik vzorků za vteřinu, buffer_size = po kolika vzorcích se počítá najednou
        # (512 / 44100 = cca 12 ms, menší buffer = menší zpoždění, ale víc práce pro počítač).
        # duplex=0: jen výstup, bez mikrofonu (míň problémů se zařízeníma).
        # pro Input() (mikrofon) je potřeba microphone=True.
        self.server = Server(sr=sample_rate, nchnls=2, buffersize=buffer_size, duplex=int(microphone))
        # 99 = poslouchat všechna MIDI vstupní zařízení (připojenou MIDI klávesnici)
        self.server.setMidiInputDevice(99)
        self.server.boot()
        self.server.start()

        # pozor, pyo objekty jde vytvářet až po boot() serveru.
        self.silence = Sig(0)
        self.source = InputFader(self.silence)   # "zásuvka" pro součet nástrojů
        self.current = None                      # právě hrající signál (držíme odkaz, jinak by zanikl)
        self.retired = []                        # předchozí signály, doznívaj při prolnutí

        self.volume = SigTo(0.5, time=0.05, init=0.5)   # Master slider, taky plynule
        # ořez na -1..1 je pojistka: hodně hlasitejch nástrojů najednou nepřebudí repro.
        self.safe = Clip(self.source * self.volume, min=-1, max=1)
        # mono signál dáme doprostřed mezi levej a pravej reprák. .out() = tohle jde fakt ven do zvukovky
        self.output = Pan(self.safe, outs=2, pan=0.5).out()

        # analyzujem signál před hlasitostí, aby byl tvar vlny vidět i při tichým poslechu.
        self.analyzer = Analyzer(self.source, sample_rate)

    def play(self, signal):
        """připojí novej signál na výstup. None = ticho.

        Mix(..., voices=1) sečte všechno do jednoho kanálu, takže se sem dá poslat
        jeden objekt i seznam objektů (výstupy nástrojů všech stop).
        """
        # starej signál necháme chvíli žít, zásuvka z něj ještě prolíná (viz Instrument.play)
        self.retired = (self.retired + [self.current])[-4:]
        self.current = Mix(signal, voices=1) if signal is not None else self.silence
        self.source.setInput(self.current, fadetime=FADE_TIME)

    def send_note(self, channel: int, note: int, velocity: int):
        """pošle notu nástrojům jako MIDI zprávu (jako by přišla z MIDI klávesnice).

        MIDI zpráva = 3 bajty: status, číslo noty (60 = C4), velocity (síla úhozu).
        status bajt: 0x90 = nota zapnutá, 0x80 = vypnutá, v nižších 4 bitech kanál (0 = kanál 1),
        takže třeba 0x92 = nota zapnutá na kanálu 3. proto + channel - 1.
        velocity 0..127, 0 znamená puštění klávesy.
        """
        status = (0x90 if velocity > 0 else 0x80) + channel - 1
        self.server.addMidiEvent(status, note, velocity)

    def set_volume(self, value: float):
        self.volume.value = value

    def close(self):
        # při zavření okna: zastavit zvuk a vypnout server
        self.server.stop()
        self.server.shutdown()
