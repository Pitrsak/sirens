from sys import flags
from typing import List
from socket import AF_INET, SOCK_DGRAM, socket
from struct import pack
import wx


class ArtNetSender():
    '''
        Example:

        >>> sender = ArtNetSender(ip='1.2.3.4')
        >>> data = [255, 255, 128, 128, 0, 0]
        >>> sender.SendValues(data)
    '''

    def __init__(self, port=6454, ip='192.168.22.21'):
        self.Port = port
        self.Target = ip
        self.Socket = socket(AF_INET, SOCK_DGRAM)
        self.Seq = 0
        self.Physical = 0
        self.Universe = 0
        self.Net = 0
        self.Pad = True
        # ID, (OpCode(Lo,Hi), ProtVer(Hi,Lo)), Sequence, Physical, SubUni, Net, Length(Hi,Lo)
        self.dgram_fmt = '< 8s 4s 6B'
        self.dgram_header = [
            b'Art-Net\0',
            b'\x00\x50\x00\x0E'
        ]

    def SendValues(self, value_array: List[int]):
        if len(value_array) > 512:
            value_array = value_array[:512]
        if self.Pad:
            pad = 512 - len(value_array)
            value_array += [0] * pad
        length = len(value_array)
        fmt = self.dgram_fmt + str(length) + 's'
        data = pack(
            fmt,
            self.dgram_header[0],
            self.dgram_header[1],
            self.Seq,
            self.Physical,
            self.Universe,
            self.Net,
            (length >> 8),
            (length & 0xFF),
            bytes(value_array)
        )
        # print(data)
        self.Socket.sendto(data, (self.Target, self.Port))
        self.Seq += 1
        if self.Seq > 255:
            self.Seq = 0


class MyFrame(wx.Frame):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.Sender = ArtNetSender()
        self.StartAddress = 0
        self.Channels = 40
        self.Data = [0] * (self.StartAddress + self.Channels)

        # Add a sizer for easier layout
        self.MySizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.MySizer)

        self.SliderText = wx.StaticText(self, label='ArtNet Kanály', )
        self.MySizer.Add(self.SliderText, flag=(wx.CENTER | wx.TOP), border=10)

        # Add a scroll panel to be able to get to the higher numbered sliders
        self.SliderPanel = wx.ScrolledWindow(self)
        self.SliderPanel.SetScrollbars(30, 0, self.Channels, 0)
        self.MySizer.Add(self.SliderPanel)

        # Channel sliders
        self.Sliders = []
        self.SliderTexts = []
        for i in range(self.Channels):
            slider = wx.Slider(self.SliderPanel, minValue=0, maxValue=255, pos=(
                i * 30, 20), style=(wx.SL_VERTICAL | wx.SL_INVERSE), id=(self.StartAddress + i))
            slider.Bind(wx.EVT_SLIDER, self.OnSliderUpdated)
            self.Sliders += [slider]
            text = wx.StaticText(self.SliderPanel, label=str(self.StartAddress + i + 1), pos=(i * 30 + 15, 120))
            self.SliderTexts += [text]

        # Target IP input box
        self.TargetText = wx.StaticText(self, label='Poslat na IP: ', pos=(10, 155))
        self.Target = wx.TextCtrl(self, value=self.Sender.Target, pos=(100, 150), size=(130, 30))
        self.Target.Bind(wx.EVT_TEXT, self.OnTextUpdated)
        self.MySizer.Add(self.TargetText, flag=(wx.CENTER))
        self.MySizer.Add(self.Target, flag=(wx.CENTER))

        # Send at 44 FPS, which is the standard maximum frequency for DMX
        self.timer = wx.Timer(self)
        self.timer.Start(int(1000. / 44.))
        self.Bind(wx.EVT_TIMER, self.OnTimer)

    def OnSliderUpdated(self, event: wx.Event):
        print(f'{event.Id}: {event.EventObject.Value}')
        self.Data[event.Id] = event.EventObject.Value
    
    def OnTextUpdated(self, event: wx.Event):
        self.Sender.Target = event.EventObject.Value

    def OnTimer(self, _):
        self.Sender.SendValues(self.Data)


app = wx.App()
frame = MyFrame(None, title="ArtNet Sender")
frame.Show()
app.MainLoop()
