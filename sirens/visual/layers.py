"""Vrstvy, ze kterých se skládá obraz (jako bloky u zvuku).

Obraz (canvas) je pole HEIGHT x WIDTH x 3 (R, G, B) s hodnotami 0..1.
Vrstvy se provedou shora dolů, každá dostane canvas a vrátí ho upravený:
 - tvary (IS_SOURCE = True) do něj něco nakreslí (kruh, vlnu, částice...),
 - efekty (IS_SOURCE = False) změní celý obraz (dozvuk, zrcadlo, záře...).

Každá vrstva může reagovat na zvuk: "React to" vybere, na co (hlasitost,
basy, středy, výšky, úder), "Reaction" jak silně. drive() z toho dá číslo
0..2, které vrstva použije (zvětší tvar, zesílí efekt, ...).

Tvary kreslí OpenCV do 8bitové vrstvy (vyhlazené čáry umí jen v 8 bitech)
a ta se k obrazu přičte (blend): světlo se sčítá jako u projektorů.
"""

import colorsys
import math

import cv2
import numpy as np

from sirens.param import Adjustable, Choice, Param

WIDTH, HEIGHT = 640, 360
REACT = ("None", "Level", "Bass", "Mid", "High", "Beat")


def react_params(default: int):
    return [
        Choice("React to", REACT, default, help="Which part of the sound drives this layer."),
        Param("Reaction", 0, 2, 1, help="How strongly it reacts."),
    ]


def colour_params(hue: float):
    return [
        Param("Color", 0, 360, hue, "deg", help="Hue on the colour wheel (0 red, 120 green, 240 blue)."),
        Param("Brightness", 0, 1, 0.9),
    ]


def blend(canvas, layer8):
    """Přičte 8bitovou vrstvu (0..255) k obrazu (0..1)."""
    canvas += layer8.astype(np.float32) * (1 / 255)
    return canvas


class Layer(Adjustable):
    NAME = ""
    IS_SOURCE = True
    POST = False        # True: jen navrch výsledku, ne do paměti pro Feedback (viz Glow)
    enabled = True      # vypnutou vrstvu painter přeskočí

    def drive(self, f) -> float:
        """Síla reakce na zvuk 0..2 podle "React to" a "Reaction" (None = 0)."""
        source = REACT[round(self.settings["React to"])]
        signal = {"None": 0.0, "Level": f.level, "Bass": f.bass, "Mid": f.mid,
                  "High": f.high, "Beat": f.beat}[source]
        return signal * self.settings["Reaction"]

    def colour(self, hue_shift: float = 0.0):
        """Barva vrstvy pro OpenCV jako (R, G, B) 0..255."""
        s = self.settings
        r, g, b = colorsys.hsv_to_rgb((s["Color"] + hue_shift) % 360 / 360, 0.7, s["Brightness"])
        return (r * 255, g * 255, b * 255)

    def apply(self, canvas, f):
        raise NotImplementedError


# --- tvary ---

class RingLayer(Layer):
    """Uzavřená křivka kolem středu: poloměr v každém úhlu dává spektrum."""

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
        levels = np.concatenate([f.spectrum, f.spectrum[::-1]])   # pravá půlka + zrcadlo vlevo
        angles = np.linspace(0, 2 * np.pi, len(levels), endpoint=False) - np.pi / 2
        radius = HEIGHT * (s["Size"] * (1 + 0.5 * self.drive(f)) + 0.25 * s["Spectrum"] * levels)
        points = np.stack([WIDTH / 2 + radius * np.cos(angles),
                           HEIGHT / 2 + radius * np.sin(angles)], axis=1).astype(np.int32)
        layer = np.zeros_like(canvas, dtype=np.uint8)
        cv2.polylines(layer, [points], True, self.colour(), round(s["Line"]), cv2.LINE_AA)
        return blend(canvas, layer)


class WaveLayer(Layer):
    """Tvar zvukové vlny přes celou šířku (jako osciloskop)."""

    NAME = "Wave"
    PARAMS = [
        *react_params(1),
        Param("Height", 0, 1, 0.3, help="How tall the wave is drawn."),
        Param("Position", 0, 1, 0.5, help="Vertical position (0 top, 1 bottom)."),
        *colour_params(160),
        Param("Line", 1, 8, 2, "px", step=1),
    ]

    def apply(self, canvas, f):
        s = self.settings
        if len(f.wave) < 2:
            return canvas
        x = np.linspace(0, WIDTH - 1, len(f.wave))
        y = HEIGHT * s["Position"] - f.wave * HEIGHT * s["Height"] * (1 + self.drive(f))
        points = np.stack([x, y], axis=1).astype(np.int32)
        layer = np.zeros_like(canvas, dtype=np.uint8)
        cv2.polylines(layer, [points], False, self.colour(), round(s["Line"]), cv2.LINE_AA)
        return blend(canvas, layer)


