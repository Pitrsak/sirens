"""Vstupní bod aplikace: `python -m sirens` nebo `python main.py`."""

import wx

from sirens.audio.engine import AudioEngine
from sirens.ui.main_frame import MainFrame


def main() -> None:
    app = wx.App()
    engine = AudioEngine()   # pyo server musí běžet dřív, než sound.py vytvoří první objekty
    frame = MainFrame(engine)
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
