import cv2 as cv
import wx
import numpy as np

FPS = 10
RESOLUTION = (640, 480)

class CVPanel(wx.Panel):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.SetDoubleBuffered(True)
        
        self.bmp = wx.Bitmap(RESOLUTION[0], RESOLUTION[1])

        self.timer = wx.Timer(self)
        self.timer.Start(int(1000. / FPS))

        self.cap1 = cv.VideoCapture(0)
        self.cap1.set(cv.CAP_PROP_FRAME_WIDTH, RESOLUTION[0])
        self.cap1.set(cv.CAP_PROP_FRAME_HEIGHT, RESOLUTION[1])
        self.cap1.set(cv.CAP_PROP_FPS, FPS)

        self.cap2 = cv.VideoCapture("https://www.publicdomainpictures.net/pictures/170000/velka/landschaft-1463581037RbE.jpg")
        _, self.background = self.cap2.read()
        self.background = cv.cvtColor(self.background, cv.COLOR_BGR2RGB)
        self.background = cv.resize(self.background, RESOLUTION)
        print(self.background.shape)
        
        self.Bind(wx.EVT_TIMER, self.OnTimer)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
    
    def OnTimer(self, _):
        ret, frame = self.cap1.read()
        if ret:
            # Snímek musí být převeden na černobílý pro funkci threshold
            converted = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
            gray = cv.cvtColor(converted, cv.COLOR_RGB2GRAY)

            # Threshold the grayscale image to create a blending mask.
            # Pixel values above 220 will go towards zero, pixels below
            # will keep their value (with the TOZERO thresholding function).
            _, weights = cv.threshold(gray, 220, 255, cv.THRESH_TOZERO)
            weights = weights.astype(np.float32) / 255

            # Finally blend the two pictures using the computed weights.
            composite = cv.blendLinear(self.background, converted, weights, 1. - weights)

            self.bmp.CopyFromBuffer(composite)
            self.Refresh()
        
    def OnPaint(self, _):
        dc = wx.BufferedPaintDC(self)
        dc.DrawBitmap(self.bmp, 0, 0)

class MyFrame(wx.Frame):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.cv = CVPanel(self)
        self.SetClientSize(RESOLUTION[0], RESOLUTION[1])

app = wx.App()
frm = MyFrame(None, title='OpenCV', size=(640, 480))
frm.Show()
app.MainLoop()