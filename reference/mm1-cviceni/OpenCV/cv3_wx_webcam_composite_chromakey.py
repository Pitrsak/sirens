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

        self.ColorKey = [20, 250, 20]
        self.Tolerance = 0.1
    
    def OnTimer(self, _):
        ret, frame = self.cap1.read()
        if ret:
            # Snímek musí být převeden na černobílý pro funkci threshold
            converted = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
            
            # Vytvoříme masku na základě středové barvy a jisté tolerance.
            # Funkce cv.inRange vrací v podstatě binární pole (0 nebo 255), takže zde
            # chybí plynulejší přechod.
            # Pro účely blendLinear je potřeba výslednou masku převést na 32bit floaty v rozsahu 0-1.
            upper_tolerance = 1.0 + self.Tolerance
            lower_tolerance = 1.0 - self.Tolerance
            lower_color = np.array(self.ColorKey) * lower_tolerance
            upper_color = np.array(self.ColorKey) * upper_tolerance
            mask = cv.inRange(converted, lower_color, upper_color) / 255.
            mask = mask.astype(np.float32)
            

            # Finally blend the two pictures using the computed weights.
            composite = cv.blendLinear(self.background, converted, mask, 1. - mask)

            self.bmp.CopyFromBuffer(composite)
            self.Refresh()
        
    def OnPaint(self, _):
        dc = wx.BufferedPaintDC(self)
        dc.DrawBitmap(self.bmp, 0, 0)

class MyFrame(wx.Frame):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.cv = CVPanel(self, pos=(0, 32), size=RESOLUTION)
        # Zde přidáváme dva další ovládací prvky pro výběr klíčované barvy (bohužel wxPython nemá nativní nástroj kapátka,
        # takže výběr barvy je manuální). Druhý prvek je na rozšíření klíčovaného rozsahu barev.
        self.picker = wx.ColourPickerCtrl(self, pos=(0, 0))
        self.picker.Bind(wx.EVT_COLOURPICKER_CHANGED, self.OnColorChanged, self.picker)
        self.tolerance = wx.Slider(self, pos=(100, 0), minValue=0, maxValue=100)
        self.tolerance.Bind(wx.EVT_SLIDER, self.OnSliderChanged, self.tolerance)
        self.SetClientSize(RESOLUTION[0], RESOLUTION[1] + 32)

    def OnColorChanged(self, event: wx.ColourPickerEvent):
        rgb = [event.Colour[0], event.Colour[1], event.Colour[2]]
        print(rgb)
        self.cv.ColorKey = rgb
    
    def OnSliderChanged(self, event):
        self.cv.Tolerance = self.tolerance.GetValue() / 100.

app = wx.App()
frm = MyFrame(None, title='OpenCV')
frm.Show()
app.MainLoop()