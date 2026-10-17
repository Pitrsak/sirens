"""Abstraktní vizualizace inspirovaná projektem Event Horizon.

Postup každého snímku (vše vlastní operace nad polem pixelů):
 1. plazma: součet sinusových vln přes souřadnice -> pole hodnot 0..1
 2. kosinová paleta: hodnoty 0..1 -> barvy
 3. posunutí pixelů (cv2.remap): rýhované sklo + vlnky od zahraných not
 4. chromatická disperze: červený a modrý kanál posuneme na opačné strany
 5. stopy: smíchání s předchozím snímkem

Zvuk to řídí přes energii v pásmech: basy -> jas, středy -> barva,
výšky -> sklo, hlasitost -> rychlost a disperze. Každá nota vyšle vlnku.
"""

import math

import cv2
import numpy as np

from fathom.param import Param

WIDTH, HEIGHT = 256, 144  # počítáme v malém rozlišení a zvětšujeme až při zobrazení

VISUAL_PARAMS = [
    Param("speed", "SPEED", 0, 3, 1.0),
    Param("scale", "SCALE", 0.5, 6, 2.0, log=True),
    Param("hue", "HUE", 0, 1, 0.0),
    Param("glass", "GLASS", 0, 1, 0.4),
    Param("chroma", "CHROMA", 0, 1, 0.4),
    Param("ripple", "RIPPLE", 0, 1, 0.6),
    Param("trails", "TRAILS", 0, 0.95, 0.3),
    Param("react", "REACT", 0, 2, 1.0),
]
VISUAL_DEFAULTS = {p.key: p.default for p in VISUAL_PARAMS}


class AbstractVisual:
    def __init__(self):
        self.values = dict(VISUAL_DEFAULTS)
        # Souřadnice každého pixelu. map_x/map_y v pixelech (pro remap),
        # u/v normalizované kolem středu (pro výpočet vzorů).
        ys, xs = np.mgrid[0:HEIGHT, 0:WIDTH].astype(np.float32)
        self.map_x, self.map_y = xs, ys
        self.u = (xs - WIDTH / 2) / (HEIGHT / 2)
        self.v = (ys - HEIGHT / 2) / (HEIGHT / 2)
        self.time = 0.0
        self.ripples = []   # seznam [x, y, stáří] pro každou vlnku
        self.previous = None

    def set(self, key: str, value: float):
        self.values[key] = value

    def on_note(self, note: int, is_on: bool):
        """Zahraná nota vyšle vlnku. Výška tónu určuje vodorovnou pozici."""
        if not is_on:
            return
        x = (note % 24) / 24 * WIDTH * 0.8 + WIDTH * 0.1
        y = HEIGHT * (0.5 + 0.3 * math.sin(note * 1.7))
        self.ripples.append([x, y, 0.0])

    def render(self, dt: float, bands: list[float], level: float) -> np.ndarray:
        p = self.values
        react = p["react"]
        third = len(bands) // 3
        low = sum(bands[:third]) / third * react
        mid = sum(bands[third:2 * third]) / third * react
        high = sum(bands[2 * third:]) / (len(bands) - 2 * third) * react

        # 1) plazma: čtyři sinusové vlny v různých směrech, posouvané v čase
        self.time += dt * p["speed"] * (0.3 + 1.5 * level * react)
        t, s = self.time, p["scale"]
        x, y = self.u * s, self.v * s
        field = (np.sin(x * 1.7 + t)
                 + np.sin(y * 2.3 - t * 0.8)
                 + np.sin((x + y) * 1.3 + t * 0.6)
                 + np.sin(np.sqrt(x * x + y * y) * 3.0 - t * 1.4))
        field = field * 0.125 + 0.5  # součet je v -4..4, převedeme na 0..1

        # 2) kosinová paleta: barva = 0.5 + 0.5*cos(2*pi*(c*hodnota + posun kanálu))
        #    c = 0.6 projde jen část barevného kruhu -> sladěné odstíny místo duhy.
        #    Mocnina field**1.5 ztmaví údolí vln, světlé zůstanou hlavně hřebeny.
        hue = p["hue"] + mid * 0.3
        brightness = 0.5 + 0.8 * min(1.0, low * 1.5)
        shade = 0.12 + 0.88 * field ** 1.5
        channels = [0.5 + 0.5 * np.cos(2 * np.pi * (0.6 * field + hue + offset)) for offset in (0.2, 0.1, 0.0)]
        img = np.dstack(channels).astype(np.float32) * (shade * brightness)[:, :, None]  # pořadí B, G, R

        # 3) posunutí pixelů: každý pixel si vezme barvu z jiného místa
        dx = np.zeros_like(self.map_x)
        dy = np.zeros_like(self.map_y)
        # rýhované sklo: vodorovný posun podle sinusovky -> svislé "lamely"
        glass = p["glass"] * (0.4 + high * 1.5)
        flute = self.map_x * 0.35          # fáze lamely; jedna lamela má cca 18 px
        dx += glass * 6.0 * np.sin(flute)
        # vlnky: kruhová vlna od místa noty, slábne se vzdáleností i časem
        for ripple in self.ripples:
            rx, ry, age = ripple
            ox, oy = self.map_x - rx, self.map_y - ry
            dist = np.sqrt(ox * ox + oy * oy) + 1.0
            wave = np.sin(dist * 0.3 - age * 14.0) * math.exp(-age * 1.8) * np.exp(-dist * 0.015)
            strength = p["ripple"] * 8.0
            dx += wave * ox / dist * strength
            dy += wave * oy / dist * strength
            ripple[2] += dt
        self.ripples = [r for r in self.ripples if r[2] < 3.0]
        img = cv2.remap(img, self.map_x + dx, self.map_y + dy, cv2.INTER_LINEAR,
                        borderMode=cv2.BORDER_REFLECT)
        # osvětlení lamel: hrana každé lamely trochu ztmavne, střed se zvýrazní
        img *= (1.0 + glass * 0.35 * np.cos(flute))[:, :, None]

        # 4) chromatická disperze: R doprava, B doleva (o pár pixelů)
        shift = p["chroma"] * (1.0 + level * react * 4.0) * 2.0
        if shift > 0.05:
            b, g, r = cv2.split(img)
            b = cv2.remap(b, self.map_x - shift, self.map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            r = cv2.remap(r, self.map_x + shift, self.map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            img = cv2.merge([b, g, r])

        # 5) stopy: vážený průměr s minulým snímkem
        if self.previous is not None and p["trails"] > 0:
            img = cv2.addWeighted(img, 1.0 - p["trails"], self.previous, p["trails"], 0)
        self.previous = img

        return np.clip(img * 255, 0, 255).astype(np.uint8)
