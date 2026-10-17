"""Barvy a písma celého UI na jednom místě, aby šel vzhled snadno změnit."""

import wx

BACKGROUND = wx.Colour(14, 15, 19)
PANEL = wx.Colour(24, 26, 32)
PANEL_BORDER = wx.Colour(40, 43, 52)
TEXT = wx.Colour(225, 225, 230)
TEXT_DIM = wx.Colour(120, 124, 135)
ACCENT = wx.Colour(255, 72, 48)      # hlavní barva (hodnota knobu, stisknuté klávesy)
KNOB_TRACK = wx.Colour(50, 53, 62)
KNOB_FACE = wx.Colour(34, 36, 44)


def font(size: int = 9, bold: bool = False) -> wx.Font:
    weight = wx.FONTWEIGHT_BOLD if bold else wx.FONTWEIGHT_NORMAL
    return wx.Font(size, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, weight)
