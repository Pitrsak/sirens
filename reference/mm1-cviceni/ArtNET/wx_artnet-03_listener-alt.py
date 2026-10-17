import wx
import time
import socket
import struct
from threading import Thread

#ARTNET_IP='192.168.22.21'
ARTNET_PORT=0x1936
PACKET_SIZE=530
GRID_ROWS = 8
GRID_COLUMNS=64

class MainWindow(wx.Frame):
    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, title=title, size=(400,250))
        self.grid = wx.GridBagSizer(5,5)
        self.mainGrid = wx.BoxSizer(wx.VERTICAL)

        self.header = wx.StaticText(self,label="Header: ...")
        self.mainGrid.Add(self.header,0,wx.CENTER)

        self.controls = []

        for i in range(GRID_ROWS):
            for j in range(GRID_COLUMNS):
                #print(f"i:{i}, j:{j}\n")
                l1 = wx.StaticText(self,label=str((i*GRID_COLUMNS)+j+1))
                l2 = wx.StaticText(self,label="0")
                
                cell = wx.BoxSizer(wx.VERTICAL)
                cell.Add(l1,0,wx.CENTER)
                cell.Add(l2,0,wx.CENTER)
                self.grid.Add(cell,pos=(i,j))
                self.controls.append(l2)
                
        self.mainGrid.Add(self.grid,0,wx.CENTER)
        self.SetSizerAndFit(self.mainGrid)
        self.Show(True)

    def fill_form(self,header,data):
        hdr = ""
        for i in range(len(header)):
            hdr = hdr + " " + str(header[i])
        hdr = "\'"+ hdr + "\'"
        self.header.SetLabelText("Header: " + hdr)

        for i in range(len(data)):
            item = str(data[i])
            if self.controls[i].GetLabelText()!=item:
                self.controls[i].SetBackgroundColour(wx.YELLOW)
            else: 
                self.controls[i].SetBackgroundColour(wx.LIGHT_GREY)
            self.controls[i].SetLabelText(item)

    #Still not Used
    def OnExit(self,e):
        self.Close(True)

class ATserver(Thread):
    def __init__ (self,form:MainWindow):
        Thread.__init__(self)
    
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.bind(("", ARTNET_PORT))
        print ("UDPServer Waiting for client on port ", ARTNET_PORT)
        self.server_socket.setblocking(False)
        self.status=0 #stopped
        self.dmxform=form

    def run(self):
        self.status=1 #running
        while self.status==1:
            try:
                data, address = self.server_socket.recvfrom(PACKET_SIZE)
            except:
                time.sleep(0.1)                
                continue
            
            headList = data[:struct.calcsize('!8s8BH')]
            restList = data[struct.calcsize('!8s8BH'):]
            head = struct.unpack('!8s8BH',headList)
            rest=()
        
            for i in range(0,len(restList)):
                rest+=struct.unpack('B',restList[i:i+1])
            
            if self.status:
                wx.CallAfter(self.dmxform.fill_form,head,rest)
            
app = wx.App(False)
frame = MainWindow(None, "Thin ArtNET Server")
serv = ATserver(frame)
serv.start()
app.MainLoop()
serv.status = 0

print("Waiting for the thread...")
while(serv.is_alive()):
   serv.join(0.3)
print("Done.")

