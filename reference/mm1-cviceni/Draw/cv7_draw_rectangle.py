import cv2 as cv
import wx
import numpy as np


SIZE = {'X':640,'Y':480}

class CVPanel(wx.Panel):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.bmp = wx.Bitmap(SIZE['X'], SIZE['Y'])
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Draw()
    
    def Draw(self):    
        size = SIZE['Y'], SIZE['X'], 3
        converted = np.zeros(size, dtype=np.uint8)

        cv.circle(converted,(300,200),5,(0,255,0),2)
        cv.rectangle(converted, (200, 100), (400, 300), (255, 0, 0), 2)
    
        # Je také možnost napsat na obrázek text, fonty, které umí OpenCV, ale podporují jen základní
        # sadu zaků bez české diakritiky.
        text = 'Picture Draw'
        text_size = cv.getTextSize(text, cv.FONT_HERSHEY_SCRIPT_COMPLEX, 2.0, 1)
        cv.putText(converted, text, (320 - text_size[0][0] // 2, 50), cv.FONT_HERSHEY_PLAIN, 2.0, (255, 255, 255))

        self.bmp.CopyFromBuffer(converted)
        self.Refresh()
        
    def OnPaint(self, _):
        dc = wx.BufferedPaintDC(self)
        dc.DrawBitmap(self.bmp, 0, 0)

class MyFrame(wx.Frame):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.cv = CVPanel(self)
        self.SetSize(640, 480)

# Standartní spuštění aplikace.
app = wx.App()
frm = MyFrame(None, title='COREL DRAW -1.0')
frm.Show()
app.MainLoop()