class BarsLayer(Layer):
    """Sloupce spektra (hluboké tóny vlevo, vysoké vpravo)."""

    NAME = "Bars"
    PARAMS = [
        *react_params(0),
        Param("Count", 8, 96, 48, step=1),
        Param("Height", 0, 1, 0.5),
        Choice("Place", ("Bottom", "Center"), 0, help="Grow from the bottom edge or both ways from the middle."),
        *colour_params(280),
    ]

    def apply(self, canvas, f):
        s = self.settings
        count = round(s["Count"])
        index = np.linspace(0, len(f.spectrum) - 1, count).astype(int)
        heights = f.spectrum[index] * HEIGHT * s["Height"] * (1 + self.drive(f))
        width = WIDTH / count
        layer = np.zeros_like(canvas, dtype=np.uint8)
        for i, h in enumerate(heights):
            x0, x1 = int(i * width + 1), int((i + 1) * width - 1)
            if s["Place"] < 0.5:
                y0, y1 = int(HEIGHT - h), HEIGHT
            else:
                y0, y1 = int(HEIGHT / 2 - h / 2), int(HEIGHT / 2 + h / 2)
            cv2.rectangle(layer, (x0, y0), (x1, y1), self.colour(i / count * 60), -1)
        return blend(canvas, layer)


class ParticlesLayer(Layer):
    """Částice vyletují ze středu (hlavně při úderech) a pomalu hasnou."""

    NAME = "Particles"
    MAX = 800
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
        self.pos = np.zeros((0, 2), dtype=np.float32)    # poloha každé částice
        self.vel = np.zeros((0, 2), dtype=np.float32)    # rychlost (posun za snímek)
        self.life = np.zeros(0, dtype=np.float32)        # jas 1 -> 0

    def apply(self, canvas, f):
        s = self.settings
        # nové částice: bez reakce stálý proud, s reakcí podle zvuku
        drive = self.drive(f) if s["React to"] >= 1 else 0.5
        born = min(int(s["Amount"] * 40 * drive), self.MAX - len(self.life))
        if born > 0:
            angle = np.random.uniform(0, 2 * np.pi, born)
            speed = np.random.uniform(0.3, 1, born) * s["Speed"]
            self.pos = np.vstack([self.pos, np.tile([WIDTH / 2, HEIGHT / 2], (born, 1))])
            self.vel = np.vstack([self.vel, np.stack([np.cos(angle), np.sin(angle)], 1) * speed[:, None]])
            self.life = np.concatenate([self.life, np.ones(born)])
        # pohyb a stárnutí; vyhaslé zahodíme
        self.pos = self.pos + self.vel
        self.life = self.life * s["Life"]
        alive = self.life > 0.05
        self.pos, self.vel, self.life = self.pos[alive], self.vel[alive], self.life[alive]

        layer = np.zeros_like(canvas, dtype=np.uint8)
        r, g, b = self.colour()
        size = round(s["Size"])
        for (x, y), life in zip(self.pos, self.life):
            cv2.circle(layer, (int(x), int(y)), size, (r * life, g * life, b * life), -1, cv2.LINE_AA)
        return blend(canvas, layer)


class OrbitLayer(Layer):
    """Kolečka obíhající kolem středu."""

    NAME = "Orbit"
    PARAMS = [
        *react_params(1),
        Param("Count", 1, 24, 6, step=1),
        Param("Radius", 0, 0.5, 0.3, help="Size of the orbit as a part of the picture height."),
        Param("Speed", -2, 2, 0.2, help="Turns per second (minus = the other way)."),
        Param("Size", 1, 40, 8, "px"),
        *colour_params(100),
    ]

    def apply(self, canvas, f):
        s = self.settings
        count = round(s["Count"])
        drive = self.drive(f)
        radius = s["Radius"] * HEIGHT * (1 + 0.5 * drive)
        layer = np.zeros_like(canvas, dtype=np.uint8)
        for i in range(count):
            angle = f.time * s["Speed"] * 2 * math.pi + i * 2 * math.pi / count
            x = WIDTH / 2 + radius * math.cos(angle)
            y = HEIGHT / 2 + radius * math.sin(angle)
            cv2.circle(layer, (int(x), int(y)), int(s["Size"] * (1 + drive)), self.colour(i * 15), -1, cv2.LINE_AA)
        return blend(canvas, layer)


# --- efekty ---

