import cv2 as cv
import wx

# Vlastní panel, který zajišťuje snímání webkamery pomocí OpenCV,
# převod do wx bitmapy a vykreslení na sebe. Musí být zařazen do
# dostatečně velikého wx Framu.
class CVPanel(wx.Panel):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.SetDoubleBuffered(True)
        
        # Vytvoříme bitmapu, do které se budou kopírovat výsledné snímky
        # ke zobrazení.
        self.bmp = wx.Bitmap(640, 480)

        # Vytvoříme časovač, který nám bude periodicky volat funkci.
        # V periodické funkci pak můžeme pomocí OpenCV přečíst další
        # snímek z webkamery.
        self.timer = wx.Timer(self)
        self.timer.Start(int(1000. / 30.))

        # Vytvoříme a nastavíme získávání snímků z webkamery pomocí OpenCV.
        # Velikost 640x480 je zvolena jen tak. Měla by ale být stejná jako velikost bitmapy výše.
        self.cap = cv.VideoCapture(1)
        self.cap.set(cv.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Nastavíme, aby nám wxPython posílal události o vypršení časovače (na získání dalšího snímku)
        # a žádosti o překreslení, kde budeme moci náš aktuální snímek vykreslit.
        self.Bind(wx.EVT_TIMER, self.OnTimer)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
    
    def OnTimer(self, _):
        # Z připraveného sběru snímků získáme další snímek a informaci, jestli byla
        # operace úspěšná.
        ret, frame = self.cap.read()
        if ret:
            # Získaný snímek je před kopií do bitmapy potřeba převést na správný barevný formát.
            # OpenCV nám z webkamery dá barevný formát BGR (blue-green-red), ale bitmapa vyžaduje
            # formát RGB (red-green-blue). Bez konverze by sice kód fungoval také, ale viděli bychom
            # špatné barvy.
            converted = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
            self.bmp.CopyFromBuffer(converted)
            # Nakonec zažádáme náš panel o překreslení.
            self.Refresh()
        
    def OnPaint(self, _):
        # Pro vykreslení bitmapy potřebujeme nástroj na kreslení. Ve světě wx se jedná o Device Context.
        # Náš panel nám pomůže (v události Paint) tento kontext vytvořit.
        dc = wx.BufferedPaintDC(self)
        # Pak už jen stačí na nějakém místě předat bitmapu k vykreslení.
        dc.DrawBitmap(self.bmp, 0, 0)

class MyFrame(wx.Frame):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        # Jednoduché okno, které pouze obsahuje třídu s obrazem z OpenCV
        # a je akorát veliké.
        self.cv = CVPanel(self)
        self.SetSize(640, 480)

# Standartní spuštění aplikace.
app = wx.App()
frm = MyFrame(None, title='OpenCV')
frm.Show()
app.MainLoop()