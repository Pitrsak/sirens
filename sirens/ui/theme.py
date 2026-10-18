"""Barvy a písma celého UI na jednom místě.

Vzhled vychází z mé aplikace Event Horizon a z nástroje Flip: téměř černá,
jen bílá jako zvýraznění, tenké světlé okraje, korálová jen pro chyby.
"""

import wx

BACKGROUND = wx.Colour(9, 9, 11)        # pozadí okna (#09090b)
SIDEBAR = wx.Colour(18, 18, 18)         # pravý panel s ovládáním (#121212)
VIEWPORT = wx.Colour(4, 5, 8)           # rámečky s osciloskopem a spektrem
BORDER = wx.Colour(36, 36, 40)          # tenké okraje (bílá na 8 % přes černou)
GRID = wx.Colour(28, 28, 32)            # mřížka v grafech

TEXT = wx.Colour(244, 244, 245)         # hlavní text
TEXT_MUTED = wx.Colour(161, 161, 170)   # nadpisy skupin, popisky
TEXT_DIM = wx.Colour(90, 90, 98)        # vysvětlující text pod slidery
ACCENT = wx.Colour(255, 255, 255)       # křivky, aktivní prvky
ERROR = wx.Colour(244, 63, 94)          # korálová, jen pro chyby (#f43f5e)

SLIDER_TRACK = wx.Colour(30, 30, 32)    # prázdná část slideru
SLIDER_FILL = wx.Colour(58, 58, 62)     # vyplněná část slideru (= hodnota)
SLIDER_FILL_HOT = wx.Colour(74, 74, 80) # vyplněná část, když je nad ní myš
VALUE_BOX = wx.Colour(11, 11, 12)       # rámeček s číslem vpravo od slideru


def font(size: int = 11, bold: bool = False) -> wx.Font:
    weight = wx.FONTWEIGHT_BOLD if bold else wx.FONTWEIGHT_NORMAL
    return wx.Font(size, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, weight)


def draw_spaced(gc, text: str, x: float, y: float, spacing: float = 1.5) -> float:
    """Nakreslí text s rozestupem mezi písmeny (wx to samo neumí).

    Kreslí znak po znaku a za každým přidá `spacing` pixelů.
    Vrací šířku nakresleného textu.
    """
    start = x
    for char in text:
        gc.DrawText(char, x, y)
        x += gc.GetTextExtent(char)[0] + spacing
    return x - start

