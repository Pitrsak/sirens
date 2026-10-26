"""Vrstvy, ze kterých se skládá obraz (jako bloky u zvuku, jen pro obraz).

Obraz (canvas) je pole HEIGHT x WIDTH x 3 (R, G, B) s hodnotami 0..1
(float, takže 0.5 = půlka jasu; během počítání to může přetýct nad 1, painter to na konci ořízne).
Vrstvy se provedou shora dolů, každá dostane canvas a vrátí ho upravenej:
 - tvary (IS_SOURCE = True) do něj něco nakreslí (kruh, částice),
 - efekty (IS_SOURCE = False) změní celej obraz (dozvuk, zrcadlo, záře, vlnění).

Každá vrstva může reagovat na zvuk: "React to" vybere na co (hlasitost,
basy, středy, výšky, úder), "Reaction" jak moc. drive() z toho udělá číslo
0..2, který si vrstva použije po svým (zvětší tvar, zesílí efekt, ...).

Tvary kreslí OpenCV do 8bitový vrstvy (vyhlazený čáry umí jen v 8 bitech)
a ta se k obrazu přičte (blend): světlo se sčítá jako u projektorů,
dvě barvy přes sebe daj světlejší, nikdy tmavší.
"""

import colorsys

import cv2
import numpy as np

from sirens.param import Adjustable, Choice, Param

WIDTH, HEIGHT = 640, 360    # rozlišení obrazu v pixelech (16:9), na fullscreen se to jen zvětší
REACT = ("None", "Level", "Bass", "Mid", "High", "Beat")    # možnosti "React to", v settings je jejich pořadí


def react_params(default: int):
    # dva slidery, který má skoro každá vrstva: na co reagovat a jak moc (default = index do REACT)
    return [
        Choice("React to", REACT, default, help="Which part of the sound drives this layer."),
        Param("Reaction", 0, 2, 1, help="How strongly it reacts."),
    ]


def colour_params(hue: float):
    # barva jako odstín na barevným kole (0..360 stupňů) + jas
    return [
        Param("Color", 0, 360, hue, "deg", help="Hue on the colour wheel (0 red, 120 green, 240 blue)."),
        Param("Brightness", 0, 1, 0.9),
    ]


def blend(canvas, layer8):
    """Přičte 8bitovou vrstvu (0..255) k obrazu (0..1).

    Vydělit 255 (to je to * (1 / 255)), ať je to ve stejným rozsahu, a sečíst pixel po pixelu.
    Pozor, += mění canvas na místě, žádná kopie nevzniká.
    """
    canvas += layer8.astype(np.float32) * (1 / 255)
    return canvas


class Layer(Adjustable):
    NAME = ""           # jméno v menu "Add layer" (a v uloženým souboru)
    IS_SOURCE = True    # True = tvar (něco kreslí), False = efekt (mění obraz)
    POST = False        # True: jen navrch výsledku, ne do paměti pro Feedback (viz Glow)
    enabled = True      # vypnutou vrstvu painter přeskočí

    def drive(self, f) -> float:
        """Síla reakce na zvuk 0..2 podle "React to" a "Reaction" (None = 0).

        Vybraná věc ze zvuku je 0..1, Reaction 0..2, a to se prostě vynásobí.
        """
        source = REACT[round(self.settings["React to"])]     # číslo zpátky na jméno, třeba 2 -> "Bass"
        # slovník jméno -> hodnota z Features, a vyberu z něj tu jednu
        signal = {"None": 0.0, "Level": f.level, "Bass": f.bass, "Mid": f.mid,
                  "High": f.high, "Beat": f.beat}[source]
        return signal * self.settings["Reaction"]

    def colour(self, hue_shift: float = 0.0):
        """Barva vrstvy pro OpenCV jako (R, G, B) 0..255.

        HSV = odstín, sytost, jas, v tom se barva vybírá líp než míchat R, G, B ručně.
        Odstín je Color + hue_shift, % 360 to přetočí dokola a / 360 dá 0..1, jak chce colorsys,
        sytost je natvrdo 0.7, jas = Brightness. colorsys to pak převede na RGB 0..1, takže krát 255.
        """
        s = self.settings
        r, g, b = colorsys.hsv_to_rgb((s["Color"] + hue_shift) % 360 / 360, 0.7, s["Brightness"])
        return (r * 255, g * 255, b * 255)

    def apply(self, canvas, f):
        raise NotImplementedError       # každá vrstva si to napíše po svým


# --- TVARY, kreslí něco novýho ---

