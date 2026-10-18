"""Světlo řízené hudbou: jedno RGB světlo (např. LED par) na DMX.

Basy svítí červeně, středy zeleně, výšky modře. Smoothing zpomaluje změny,
aby světlo neblikalo. Kanály světla jsou Address (R), Address+1 (G), Address+2 (B).
"""

from sirens.param import Adjustable, Param

DMX_CHANNELS = 512


class LightRig(Adjustable):
    PARAMS = [
        Param("Brightness", 0, 1, 1, help="Maximum brightness of the light."),
        Param("Smoothing", 0, 0.95, 0.6, help="Higher = slower, softer changes. Lower = sharper flashes."),
        Param("Address", 1, 510, 1, help="DMX channel of red. Green and blue are the next two."),
        Param("Universe", 0, 15, 0, help="Art-Net universe the light listens on."),
    ]

    def __init__(self):
        super().__init__()
        self.rgb = [0.0, 0.0, 0.0]     # aktuální barva, každá složka 0..1

    def update(self, bands):
        """Posune barvu směrem k (basy, středy, výšky).

        Vyhlazení: nová hodnota = kus staré + kus cílové. Čím víc Smoothing,
        tím víc staré a tím pomaleji se světlo mění.
        """
        keep = self.settings["Smoothing"]
        self.rgb = [keep * old + (1 - keep) * new for old, new in zip(self.rgb, bands)]

    def values(self) -> list[int]:
        """R, G, B jako DMX hodnoty 0..255."""
        brightness = self.settings["Brightness"]
        return [round(c * brightness * 255) for c in self.rgb]

    def address(self) -> int:
        return round(self.settings["Address"])

    def universe(self) -> int:
        return round(self.settings["Universe"])

    def channels(self) -> list[int]:
        """Všech 512 kanálů universa: nuly a na místě světla jeho R, G, B."""
        frame = [0] * DMX_CHANNELS
        start = self.address() - 1          # kanály se číslují od 1, seznam od 0
        frame[start:start + 3] = self.values()
        return frame
