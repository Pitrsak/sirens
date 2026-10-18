"""Abstraktní obraz, který reaguje na hudbu (OpenCV + numpy).

Obraz je pole HEIGHT x WIDTH x 3 (R, G, B) s hodnotami 0..1. Každý snímek:
 1. zpětná vazba: minulý snímek trochu zvětšíme a pootočíme (cv2.warpAffine),
    takže staré tvary odplouvají od středu a točí se jako v tunelu,
 2. vyhasínání (vlastní operace): každý pixel vynásobíme číslem Trail < 1,
 3. nový tvar: uzavřená křivka kolem středu; její poloměr v každém úhlu
    udává spektrum (nahoře hluboké tóny, dole vysoké, zrcadlově vlevo a vpravo),
    velikost dávají basy, barvu výšky, jas nejsilnější pásmo,
 4. sloučení (vlastní operace): v každém pixelu necháme jasnější z obou vrstev,
 5. převod na 8 bitů (0..255) pro zobrazení.
"""

import colorsys

import cv2
import numpy as np

from sirens.param import Adjustable, Param

WIDTH, HEIGHT = 640, 360
POINTS = 96     # bodů na jedné polovině křivky (druhá je zrcadlová)


class Painter(Adjustable):
    PARAMS = [
        Param("Trail", 0.5, 0.99, 0.9, help="How long old shapes stay before they fade out."),
        Param("Zoom", 0.95, 1.1, 1.02, help="Above 1 old shapes fly outwards, below 1 they fall inwards."),
        Param("Spin", -5, 5, 0.5, "deg", help="How much old shapes turn every frame."),
        Param("Reaction", 0, 2, 1, help="How strongly the shape follows the music."),
        Param("Color", 0, 360, 200, "deg", help="Base hue on the colour wheel. High frequencies shift it."),
        Param("Line", 1, 8, 2, "px", help="Thickness of the line."),
    ]

    def __init__(self):
        super().__init__()
        self.canvas = np.zeros((HEIGHT, WIDTH, 3), dtype=np.float32)

    def render(self, analyzer) -> np.ndarray:
        """Spočítá další snímek a vrátí ho jako 8bitové RGB pole."""
        s = self.settings
        # 1) zpětná vazba: otočení o Spin stupňů a zvětšení Zoom kolem středu
        matrix = cv2.getRotationMatrix2D((WIDTH / 2, HEIGHT / 2), s["Spin"], s["Zoom"])
        self.canvas = cv2.warpAffine(self.canvas, matrix, (WIDTH, HEIGHT))
        # 2) vyhasínání
        self.canvas *= s["Trail"]
        # 3) + 4) nový tvar do zvláštní vrstvy, pak jasnější z obou
        layer = self._draw_shape(analyzer)
        self.canvas = np.maximum(self.canvas, layer.astype(np.float32) / 255)
        # 5) 0..1 -> 0..255
        return (np.clip(self.canvas, 0, 1) * 255).astype(np.uint8)

    def _draw_shape(self, analyzer) -> np.ndarray:
        s = self.settings
        bass, mid, high = analyzer.bands()
        loudest = max(bass, mid, high)
        layer = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        if loudest == 0:
            return layer      # ticho: nic nekreslíme

        # Síla spektra (0..1) na frekvencích rozložených logaritmicky 40 Hz - 10 kHz.
        freqs = np.geomspace(40, 10000, POINTS)
        bins = np.minimum(np.searchsorted(analyzer.freqs, freqs), len(analyzer.freqs) - 1)
        levels = np.clip((analyzer.spectrum[bins] + 60) / 60, 0, 1)
        levels = np.concatenate([levels, levels[::-1]])   # pravá půlka + zrcadlo vlevo

        # Úhly od vrcholu kruhu (-90 stupňů) dokola.
        angles = np.linspace(0, 2 * np.pi, len(levels), endpoint=False) - np.pi / 2
        react = s["Reaction"]
        radius = HEIGHT * (0.12 + 0.10 * bass * react + 0.18 * levels * react)
        x = WIDTH / 2 + radius * np.cos(angles)
        y = HEIGHT / 2 + radius * np.sin(angles)
        points = np.stack([x, y], axis=1).astype(np.int32)

        # Barva: odstín Color posunutý výškami, jas podle nejsilnějšího pásma.
        hue = (s["Color"] + high * 120) % 360 / 360
        r, g, b = colorsys.hsv_to_rgb(hue, 0.65, 0.4 + 0.6 * loudest)
        cv2.polylines(layer, [points], True, (r * 255, g * 255, b * 255),
                      round(s["Line"]), cv2.LINE_AA)
        return layer
