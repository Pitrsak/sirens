from typing import Callable, List
from socket import AF_INET, SOCK_DGRAM, socket
from struct import unpack, calcsize
import wx


class ArtNetListener():
    def __init__(self, port=6454):
        self.Port = port
        self.Socket = socket(AF_INET, SOCK_DGRAM)
        self.Socket.bind(('0.0.0.0', self.Port))
        # ID, (OpCode(Lo,Hi), ProtVer(Hi,Lo)), Sequence, Physical, SubUni, Net, Length(Hi,Lo)
        self.dgram_fmt = '< 6B'
        self.hdr_fmt = '< 8s 4s'
        self.dgram_len = calcsize(self.dgram_fmt)
        self.hdr_len = calcsize(self.hdr_fmt)
        self.data_start = self.hdr_len + self.dgram_len
        self.hdr_contents = [
            b'Art-Net\0',
            b'\x00\x50\x00\x0E'
        ]
        #self.Socket.settimeout(1.0)
        self.Socket.setblocking(False)

    def ReceiveData(self) -> tuple[bool, int, list[int]]:
        '''
            Returns `True, universe, values` if data was received and
            successfully parsed. Returns `False, 0, []` if not.
        '''
        try:
            # Buffer has to be larger than largest possible ArtDMX packet
            data, addrinfo = self.Socket.recvfrom(530)
        except:
            return False, 0, []
        # Unpack received data into relevant fields - header to check packet validity, universe, and length of following data.
        # Other fields are discarded.
        if len(data) < self.hdr_len:
            return False, 0, []
        header = unpack(self.hdr_fmt, data[0:self.hdr_len])
        if header[0] != self.hdr_contents[0] or header[1] != self.hdr_contents[1]:
            return False, 0, []
        _, _, universe, _, length_hi, length_lo = unpack(self.dgram_fmt, data[self.hdr_len:self.data_start])
        # Construct length from the two separate bytes by shifting the high portion 8 bits to the left.
        length = length_hi << 8 + length_lo
        # Unpack the rest - the actual DMX values - and return the result.
        values, = unpack(str(length) + 's', data[self.data_start:])
        return True, universe, values


class MyFrame(wx.Frame):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.Listener = ArtNetListener()
        self.Data = [0] * 10

        # Channel sliders
        self.SliderText = wx.StaticText(self, label='ArtNet Kanály 1-10', pos=(100, 10))
        self.Sliders = []
        self.SliderTexts = []
        for i in range(10):
            slider = wx.Slider(self, minValue=0, maxValue=255, pos=(
                i * 30, 20), style=(wx.SL_VERTICAL | wx.SL_INVERSE), id=i)
            slider.Disable()
            self.Sliders += [slider]
            text = wx.StaticText(self, label=str(i + 1), pos=(i * 30 + 15, 120))
            self.SliderTexts += [text]
        
        self.Timer = wx.Timer(self)
        self.Timer.StartOnce(10)
        self.Bind(wx.EVT_TIMER, self.OnTimer)
    
    def OnTimer(self, _):
        # Get data from socket, parsed into DMX values
        ret, universe, data = self.Listener.ReceiveData()

        if not ret:
            # Repeat timer if no data is ready
            self.Timer.StartOnce(10)
            return
        # Print received data and move sliders if we got valid values
        print(f'Data for universe: {universe}')
        for i in range(10):
            self.Sliders[i].Value = data[i]
        # Restart timer
        self.Timer.StartOnce(10)


app = wx.App()
frame = MyFrame(None, title="ArtNet Sender")
frame.Show()
app.MainLoop()
