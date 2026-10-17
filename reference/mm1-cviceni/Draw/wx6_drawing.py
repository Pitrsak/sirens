'''APlikace, která vytvoří v okně dvě sekce pomocí nástroje BoxSizer. 
Spodní vyplňují tlačítka a do horní se kreslí.'''

#import wx
from pyo import *


class MainWindow(wx.Frame):

    setup = [220,440,550,600,700,850,900,1000]

    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, title=title, size=(1000,600))

        '''Spojení sizeru s oknem.'''
        sz = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sz)

        '''Vytvoření panelu pro kreslení.'''
        self.pnl_display = wx.Panel(self,size=(1000,200),name="display")
        '''Přidání panelu pnl_display do sizeru sz.'''
        sz.Add(self.pnl_display)
        '''Nastaven9 callbacku OnPaint pro překreslování obsahu.'''
        self.pnl_display.Bind(wx.EVT_PAINT, self.OnPaint)

        '''Vytvoření panelu pro tlačítka.'''
        self.panel = wx.Panel(self,size=(1000,400),name="panel")
        '''Přidání panelu panel do sizeru sz.'''
        sz.Add(self.panel)
        '''Vytvoření sizeru pro tlačítka.'''
        sz_grid = wx.GridSizer(3,8,2,2)
        
        '''Nastavení sizeru sz_grid pro panel s tlačítky.'''
        self.panel.SetSizer(sz_grid)
        '''Vytvoření seznamu tlačítek, jejich přidání do sizeru sz_grid a nastavení callbacku OnClick.'''
        self.buttons = []
        for i in range(24):
            self.buttons.extend([wx.Button(self.panel, size=(100,100) ,id=i+1, label=str(i+1), name=str(i+1))])
            sz_grid.Add(self.buttons[i],flag=wx.EXPAND)
            self.Bind(wx.EVT_BUTTON,self.OnClick, self.buttons[i])

        self.Show(True)

    '''Vykreslení obsahu panelu pnl_display.'''
    def OnPaint(self, _):
        '''Získání kontextu.'''
        dc = wx.PaintDC(self.pnl_display) 
        '''Nastavení barvy pro vyplňování - bílá.'''
        brush = wx.Brush("white")  
        dc.SetBackground(brush)  
        dc.Clear() 

        '''Nastavení barvy pro vyplňování - červená.'''
        color = wx.Colour(255,0,0)
        b = wx.Brush(color) 
		
        '''Nastavení štětce a vykreslení kružnic.'''
        dc.SetBrush(b) 
        dc.DrawCircle(850,100,50) 
        dc.SetBrush(wx.Brush(wx.Colour(0,0,0))) 
        dc.DrawCircle(850,100,30) 
		
        '''Nastavení fontu.'''
        font = wx.Font(18, wx.ROMAN, wx.ITALIC, wx.NORMAL) 
        dc.SetFont(font) 
        '''Vykreslení textu.'''
        txt = "Profi Audio Equipment Ltd."
        dc.DrawText(txt,10,8) 
        txt_size = dc.GetTextExtent(txt)
		
        '''Nastavení pera a vykreslení čáry pod textem.'''
        pen = wx.Pen(wx.Colour(0,0,255)) 
        dc.SetPen(pen) 
        dc.DrawLine(10,txt_size[1]+2,txt_size[0]+10,txt_size[1]+2) 

        '''Nastavení čtětce a výplně a vykreslení obdélníku se šrafováním.
        Pero kreslí obrys a štětec výlň.'''
        dc.SetBrush(wx.Brush(wx.Colour(0,255,0), wx.CROSS_HATCH)) 
        dc.DrawRectangle(400, 15, 200, 180) 

    '''Nastavení obsluhy tlačítek.'''
    def OnClick(self,event):
        fr = 0
        '''Identifikace tlačítka (zdroje události) a vpis jeho ID.'''
        id = event.GetEventObject().GetId()
        if id < 9:
            fr = self.setup[id-1]
        print(f"frq: {fr}, Id: {event.GetEventObject().GetId()}")

    def OnExit(self,e):
        self.s.shutdown()
        self.Close(True)

app = wx.App(False)
frame = MainWindow(None, "IIaMaha")
app.MainLoop()