class RingLayer(Layer):
    """Uzavřená křivka kolem středu, poloměr v každým úhlu dává spektrum.

    Basy jsou nahoře, výšky dole, levá půlka je zrcadlo pravý.
    """

    NAME = "Ring"
    PARAMS = [
        *react_params(2),
        Param("Size", 0.05, 0.5, 0.2, help="Radius as a part of the picture height."),
        Param("Spectrum", 0, 1, 0.5, help="How much the outline follows the spectrum."),
        *colour_params(200),
        Param("Line", 1, 8, 2, "px", step=1),
    ]

    def apply(self, canvas, f):
        s = self.settings
        levels = np.concatenate([f.spectrum, f.spectrum[::-1]])   # pravá půlka + zrcadlo vlevo ([::-1] = pozpátku)
        # úhel pro každej bod dokola, - pi/2 = začíná se nahoře (y v obrázku roste dolů)
        angles = np.linspace(0, 2 * np.pi, len(levels), endpoint=False) - np.pi / 2
        # poloměr = základ Size (nafouknutej podle zvuku) + kousek podle spektra v tom úhlu
        radius = HEIGHT * (s["Size"] * (1 + 0.5 * self.drive(f)) + 0.25 * s["Spectrum"] * levels)
        # z úhlu a poloměru na pixely: x = střed + r*cos, y = střed + r*sin, a na celý čísla (OpenCV chce int)
        points = np.stack([WIDTH / 2 + radius * np.cos(angles),
                           HEIGHT / 2 + radius * np.sin(angles)], axis=1).astype(np.int32)
        layer = np.zeros_like(canvas, dtype=np.uint8)     # prázdná černá 8bitová vrstva, stejně velká
        # polylines = lomená čára přes body, True = uzavřená, LINE_AA = vyhlazená
        cv2.polylines(layer, [points], True, self.colour(), round(s["Line"]), cv2.LINE_AA)
        return blend(canvas, layer)


class ParticlesLayer(Layer):
    """Částice vyletujou ze středu (hlavně při úderech) a pomalu hasnou."""

    NAME = "Particles"
    MAX = 800       # strop, víc částic najednou ne
    PARAMS = [
        *react_params(5),
        Param("Amount", 0, 1, 0.5, help="How many particles are born."),
        Param("Speed", 0.5, 10, 3, "px", help="How fast they fly (pixels per frame)."),
        Param("Size", 1, 8, 2, "px", step=1),
        Param("Life", 0.8, 0.99, 0.95, help="How slowly they fade out."),
        *colour_params(30),
    ]

    def __init__(self):
        super().__init__()
        # každá částice = jeden řádek v polích, takže se dají hýbat všechny najednou
        self.pos = np.zeros((0, 2), dtype=np.float32)    # poloha každý částice (x, y)
        self.vel = np.zeros((0, 2), dtype=np.float32)    # rychlost (posun za snímek)
        self.life = np.zeros(0, dtype=np.float32)        # jas 1 -> 0

    def apply(self, canvas, f):
        s = self.settings
        # nový částice: bez reakce stálej proud, s reakcí podle zvuku
        # ("React to" 0 = None, takže >= 1 znamená, že je něco vybraný)
        drive = self.drive(f) if s["React to"] >= 1 else 0.5
        born = min(int(s["Amount"] * 40 * drive), self.MAX - len(self.life))    # kolik se jich narodí, max do stropu
        if born > 0:
            angle = np.random.uniform(0, 2 * np.pi, born)          # náhodnej směr
            speed = np.random.uniform(0.3, 1, born) * s["Speed"]   # náhodná rychlost 30..100 % ze Speed
            self.pos = np.vstack([self.pos, np.tile([WIDTH / 2, HEIGHT / 2], (born, 1))])    # všechny začínaj uprostřed
            # směr (cos, sin) krát rychlost = posun za snímek
            self.vel = np.vstack([self.vel, np.stack([np.cos(angle), np.sin(angle)], 1) * speed[:, None]])
            self.life = np.concatenate([self.life, np.ones(born)])     # plnej jas
        # pohyb a stárnutí, vyhaslý zahodím
        self.pos = self.pos + self.vel
        self.life = self.life * s["Life"]       # každej snímek trochu zhasnou (Life 0.95 = o 5 %)
        alive = self.life > 0.05                # maska, kdo ještě svítí
        self.pos, self.vel, self.life = self.pos[alive], self.vel[alive], self.life[alive]

        layer = np.zeros_like(canvas, dtype=np.uint8)
        r, g, b = self.colour()
        size = round(s["Size"])
        for (x, y), life in zip(self.pos, self.life):
            # plný (-1) vyhlazený kolečko, barva ztlumená podle life
            cv2.circle(layer, (int(x), int(y)), size, (r * life, g * life, b * life), -1, cv2.LINE_AA)
        return blend(canvas, layer)


