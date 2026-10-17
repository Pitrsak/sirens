#import wx #netřeba pyo už wx importuje 
from pyo import *
import time

#základní třída pro generátor, konstruktor definuje způsob generování zvuku. 
# ostatní metody jsou u odvozených tříd stejné
class Generator():
    def __init__(self, time, looplen=1, freq=440,attack=.01, decay=.1, sustain=.5, release=.1, dur=0.4, mul=1.0):
        self.baseFreq = freq
        self.duration = dur
        #vytvoření obálky
        self.adsr = {'attack':attack, 'decay':decay,'sustain':sustain,'release':release,'dur':dur}
        self.envelope = Adsr(attack=attack, decay=decay, sustain=sustain, release=release, dur=dur, mul=mul)

        #definice vzniku signálu
        self.signal =  Sine(freq=self.baseFreq, mul=self.envelope)   
        #vytvoření struktury tabulka, looper a tabwriter
        self.table = NewTable(length=looplen)       
        self.player = Looper(self.table,dur=looplen).stop()
        self.tabwriter = TableWrite(self.signal, time, self.table).stop()
        #generování zapnuto/vypnuto
        self.on = False

    #nastavení obálky uživatelem
    def setADSR(self, envelopeParameter, val):
        print(f"Generator.setADSR: param {envelopeParameter} adsr \
\'{list(self.adsr.keys())[envelopeParameter]}\' value {val}")
        
        match  envelopeParameter:
            case 0: self.envelope.setAttack(val)
            case 1: self.envelope.setDecay(val)
            case 2: self.envelope.setSustain(val)
            case 3: self.envelope.setRelease(val)
            case 4: self.envelope.setDur(val)

    #dotaz jestli je generátor zapnutý
    def IsOn(self):
        return self.on
    
    #start generátoru -looperu
    def start(self, freq=440):
        self.signal.setFreq(freq)
        self.baseFreq = freq
        self.player.out()
        self.on = True

    #zastavení generátoru
    def stop(self):
        self.player.stop()
        self.on = False
    
    #zkopírování signálu s aktuální obálkou do tabulky looperu
    def copy(self):
        if self.on:
            self.tabwriter.play(self.duration)
            self.envelope.play()
    
    #vymazání tabulky generátoru
    def clear(self):
        self.table.reset()

#další odvozené generátory G1-G3
class G1(Generator):
    def __init__(self, time, looplen=1, freq=440,attack=.01, decay=.1, sustain=.5, release=.1, dur=0.4, mul=1.0):
        self.baseFreq = freq/440
        self.duration = dur
        self.adsr = {'attack':attack, 'decay':decay,'sustain':sustain,'release':release,'dur':dur}
        self.envelope = Adsr(attack=attack, decay=decay, sustain=sustain, release=release, dur=dur, mul=mul)

        #modulace frekvence sinu pilou-rampou od 0 do 1
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

        #generování pomocí součtové syntézy z 10 harmonických - viz příklady v dokumentaci PYO knihovny
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

        #jiný příklad součtové syntézy
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
        self.player.out()
        self.tabwriter.play(self.duration)
        self.envelope.play()
        self.on = True

