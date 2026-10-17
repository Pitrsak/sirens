"""Vstupní bod aplikace: `python -m fathom` nebo `python main.py`."""

import wx

from fathom.audio.engine import AudioEngine
from fathom.ui.keyboard import ComputerKeyboard
from fathom.ui.main_frame import MainFrame


def main() -> None:
    app = wx.App()
    engine = AudioEngine()
    frame = MainFrame(engine)
    # Filtr událostí pro hraní na klávesnici počítače platí pro celou aplikaci.
    keyboard = ComputerKeyboard(engine.synth, on_octave_change=frame.on_octave_change)
    wx.EvtHandler.AddFilter(keyboard)
    frame.Show()
    app.MainLoop()
    wx.EvtHandler.RemoveFilter(keyboard)


if __name__ == "__main__":
    main()
