import wx
import wx.html2

class MyFrame(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title='wxPython HTML Example')
        self.panel = wx.Panel(self)
        
        self.web_view = wx.html2.WebView.New(self.panel)
        self.text_ctrl = wx.TextCtrl(self.panel, style=wx.TE_PROCESS_ENTER)
        self.button = wx.Button(self.panel, label="Update text")

        self.st = wx.StaticText(self.panel, label="Input HEX color codes:")
        self.color_ctrl = wx.TextCtrl(self.panel, style=wx.TE_PROCESS_ENTER, )
        self.button_color = wx.Button(self.panel, label="Update color")
        
        self.text = ""
        self.color = 'f00'
        self.html_content = self.get_html_content()
        
        self.web_view.SetPage(self.html_content, "")
        
        self.button.Bind(wx.EVT_BUTTON, self.on_button)
        self.text_ctrl.Bind(wx.EVT_TEXT_ENTER, self.on_button)

        self.button_color.Bind(wx.EVT_BUTTON, self.on_button_color)
        self.color_ctrl.Bind(wx.EVT_TEXT_ENTER, self.on_button_color)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        input_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        input_sizer.Add(self.text_ctrl, 1, wx.EXPAND | wx.ALL, 5)
        input_sizer.Add(self.button, 0, wx.ALL, 5)

        input_sizer_color = wx.BoxSizer(wx.HORIZONTAL)
        input_sizer_color.Add(self.st, 1, wx.ALL, 5)
        input_sizer_color.Add(self.color_ctrl, 1, wx.EXPAND | wx.ALL, 5)
        input_sizer_color.Add(self.button_color, 0, wx.ALL, 5)
        
        sizer.Add(input_sizer, 0, wx.EXPAND)
        sizer.Add(input_sizer_color, 0, wx.EXPAND)
        sizer.Add(self.web_view, 1, wx.EXPAND)
        
        self.panel.SetSizer(sizer)
        
        self.Show()

    def get_html_content(self):
        return f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background-color: #f0f0f0;
                }}
                h1 {{
                    color: #{self.color if is_valid_hex_color(self.color) else "f00"};
                }}
            </style>
        </head>
        <body>
            <h1>{self.text if self.text else "Enter some text and press the button!"}</h1>
        </body>
        </html>
        """

    def on_button(self, event):
        self.text = self.text_ctrl.GetValue()
        self.html_content = self.get_html_content()
        self.web_view.SetPage(self.html_content, "")
        self.text_ctrl.SetValue("")

    def on_button_color(self, event):
        self.color = self.color_ctrl.GetValue()
        self.html_content = self.get_html_content()
        self.web_view.SetPage(self.html_content, "")
        self.color_ctrl.SetValue("")


def is_valid_hex_color(color_string):
    # Remove the leading '#' if present
    if color_string.startswith('#'):
        color_string = color_string[1:]
    
    # Check if the length is either 3 or 6
    if len(color_string) not in (3, 6):
        return False
    
    # Check if all characters are valid hexadecimal digits
    return all(c in '0123456789ABCDEFabcdef' for c in color_string)

if __name__ == '__main__':
    app = wx.App()
    frame = MyFrame()
    app.MainLoop()