#okno aplikace
class MainWindow(wx.Frame):
    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, title=title, size=(980,900))
        
        # INIT ZVUKUUU
        ########################################################################################
        self.path = 'apka/Sounds/'
        self.samples = ['1.mp3','2.mp3','3.mp3','4.mp3','5.mp3','6.mp3','7.mp3','8.mp3']
        self.initVolume = 0

        self.initSndServer()
        self.sampleBank = self.LoadBank()
        
        # NASTAVENI GENRÁTORŮ 
        ########################################################################################

        # looper pro přehrání samplů z banky
        self.loopDuration = 1
        self.master = NewTable(length=1,chnls=2)
        self.player = Looper(self.master,dur=self.loopDuration).out()
        
        #vytvoření sady generátorů řízených looperem self.player 
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
        #vytvoření struktury ovládacích prvků pomocí widgetů Button, Slider a Sizer
        self.liveButtons = [i for i in range(0,144)]
        self.title = title
        sz = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sz)

        self.pnl_display = wx.Panel(self,size=(1000,250),name="display")
        self.sz_pnl_display = wx.BoxSizer(wx.HORIZONTAL)
        self.pnl_display.SetSizer(self.sz_pnl_display)

        #vytvoření panelu se zobrazením generovaných signálů
        signals_to_draw = [self.player]+[self.generators[i].player for i in range(len(self.generators))]
        self.display = PyoGuiScope(self.pnl_display,size=(1000,200))
        self.display.setAnalyzer(Scope(signals_to_draw,function=lambda a: ...))
        #self.display.setAnalyzer(Spectrum(self.player,function=lambda a: ...))

        self.sz_state_btn = wx.GridSizer(2,2,2,2)

        self.StartBtn = wx.Button(self.pnl_display,id=1001,label="Start",size=(100,100))
        self.StartBtn.SetBackgroundColour('Gray')
        
        #nastavení hlasitosti všech signálů na výstupu
        self.MasterVolume = wx.Slider(self.pnl_display,id=1002,value=0,minValue=0,
                                      maxValue=100,size=(-1,200), 
                                      style=(wx.SL_VERTICAL | wx.SL_INVERSE |wx.SL_VALUE_LABEL | wx.SL_AUTOTICKS))
        self.Quit = wx.Button(self.pnl_display,id=1002,label="Quit",size=(100,100))
        self.Quit.SetBackgroundColour('Red')
        #reset masteru
        self.Clear = wx.Button(self.pnl_display,id=1003,label="Clear",size=(100,100))
        self.Clear.SetBackgroundColour('Blue')
        #reset všech generátorů současně
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

        self.panel = wx.Panel(self,size=(1000,700),name="panel")
        sz_panel = wx.GridSizer(2,8,2,2)
        self.panel.SetSizer(sz_panel)
        sz.Add(self.panel)      

        #nastavení ovládacích prvků pro 16 generátorů
        self.buttons = []
        self.btnClr = ['Blue','Orange','Yellow','Red','Cyan','Orange','Cyan','Orange','Cyan']*16
        self.sliders = []

        #každý cyklus nastaví rozhraní pro jeden generátor
        for i in range(0,144,9):
            sz_btn = wx.BoxSizer(wx.VERTICAL)

            sz_panel.Add(sz_btn)
            sz_btn_grid = wx.GridSizer(2,2,2,2)
            sz_btn.Add(sz_btn_grid)

            print(f"Main: i = {i} -> Generating the widget IDs <{i}, {i+3}>, len buttons {len(self.buttons)}")
            #generátor má 9 ovládacích prvků, ale jednotlivé generátory jsou očíslovány kontinuálně od 1 do 16
            generator = i // 9
            k = generator * 4
            #první 4 tlačítka
            labels = ["spl","gen","copy","del"]
            b = [wx.Button(self.panel, size=(60,30), id=i+j, label=labels[j]+str(generator+1)) for j in range(4)]
            
            self.buttons += b
            print(f"Main: i = {i} -> Generating the widget IDs <{i}, {i+3}>, len buttons {len(self.buttons)}")
            
            self.Bind(wx.EVT_BUTTON,self.OnSampleClick, self.buttons[k])
            self.Bind(wx.EVT_BUTTON,self.OnGenerClick, self.buttons[k+1])
            self.Bind(wx.EVT_BUTTON,self.OnCopyClick, self.buttons[k+2])
            self.Bind(wx.EVT_BUTTON,self.OnDelLooper, self.buttons[k+3])

            for j in range(4):
                self.buttons[k+j].SetBackgroundColour(self.btnClr[i+j])
                sz_btn_grid.Add(self.buttons[k+j])
            
            print(f"Main: i = {i} -> Generating the widget IDs <{i}, {i+3}>")
            
            #ovládání obálky generátoru
            #každý generátor má 5 sliderů pro nastavení obálky
            ADSRenvelope = ["attack","decay","sustain","release","duration"] 
            ADSRvals = [1,10,5,10,40]
            k = (i // 9) * 5
            for j in range(4,9):
                self.sliders.append(wx.Slider(self.panel, id=i+j, value=ADSRvals[j-4], maxValue = 500, 
                                        style=(wx.SL_HORIZONTAL|wx.SL_VALUE_LABEL),  
                                        name=ADSRenvelope[j-4]))
                sz_btn.Add(self.sliders[k+j-4], flag=wx.EXPAND)
                self.Bind(wx.EVT_SLIDER,self.OnEnvelopeChanged,self.sliders[k+j-4])
                self.sliders[k+j-4].SetBackgroundColour(self.btnClr[i+j])
            print(f"Main: i = {i} -> Generated the widget IDs <{i+4}, {i+8}>, len sliders {len(self.sliders)}")
            
        #čítač cyků looperu pro zobrazení v záhlaví okna
        self.cntDriver = TrigFunc(self.player['trig'],self.updateCounter)
        self.time = time.time()
        
        self.Show(True)    
        #self.s.gui(locals())
        
    #spuštění zvukového serveru
    def OnStart(self,event):
        b: wx.Button = event.GetEventObject()
        if self.s.getIsStarted():
            self.s.stop()
            b.SetBackgroundColour('Gray')
            b.SetLabelText("Start")
        else:
            self.s.start()
            b.SetBackgroundColour('Green')
            b.SetLabelText("Stop")
            self.s.setAmp(self.initVolume)
    
    #změna hlasitosti
    def OnMasterChanged(self,event: wx.Event):
        amp = event.EventObject.Value
        self.s.setAmp(amp/100.0)

    #reset masteru
    def OnClear(self,event):
        self.master.reset()

    #reset všech generátorů
    def OnClearAll(self,event):
        for x in self.generators:
            x.clear()

    #aktualizace čítače cyklů v záhlaví okna
    def updateCounter(self):
        self.cycle += 1
        tm = time.time()-self.time
        self.SetTitle(self.title+"- cycle: "+str(self.cycle)+" time: "+str(tm))
                     
    #inicializace audio serveru
    def initSndServer(self):
        self.s = Server(duplex = 0)
        self.s.setOutputDevice(pa_get_default_output())
        self.s.boot()

    #načtení zamplů do banky
    def LoadBank(self):
        return [SndTable(self.path+x) for x in self.samples]
    
    #spuštění generátoru
    def OnGenerClick(self,event):
        b:wx.Button = event.GetEventObject()
        bt = b.GetId()
        #určení id generátoru z id buttonu
        genid = bt // 9
        print(f"GenerClick: Button ID {bt} pressed...")
        if bt in self.liveButtons:
            if not self.generators[genid].IsOn():
                self.generators[genid].start(genid*440)
                b.SetBackgroundColour('Green')
            else:
                self.generators[genid].stop()
                b.SetBackgroundColour(self.btnClr[bt])

    #kopírování výstupu generátoru do tabulky looperu
    def OnCopyClick(self,event):
        bt = event.GetEventObject().GetId()
        genid = bt // 9
        print(f"CopyClick: Button ID {bt} pressed...")
        if bt in self.liveButtons:
            if self.generators[genid].IsOn():
                self.generators[genid].copy()
    
    #reset konkrétního generátoru
    def OnDelLooper(self,event):
        bt = event.GetEventObject().GetId()
        genid = bt // 9
        print(f"OnDelLooper: Button ID {bt} pressed...")
        if bt in self.liveButtons:
            self.generators[genid].clear()

    #změna nastavení adsr obálky pro konkrétní looper-generátor
    def OnEnvelopeChanged(self,event):
        slider = event.GetEventObject().GetId()
        val = event.EventObject.Value/100.0
        genID = slider // 9
        envelopeParameter = slider % 9 - 4
        print(f"OnEnvelopeChanged: Slider ID {slider} changed, generator: {genID}, adsrPar: {envelopeParameter}, value: {val}")
        if genID < len(self.generators):
            self.generators[genID].setADSR(envelopeParameter, val)
    
    #spuštění konkrétního samplu z banky
    def OnSampleClick(self,event):
        bt = event.GetEventObject().GetId()
        print(f"OnSampleClick: Button ID {bt} pressed...")
        sampleid = bt // 9
        tm = round(self.player['time'].get()*self.master.size)
        table_snd = self.sampleBank[sampleid % len(self.sampleBank)]
        #kopírování samplu z banky do tabulky looperu
        self.master.copyData(table_snd,destpos=tm)

    #ukončení aplikace
    def OnExit(self,e):
        if self.s.getIsBooted():
            self.s.shutdown()
        self.Close(True)

app = wx.App(False)
frame = MainWindow(None, "IIaMaha")
app.MainLoop()