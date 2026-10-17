#import wx
from pyo import *
import time

class Generator():
    def __init__(self, time, looplen=1, freq=440,attack=.01, decay=.1, sustain=.5, release=.1, dur=0.4, mul=1.0):
        self.baseFreq = freq
        self.duration = dur
        self.adsr = {'attack':attack, 'decay':decay,'sustain':sustain,'release':release,'dur':dur}
        self.envelope = Adsr(attack=attack, decay=decay, sustain=sustain, release=release, dur=dur, mul=mul)

        self.signal =  Sine(freq=self.baseFreq, mul=self.envelope)   
        self.table = NewTable(length=looplen)       
        self.player = Looper(self.table,dur=looplen).stop()
        self.tabwriter = TableWrite(self.signal, time, self.table).stop()
        self.on = False

    def setADSR(self, envelopeParameter, val):
        print(f"Generator.setADSR: param {envelopeParameter} adsr \
\'{list(self.adsr.keys())[envelopeParameter]}\' value {val}")
        #self.envelope.set(list(self.adsr.keys())[envelopeParameter],val)    
        match  envelopeParameter:
            case 0: self.envelope.setAttack(val)
            case 1: self.envelope.setDecay(val)
            case 2: self.envelope.setSustain(val)
            case 3: self.envelope.setRelease(val)
            case 4: self.envelope.setDur(val)

    def IsOn(self):
        return self.on
    
    def start(self, freq=440):
        self.signal.setFreq(freq)
        self.baseFreq = freq
        self.player.out()
        self.tabwriter.play(self.duration)
        self.envelope.play()
        self.on = True

    def stop(self):
        self.player.stop()
        self.on = False

    def copy(self):
        if self.on:
            self.tabwriter.play(self.duration)
            self.envelope.play()

class G1(Generator):
    def __init__(self, time, looplen=1, freq=440,attack=.01, decay=.1, sustain=.5, release=.1, dur=0.4, mul=1.0):
        self.baseFreq = freq/440
        self.duration = dur
        self.adsr = {'attack':attack, 'decay':decay,'sustain':sustain,'release':release,'dur':dur}
        self.envelope = Adsr(attack=attack, decay=decay, sustain=sustain, release=release, dur=dur, mul=mul)

        a = Phasor(freq=self.baseFreq, mul=1000, add=500)
        self.signal = Sine(a, mul=self.envelope)

        self.table = NewTable(length=looplen)       
        self.player = Looper(self.table,dur=looplen).stop()
        self.tabwriter = TableWrite(self.signal, time, self.table).stop()
        self.on = False

class G2(Generator):
    def __init__(self, time, looplen=1, freq=100,attack=.01, decay=.1, sustain=.5, release=.1, dur=0.4, mul=1.0):
        self.baseFreq = freq
        self.duration = dur
        self.adsr = {'attack':attack, 'decay':decay,'sustain':sustain,'release':release,'dur':dur}
        self.envelope = Adsr(attack=attack, decay=decay, sustain=sustain, release=release, dur=dur, mul=mul)

        # Sets fundamental frequency.
        #freq = 100
        # Sets the highest harmonic.
        high = 10

        # Generates the list of harmonic frequencies (odd only).
        harms = [self.baseFreq * i for i in range(1, high) if i % 2 == 1]
        # Generates the list of harmonic amplitudes (1 / n).
        amps = [0.33 / i for i in range(1, high) if i % 2 == 1]

        # Creates all sine waves at once.
        a = Sine(freq=harms, mul=amps)

        # The mix(voices) method (defined in PyoObject) mixes
        # the object streams into `voices` streams.
        b = a.mix(voices=1).play()

        self.signal = self.envelope*b

        self.table = NewTable(length=looplen)       
        self.player = Looper(self.table,dur=looplen).stop()
        self.tabwriter = TableWrite(self.signal, time, self.table).stop()
        self.on = False

    def start(self, freq=440):
        self.baseFreq = freq
        self.player.out()
        self.tabwriter.play(self.duration)
        self.envelope.play()
        self.on = True

