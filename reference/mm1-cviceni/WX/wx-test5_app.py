#import wx
from pyo import *
import time

class MainWindow(wx.Frame):
    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, title=title, size=(400,250))
        self.logger = wx.TextCtrl(self, pos=(150,10), size=(230,150), style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.control1 = wx.Button(self,label="Tone &A", name="T1", pos=(10, 10))
        self.control2 = wx.Button(self,label="Tone &B", name="T2", pos=(10, 50))
        self.control3 = wx.Button(self,label="Tone &C", name="T3", pos=(10, 90))
        self.control4 = wx.Button(self,label="Tone &D", name="T4", pos=(10, 130))
        self.Bind(wx.EVT_BUTTON, self.OnClick,self.control1)
        self.Bind(wx.EVT_BUTTON, self.OnClick,self.control2)
        self.Bind(wx.EVT_BUTTON, self.OnClick,self.control3)
        self.Bind(wx.EVT_BUTTON, self.OnClick,self.control4)

        self.CreateStatusBar() # A Statusbar in the bottom of the window

        # Setting up the menu.
        filemenu= wx.Menu()

        # wx.ID_ABOUT and wx.ID_EXIT are standard IDs provided by wxWidgets.
        filemenu.Append(wx.ID_ABOUT, "&About"," Information about this program")
        filemenu.AppendSeparator()
        item = filemenu.Append(wx.ID_EXIT,"E&xit"," Terminate the program")
        self.Bind(wx.EVT_MENU, self.OnExit, item)
        
        # Creating the menubar.
        menuBar = wx.MenuBar()
        menuBar.Append(filemenu,"&File") # Adding the "filemenu" to the MenuBar
        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.
        self.Show(True)

        self.s = Server(duplex=0)
        self.s.setOutputDevice(pa_get_default_output())
        self.s.boot()

    def OnClick(self,event):
        #self.logger.AppendText(" Click on object with Id %d\n" %event.GetId())
        self.logger.AppendText(" Click on object with Id %s\n" %event.GetEventObject().GetName())
        
        fr = 0
        match event.GetEventObject().GetName():
            case "T1": fr = 440
            case "T2": fr = 800
            case "T3": fr = 1000
            case "T4": fr = 2000
        
        self.s.start()
        
        a = Sine(freq=fr, mul=0.5).out()
        time.sleep(1)
        self.s.stop()

    def OnExit(self,e):
        self.s.shutdown()
        self.Close(True)

app = wx.App(False)
frame = MainWindow(None, "Sample editor")
app.MainLoop()
