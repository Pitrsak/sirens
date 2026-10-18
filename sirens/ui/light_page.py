"""Záložka Light: RGB světlo řízené zvukem, posílané přes Art-Net.

Světlo se počítá pořád (i když je vidět jiná záložka), aby svítilo s hudbou.
Náhled ukazuje barvu i bez skutečného světla.
"""

import ipaddress

import wx

from sirens.light.artnet import ArtNetSender
from sirens.light.rig import LightRig
from sirens.ui import theme
from sirens.ui.sidebar import Sidebar, divider
from sirens.ui.views import LightView
from sirens.ui.widgets import StatusPill


class LightPage(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        self.SetBackgroundColour(theme.BACKGROUND)
        self.rig = LightRig()
        self.sender = ArtNetSender()
        self.ip = "127.0.0.1"
        self.sending = False

        self.view = LightView(self)
        self.status = StatusPill(self)
        column = wx.BoxSizer(wx.VERTICAL)
        column.Add(self.view, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 20)
        column.Add(self.status, 0, wx.EXPAND | wx.ALL, 20)

        self.sidebar = Sidebar(self)
        self.sidebar.add_group("Art-Net")
        self.sidebar.add_text("IP", self.ip, self._set_ip,
                              help="Address of the Art-Net node or lighting console.")
        self.send_button = self.sidebar.add_button("Start sending", self._toggle_sending)
        self.sidebar.add_group("Light")
        self.sidebar.add_note("Bass lights red, middles green, highs blue.")
        self.sidebar.add_params(self.rig)
        self.sidebar.finish()

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(column, 1, wx.EXPAND)
        row.Add(divider(self, vertical=True), 0, wx.EXPAND)
        row.Add(self.sidebar, 0, wx.EXPAND)
        self.SetSizer(row)

    def _set_ip(self, text: str):
        self.ip = text

    def _toggle_sending(self):
        self.sending = not self.sending
        self.send_button.set_label("Stop sending" if self.sending else "Start sending")
        self.send_button.GetParent().Layout()

    def _send(self) -> str:
        """Pošle aktuální hodnoty světla. Vrací text pro stavový štítek."""
        if not self.sending:
            return "Not sending. Start sending to drive a real light."
        try:
            ipaddress.IPv4Address(self.ip)   # jen kontrola, že je to platná adresa
        except ValueError:
            return f"'{self.ip}' is not a valid IP address."
        try:
            self.sender.send(self.ip, self.rig.universe(), self.rig.channels())
        except OSError as error:
            return f"Cannot send: {error}"
        return f"Sending to {self.ip}, universe {self.rig.universe()}."

    def tick(self, analyzer):
        """Každý snímek: barva podle zvuku, odeslání, a když je záložka vidět, náhled."""
        self.rig.update(analyzer.bands())
        text = self._send()
        if self.IsShown():
            self.view.show(self.rig.values(), self.rig.address())
            self.status.show(text, error=self.sending and not text.startswith("Sending"))

    def close(self):
        self.sender.close()
