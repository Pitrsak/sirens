"""Obraz poskládaný z vrstev (viz layers.py), kterej reaguje na hudbu.

Každej snímek jde takhle:
 1. Features spočítá, co je ve zvuku (basy, úder, spektrum, ...),
 2. začne se od minulýho snímku (když je v seznamu Feedback), jinak od černý,
 3. vrstvy se provedou shora dolů, výsledek si pamatuju na příští snímek,
 4. navrch se přičte záře (Glow), ta se do paměti nedává,
 5. ořez na 0..1 a převod na 8 bitů (0..255), ať se to dá zobrazit.
"""

import numpy as np

from sirens.stack import Stack
from sirens.visual.features import Features
from sirens.visual.layers import HEIGHT, WIDTH, FeedbackLayer


# Stack = seznam vrstev, co umí přidat / smazat / posunout / vypnout (sirens/stack.py)
class Painter(Stack):
    def __init__(self):
        super().__init__()
        # paměť obrazu: výška x šířka x 3 barvy, float 0..1 (na tohle navazuje Feedback)
        self.canvas = np.zeros((HEIGHT, WIDTH, 3), dtype=np.float32)
        self.features = Features()

    @property
    def layers(self):
        # vrstvy jsou prostě prvky ze Stacku, jen se to tak líp čte
        return self.items

    def render(self, analyzer, dt: float) -> np.ndarray:
        """Spočítá další snímek a vrátí ho jako 8bitový RGB pole (výška x šířka x 3, 0..255)."""
        self.features.update(analyzer, dt)
        layers = [layer for layer in self.layers if layer.enabled]      # vypnutý vrstvy přeskočím
        keep = any(isinstance(layer, FeedbackLayer) for layer in layers)   # je tam zapnutej Feedback?
        canvas = self.canvas if keep else np.zeros_like(self.canvas)     # navázat na minulej snímek, jinak čistá černá
        halos = []      # záře z Glow vrstev, přičtou se až úplně na konci
        for layer in layers:
            if layer.POST:
                # Glow: záře z toho, co je zatím nakreslený, ale do canvasu se nepřidává
                halos.append(layer.halo(canvas, self.features))
            else:
                canvas = layer.apply(canvas, self.features)
        # tohle si pamatuju na příští snímek, oříznutý na 0..1 (přičítání to klidně přetáhne nad 1)
        self.canvas = np.clip(canvas, 0, 1).astype(np.float32)
        shown = self.canvas + sum(halos) if halos else self.canvas      # co se ukáže = paměť + všechny záře
        return (np.clip(shown, 0, 1) * 255).astype(np.uint8)     # 0..1 -> 0..255 celý čísla, takhle to chce wx.Bitmap
