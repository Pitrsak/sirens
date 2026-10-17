import wx
import cv2
import pyo
from threading import Thread
from time import sleep

FPS = 10
RESOLUTION = (640, 480)

class CVStream(wx.Panel):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.SetDoubleBuffered(True)
        self.img = None
        self.bitmap = wx.Bitmap(RESOLUTION[0], RESOLUTION[1])
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.SetSize(RESOLUTION[0], RESOLUTION[1])
    
    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        dc.DrawBitmap(self.bitmap, 0, 0)
    
    def update(self, img):
        self.bitmap.CopyFromBuffer(img)
        self.Refresh()
    
    def UpdateImage(self, img):
        wx.CallAfter(self.update, img)


class Application(wx.App):
    def OnInit(self):
        self.mainWindow = wx.Frame(None)
        self.mainWindow.Show()
        self.imgPanel = CVStream(self.mainWindow, pos=(0, 200))
        self.scope = pyo.PyoGuiScope(self.mainWindow, size=(RESOLUTION[0], 200))
        self.mainWindow.SetClientSize(RESOLUTION[0], RESOLUTION[1] + 200)
        self.SetTopWindow(self.mainWindow)
        return super().OnInit()

    def SetAnalyzer(self, scope):
        self.scope.setAnalyzer(scope)
        scope.setWidth(self.scope.Size[0])
        scope.setHeight(self.scope.Size[1])

app = Application()

def cv():
    global app
    stream = cv2.VideoCapture(0)
    stream.set(cv2.CAP_PROP_FRAME_WIDTH, RESOLUTION[0])
    stream.set(cv2.CAP_PROP_FRAME_HEIGHT, RESOLUTION[1])
    stream.set(cv2.CAP_PROP_FPS, FPS)

    while True and app.IsMainLoopRunning():
        read, img = stream.read()
        if not read:
            break
        converted = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        flipped = cv2.flip(converted, 1)
        app.imgPanel.UpdateImage(flipped)
        sleep(1. / FPS)
    stream.release()

def audio():
    server = pyo.Server(duplex=1)
    #server.setOutputDevice(6)
    #server.setInputDevice(6)
    server.boot()
    i = pyo.Input()
    n = pyo.generators.Noise(.1)
    s = pyo.generators.Sine(440)
    mix = pyo.Mix([i]).out()
    scope = pyo.Scope(mix, function=lambda a: ...)
    app.SetAnalyzer(scope)
    server.start()
    while app.IsMainLoopRunning():
        sleep(0.1)
    #server.gui(locals())
    server.stop()
    server.shutdown()

pyo.pa_list_devices()

thr = Thread(target=cv)
thr.start()
audiothr = Thread(target=audio)
audiothr.start()


app.MainLoop()
thr.join()
audiothr.join()