class G3(Generator):
    def __init__(self, time, looplen=1, freq=100,attack=.01, decay=.1, sustain=.5, release=.1, dur=0.4, mul=1.0):
        self.baseFreq = freq
        self.duration = dur
        self.adsr = {'attack':attack, 'decay':decay,'sustain':sustain,'release':release,'dur':dur}
        self.envelope = Adsr(attack=attack, decay=decay, sustain=sustain, release=release, dur=dur, mul=mul)

        # 12 streams with different combinations of `freq` and `ratio`.
        a = SumOsc(
            freq=[1.00*self.baseFreq, 1.502*self.baseFreq, 2.005*self.baseFreq, 2.507*self.baseFreq],
            ratio=[0.501, 0.753, 1.255],
            index=[0.3, 0.4, 0.5, 0.6, 0.7, 0.4, 0.5, 0.3, 0.6, 0.7, 0.3, 0.5],
            mul=0.05,
        )

        # Adds a stereo reverberation to the signal
        rev = Freeverb(a.mix(2), size=0.80, damp=0.70, bal=0.30)

        self.signal =  rev*self.envelope
        self.table = NewTable(length=looplen)       
        self.player = Looper(self.table,dur=looplen).stop()
        self.tabwriter = TableWrite(self.signal, time, self.table).stop()
        self.on = False

    def start(self, freq=440):
        #self.baseFreq = freq
        self.player.out()
        self.tabwriter.play(self.duration)
        self.envelope.play()
        self.on = True

