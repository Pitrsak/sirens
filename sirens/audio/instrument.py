"""NÁSTROJ: noty, obálka a rack bloků, ze kterých se skládá jeho zvuk.

noty přicházej jako MIDI zprávy na kanál nástroje (1-16): ze skutečný
MIDI klávesnice, z klávesnice počítače i ze sekvenceru (ty dvě posílaj
zprávy přes server.addMidiEvent, jako by to byla klávesnice). pyo Notein z nich udělá VOICES hlasů:
každej hlas má svou výšku (pitch, v Hz) a sílu (velocity, 0..1, po puštění
klávesy 0). hraje-li víc not najednou, každá dostane volnej hlas.

obálka (MidiAdsr) určuje, jak nota začne a skončí, tj. jak se v čase mění hlasitost:
    Attack   jak rychle nota naběhne po stisku
    Decay    jak rychle pak klesne na Sustain
    Sustain  jak silně zní, dokud je klávesa držená
    Release  jak dlouho doznívá po puštění

bloky v racku dostanou pitch a obálku a pro každej hlas vytvoří jeden signál.
výsledek racku se sečte do jednoho kanálu a přes "zásuvku" (InputFader)
jde na výstup nástroje, takže rack jde kdykoli přestavět bez lupnutí
(zásuvka starej a novej zvuk krátce prolne, místo aby to skočilo).
"""

import time

from pyo import InputFader, MidiAdsr, Mix, Notein, Sig, SigTo

from sirens.audio.rack import Rack
from sirens.param import Adjustable, Param

# kolik not může nástroj hrát najednou (= kolik hlasů má Notein).
# každej hlas je vlastní kopie všech bloků a pyo je počítá pořád, i v tichu,
# takže víc hlasů = víc práce pro procesor. písně potřebujou max 3 noty naráz, 4 stačí.
VOICES = 4
FADE_TIME = 0.05    # prolnutí při přestavbě racku (s)
RETIRE_AFTER = 1.0  # za kolik s se starej zvuk zahodí (prolnutí trvá jen FADE_TIME, takže bohatě)


class Instrument(Adjustable):
    """jeden nástroj = jedna stopa. slidery obálky a hlasitosti jsou tady, zbytek zvuku dělá rack."""

    PARAMS = [
        Param("Attack", 0.001, 4, 0.01, "s", log=True, help="How fast a note starts after the key is pressed."),
        Param("Decay", 0.01, 4, 0.3, "s", log=True, help="How fast it then falls to the sustain level."),
        Param("Sustain", 0, 1, 0.7, help="Level while the key is held (1 = full)."),
        Param("Release", 0.01, 8, 0.4, "s", log=True, help="How long the note fades after the key is released."),
        Param("Volume", 0, 1, 0.8, help="Loudness of this instrument."),
    ]

    def __init__(self, channel: int):
        super().__init__()   # Adjustable: naplní self.settings výchozíma hodnotama sliderů
        self.channel = channel
        # scale=1 = výška rovnou v Hz (ne číslo noty), first/last = bereme všech 128 MIDI not
        self.notes = Notein(poly=VOICES, scale=1, first=0, last=127, channel=channel)
        self.pitch = self.notes["pitch"]          # Hz, jeden signál na hlas
        self.trigger = self.notes["trigon"]       # krátkej impuls ve chvíli stisku (na Pitch drop a Sampler)
        s = self.settings
        # obálka dostane velocity: >0 = klávesa dole (rozjede Attack), 0 = puštěno (Release)
        self.envelope = MidiAdsr(self.notes["velocity"], attack=s["Attack"], decay=s["Decay"],
                                 sustain=s["Sustain"], release=s["Release"])
        self.volume = SigTo(s["Volume"], time=0.03, init=s["Volume"])
        self.socket = InputFader(Sig(0))          # na začátku je v zásuvce ticho
        # tady operátor * nevadí, socket i volume žijou stejně dlouho jako nástroj
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
        """zavolá to rack po každý změně: novej zvuk do zásuvky (None = ticho).

        zásuvka ještě 50 ms prolíná ze starýho zvuku, ale drží jen odkaz na novej.
        kdyby Python starej zvuk hned uvolnil, zvukový vlákno by četlo uvolněnou
        paměť a program spadl. proto si starej zvuk necháme v retired i s časem,
        kdy jsme ho vyměnili, a zahodí ho až tidy(), když už dávno doprolínal.
        """
        self.tidy()
        self.retired.append((time.monotonic(), self.current))
        # voices=1: všechny hlasy sečíst do jednoho kanálu
        self.current = Mix(flow, voices=1) if flow is not None else Sig(0)
        self.socket.setInput(self.current, fadetime=FADE_TIME)

    def tidy(self):
        """zahodí z retired starý zvuky, který už doprolínaly.

        dokud na ně v Pythonu je odkaz, pyo je pořád počítá (i když je nikdo neposlouchá),
        takže by jen žraly procesor. volá se z play() a každý 2 s z hlavní smyčky okna.
        """
        now = time.monotonic()
        self.retired = [(when, sound) for when, sound in self.retired if now - when < RETIRE_AFTER]
