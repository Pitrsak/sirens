"""Analytická vizualizace: osciloskop, spektrum v pásmech a posuvný spektrogram.

Obraz kreslíme sami do pole pixelů (OpenCV obraz = numpy pole výška x šířka x 3, BGR).
"""

import cv2
import numpy as np

from fathom.audio.analyzer import BAND_COUNT

WIDTH, HEIGHT = 640, 360
HISTORY = 160  # kolik snímků (sloupců) si spektrogram pamatuje


class SpectrumVisual:
    def __init__(self):
        # Historie spektra: řádky = pásma, sloupce = čas. Hodnoty 0..255.
        self.history = np.zeros((BAND_COUNT, HISTORY), dtype=np.uint8)

    def render(self, bands: list[float], scope: list[float]) -> np.ndarray:
        img = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        self._draw_scope(img, scope, top=10, height=90)
        self._draw_bars(img, bands, top=110, height=100)
        self._draw_spectrogram(img, bands, top=220, height=HEIGHT - 230)
        return img

    def _draw_scope(self, img, samples, top, height):
        """Průběh signálu v čase. Začátek kreslení zarovnáme na průchod nulou
        směrem nahoru, aby periodický signál na obrazovce "stál" a neutíkal."""
        if len(samples) < 2:
            return
        start = 0
        for i in range(1, len(samples) // 2):
            if samples[i - 1] < 0 <= samples[i]:
                start = i
                break
        window = samples[start:start + len(samples) // 2]
        mid = top + height // 2
        xs = np.linspace(10, WIDTH - 10, len(window))
        ys = mid - np.clip(np.array(window), -1, 1) * (height / 2)
        points = np.stack([xs, ys], axis=1).astype(np.int32)
        cv2.line(img, (10, mid), (WIDTH - 10, mid), (40, 40, 40), 1)
        cv2.polylines(img, [points], False, (235, 235, 235), 1, cv2.LINE_AA)

    def _draw_bars(self, img, bands, top, height):
        """Sloupce pásem, barva podle výšky z barevné mapy INFERNO."""
        values = (np.array(bands) * 255).astype(np.uint8)
        colors = cv2.applyColorMap(values.reshape(-1, 1), cv2.COLORMAP_INFERNO)
        bar_w = (WIDTH - 20) / BAND_COUNT
        for i, v in enumerate(bands):
            x0 = int(10 + i * bar_w)
            x1 = int(10 + (i + 1) * bar_w) - 2
            y0 = int(top + height * (1 - v))
            color = tuple(int(c) for c in colors[i, 0])
            cv2.rectangle(img, (x0, y0), (x1, top + height), color, -1)

    def _draw_spectrogram(self, img, bands, top, height):
        """Historie posunutá o jeden sloupec doleva, nový sloupec vpravo."""
        self.history = np.roll(self.history, -1, axis=1)
        self.history[:, -1] = (np.array(bands) * 255).astype(np.uint8)
        # Nízké frekvence chceme dole, proto obrátíme pořadí řádků.
        picture = cv2.resize(self.history[::-1], (WIDTH - 20, height), interpolation=cv2.INTER_NEAREST)
        img[top:top + height, 10:WIDTH - 10] = cv2.applyColorMap(picture, cv2.COLORMAP_INFERNO)
