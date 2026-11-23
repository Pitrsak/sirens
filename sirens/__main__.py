"""Vstupní bod, tady to celý startuje: `python -m sirens` nebo `python main.py` (ten sem jen skočí).

pořadí je důležitý: nejdřív wx.App, pak zvukovej engine, až potom okno.
"""

import wx

from sirens.audio.engine import AudioEngine
from sirens.ui.main_frame import MainFrame


def main() -> None:
    app = wx.App()           # wx aplikace musí existovat dřív než jakýkoli okno
    engine = AudioEngine()   # pozor: pyo server musí běžet dřív, než bloky vytvoří první pyo objekty
    frame = MainFrame(engine)
    frame.Show()
    app.MainLoop()           # tady program visí a obsluhuje kliky, klávesy a časovače, dokud se okno nezavře


if __name__ == "__main__":
    main()
