import wx

class MyFrame(wx.Frame):
    def __init__(self, *args, **kw):
        super(MyFrame, self).__init__(*args, **kw)
        
        # Create a main panel
        main_panel = wx.Panel(self)
        
        # Create two sub-panels
        panel1 = wx.Panel(main_panel, size=(150, 100))
        panel1.SetBackgroundColour(wx.Colour(255, 0, 0))  # Red background
        
        panel2 = wx.Panel(main_panel, size=(150, 100))
        panel2.SetBackgroundColour(wx.Colour(0, 255, 0))  # Green background
        
        # Create a sizer for the main panel
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # Add the two panels to the sizer
        sizer.Add(panel1, 1, wx.EXPAND | wx.ALL, 10)
        sizer.Add(panel2, 2, wx.EXPAND | wx.ALL, 50)
        
        # Set the sizer for the main panel
        main_panel.SetSizer(sizer)
        
        # Set the title of the frame
        self.SetTitle("Hello World with Two Panels")
        self.SetSize((400, 200))
        self.Centre()

class MyApp(wx.App):
    def OnInit(self):
        frame = MyFrame(None)
        frame.Show(True)
        return True

# Run the application
if __name__ == '__main__':
    app = MyApp(False)
    app.MainLoop()
