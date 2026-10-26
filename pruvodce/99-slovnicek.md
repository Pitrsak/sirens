# 99 — Slovníček

Abecedně. Podrobnější vysvětlení je v kapitole v závorce.

**ADSR** — obálka noty: Attack (náběh), Decay (pokles), Sustain (úroveň při držení), Release (doznění). (10)

**Aliasing** — falešné tóny, když signál obsahuje vyšší frekvence, než vzorkování zvládne zachytit. (10)

**Amplituda** — velikost chvění = hlasitost. (01)

**Aranžmá (arrangement)** — co která stopa hraje v kterém taktu písně; časová osa na Song. (20)

**Art-Net** — protokol, který posílá DMX hodnoty po síti v UDP paketech na port 6454. (30)

**Atribut** — proměnná patřící objektu (`self.name`) nebo třídě (`NAME`). (01)

**Automatizace** — slider, který se sám mění v čase písně podle bodů na časové ose. (20)

**Beat (úder)** — chvíle, kdy basy prudce vyskočí nad svůj průměr. (30)

**Blok** — jeden díl zvuku nástroje: zdroj (vyrábí zvuk) nebo efekt (upravuje ho). (10)

**BPM** — tempo, počet dob za minutu. (01, 20)

**Broadcast** — adresa, na kterou když pošleš paket, dostanou ho všichni v síti. (30)

**Buffer** — kousek vzorků, který zvuková karta zpracuje naráz (512 = ~11,6 ms). (01)

**Callback** — funkce, kterou předáš jinému kódu, aby ji zavolal, až se něco stane (`on_change`). (40)

**DC (device context)** — „plátno“ ve wx, na které se v EVT_PAINT kreslí. (40)

**dB (decibel)** — logaritmická míra hlasitosti; -6 dB ≈ poloviční amplituda. (01, 30)

**Dědičnost** — třída přebírá metody jiné třídy (`class Rack(Stack)`). (01)

**DFT / FFT** — Fourierova transformace: rozklad úseku zvuku na frekvence. FFT je rychlý algoritmus pro totéž; my počítáme DFT podle definice. (30)

**DMX** — standard pro světla: 512 kanálů, každý 0..255. (30)

**Docstring** — popis funkce nebo třídy v trojitých uvozovkách hned pod `def` / `class`. (01)

**Doba / takt / krok / tik** — doba = jeden úder tempa; takt = 4 doby; krok = jedno políčko mřížky patternu; tik = 1/48 taktu, nejmenší jednotka přehrávače. (20)

**Envelope (obálka)** — jak se hlasitost noty mění v čase, viz ADSR. (10)

**Event / událost** — něco, co se stalo (klik, klávesa, časovač); wx na to zavolá navázanou funkci. (40)

**Feedback** — vrstva obrazu, která pokračuje z minulého snímku, takže vznikají stopy a ozvěny. (30)

**Frekvence (Hz)** — kolikrát za sekundu se vlna opakuje = jak vysoko tón zní. (01)

**Grid (mřížka)** — kolik kroků má takt v patternu: 16, 12 nebo 24 (trioly). (20)

**Hann (okno)** — křivka, kterou se před DFT ztlumí kraje úseku. (30)

**Hlas (voice)** — jedna současně znějící nota nástroje; nástroj jich má 8. (10)

**InputFader** — pyo „zásuvka“, kde jde vyměnit vstup s krátkým prolnutím. (10)

**JSON** — textový formát dat (slovníky, seznamy, čísla, texty), do kterého se ukládá práce. (20)

**Komentář** — text za `#`, Python ho ignoruje, je pro lidi. (01)

**Lambda** — malá funkce bez jména (`lambda: self.undo()`). (01)

**Layer (vrstva)** — jeden díl obrazu: tvar nebo efekt. (30)

**Logaritmická stupnice** — stupnice, kde stejný kus pruhu = stejný *násobek* (ne přírůstek); hodí se na frekvence a časy. (40)

**MIDI** — standard pro noty: kanál, číslo noty (60 = C4), síla 0..127. (01)

**`mul=`** — parametr pyo objektu, který násobí jeho výstup (hlasitost). (10)

**numpy pole (array)** — pole čísel, se kterým jde počítat naráz; obraz i úsek zvuku jsou pole. (01)

**Objekt** — konkrétní věc vytvořená podle třídy. (01)

**Oktáva** — dvojnásobná frekvence; o 12 MIDI čísel výš. (01)

**Pattern** — krátký úsek not (1, 2 nebo 4 takty) jedné stopy, A až H. (20)

**Piano roll** — mřížka na Song, kde se kreslí noty: vodorovně čas, svisle výška. (50)

**Pyo objekt** — signál, který počítá pyo server: oscilátor, filtr, tabulka... (01)

**Rack** — seznam bloků jednoho nástroje, zvuk teče shora dolů. (10)

**Refresh** — žádost ve wx, aby se prvek překreslil. (40)

**RGB** — barva ze tří složek: červená, zelená, modrá. (30)

**Sample rate** — vzorků za sekundu, v Sirens 44 100. (01)

**Server (pyo)** — motor pyo, který ve vlastním vlákně počítá zvuk. (01, 10)

**Sizer** — rozvržení prvků ve wx (pod sebe / vedle sebe). (40)

**Slider** — pruh, kterým se nastavuje číslo; v Sirens vlastní kreslený (`slider.py`). (40)

**Socket** — „zásuvka“ do sítě, přes kterou program posílá pakety. (30)

**Spektrum** — kolik je ve zvuku které frekvence. (30)

**Stack** — obecný seznam prvků pod sebou, ze kterého dědí Rack i Painter. (20)

**Stopa (track)** — jeden nástroj s vlastními patterny a řádkem na časové ose. (20)

**Tabulka (pyo table)** — řada čísel v paměti: křivka, nahraný zvuk. (10)

**Thread / vlákno** — část programu, která běží souběžně s ostatními. (01)

**Timer (wx.Timer)** — budík, který pravidelně volá funkci; Sirens 30x za sekundu. (40)

**Třída** — šablona pro objekty (`class Track:`). (01)

**UDP** — síťový protokol: pošli paket a nečekej na potvrzení. (30)

**uint8 / float32** — typ čísel v poli: celá 0..255 (zobrazení) / desetinná (výpočty). (30)

**Undo / Redo** — vrátit / znovu provést změnu; snímky stavu v `history.py`. (20)

**Universe** — jedna sada 512 DMX kanálů; Art-Net jich umí víc. (30)

**Velocity (síla)** — jak silně je nota zahraná = jak hlasitě zazní, 1..127. (20)

**Vyhlazování** — hodnota se k nové blíží postupně („kus starého + kus nového“), aby neblikala. (01)

**Vzorek (sample)** — jedno číslo zvuku, poloha membrány v jednom okamžiku, -1..1. (01)
