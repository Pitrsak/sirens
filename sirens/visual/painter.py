"""Obraz složený z vrstev (viz layers.py), který reaguje na hudbu.

Každý snímek:
 1. Features spočítá, co je ve zvuku (basy, úder, spektrum, ...),
 2. začne se od minulého snímku (když je v seznamu Feedback), jinak od černé,
 3. vrstvy se provedou shora dolů; výsledek si pamatujeme pro příští snímek,
 4. navrch se přičte záře (Glow), ta se do paměti nedává,
 5. ořez na 0..1 a převod na 8 bitů (0..255) pro zobrazení.
"""

import numpy as np

from sirens.stack import Stack
from sirens.visual.features import Features
from sirens.visual.layers import HEIGHT, WIDTH, FeedbackLayer


class Painter(Stack):
    def __init__(self):
        super().__init__()
        self.canvas = np.zeros((HEIGHT, WIDTH, 3), dtype=np.float32)
        self.features = Features()

    @property
    def layers(self):
        return self.items

    def render(self, analyzer, dt: float) -> np.ndarray:
        """Spočítá další snímek a vrátí ho jako 8bitové RGB pole."""
        self.features.update(analyzer, dt)
        keep = any(isinstance(layer, FeedbackLayer) for layer in self.layers)
        canvas = self.canvas if keep else np.zeros_like(self.canvas)
        halos = []
        for layer in self.layers:
            if layer.POST:
                halos.append(layer.halo(canvas, self.features))
            else:
                canvas = layer.apply(canvas, self.features)
        self.canvas = np.clip(canvas, 0, 1).astype(np.float32)
        shown = self.canvas + sum(halos) if halos else self.canvas
        return (np.clip(shown, 0, 1) * 255).astype(np.uint8)
