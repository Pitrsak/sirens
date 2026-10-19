"""Nástroj: noty, obálka a rack bloků, ze kterých se skládá jeho zvuk.

Noty přicházejí jako MIDI zprávy na kanál nástroje (1-16): ze skutečné
MIDI klávesnice, z klávesnice počítače i ze sekvenceru (ty dvě posílají
zprávy přes server.addMidiEvent). Pyo Notein z nich udělá VOICES hlasů:
každý hlas má svou výšku (pitch, v Hz) a sílu (velocity, 0..1; po puštění
klávesy 0). Hraje-li víc not najednou, každá dostane volný hlas.

Obálka (MidiAdsr) určuje, jak nota začne a skončí:
    Attack   jak rychle nota naběhne po stisku
    Decay    jak rychle pak klesne na Sustain
    Sustain  jak silně zní, dokud je klávesa držená
    Release  jak dlouho doznívá po puštění

Bloky v racku dostanou pitch a obálku a pro každý hlas vytvoří jeden signál.
Výsledek racku se sečte do jednoho kanálu a přes "zásuvku" (InputFader)
jde na výstup nástroje, takže rack jde kdykoli přestavět bez lupnutí.
"""

from pyo import InputFader, MidiAdsr, Mix, Notein, Sig, SigTo

from sirens.audio.rack import Rack
from sirens.param import Adjustable, Param

VOICES = 8          # kolik not může nástroj hrát najednou
FADE_TIME = 0.05    # prolnutí při přestavbě racku (s)


class Instrument(Adjustable):
    PARAMS = [
        Param("Attack", 0.001, 4, 0.01, "s", log=True, help="How fast a note starts after the key is pressed."),
        Param("Decay", 0.01, 4, 0.3, "s", log=True, help="How fast it then falls to the sustain level."),
        Param("Sustain", 0, 1, 0.7, help="Level while the key is held (1 = full)."),
        Param("Release", 0.01, 8, 0.4, "s", log=True, help="How long the note fades after the key is released."),
        Param("Volume", 0, 1, 0.8, help="Loudness of this instrument."),
    ]

    def __init__(self, channel: int):
        super().__init__()
        self.channel = channel
        self.notes = Notein(poly=VOICES, scale=1, first=0, last=127, channel=channel)
        self.pitch = self.notes["pitch"]          # Hz, jeden signál na hlas
        self.trigger = self.notes["trigon"]       # krátký impuls ve chvíli stisku
        s = self.settings
        self.envelope = MidiAdsr(self.notes["velocity"], attack=s["Attack"], decay=s["Decay"],
                                 sustain=s["Sustain"], release=s["Release"])
        self.volume = SigTo(s["Volume"], time=0.03, init=s["Volume"])
        self.socket = InputFader(Sig(0))
        self.output = self.socket * self.volume   # jeden kanál, jde do mixu
        self.current = None
        self.retired = []      # předchozí zvuky, viz play()
        self.rack = Rack(self)

    def set(self, label: str, value: float):
        super().set(label, value)
        if label == "Volume":
            self.volume.value = value
        elif label in ("Attack", "Decay", "Sustain", "Release"):
            setattr(self.envelope, label.lower(), value)   # např. envelope.attack = value

    def play(self, flow):
        """Zavolá rack po každé změně: nový zvuk do zásuvky (None = ticho).

        Zásuvka ještě 50 ms prolíná ze starého zvuku, ale drží jen odkaz na nový.
        Kdyby Python starý zvuk hned uvolnil, zvukové vlákno by četlo uvolněnou
        paměť a program spadl. Proto si pár předchozích zvuků necháme v retired.
        """
        self.retired = (self.retired + [self.current])[-4:]
        self.current = Mix(flow, voices=1) if flow is not None else Sig(0)
        self.socket.setInput(self.current, fadetime=FADE_TIME)
