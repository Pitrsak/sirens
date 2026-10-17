'''Ukázka kreslení do bitové mapy pomocí knihovny openCV 
a její následné vykreslení v kontextu knihovny wxPython.'''

import cv2 as cv
import wx
import numpy as np
import time as tm


SIZE = {'X':480,'Y':700}
EPS = 2

'''Třída CVPanel reprezentující control widget s nástroji pro vykreslení 2D objektů.'''
class CVPanel(wx.Panel):
    def __init__(self, *args, **kw):
        '''Volání konstruktoru rodičovsjé třídy.'''
        super().__init__(*args, **kw)

        '''Vytvoření bitové mapy v paměti. Kontrolováno nástroji wxPython.'''
        self.bmp = wx.Bitmap(SIZE['X'], SIZE['Y'])
        
        '''Inicializace objektu Timer pro časování animační smyčky.'''
        self.timer = wx.Timer(self)
        '''Odpovídá snímkové frekvenci 30FPS. 1/30s ~ 1000/30ms'''
        self.timer.Start(int(1000. / 30.))
        
        '''Inicializace stavových proměnných.'''
        self.animated = False
        self.dy = 0
        
        '''Tíhové zrychlení. Pro zjednodušení se zde používá jako délková jednotka pixel namísto metru. 
        Pro zrychlení animace se proto použila desetinásobná hodnota , než je obvyklé pro reálný objekt.'''
        self.g = 100

        self.objectposition = 0
        self.objectvelocity = 0
        self.objectdirection = 1
        self.ct = tm.time_ns()/1E09

        self.Bind(wx.EVT_TIMER, self.OnTimer)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_LEFT_DOWN,self.onClicked,self)

    '''Pokud uživatel klikne na plochu widgetu, povolí se spuštění animace.'''
    def onClicked(self,_):
        self.ct = tm.time_ns()/1E09
        self.animated = not self.animated
        
    '''Výpočet animace.'''
    def move(self):
        '''Zjitění času, který uběhl od poslední aktualizace .'''
        ct = tm.time_ns()/1E09
        dt = ct - self.ct
        dv = self.g*dt

        '''Detekce kolize čtverce s podložkou, která s nachází v hloubce 
        rovné polovině výšky okna, podpočáteční polohou objektu.'''
        if round(self.objectposition) > (SIZE['Y']/2)-1:
            self.colliding = True
            '''Pokud je detekována kolize, dojde ke změně směru pohybu 
            do protisměru (odraz nahoru) a úbytku 20% energie'''
            if self.objectdirection > 0:
                self.objectvelocity *= 0.8
            self.objectdirection = -1
        else:
            self.colliding = False
            
        '''Detekce vrcholu trajektorie objektu. Pokud let9 nahoru a jeho rychlost 
        klesla pod hodnotu EPS, dojde ke změně směru pohybu objektu do opačného směru dolů.'''
        if self.objectdirection < 0 and abs(self.objectvelocity)<EPS:
            self.objectdirection = 1
        
        '''Výpočet dráhy za čas dt, aktuální rychlosti a polohy.'''
        ds = self.objectdirection*self.objectvelocity*dt+0.5*dv*dt
        self.objectvelocity += dv*self.objectdirection
        self.objectposition += ds

        '''Pokud je detekován stav kolize a aktuální 
        změna polohy klesne pod danou mez, je animace zastavena.'''
        if abs(ds)<0.05 and self.colliding:
            self.animated = False
        
        '''Aktualizace času a polohy.'''
        self.ct = ct
        self.dy = int(self.objectposition)
        print(f"dv: {dv}, DS: {ds} DY: {self.dy}, velocity {self.objectvelocity}, gt: {0.5*dv*dt}, colliding: {self.colliding}, position: {self.objectposition}") 
    
    '''časovač, který je volán v pravidelných intervalech, a který aktualizuje data.'''
    def OnTimer(self,_):
        
        '''Vytvoření bitové obdélníkové matice pro přenos snímku.'''
        size = SIZE['Y'], SIZE['X'], 3
        converted = np.zeros(size, dtype=np.uint8)

        '''Je-li povolena animace, spustí se výpočet jednoho snímku.'''
        if self.animated:
            self.move()

        '''Vykreslení objektů s aktualizovanou polohou do paměti.'''
        cv.circle(converted,(300,200),5,(0,255,0),-1)
        cv.rectangle(converted, (200, 100+self.dy), (400, 300+self.dy), (255, 0, 0), -1)
        
        '''Vykreslení textu do paměti.'''
        text = 'Picture Animation'
        text_size = cv.getTextSize(text, cv.FONT_HERSHEY_SCRIPT_COMPLEX, 2.0, 1)
        cv.putText(converted, text, (320 - text_size[0][0] // 2, 50), cv.FONT_HERSHEY_PLAIN, 2.0, (255, 255, 255))

        '''Zkopírování paměti s vykresleným obsahem do bitové mapy ve wx.'''
        self.bmp.CopyFromBuffer(converted)

        '''Vyvolání rutin pro vykreslení bitové mapy do okna.'''
        self.Refresh()
        
    '''Obsluha požadavku na vykreslení.'''
    def OnPaint(self, _):
        '''Získání kontextu panelu do kterého chceme kreslit.'''
        dc = wx.BufferedPaintDC(self)
        '''Vykreslení bitové mapy.'''
        dc.DrawBitmap(self.bmp, 0, 0)

'''Třída reprezentující okno aplikace.'''
class MyFrame(wx.Frame):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        '''Vytvoření CVPanelu a jeho vložení do okna.'''
        self.cv = CVPanel(self)
        self.SetSize(640, 750)

'''Standartní spuštění aplikace.'''
app = wx.App()
frm = MyFrame(None, title='COREL DRAW -1.0')
frm.Show()
app.MainLoop()