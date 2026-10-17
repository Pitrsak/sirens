import cv2 as cv
import wx
import numpy as np
from urllib.request import urlopen

IMAGE_URL='https://openclipart.org/image/400px/245851'
SIZE = {'X':600,'Y':600}

class CVPanel(wx.Panel):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.bmp = wx.Bitmap(SIZE['X'], SIZE['Y'])

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
        
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Draw()
    
    def Draw(self):
        
        size = SIZE['X'], SIZE['Y'], 3
        converted = np.zeros(size, dtype=np.uint8)

        cv.circle(converted,(300,200),5,(0,255,0),2)
        cv.rectangle(converted, (200, 100), (400, 300), (255, 0, 0), 2)
        cv.arrowedLine(converted, (150, 50),  (200, 100), (255, 255, 0  ), 2)
        cv.arrowedLine(converted, (450, 50),  (400, 100), (0  , 255, 0  ), 2)
        cv.arrowedLine(converted, (150, 350), (200, 300), (0  , 0  , 255), 2)
        cv.arrowedLine(converted, (450, 350), (400, 300), (0  , 255, 255), 2)

        # Je také možnost napsat na obrázek text, fonty, které umí OpenCV, ale podporují jen základní
        # sadu zaků bez české diakritiky.
        text = 'Picture Draw'
        text_size = cv.getTextSize(text, cv.FONT_HERSHEY_SCRIPT_COMPLEX, 2.0, 1)
        cv.putText(converted, text, (320 - text_size[0][0] // 2, 50), cv.FONT_HERSHEY_PLAIN, 2.0, (255, 255, 255))

        # Na obrázek můžeme snadno zapsat stažený soubor, který máme v proměnné self.img.
        # Musíme vybrat pouze první tři barvy (část 0:3), jelikož je stažebý soubor ve formátu RGBA a náš obrázek pouze RGB.
        converted[100:300,200:400] = self.img[:,:,0:3]

        self.bmp.CopyFromBuffer(converted)
        self.Refresh()
        
    def OnPaint(self, _):
        dc = wx.BufferedPaintDC(self)
        dc.DrawBitmap(self.bmp, 0, 0)

class MyFrame(wx.Frame):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

         # Pridani menu
        filemenu= wx.Menu()

        # wx.ID_EXIT je standardni ID od wxWidgets, problém může být u MACOS.         
        item = filemenu.Append(wx.ID_EXIT,"E&xit"," Terminate the program")
        self.Bind(wx.EVT_MENU, self.OnExit, item)
        
        # vytvoreni menubaru
        menuBar = wx.MenuBar()
        menuBar.Append(filemenu,"&File") # Adding the "filemenu" to the MenuBar
        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.

        self.cv = CVPanel(self)
        self.SetSize(640, 480)

    def OnExit(self,_):
        print("Closing session...")

        self.Close(True)

# Standartní spuštění aplikace.
app = wx.App()
frm = MyFrame(None, title='COREL DRAW -1.0')
frm.Show()
app.MainLoop()