class MainWindow(wx.Frame):
    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, title=title, size=(800,770))
        
        # INIT ZVUKUUU
        ########################################################################################
        self.path = 'apka/Sounds/'
        self.samples = ['1.mp3','2.mp3','3.mp3','4.mp3','5.mp3','6.mp3','7.mp3','8.mp3']
        self.volume = 0

        self.initSndServer()
        self.sampleBank = self.LoadBank()
        
        # NASTAVENI GENRÁTORŮ 
        ########################################################################################

        # looper pro přehrání samplů z banky
        self.loopDuration = 1
        self.master = NewTable(length=1,chnls=2)
        self.player = Looper(self.master,dur=self.loopDuration).out()

        self.generators = [Generator(self.player['time']), Generator(self.player['time']),
                           Generator(self.player['time']),Generator(self.player['time']),
                           Generator(self.player['time']),Generator(self.player['time']),
                           Generator(self.player['time']),Generator(self.player['time']),
                           G1(self.player['time']), G1(self.player['time']), G1(self.player['time']), G1(self.player['time']),
                           G2(self.player['time']),G2(self.player['time']),G3(self.player['time']),G3(self.player['time'])]

        self.cycle = 0

        # NASTAVENÍ GUI
    ###############################################################################################

        #self.liveButtons = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,
        #                    21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40]
        self.liveButtons = [i for i in range(1,40)]
        self.title = title
        sz = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sz)

        self.pnl_display = wx.Panel(self,size=(1000,200),name="display")
        self.sz_pnl_display = wx.BoxSizer(wx.HORIZONTAL)
        self.pnl_display.SetSizer(self.sz_pnl_display)
        signals_to_draw = [self.player]+[self.generators[i].player for i in range(len(self.generators))]
        self.display = PyoGuiScope(self.pnl_display,size=(1000,200))
        self.display.setAnalyzer(Scope(signals_to_draw,function=lambda a: ...))
        #self.display.setAnalyzer(Spectrum(self.player,function=lambda a: ...))

        self.sz_state_btn = wx.GridSizer(2,2,2,2)

        self.StartBtn = wx.Button(self.pnl_display,id=1001,label="Start",size=(100,100))
        self.StartBtn.SetBackgroundColour('Gray')
        self.MasterVolume = wx.Slider(self.pnl_display,id=1002,value=0,minValue=0,
                                      maxValue=100,size=(-1,200), 
                                      style=(wx.SL_VERTICAL | wx.SL_INVERSE | wx.SL_VALUE_LABEL | wx.SL_AUTOTICKS))
        self.Quit = wx.Button(self.pnl_display,id=1002,label="Quit",size=(100,100))
        self.Quit.SetBackgroundColour('Red')
        self.Clear = wx.Button(self.pnl_display,id=1003,label="Clear",size=(100,100))
        self.Clear.SetBackgroundColour('Blue')
        self.ClearAll = wx.Button(self.pnl_display,id=1004,label="Clear All",size=(100,100))
        self.ClearAll.SetBackgroundColour('Grey')

        self.sz_state_btn.Add(self.StartBtn)
        self.sz_state_btn.Add(self.Quit)
        self.sz_state_btn.Add(self.Clear)
        self.sz_state_btn.Add(self.ClearAll)

        self.sz_pnl_display.Add(self.sz_state_btn)
        self.sz_pnl_display.Add(self.MasterVolume)
        self.sz_pnl_display.Add(self.display,flag=wx.EXPAND)
        
        self.Bind(wx.EVT_BUTTON,self.OnStart,self.StartBtn)
        self.Bind(wx.EVT_SLIDER,self.OnMasterChanged,self.MasterVolume)
        self.Bind(wx.EVT_BUTTON,self.OnExit,self.Quit)
        self.Bind(wx.EVT_BUTTON,self.OnClear,self.Clear)
        self.Bind(wx.EVT_BUTTON,self.OnClearAll,self.ClearAll)

        sz.Add(self.pnl_display)

        self.panel = wx.Panel(self,size=(1000,600),name="panel")
    
        sz_grid1 = wx.GridSizer(1,8,2,2)
        sz_grid2 = wx.GridSizer(2,8,2,2)
        sz_panel = wx.BoxSizer(wx.VERTICAL)
        self.panel.SetSizer(sz_panel)

        sz_panel.Add(sz_grid1)
        sz_panel.Add(sz_grid2)
        sz.Add(self.panel)      

        self.buttons = []
        self.btnClr = ['Lightgray']*8+['Orange','Yellow']*16

        for i in range(8):
            b1 = wx.Button(self.panel, size=(100,30) ,id=i+1, label='smpl '+str(i+1))
            sz_grid1.Add(b1)
            self.buttons.append(b1)
            self.Bind(wx.EVT_BUTTON,self.OnSampleClick, self.buttons[i])
            self.buttons[i].SetBackgroundColour(self.btnClr[i])
            print(f"Main: i = {i} -> Generating 1st row IDs {i+1}")

        for i in range(8,24):
            sz_btn1 = wx.BoxSizer(wx.VERTICAL)
            sz_btn2 = wx.BoxSizer(wx.HORIZONTAL)
            b1 = wx.Button(self.panel, size=(50,30) ,id=i+1, label='gen'+str(i-7))
            b2 = wx.Button(self.panel, size=(50,30) ,id=i+1+16, label='copy')
            self.buttons.append(b1)
            self.buttons.append(b2)
            
            self.Bind(wx.EVT_BUTTON,self.OnGenerClick, self.buttons[2*i-8])
            self.Bind(wx.EVT_BUTTON,self.OnCopyClick, self.buttons[2*i-7])
            self.buttons[2*i-8].SetBackgroundColour(self.btnClr[2*i-8])
            self.buttons[2*i-7].SetBackgroundColour(self.btnClr[2*i-7])

            if i<16: 
                print(f"Main: i = {i} -> Generating the 2nd row IDs {i+1}, {i+1+16}")
            else:
                print(f"Main: i = {i} -> Generating the 3rd row IDs {i+1}, {i+1+16}")

            sz_btn2.Add(b1)
            sz_btn2.Add(b2)
            sz_btn1.Add(sz_btn2)

            j = 5*(i-8)+41
            attack = wx.Slider(self.panel, id=j, value=1, maxValue = 500, style=(wx.SL_HORIZONTAL|wx.SL_VALUE_LABEL),  name='attack')
            sz_btn1.Add(attack,flag=wx.EXPAND)
            self.Bind(wx.EVT_SLIDER,self.OnEnvelopeChanged,attack)
            decay = wx.Slider(self.panel, id=j+1, value=10, maxValue = 500, style=(wx.SL_HORIZONTAL|wx.SL_VALUE_LABEL),  name='decay')
            sz_btn1.Add(decay,flag=wx.EXPAND)
            self.Bind(wx.EVT_SLIDER,self.OnEnvelopeChanged,decay)
            sustain = wx.Slider(self.panel, id=j+2, value=5, maxValue = 100, style=(wx.SL_HORIZONTAL|wx.SL_VALUE_LABEL), name='sustain')
            sz_btn1.Add(sustain,flag=wx.EXPAND)
            self.Bind(wx.EVT_SLIDER,self.OnEnvelopeChanged,sustain)
            release = wx.Slider(self.panel, id=j+3, value=10, maxValue = 1000, style=(wx.SL_HORIZONTAL|wx.SL_VALUE_LABEL), name='release')
            sz_btn1.Add(release,flag=wx.EXPAND)
            self.Bind(wx.EVT_SLIDER,self.OnEnvelopeChanged,release)
            duration = wx.Slider(self.panel, id=j+4, value=40, maxValue = 2000, style=(wx.SL_HORIZONTAL|wx.SL_VALUE_LABEL), name='duration')
            sz_btn1.Add(duration,flag=wx.EXPAND)
            self.Bind(wx.EVT_SLIDER,self.OnEnvelopeChanged,duration)

            sz_grid2.Add(sz_btn1,flag=wx.EXPAND)

        self.cntDriver = TrigFunc(self.player['trig'],self.updateCounter)
        self.time = time.time()
        
        self.Show(True)    
        #self.s.gui(locals())
        
    def OnStart(self,event):
        b: wx.Button = event.GetEventObject()
        if self.s.getIsStarted():
            self.s.stop()
            b.SetBackgroundColour('Gray')
            b.SetLabelText("Start")
        else:
            self.s.start()
            self.s.setAmp(self.volume)
            b.SetBackgroundColour('Green')
            b.SetLabelText("Stop")

    def OnMasterChanged(self,event: wx.Event):
        amp = event.EventObject.Value
        self.volume = amp / 100.0
        self.s.setAmp(self.volume)
        #print(f"OnMasterChanged: Current amplitude is set to {self.s.getCurrentAmp()}.")

    def OnClear(self,event):
        self.master.reset()

    def OnClearAll(self,event):
        for x in self.generators:
            x.table.reset()        

    def updateCounter(self):
        self.cycle += 1
        tm = time.time()-self.time
        self.SetTitle(self.title+"- cycle: "+str(self.cycle)+" time: "+str(tm))
                     
    def initSndServer(self):
        self.s = Server(duplex = 0)
        self.s.setOutputDevice(pa_get_default_output())
        self.s.boot()
        #print(f"initSndServer: Current amplitude is set to {self.s.getCurrentAmp()}.")

        

    def LoadBank(self):
        return [SndTable(self.path+x) for x in self.samples]
    
    def OnGenerClick(self,event):
        b:wx.Button = event.GetEventObject()
        bt = b.GetId()
        print(f"GenerClick: Button ID {bt} pressed...")
        if bt in self.liveButtons:
            if not self.generators[bt-9].IsOn():
                self.generators[bt-9].start(((bt)/10)*440)
                b.SetBackgroundColour('Green')
            else:
                self.generators[bt-9].stop()
                b.SetBackgroundColour(self.btnClr[2*bt-10])

    def OnCopyClick(self,event):
        bt = event.GetEventObject().GetId()
        print(f"CopyClick: Button ID {bt} pressed...")
        if bt in self.liveButtons:
            if self.generators[bt-25].IsOn():
                self.generators[bt-25].copy()
    
    def OnEnvelopeChanged(self,event):
        slider = event.GetEventObject().GetId()
        val = event.EventObject.Value/100.0
        generatorID = (slider-41) // 5
        envelopeParameter = (slider-41) % 5
        print(f"OnEnvelopeChanged: Slider ID {slider} changed, generator: {generatorID}, adsrPar: {envelopeParameter}, value: {val}")
        if generatorID < len(self.generators):
            self.generators[generatorID].setADSR(envelopeParameter, val)
    
    def OnSampleClick(self,event):
        bt = event.GetEventObject().GetId()
        tm = round(self.player['time'].get()*self.master.size)
        table_snd = self.sampleBank[bt % len(self.sampleBank)]
        self.master.copyData(table_snd,destpos=tm)

    def OnExit(self,e):
        if self.s.getIsBooted():
            self.s.shutdown()
        self.Close(True)

print("Audio host APIS:")
pa_list_host_apis()
pa_list_devices()
print("Default input device: %i" % pa_get_default_input())
print("Default output device: %i" % pa_get_default_output())

app = wx.App(False)
frame = MainWindow(None, "IIaMaha")
app.MainLoop()