class FeedbackLayer(Layer):
    """Dozvuk obrazu: minulý snímek se zvětší, pootočí a ztmaví, nové tvary se kreslí přes něj.

    Staré tvary tak odplouvají a hasnou jako v tunelu. Patří nahoru (první vrstva).
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
        zoom = s["Zoom"] + 0.05 * self.drive(f)
        matrix = cv2.getRotationMatrix2D((WIDTH / 2, HEIGHT / 2), s["Spin"], zoom)
        canvas = cv2.warpAffine(canvas, matrix, (WIDTH, HEIGHT))
        return canvas * s["Fade"]


class MirrorLayer(Layer):
    """Zrcadlení (vlastní operace s polem): jedna polovina obrazu se překlopí na druhou."""

    NAME = "Mirror"
    IS_SOURCE = False
    PARAMS = [Choice("Mode", ("Left-right", "Top-bottom", "Both"), 0)]

    def apply(self, canvas, f):
        mode = round(self.settings["Mode"])
        if mode in (0, 2):
            canvas[:, WIDTH // 2:] = canvas[:, :WIDTH // 2][:, ::-1]    # levá půlka obráceně vpravo
        if mode in (1, 2):
            canvas[HEIGHT // 2:] = canvas[:HEIGHT // 2][::-1]          # horní půlka obráceně dole
        return canvas


class GlowLayer(Layer):
    """Záře: rozmazaná kopie obrazu přičtená navrch, světlá místa svítí do okolí.

    Záře se přidá jen k tomu, co se zobrazí, ne do paměti pro Feedback (POST):
    jinak by se světlo každý snímek přičítalo znovu a obraz by během chvíle zbělal.
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
        """Obraz záře, který se přičte k výslednému snímku."""
        s = self.settings
        return cv2.GaussianBlur(canvas, (0, 0), s["Radius"]) * s["Amount"] * (1 + self.drive(f))


class WarpLayer(Layer):
    """Vlnění: každý pixel se vezme z místa posunutého o sinusovou vlnu (cv2.remap)."""

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
        self.xs, self.ys = np.meshgrid(np.arange(WIDTH, dtype=np.float32), np.arange(HEIGHT, dtype=np.float32))

    def apply(self, canvas, f):
        s = self.settings
        amount = s["Amount"] * (1 + self.drive(f))
        phase = f.time * s["Speed"]
        dx = amount * np.sin(2 * np.pi * s["Waves"] * self.ys / HEIGHT + phase)
        dy = amount * np.sin(2 * np.pi * s["Waves"] * self.xs / WIDTH + phase * 1.3)
        return cv2.remap(canvas, self.xs + dx, self.ys + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


class SplitLayer(Layer):
    """Rozjetí barev: červená složka se posune doprava, modrá doleva (glitch)."""

    NAME = "RGB Split"
    IS_SOURCE = False
    PARAMS = [Param("Shift", 0, 30, 4, "px"), *react_params(5)]

    def apply(self, canvas, f):
        shift = int(self.settings["Shift"] * (1 + 2 * self.drive(f)))
        canvas[..., 0] = np.roll(canvas[..., 0], shift, axis=1)
        canvas[..., 2] = np.roll(canvas[..., 2], -shift, axis=1)
        return canvas


class PixelateLayer(Layer):
    """Zhrubnutí: obraz se zmenší a zase zvětší bez vyhlazení, vzniknou čtverce."""

    NAME = "Pixelate"
    IS_SOURCE = False
    PARAMS = [Param("Size", 1, 40, 8, "px", help="Size of one square."), *react_params(0)]

    def apply(self, canvas, f):
        size = max(1, int(self.settings["Size"] * (1 + self.drive(f))))
        small = cv2.resize(canvas, (max(1, WIDTH // size), max(1, HEIGHT // size)), interpolation=cv2.INTER_AREA)
        return cv2.resize(small, (WIDTH, HEIGHT), interpolation=cv2.INTER_NEAREST)


class TintLayer(Layer):
    """Přebarvení (vlastní operace): podle jasu pixelu barva mezi Dark a Light odstínem."""

    NAME = "Tint"
    IS_SOURCE = False
    PARAMS = [
        Param("Dark", 0, 360, 240, "deg", help="Hue for dark parts."),
        Param("Light", 0, 360, 30, "deg", help="Hue for bright parts."),
        Param("Amount", 0, 1, 1, help="0 = original colours, 1 = fully tinted."),
    ]

    def apply(self, canvas, f):
        s = self.settings
        dark = np.array(colorsys.hsv_to_rgb(s["Dark"] / 360, 0.8, 1), dtype=np.float32)
        light = np.array(colorsys.hsv_to_rgb(s["Light"] / 360, 0.6, 1), dtype=np.float32)
        lum = np.clip(canvas.mean(axis=2, keepdims=True), 0, 1)     # jas pixelu 0..1
        tinted = (dark * (1 - lum) + light * lum) * lum              # odstín podle jasu, krát jas
        return canvas * (1 - s["Amount"]) + tinted * s["Amount"]


CATALOG = [RingLayer, WaveLayer, BarsLayer, ParticlesLayer, OrbitLayer,
           FeedbackLayer, MirrorLayer, GlowLayer, WarpLayer, SplitLayer, PixelateLayer, TintLayer]
