"""Barvy a písma celýho UI na jednom místě, ať to nemusím hledat po souborech.

Vzhled je podle mojí appky Event Horizon a podle nástroje Flip: skoro černá,
jako zvýraznění jen bílá, tenký světlý okraje, a korálová jen pro chyby.
"""

import wx

# wx.Colour(červená, zelená, modrá), každá 0..255
BACKGROUND = wx.Colour(9, 9, 11)        # pozadí okna (#09090b)
SIDEBAR = wx.Colour(18, 18, 18)         # pravej panel s ovládáním (#121212)
VIEWPORT = wx.Colour(4, 5, 8)           # rámečky s osciloskopem a spektrem
BORDER = wx.Colour(36, 36, 40)          # tenký okraje (bílá na 8 % přes černou)
GRID = wx.Colour(28, 28, 32)            # mřížka v grafech

TEXT = wx.Colour(244, 244, 245)         # hlavní text
TEXT_MUTED = wx.Colour(161, 161, 170)   # nadpisy skupin, popisky
TEXT_DIM = wx.Colour(90, 90, 98)        # vysvětlující text pod slidery
ACCENT = wx.Colour(255, 255, 255)       # křivky, aktivní prvky
ERROR = wx.Colour(244, 63, 94)          # korálová, fakt jen pro chyby (#f43f5e)

SLIDER_TRACK = wx.Colour(30, 30, 32)    # prázdná část slideru
SLIDER_FILL = wx.Colour(58, 58, 62)     # vyplněná část slideru (= hodnota)
SLIDER_FILL_HOT = wx.Colour(74, 74, 80) # vyplněná část, když je nad ní myš
VALUE_BOX = wx.Colour(11, 11, 12)       # rámeček s číslem vpravo od slideru


def font(size: float = 11, bold: bool = False) -> wx.Font:
    """Písmo dané velikosti, na všech systémech stejně velký v pixelech.

    Proč to přepočítávat? macOS bere 1 bod = 1 pixel (72 DPI), Windows a Linux
    1 bod = 96/72 pixelu, takže stejný číslo by tam dalo o třetinu větší text
    a nevešel by se do sliderů a tlačítek (ty mají výšku napevno v pixelech).
    Mimo macOS se to proto zmenší.
    """
    if wx.Platform != "__WXMAC__":
        size = size * 72 / 96
    # SWISS = nějaký bezpatkový písmo, který konkrétní si vybere systém sám
    return wx.Font(wx.FontInfo(size).Family(wx.FONTFAMILY_SWISS).Bold(bold))


def draw_spaced(gc, text: str, x: float, y: float, spacing: float = 1.5) -> float:
    """Nakreslí text s mezerama mezi písmenama (wx to sám neumí).

    Kreslí se prostě znak po znaku a za každým se přidá `spacing` pixelů.
    Vrací šířku toho, co nakreslil.
    """
    start = x
    for char in text:
        gc.DrawText(char, x, y)
        x += gc.GetTextExtent(char)[0] + spacing   # GetTextExtent = (šířka, výška) textu v pixelech
    return x - start
