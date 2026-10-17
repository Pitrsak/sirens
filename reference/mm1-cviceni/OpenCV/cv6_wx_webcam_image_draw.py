import cv2 as cv
import wx
import numpy as np
from urllib.request import urlopen

IMAGE_URL='https://openclipart.org/image/400px/245851'

FPS = 10
RESOLUTION = (640, 480)

class CVPanel(wx.Panel):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.SetDoubleBuffered(True)
        self.bmp = wx.Bitmap(RESOLUTION[0], RESOLUTION[1])
        self.timer = wx.Timer(self)
        self.timer.Start(int(1000. / FPS))

        self.cap = cv.VideoCapture(0)
        self.cap.set(cv.CAP_PROP_FRAME_WIDTH, RESOLUTION[0])
        self.cap.set(cv.CAP_PROP_FRAME_HEIGHT, RESOLUTION[1])
        self.cap.set(cv.CAP_PROP_FPS, FPS)

        # Zde je dopředu načtený obrázek z nastaveného webu.
        # cv.imdecode zpracuje stažená data do pole barev, se kterým
        # lze dál pracovat. Načítá ve formátu BGR (resp. BGRA), takže
        # bude pro účely zobrazení potřeba obrázek převést na formát RGB(A).
        with urlopen(IMAGE_URL) as imgfile:
            bytedata = bytearray(imgfile.read())
            data = np.asarray(bytedata, dtype=np.uint8)
            self.img = cv.imdecode(data, cv.IMREAD_UNCHANGED)
            self.img = cv.resize(self.img, (200, 200))
            self.img = cv.cvtColor(self.img, cv.COLOR_BGRA2RGBA)
        
        self.Bind(wx.EVT_TIMER, self.OnTimer)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
    
    def OnTimer(self, _):
        ret, frame = self.cap.read()
        if ret:
            converted = cv.cvtColor(frame, cv.COLOR_BGR2RGB)

            # Základní možnosti kreslení pomocí OpenCV. Použitý je zde obdélník (resp. čtverec)
            # a šipky. Ecistují i další možnosti, např. kruh, čáry, atd.
            cv.rectangle(converted, (200, 100), (400, 300), (255, 0, 0), 2)
            cv.arrowedLine(converted, (150, 50),  (200, 100), (255, 255, 0  ), 2)
            cv.arrowedLine(converted, (450, 50),  (400, 100), (0  , 255, 0  ), 2)
            cv.arrowedLine(converted, (150, 350), (200, 300), (0  , 0  , 255), 2)
            cv.arrowedLine(converted, (450, 350), (400, 300), (0  , 255, 255), 2)

            # Je také možnost napsat na obrázek text, fonty, které umí OpenCV, ale podporují jen základní
            # sadu zaků bez české diakritiky.
            text = 'Blendovani obrazku'
            text_size = cv.getTextSize(text, cv.FONT_HERSHEY_PLAIN, 1.0, 1)
            cv.putText(converted, text, (320 - text_size[0][0] // 2, 50), cv.FONT_HERSHEY_PLAIN, 1.0, (255, 255, 255))

            # Jelikož obrázek načtený pomocí OpenCV (ať už z videa, nebo ze statického obrázku) je v
            # podstatě numpy pole, jde s ním taky tak nakládat. V následujícím kódu je vybrán výřez obrazu
            # 200x200 px, který je pak manuálně pomocí numpy blendovaný s dříve načteným (a převedeným/zmenšeným)
            # obrázkem pomocí jednoduché kompozice. Hodí se zde znát syntax přístupu k numpy polím.
            # Abychom mohli data obrázků násobit, musíme škálovat hodnoty z původního rozsahu 0-255 na
            # rozsah 0-1 - toho lze docílit jednoduchým dělením.
            alpha = np.reshape(self.img[:,:,3], (200, 200, 1)) / 255.
            original = converted[100:300,200:400]
            overlay = self.img[:,:,0:3]
            converted[100:300,200:400] = overlay * alpha + original * (1.0 - alpha)

            self.bmp.CopyFromBuffer(converted)
            self.Refresh()
        
    def OnPaint(self, _):
        dc = wx.BufferedPaintDC(self)
        dc.DrawBitmap(self.bmp, 0, 0)

class MyFrame(wx.Frame):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.cv = CVPanel(self)
        self.SetClientSize(RESOLUTION)

# Standartní spuštění aplikace.
app = wx.App()
frm = MyFrame(None, title='OpenCV')
frm.Show()
app.MainLoop()