class FeedbackLayer(Layer):
    """Dozvuk obrazu: minulej snímek se zvětší, pootočí a ztmaví, nový tvary se kreslí přes něj.

    Starý tvary tak odplouvaj a hasnou jako v tunelu. Patří nahoru (první vrstva).
    """

    NAME = "Feedback"
    IS_SOURCE = False
    PARAMS = [
        Param("Fade", 0.5, 0.99, 0.9, help="How long old frames stay (higher = longer trails)."),
        Param("Zoom", 0.9, 1.1, 1.02, help="Above 1 old shapes fly outwards, below 1 inwards."),
        Param("Spin", -5, 5, 0.5, "deg", help="Turn of the old frame every frame."),
        *react_params(0),
    ]

    def apply(self, canvas, f):
        s = self.settings
        zoom = s["Zoom"] + 0.05 * self.drive(f)     # se zvukem se zoom ještě přidá, max o 0.1
        # matice 2x3, která otočí o Spin stupňů a zvětší o zoom, obojí kolem středu obrázku
        matrix = cv2.getRotationMatrix2D((WIDTH / 2, HEIGHT / 2), s["Spin"], zoom)
        # warpAffine přesune každej pixel podle tý matice (otočení + zvětšení najednou)
        canvas = cv2.warpAffine(canvas, matrix, (WIDTH, HEIGHT))
        return canvas * s["Fade"]       # ztmavení, třeba na 90 % každej snímek, starý věci tak postupně zmizí


class MirrorLayer(Layer):
    """Zrcadlení (vlastní operace s polem): jedna půlka obrazu se překlopí na druhou."""

    NAME = "Mirror"
    IS_SOURCE = False
    PARAMS = [Choice("Mode", ("Left-right", "Top-bottom", "Both"), 0)]

    def apply(self, canvas, f):
        mode = round(self.settings["Mode"])     # 0 = zleva doprava, 1 = shora dolů, 2 = obojí
        if mode in (0, 2):
            canvas[:, WIDTH // 2:] = canvas[:, :WIDTH // 2][:, ::-1]    # levá půlka obráceně vpravo (sloupce pozpátku)
        if mode in (1, 2):
            canvas[HEIGHT // 2:] = canvas[:HEIGHT // 2][::-1]          # horní půlka obráceně dole (řádky pozpátku)
        return canvas


class GlowLayer(Layer):
    """Záře: rozmazaná kopie obrazu přičtená navrch, světlý místa svítí do okolí.

    Záře se přidá jen k tomu, co se zobrazí, ne do paměti pro Feedback (POST),
    jinak by se světlo každej snímek přičítalo znova a obraz by za chvilku zbělal.
    """

    NAME = "Glow"
    IS_SOURCE = False
    POST = True
    PARAMS = [
        Param("Amount", 0, 2, 0.8, help="Strength of the halo."),
        Param("Radius", 1, 30, 10, "px", help="How far the halo reaches."),
        *react_params(0),
    ]

    def halo(self, canvas, f):
        """Obraz záře, kterej se přičte k výslednýmu snímku.

        GaussianBlur = rozmazání, každej pixel je váženej průměr okolí (váhy ve tvaru zvonu,
        Gaussova křivka). (0, 0) = velikost okna si OpenCV dopočítá samo z Radius (sigma).
        """
        s = self.settings
        return cv2.GaussianBlur(canvas, (0, 0), s["Radius"]) * s["Amount"] * (1 + self.drive(f))


class WarpLayer(Layer):
    """Vlnění: každej pixel se vezme z místa posunutýho o sinusovou vlnu (cv2.remap)."""

    NAME = "Warp"
    IS_SOURCE = False
    PARAMS = [
        Param("Amount", 0, 40, 10, "px", help="How far pixels are moved."),
        Param("Waves", 1, 10, 3, help="How many waves fit across the picture."),
        Param("Speed", 0, 5, 1, help="How fast the waves move."),
        *react_params(2),
    ]

    def __init__(self):
        super().__init__()
        # mřížka souřadnic, xs[y, x] = x a ys[y, x] = y, každej pixel zná svoji polohu (počítá se jednou)
        self.xs, self.ys = np.meshgrid(np.arange(WIDTH, dtype=np.float32), np.arange(HEIGHT, dtype=np.float32))

    def apply(self, canvas, f):
        s = self.settings
        amount = s["Amount"] * (1 + self.drive(f))      # o kolik pixelů se posouvá, se zvukem víc
        phase = f.time * s["Speed"]                     # posun vlny v čase, ať se to hýbe
        # vodorovnej posun závisí na řádku (y), svislej na sloupci (x), takže se to vlní oběma směry
        dx = amount * np.sin(2 * np.pi * s["Waves"] * self.ys / HEIGHT + phase)
        dy = amount * np.sin(2 * np.pi * s["Waves"] * self.xs / WIDTH + phase * 1.3)    # 1.3 = jiná rychlost než dx
        # remap: výsledek[y, x] = canvas[ys + dy, xs + dx], mezi pixely se dopočítá (INTER_LINEAR),
        # na krajích se obraz zrcadlí (BORDER_REFLECT), ať tam nejsou černý díry
        return cv2.remap(canvas, self.xs + dx, self.ys + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


CATALOG = [RingLayer, ParticlesLayer, FeedbackLayer, MirrorLayer, GlowLayer, WarpLayer]
