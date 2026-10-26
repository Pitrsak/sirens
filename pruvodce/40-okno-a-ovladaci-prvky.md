# 40 — Hlavní okno a ovládací prvky

Tahle kapitola vysvětluje všechno, co je v Sirens "okno": jak se poskládá hlavní okno,
jak funguje wxPython, proč a jak si kreslíme vlastní slidery a tlačítka, jak funguje
pravý panel a jak se kreslí osciloskop, spektrum, obraz a světlo.

Soubory, o kterých je řeč:

| Soubor | Co v něm je |
|---|---|
| `sirens/ui/main_frame.py` | `MainFrame`: hlavní okno, hlavička, menu, časovač, ukládání, Undo / Redo, export |
| `sirens/ui/theme.py` | barvy a písmo celé aplikace, kreslení textu s rozestupem |
| `sirens/ui/slider.py` | `Slider`: vlastní kreslený slider |
| `sirens/ui/widgets.py` | malé kreslené prvky: `Caption`, `PillButton`, `TextButton`, `ArrowButton`, `StatusPill`, `ChoiceRow`, `confirm` |
| `sirens/ui/sidebar.py` | `Sidebar`: pravý panel, do kterého se skládají slidery; `divider` (tenká čára) |
| `sirens/ui/stack_editor.py` | `StackEditor`: úprava seznamu bloků zvuku / vrstev obrazu v panelu |
| `sirens/ui/views.py` | `GraphView` a podtřídy `ScopeView`, `SpectrumView`, `VisualView`, `LightView` |
| `sirens/ui/__init__.py` | prázdný, jen dělá ze složky `ui` balíček |

Samotné záložky (`sound_page.py`, `song_page.py`, ...) jsou v kapitole 50. Tady jde o to,
z čeho jsou postavené.

---

## Úvod: jak okno vypadá a kdo kreslí co

```
+--------------------------------------------------------------------------------------+
| SIRENS  <- ->   [Sound] [Song] [Visual] [Light]          [Open] [Save]   [ Play ]   |  hlavička
+--------------------------------------------------------------------------------------+  divider
|                                                      | OUTPUT                        |
|   +-----------------------------------------------+  | [Master ██████░░░░]  [0.50]   |
|   | SCOPE                    peak -6.0 dB  21.3 ms|  |-------------------------------|
|   |   ~~~~/\~~~~/\~~~~                            |  | TRACK              Copy sound |
|   +-----------------------------------------------+  | Edit  [Track 1        v]      |
|   +-----------------------------------------------+  | Name  [Track 1         ]      |
|   | SPECTRUM                 strongest 440.0 Hz   |  | ENVELOPE                      |
|   |   ___/\____/\___                              |  | [Attack ██░░░░░] [0.01] s     |
|   +-----------------------------------------------+  | šedé vysvětlení pod sliderem  |
|   ( Track 1: Oscillator -> Filter )                  | OSCILLATOR   Off Up Down Remove|
|   [ klaviatura ]                                     | [Add block]                   |
+--------------------------------------------------------------------------------------+
        viewport (levá část)                               sidebar (pravý panel)
```

Kdo co kreslí:

- **Celé okno, hlavička, menu Edit**: `MainFrame` v `sirens/ui/main_frame.py`.
- **Logo "SIRENS" a nadpisy skupin** ("OUTPUT", "ENVELOPE"): `Caption` ve `widgets.py`.
- **Šipky Undo / Redo** vedle loga: `ArrowButton` ve `widgets.py`.
- **Záložky, Open, Save, Play a tlačítka typu "Add block"**: `PillButton` ve `widgets.py`.
  Vybraná záložka a Play jsou bílé (`primary=True`).
- **Malá textová tlačítka** u nadpisu (Off, Up, Down, Remove, Copy sound): `TextButton`.
- **Rámečky SCOPE, SPECTRUM, VISUAL, LIGHT**: `views.py`.
- **Štítek pod grafy** ("Track 1: Oscillator -> Filter"): `StatusPill`.
- **Pravý panel**: `Sidebar` v `sidebar.py`, slidery v něm: `Slider` v `slider.py`,
  řady tlačítek typu Sine / Saw / Square: `ChoiceRow`.
- **Seznam bloků v panelu** (nadpis bloku s tlačítky, jeho slidery, Add block): `StackEditor`.
- **Klaviatura, piano roll, časová osa**: to už jsou jiné soubory (kapitola 50), ale
  berou barvy z `theme.py`.

Každá záložka (Sound, Song, Visual, Light) je jeden `wx.Panel`, který má vlevo
viewport (grafy) a vpravo `Sidebar`. Všechny čtyři existují pořád, jen tři jsou schované.

---

## Jak funguje wxPython, od nuly

Kapitola 01 má krátkou tabulku pojmů. Tady je to pořádně, na našem kódu.

### Aplikace a hlavní smyčka

Program s okny nefunguje jako skript "shora dolů a konec". Funguje takhle:

1. Vytvoří se aplikace a okna.
2. Spustí se **hlavní smyčka** (main loop), která pořád dokola čeká na **události**:
   klik myší, stisk klávesy, "tohle okno se má překreslit", "tikl časovač"...
3. Když událost přijde, wx zavolá funkci, kterou jsme k ní předem **navázali**.
4. Funkce doběhne a smyčka zase čeká.

V Sirens je to v `sirens/__main__.py`:

```python
app = wx.App()                 # aplikace (musí existovat dřív než jakékoli okno)
engine = AudioEngine()
frame = MainFrame(engine)      # postaví celé okno (zatím neviditelné)
frame.Show()                   # ukáže ho
app.MainLoop()                 # tady program "visí" a obsluhuje události, dokud se okno nezavře
```

Důležitý důsledek: **všechen náš kód v UI běží v té jedné smyčce**. Když nějaká funkce
trvá dlouho, celé okno zamrzne (nepřekresluje se, nereaguje). Proto se v `_on_tick`
dělá jen málo práce a kreslí se jen to, co je vidět.

### Frame a Panel

- `wx.Frame` = okno s titulkem a křížkem. `MainFrame` z něj dědí
  (`class MainFrame(wx.Frame)`, `sirens/ui/main_frame.py:53`).
- `wx.Panel` = obdélník uvnitř okna, do kterého se dávají další prvky. Do Frame se
  nekreslí přímo, dá se do něj jeden panel (`root = wx.Panel(self)`, `main_frame.py:73`)
  a všechno ostatní je jeho dítě.

Každý prvek má **rodiče** (parent): první argument konstruktoru. `SoundPage(root, ...)`
znamená "SoundPage leží uvnitř root". Rodič určuje, kde prvek je, a když se rodič
zruší, zruší se i jeho děti.

### Sizery: kdo kam a jak velký

Prvky bychom mohli umístit ručně na pixely, ale pak by se při změně velikosti okna nic
nepřizpůsobilo. Místo toho se používá **sizer**: neviditelný "skládač", který sám počítá
pozice a velikosti.

`wx.BoxSizer(wx.VERTICAL)` skládá prvky pod sebe, `wx.BoxSizer(wx.HORIZONTAL)` vedle sebe.
Prvek se přidá metodou `Add(prvek, proportion, flagy, okraj)`:

- **proportion** `0` = prvek dostane jen tolik místa, kolik sám chce (svoji min. velikost);
  `1` = dostane podíl zbylého místa (když jsou dva s `1`, rozdělí se napůl).
- **flagy**: `wx.EXPAND` = roztáhnout se i v druhém směru (u svislého sizeru do šířky);
  `wx.LEFT | wx.RIGHT | wx.TOP` = na kterých stranách je okraj;
  `wx.ALIGN_CENTER_VERTICAL` = zarovnat na střed výšky.
- **okraj** = kolik pixelů na těch stranách.

Příklad z `MainFrame.__init__` (`main_frame.py:88`):

```python
layout = wx.BoxSizer(wx.VERTICAL)
layout.Add(self._build_header(root), 0, wx.EXPAND)   # hlavička: jen svoje výška, celá šířka
layout.Add(divider(root), 0, wx.EXPAND)              # čára 1 px
for page in self.pages.values():
    layout.Add(page, 1, wx.EXPAND)                   # záložky: zbytek výšky
root.SetSizer(layout)
```

Sizer přeskakuje schované prvky, takže když jsou tři záložky schované, celý zbytek
výšky dostane ta jedna viditelná.

Další užitečné věci ze sizerů v našem kódu:
- `AddSpacer(12)` = prázdné místo 12 px (mezery mezi slidery v `sidebar.py`).
- `AddStretchSpacer()` = "pružina", která zabere všechno volné místo. V hlavičce
  (`main_frame.py:131`) odtlačí Open / Save / Play doprava.
- `SetMinSize((-1, 56))` = minimální velikost, `-1` znamená "v tomhle rozměru je mi to jedno".
- `Layout()` = "přepočítej rozložení teď". Volá se, když se něco změní za běhu
  (přepnutí záložky, Play se změní na Stop a má jinou šířku).

### Události a `Bind`

`Bind` říká: "až na tomhle prvku nastane tahle událost, zavolej tuhle funkci".

```python
self.Bind(wx.EVT_PAINT, self._on_paint)          # má se překreslit -> _on_paint
self.Bind(wx.EVT_LEFT_DOWN, self._on_down)       # stisk levého tlačítka myši
self.Bind(wx.EVT_MOTION, self._on_motion)        # pohyb myši
```

Navázaná funkce dostane jeden argument, objekt **události** (`event`), ze kterého se dá
zjistit podrobnosti: `event.GetX()` (kde je myš), `event.GetWheelRotation()` (kam se
točí kolečko), `event.GetKeyCode()` (jaká klávesa), `event.GetActive()` (získalo okno fokus?).

Když funkci argument nestojí za nic, používáme lambdu, která ho zahodí:
`self.Bind(wx.EVT_LEFT_UP, lambda e: self.on_click())`.

**`event.Skip()`**: znamená "já jsem s tím hotový, ale ať to zpracuje i někdo další
(nebo wx sám)". Je potřeba hlavně u událostí, kde wx má i vlastní chování. Příklad
`_on_close` (`main_frame.py:402`): bez `event.Skip()` na konci by se okno nezavřelo,
protože bychom zavření "spolkli". U `_on_editor_key` ve slideru se `Skip()` volá pro
všechny klávesy kromě Esc, aby normální písmena došla do textového políčka.

Události, které v naší části potkáš:

| Událost | Kdy přijde | Kde |
|---|---|---|
| `EVT_TIMER` | tikl časovač | `MainFrame._on_tick` |
| `EVT_PAINT` | prvek se má nakreslit | všechny kreslené prvky |
| `EVT_SIZE` | změnila se velikost | `GraphView` (překreslí se) |
| `EVT_LEFT_DOWN` / `EVT_LEFT_UP` | stisk / puštění levého tlačítka | slider, tlačítka |
| `EVT_LEFT_DCLICK` | dvojklik | slider (výchozí hodnota) |
| `EVT_MOTION` | pohyb myši | slider (tažení, kurzor) |
| `EVT_MOUSEWHEEL` | kolečko | slider |
| `EVT_ENTER_WINDOW` / `EVT_LEAVE_WINDOW` | myš vjela nad prvek / odjela | zvýraznění pod myší ("hot") |
| `EVT_MENU` | položka menu (i přes klávesovou zkratku) | Undo / Redo, menu Add block |
| `EVT_ACTIVATE` | okno získalo / ztratilo fokus | `MainFrame._on_activate` |
| `EVT_CLOSE` | okno se zavírá | `MainFrame._on_close` |
| `EVT_TEXT`, `EVT_TEXT_ENTER` | změna textu / Enter v políčku | `Sidebar.add_text`, slider |
| `EVT_KILL_FOCUS` | políčko ztratilo fokus | slider (potvrzení hodnoty) |
| `EVT_CHAR_HOOK` | klávesa, dřív než ji dostane políčko | slider (Esc) |
| `EVT_CHOICE` | výběr v rozbalovacím seznamu | `Sidebar.add_dropdown` |

### Kreslení: `EVT_PAINT`, DC, GraphicsContext, `Refresh`

Tohle je nejdůležitější věc celé kapitoly, protože skoro všechno v UI si kreslíme sami.

**Pravidlo č. 1: kreslí se jen uvnitř `EVT_PAINT`.** Operační systém si sám řekne, kdy se
má prvek nakreslit (poprvé, po odkrytí, po změně velikosti). Pošle `EVT_PAINT` a my
v obsluze nakreslíme celý prvek od nuly.

**Pravidlo č. 2: když chceme překreslit my, zavoláme `Refresh()`.** `Refresh()` nic
nekreslí, jen prvek označí "je potřeba překreslit". Systém pak co nejdřív pošle
`EVT_PAINT`. Výhoda: když se hodnota změní 5x během jednoho okamžiku, nakreslí se to
jednou. `Refresh(False)` = navíc nemazat předem pozadí (stejně ho přemalujeme celé).

Typická obsluha kreslení (zkrácený `Caption._on_paint`, `widgets.py:33`):

```python
def _on_paint(self, event):
    dc = wx.AutoBufferedPaintDC(self)                                    # 1. plátno
    dc.SetBackground(wx.Brush(self.GetParent().GetBackgroundColour()))  # 2. smazat pozadí
    dc.Clear()
    gc = wx.GraphicsContext.Create(dc)                                   # 3. lepší kreslení
    gc.SetFont(theme.font(self.size, bold=True), self.colour)            # 4. kreslit
    theme.draw_spaced(gc, self.text, 0, 2, self.spacing)
```

Co to znamená:

- **DC** (device context) = "plátno", na které se kreslí. `wx.PaintDC` je plátno přímo
  na obrazovce. **`AutoBufferedPaintDC`** kreslí nejdřív do obrázku v paměti a na
  obrazovku ho dá až hotový. Díky tomu nevidíš mezistav (smazané pozadí, napůl
  nakreslený slider), tedy **nebliká to**.
- `SetBackgroundStyle(wx.BG_STYLE_PAINT)` v konstruktoru říká wx: "pozadí si smažu
  sám v `_on_paint`, ty ho nemaž". Jinak by wx pozadí smazal zvlášť a blikalo by to.
  `AutoBufferedPaintDC` tohle nastavení vyžaduje.
- Pozadí mažeme barvou rodiče (`GetParent().GetBackgroundColour()`), takže prvek
  splyne s panelem pod sebou a vypadá "průhledně".
- **`GraphicsContext`** (gc) je nadstavba nad DC: umí vyhlazené hrany (antialiasing),
  zaoblené obdélníky, desetinné souřadnice, cesty (křivky), průhlednost. Obyčejný DC
  by kreslil zubaté čáry.
- **Pen** = čím se kreslí obrys (barva, tloušťka), **Brush** = čím se vyplňuje.
  `wx.TRANSPARENT_PEN` = žádný obrys, `wx.TRANSPARENT_BRUSH` = žádná výplň.
- Souřadnice: `(0, 0)` je **levý horní roh** prvku, x roste doprava, **y roste dolů**.
  Proto se v osciloskopu odečítá: `py = mid - hodnota * scale` (kladná hodnota = nahoru).
- Proč se často kreslí od `0.5`: čára široká 1 px nakreslená na celé souřadnici leží
  na hranici dvou pixelů a vyhlazování ji rozmaže do dvou šedých. Posun o půl pixelu
  ji dá přesně doprostřed jednoho pixelu, takže je ostrá.

**Cesty** (`gc.CreatePath()`): posloupnost bodů a oblouků. `MoveToPoint` = přesuň pero
bez kreslení, `AddLineToPoint` = čára k bodu, `AddArc` = oblouk. Pak `gc.StrokePath(path)`
= obtáhni čarou, `gc.FillPath(path)` = vyplň. Takhle se kreslí křivka osciloskopu,
spektra i šipky Undo / Redo.

### Časovač `wx.Timer`

Časovač je budík, který každých N milisekund pošle událost `EVT_TIMER`.
V `MainFrame.__init__` (`main_frame.py:104`):

```python
self.timer = wx.Timer(self)
self.Bind(wx.EVT_TIMER, self._on_tick, self.timer)
self.timer.Start(int(1000 / FPS))      # FPS = 30 -> každých 33 ms
```

`_on_tick` je tedy "srdce" UI, volá se 30x za sekundu. Časovač běží ve stejné hlavní
smyčce jako všechno ostatní (není to vlákno), takže v něm můžeme bez obav sahat na prvky
okna. Není ale úplně přesný (když je smyčka zrovna zaneprázdněná, tik se opozdí), proto
se měří skutečný uplynulý čas `dt` přes `time.monotonic()`.

### Myš: capture

Když táhneš slider a myš ujede mimo něj (třeba nahoru nad jiný prvek), normálně by
události pohybu dostával ten jiný prvek a tažení by se zaseklo. `CaptureMouse()` říká
"všechny události myši posílej mně, dokud ji nepustím". Při puštění tlačítka
(`EVT_LEFT_UP`) se volá `ReleaseMouse()`. Capture se musí vždycky pustit, jinak by
slider "držel" myš dál.

### Klávesnice: fokus a zkratky

**Fokus** = který prvek právě dostává klávesy. Typicky textové políčko, do kterého se
píše. `SetFocus()` ho prvku dá, `EVT_KILL_FOCUS` přijde, když ho prvek ztratí.

V Sirens jsou dvě cesty, kudy jdou klávesy:

1. **Hraní na klávesnici** (`keys.py`, kapitola 50) chytá stisky **filtrem událostí**,
   který vidí každou klávesu v celé aplikaci dřív než prvky. Proto naše kreslené
   prvky nemusí řešit fokus. Výjimka: textová políčka (`wx.TextCtrl`) a stisky
   s Cmd / Ctrl filtr pouští dál.
2. **Klávesové zkratky menu** (accelerators): v názvu položky menu je za tabulátorem
   zkratka, `"Undo\tCtrl+Z"`. wx ji hlídá sám a při stisku pošle `EVT_MENU`, jako
   by se kliklo v menu. Na macOS wx `Ctrl` sám přeloží na `Cmd`. Druhá zkratka pro
   Redo se přidá přes `AddExtraAccel` (`main_frame.py:150`). Klávesa Z je zároveň nota,
   ale protože filtr stisky s Cmd/Ctrl propouští, Cmd+Z dojde až do menu.

`EVT_ACTIVATE` (`main_frame.py:395`): když přepneš do jiné aplikace, okno ztratí fokus
a puštění klávesy už k nám nedojde. Kdybychom nic neudělali, nota by zněla donekonečna.
Proto `_on_activate` zavolá `self.keys.focus_lost()`.

### `wx.CallAfter`

`wx.CallAfter(funkce)` = "zavolej tuhle funkci, až dokončíš událost, kterou teď zpracováváš".
Potřebujeme to, když by obsluha události **zrušila prvek, ze kterého událost přišla**.
Například kliknutí na Remove: tlačítko Remove leží v panelu, který se kvůli tomu celý
smaže a postaví znovu. Kdyby se smazal uprostřed obsluhy vlastního kliknutí, wx by
spadl. Proto `StackEditor._later` (`stack_editor.py:47`) a `Slider._finish_edit`
(`slider.py:186`, `wx.CallAfter(editor.Destroy)`).

### Dialogy

`wx.FileDialog`, `wx.MessageDialog`, `wx.MessageBox` jsou hotová okna systému.
`ShowModal()` dialog ukáže a **čeká**, dokud ho uživatel nezavře, a vrátí, na co klikl
(`wx.ID_OK`, `wx.ID_CANCEL`, `wx.ID_YES`). Konstrukce `with wx.FileDialog(...) as dialog:`
zajistí, že se dialog po použití zruší.

---

## Jak to spolu souvisí

```
__main__.py
  wx.App ---> MainLoop (čeká na události)
  MainFrame (main_frame.py)
   |-- song, player, keys (KeyboardPlayer), history, export
   |-- root (wx.Panel)
   |    |-- hlavička: Caption "SIRENS", ArrowButton x2, PillButton (záložky, Open, Save, Play)
   |    |-- divider
   |    |-- SoundPage  --+-- ScopeView, SpectrumView, StatusPill, PianoView   (viewport)
   |    |                +-- Sidebar --+-- fixed: Caption, Slider "Master", ChoiceRow "Keys"
   |    |                |             +-- scroll: Caption, wx.Choice, wx.TextCtrl,
   |    |                |                          Slider..., ChoiceRow..., TextButton..., PillButton
   |    |                +-- StackEditor (plní Sidebar bloky z racku)
   |    |-- SongPage   --+-- pattern / timeline views + Sidebar
   |    |-- VisualPage --+-- VisualView + Sidebar + StackEditor (vrstvy)
   |    |-- LightPage  --+-- LightView, StatusPill + Sidebar
   |-- menu Edit (Undo, Redo)
   |-- wx.Timer 30x/s
          |
          v
     _on_tick (každých 33 ms)
       |-- každý 10. tik: _snapshot -> history.record (Undo)
       |                    \-- každý 60. tik: _autosave -> ~/.sirens/autosave.json
       |-- běží export? -> _export_tick
       |-- analyzer.update()  (nový úsek zvuku?)
       |-- viditelná záložka .tick(...) -> view.show(data) -> Refresh() -> EVT_PAINT -> draw
       \-- light_page.tick (vždycky, světlo svítí pořád)

Uživatel táhne slider:
  EVT_LEFT_DOWN / EVT_MOTION -> Slider._set_from_mouse -> set_value
     -> Refresh() (překreslit pruh)
     -> on_change(hodnota) -> owner.set("Cutoff", hodnota)  (blok zvuku / vrstva / světlo)
```

Důležitá myšlenka: **UI prvky nevědí nic o zvuku.** Slider jen zavolá funkci `on_change`,
kterou mu někdo dal. Sidebar jen projde seznam `PARAMS` a pro každý udělá slider.
Co se se hodnotou stane, řeší objekt, kterému patří (blok, vrstva, světlo). Tomu se
říká oddělení zobrazení od logiky a je to dobrý argument u otázky na architekturu.

---

## Soubor po souboru

### `sirens/ui/main_frame.py`: hlavní okno

#### Konstanty (`main_frame.py:44`)

- `FPS = 30`: kolikrát za sekundu tiká časovač. 30 snímků stačí na plynulý pohyb
  grafů a nezatíží procesor.
- `SNAPSHOT_EVERY = 10`: každý 10. tik (1/3 s) se zachytí stav pro Undo.
- `AUTOSAVE_EVERY = 2 * FPS`: každý 60. tik (2 s) autosave. Musí to být násobek 10,
  protože autosave se kontroluje uvnitř `_snapshot`, který se volá jen každý 10. tik.
- `SAVE_FOLDER`: složka `assets/` v kořeni projektu. `Path(__file__).resolve().parents[2]`:
  `__file__` je cesta k `main_frame.py`, `parents[0]` je `ui/`, `[1]` je `sirens/`,
  `[2]` je kořen.
- `FILE_TYPES`, `WAV_TYPES`: filtr do dialogu ve formátu `"popisek|maska"`.

#### `__init__` (`main_frame.py:54`)

Postupně:
1. Okno 1280 x 820, minimum 1000 x 680 (menší by se nevešel panel se slidery).
2. Vytvoří píseň s jednou stopou, přehrávač, hraní na klávesnici (mezerník = Play / Stop),
   pustí výstupy všech stop do enginu.
3. `root` panel a v něm všechny čtyři záložky. Záložky dostávají **funkce** z okna jako
   argumenty (`self.select_track`, `self._tracks_changed`, `self._export_wav`), takže
   když uživatel v záložce vybere stopu, záložka zavolá okno a okno to rozešle všem.
   Záložky o sobě navzájem nevědí.
4. Sizer: hlavička, čára, záložky.
5. Menu, načtení autosave, první záznam do historie (výchozí stav pro Undo), výběr
   záložky Sound.
6. Časovač a navázání `EVT_ACTIVATE` a `EVT_CLOSE`.

#### Hlavička: `_build_header` (`main_frame.py:110`)

Vodorovný sizer: logo, šipky, čtyři záložky, pružina, Open, Save, Play. Zajímavý je jeden řádek:

```python
self.tabs[name] = PillButton(header, name, lambda n=name: self._select_tab(n))
```

Proč `n=name` a ne jen `lambda: self._select_tab(name)`? Lambda si nepamatuje **hodnotu**
proměnné, ale **proměnnou samotnou**. Až by se na tlačítko kliklo, cyklus by byl dávno
hotový a `name` by bylo `"Light"`, takže všechna čtyři tlačítka by přepínala na Light.
Výchozí hodnota parametru (`n=name`) se ale vyhodnotí hned při vytvoření lambdy, takže
každá lambda dostane svoji kopii. Stejný trik je v `sidebar.py:114` a `stack_editor.py`.

#### Menu: `_build_menu` (`main_frame.py:139`)

Menu Edit s Undo (`Ctrl+Z`) a Redo (`Ctrl+Shift+Z`, navíc `Ctrl+Y`). `Bind(wx.EVT_MENU, ...,
self.undo_item)`: třetí argument říká, že se to týká jen téhle položky.

#### Přepínání záložek: `_select_tab` (`main_frame.py:159`)

```python
for tab_name, page in self.pages.items():
    page.Show(tab_name == name)                      # vybraná se ukáže, ostatní schovají
    self.tabs[tab_name].set_primary(tab_name == name)  # vybraná záložka má bílé tlačítko
page.GetParent().Layout()
```

`Layout()` přepočítá sizer, aby nově ukázaná záložka dostala místo. `page` je po cyklu
poslední záložka, ale všechny mají stejného rodiče (`root`), takže je to jedno.

#### Stopy: `select_track`, `_tracks_changed` (`main_frame.py:170`)

Okno hlídá, aby Sound i Song měly vybranou stejnou stopu, a přepne klávesnici na kanál
nástroje té stopy. Po přidání / smazání stopy pošle enginu nový mix výstupů.

#### Přehrávání a export (`main_frame.py:183` až `:243`)

- `_toggle_playing`: Play / Stop. Když běží export, Stop (i mezerník) export zruší.
- `_show_playing`: text tlačítka Play / Stop podle stavu.
- `_export_wav`: zkontroluje, že na časové ose něco je, zeptá se na soubor (`FileDialog`)
  a spustí `start_export`. Ten pustí držené klávesy (jinak by se nahrály) a vytvoří
  `Export` (kapitola 20).
- `_export_tick`: volá se každý tik, ukazuje průběh v záložce Song; po dokončení `export = None`.
- Během exportu nejde Undo, Redo ani Open (`self.export is not None` -> `return`),
  aby se píseň uprostřed nahrávání nezměnila.

#### Ukládání (`main_frame.py:245` až `:293`)

- `_capture`: celý stav jako slovník (`session.capture`, kapitola 20).
- `_apply`: zastaví přehrávač, obnoví stav, znovu zapojí výstupy, překreslí panely,
  vybere první stopu.
- `_load_autosave`: při startu načte `~/.sirens/autosave.json`. Když je poškozený,
  začne s prázdnou písní (`_apply({})`) místo pádu.
- `_autosave`: zapíše jen tehdy, když se text liší od minula (`last_saved`).
- `_save`, `_open`: dialogy. Chyba při otevírání = hláška, ne pád.

#### Undo / Redo (`main_frame.py:295` až `:373`)

`_snapshot` (`main_frame.py:295`) se volá každou 1/3 s:

```python
mouse = wx.GetMouseState()
if not (mouse.LeftIsDown() or mouse.RightIsDown() or mouse.MiddleIsDown()):
    self.history.record(json.dumps(data), change_key(data))
```

Trik: dokud držíš tlačítko myši (táhneš slider, notu), stav se do historie nezapisuje.
Zapíše se až po puštění, takže **celé tažení = jeden krok Undo**, ne desítky malých.

`_go_to` obnoví stav z historie. Protože `_apply` vyrobí všechny objekty znovu, nejde si
pamatovat "vybraný objekt", pamatuje se **pořadí** vybrané stopy a ukázané automatizace
(`_lane_place`, `_show_lane`). Pokud se hrálo, přehrávání pokračuje od `player.tick`.

`_update_menu` zapne / vypne položky menu a šipky podle toho, jestli je co vracet.

#### Hlavní smyčka: `_on_tick` (`main_frame.py:375`)

```python
now = time.monotonic()
dt, self.last_time = now - self.last_time, now
self.ticks += 1
if self.ticks % SNAPSHOT_EVERY == 0:
    self._snapshot()
if self.export is not None:
    self._export_tick()
analyzer = self.engine.analyzer
fresh = analyzer.update()
if self.sound_page.IsShown():
    self.sound_page.tick(analyzer, fresh)
...
self.light_page.tick(analyzer)
```

- `dt` = skutečně uplynulý čas, potřebuje ho obraz (pohyb nezávislý na zpoždění časovače).
- `fresh` = jestli analyzer má nový úsek zvuku; grafy se mění jen tehdy.
- Kreslí se **jen viditelná záložka** (`IsShown()`), ať se zbytečně nepálí procesor.
  Výjimka: Visual běží i z jiné záložky, když je otevřený fullscreen (projektor).
  Světlo běží vždycky, svítí, ať se díváš kamkoli.

#### Zavření: `_on_close` (`main_frame.py:402`)

Pořadí je důležité: zastavit časovač (ať netiká do napůl zrušených věcí), uložit autosave,
dopsat rozdělaný export (dřív než se zastaví zvukový server), zavřít přehrávač,
klávesnici, fullscreen okno, světlo, engine. Nakonec `event.Skip()`, teprve to okno
opravdu zavře.

---

### `sirens/ui/theme.py`: barvy a písmo

Jedno místo pro všechny barvy (`wx.Colour(r, g, b)`, každá složka 0 až 255). Vzhled je
podle aplikace Event Horizon a nástroje Flip: skoro černá, bílá jen jako zvýraznění,
tenké světlé okraje, korálová (`ERROR`) jen pro chyby. Když chceš změnit vzhled celé
aplikace, měníš jen tenhle soubor.

`font(size, bold)` (`theme.py:28`): macOS počítá 1 bod písma = 1 pixel, Windows a Linux
1 bod = 96/72 pixelu. Stejná velikost by tam dala o třetinu větší text a nevešel by se do
sliderů, které mají výšku v pixelech. Proto se mimo macOS velikost násobí `72 / 96`.

`draw_spaced` (`theme.py:42`): wx neumí rozestupy mezi písmeny, tak se text kreslí znak po
znaku a za každým se posune o šířku znaku (`GetTextExtent`) plus `spacing`. Používá se
pro nadpisy "SCOPE", "OUTPUT" a logo.

---

### `sirens/ui/slider.py`: vlastní slider

Tohle je nejdůležitější prvek celého UI, na každý zvukový parametr je jeden.

#### Jak vypadá a z čeho se skládá

```
|<------------------- šířka prvku (w) ------------------->|
[ Cutoff ███████████░░░░░░░░░░ ] GAP [  1200  ]  Hz
|<------- pruh (bar) -------->|  6px |<- 64 ->|<-26->|
```

- `_bar_rect` (`slider.py:104`): pruh zabere všechno, co zbyde po rámečku s číslem,
  mezeře a jednotce: šířka `w - 64 - 26 - 6`, ale aspoň 10 px. V panelu širokém 340 px
  je slider široký asi 308 px, takže pruh má asi 210 px.
- `_box_rect` (`slider.py:108`): rámeček s číslem hned za pruhem.
- `_in_box(x)`: je myš v rámečku (nebo za ním)? Podle toho se rozhoduje, jestli klik
  nastavuje hodnotu, nebo otevírá psaní.

Rozměry se počítají při každém použití znovu z `GetClientSize()`, protože se okno dá
roztáhnout.

#### Stav slideru (`__init__`, `slider.py:45`)

`label, lo, hi, default, unit, log, step, on_change, value`, k tomu `hot` (je nad ním myš)
a `editor` (textové políčko, když se zrovna píše). Logaritmický slider s `lo <= 0` je chyba
(logaritmus nuly neexistuje), tak se hned vyhodí `ValueError` s jasnou hláškou.

#### Převod hodnota <-> poloha (`slider.py:79`)

Slider uvnitř pracuje s **polohou** od 0 (úplně vlevo) do 1 (úplně vpravo).

Lineárně:

```python
pos   = (value - lo) / (hi - lo)       # _to_pos
value = lo + pos * (hi - lo)           # _from_pos
```

Příklad: Master 0..1, hodnota 0.5 -> poloha 0.5 -> půlka pruhu.

Logaritmicky (`log=True`, frekvence a časy):

```python
pos   = log(value / lo) / log(hi / lo)     # _to_pos
value = lo * (hi / lo) ** pos              # _from_pos
```

Proč? Výšku tónu slyšíme v **poměrech**: 100 -> 200 Hz zní jako stejně velký skok jako
1000 -> 2000 Hz (obojí o oktávu). Na logaritmickém pruhu má každý stejný poměr stejnou
délku: 20 -> 200 Hz je stejně dlouhý kus jako 200 -> 2000 Hz.

Příklad: Cutoff filtru, 20 až 20000 Hz.
- Myš v půlce pruhu (pos = 0.5): `20 * 1000 ** 0.5 = 20 * 31.6 = 632 Hz`.
  Lineárně by to bylo 10010 Hz a celé "zajímavé" pásmo pod 1000 Hz by se namačkalo
  do prvních 5 % pruhu.
- Hodnota 1200 Hz: `log(60) / log(1000) = 4.09 / 6.91 = 0.59`, výplň sahá do 59 % pruhu.

`_from_pos` nejdřív ořízne polohu do 0..1 (`min(1.0, max(0.0, pos))`), protože myš při
tažení může být i mimo pruh.

#### Nastavení hodnoty: `set_value` (`slider.py:91`)

Sem vede všechno: myš, kolečko, dvojklik i napsané číslo.

```python
if self.step:
    value = self.lo + round((value - self.lo) / self.step) * self.step
self.value = min(self.hi, max(self.lo, value))
self.Refresh()
if self.on_change:
    self.on_change(self.value)
```

1. **Krok** (`step > 0`): hodnota se zaokrouhlí na nejbližší násobek kroku počítaný
   od `lo`. Příklad: délka písně 4..512 taktů, krok 4, myš ukazuje 33.7:
   `(33.7 - 4) / 4 = 7.4`, zaokrouhleno 7, `4 + 7 * 4 = 32`.
2. Ořízne se do rozsahu `lo..hi`.
3. `Refresh()` = překreslit.
4. Zavolá `on_change`, to je funkce od toho, kdo slider vyrobil
   (např. `lambda v: owner.set("Cutoff", v)`).

#### Myš

- `_on_down` (`slider.py:126`): klik do rámečku -> `_start_edit` (psaní). Klik do pruhu
  -> `_set_from_mouse` a `CaptureMouse()` (tažení může pokračovat i mimo slider).
- `_set_from_mouse` (`slider.py:121`): **tady se z x myši stane hodnota**:
  ```python
  bx, _, bw, _ = self._bar_rect()
  self.set_value(self._from_pos((x - bx) / bw))
  ```
  `x` je vzdálenost myši od levého kraje slideru v pixelech. `(x - bx) / bw` je, jakou
  část pruhu to je (0 až 1). `_from_pos` z toho udělá hodnotu (lineárně nebo
  logaritmicky), `set_value` ji zaokrouhlí na krok, ořízne a ohlásí.
  Příklad: pruh 200 px, myš na x = 50 -> poloha 0.25 -> u Master 0..1 hodnota 0.25.
- `_on_motion` (`slider.py:139`): mění kurzor (nad pruhem šipky doleva-doprava, nad
  číslem textový kurzor) a když se táhne (`event.Dragging()`) a slider má capture,
  nastaví hodnotu. Capture je jen tehdy, když stisk začal v pruhu.
- `_on_up` (`slider.py:135`): pustí capture.
- `_on_wheel` (`slider.py:145`): kolečko posune **polohu** o 1 % (`± 0.01`), ne hodnotu.
  U logaritmického slideru je tedy i krok kolečka "logaritmický".
- `_on_double_click` (`slider.py:150`): dvojklik do pruhu vrátí `default`.
- `EVT_ENTER_WINDOW` / `EVT_LEAVE_WINDOW`: nastaví `hot`, výplň se pod myší trochu zesvětlí.

#### Psaní přesné hodnoty

`_start_edit` (`slider.py:157`) položí přes rámeček skutečné textové políčko
`wx.TextCtrl` (dítě slideru), předvyplní ho aktuálním číslem, označí text a dá mu fokus,
takže se dá hned psát.

- Enter (`EVT_TEXT_ENTER`, díky stylu `TE_PROCESS_ENTER`) -> potvrdit.
- Kliknutí jinam (`EVT_KILL_FOCUS`) -> taky potvrdit.
- Esc (`EVT_CHAR_HOOK`, který vidí klávesu dřív než políčko) -> zrušit.

`_finish_edit` (`slider.py:181`):
- Enter i ztráta fokusu přijdou oba, proto se nejdřív `self.editor` nastaví na `None`
  a druhé volání hned skončí.
- Čárka se nahradí tečkou, takže jde napsat i `0,5`.
- Políčko se zruší přes `wx.CallAfter`, protože prvek nejde zrušit uvnitř jeho vlastní
  události.
- Nesmysl (`float("abc")` -> `ValueError`) se ignoruje, hodnota zůstane.
- Napsaná hodnota jde přes `set_value`, takže se taky ořízne do rozsahu a na krok.

Hraní na klávesnici napsání čísla nepřekáží, protože filtr kláves (`keys.py`) stisky
v `wx.TextCtrl` pouští dál.

#### Kreslení: `_on_paint` (`slider.py:197`)

1. Plátno, pozadí barvou rodiče, `GraphicsContext`.
2. Celá dráha pruhu (`SLIDER_TRACK`, zaoblený obdélník).
3. Výplň: `fill = bw * self._to_pos(self.value)` pixelů, tedy hodnota převedená na polohu
   a vynásobená šířkou pruhu. Zaoblení výplně je nejvýš polovina její šířky (jinak by
   se úzká výplň rozbila). Pravý okraj výplně se dokreslí rovným obdélníkem, aby výplň
   končila rovně, ne kulatě (jen když je výplň dost široká a nesahá až na konec).
4. Popisek uvnitř pruhu, svisle na střed (`(bh - th) / 2`, kde `th` je výška textu).
5. Rámeček s číslem a číslo zarovnané doprava. Když se zrovna píše, číslo nekreslíme
   (kreslí ho políčko).
6. Jednotka šedě za rámečkem.

#### `format_value` (`slider.py:29`)

Kolik desetinných míst ukázat: celočíselný krok -> 0 míst; jinak podle šířky rozsahu:
rozsah aspoň 200 (Hz) -> 0 míst, aspoň 20 -> 1, aspoň 1 -> 2, menší -> 3.
Takže 0..20000 Hz ukáže `1200`, 0..1 ukáže `0.50`.

---

### `sirens/ui/widgets.py`: malé kreslené prvky

Proč ne `wx.Button`? Nativní tlačítko na macOS nedovolí změnit barvu ani tvar, takže by
v tmavém okně svítilo systémové tlačítko. Všechny prvky tady jedou podle stejného receptu:
dědí z `wx.Control`, mají `BG_STYLE_PAINT`, kreslí se v `_on_paint` přes
`AutoBufferedPaintDC` a `GraphicsContext`, a po změně stavu volají `Refresh()`.

- **`Caption`** (`widgets.py:22`): nadpis velkými písmeny s rozestupem (`draw_spaced`).
- **`PillButton`** (`widgets.py:42`): zaoblené tlačítko. `primary=True` = bílé s černým
  textem (Play, vybraná záložka), jinak jen obrys. Klik = `EVT_LEFT_UP` (puštění tlačítka
  myši) zavolá `on_click`. `set_label` změní text a přepočítá šířku (text + 32 px, aspoň
  72 px). `set_primary` přepíná vzhled u záložek. Kurzor ručička (`CURSOR_HAND`).
- **`TextButton`** (`widgets.py:95`): jen text (Off, Remove...), pod myší zkorálovatí.
- **`ArrowButton`** (`widgets.py:125`): ikona Undo / Redo nakreslená cestou: čára, půlkruh
  (`AddArc`), hrot. Redo je stejný kód zrcadlově: `gc.Translate(SIZE, 0)` posune počátek
  na pravý okraj a `gc.Scale(-1, 1)` otočí osu x. `set_enabled` vypne prvek, když není
  co vracet; vypnutý prvek wx kliknutí vůbec nepošle, a prvek se nakreslí tmavě.
  Překresluje se jen při změně, protože se volá 3x za sekundu. Má tooltip
  (bublina se zkratkou).
- **`StatusPill`** (`widgets.py:186`): štítek pod grafy, `show(text, error)`. Při chybě
  korálový okraj a text.
- **`ChoiceRow`** (`widgets.py:215`): popisek a řada tlačítek, vybrané je právě jedno
  (Sine / Saw / Square, Loop / Song). Šířka za popiskem se rozdělí rovným dílem
  (`_option_rects`); při kliknutí se najde obdélník, ve kterém je x myši, a zavolá se
  `on_change(index)`.
- **`confirm`** (`widgets.py:267`): dialog před nevratnou akcí. Tlačítka se jmenují podle
  akce ("Remove" / "Cancel"), protože u "Yes / No" se na macOS snadno klikne na modré
  výchozí No. `wx.NO_DEFAULT` = výchozí je bezpečná volba.

---

### `sirens/ui/sidebar.py`: pravý panel

`Sidebar` (`sidebar.py:45`) je `wx.Panel` široký 340 px (`WIDTH`) se svislým sizerem.
Má dvě části:

- **pevná** (`fixed`, jen když `with_fixed=True`): nahoře, neposouvá se a nemaže se
  při `clear()`. Na Sound je tam Master a Keys, na Visual tlačítko Fullscreen.
- **posuvná** (`scroll`): `wx.ScrolledWindow` = panel s posuvníkem, když se obsah
  nevejde. `SetScrollRate(0, 12)` = vodorovně neposouvat, svisle po 12 px.

`_area(fixed)` (`sidebar.py:72`) vrací dvojici (rodič, sizer) pro jednu z částí. Je to
důležité, protože **prvek musí mít za rodiče ten panel, do jehož sizeru se přidává**.

Metody na stavění panelu (všechny přidávají na konec, shora dolů):

| Metoda | Co přidá |
|---|---|
| `add_group(title, actions)` | čáru (pokud to není první skupina), nadpis a vpravo `TextButton`y |
| `add_slider(...)` | mezeru 12 px, `Slider`, pod ním šedé vysvětlení (`help`) |
| `add_params(owner)` | pro každý `Param` z `owner.PARAMS` slider nebo `ChoiceRow` |
| `add_choice(...)` | `ChoiceRow` |
| `add_button(...)` | `PillButton` |
| `add_text(...)` | popisek + `wx.TextCtrl` (název stopy, IP adresa) |
| `add_dropdown(...)` | popisek + `wx.Choice` (rozbalovací seznam) |
| `add_note(text)` / `set_note` | volný text, jde později změnit |

`add_params` (`sidebar.py:105`) je klíčová:

```python
for p in owner.PARAMS:
    on_change = lambda v, label=p.label: owner.set(label, v)
    if p.choices:
        self.add_choice(p.label, p.choices, round(owner.get(p.label)), on_change, p.help, fixed)
    else:
        self.add_slider(p.label, p.lo, p.hi, p.default, p.unit, p.log, p.help,
                        on_change=on_change, value=owner.get(p.label), fixed=fixed, step=p.step)
```

Blok zvuku, vrstva obrazu i světlo mají seznam `PARAMS` (popisy sliderů, `sirens/param.py`)
a metody `get` / `set`. Panel tedy **nemusí vědět, co je Cutoff nebo Attack**; jen projde
seznam a pro každý parametr udělá slider s aktuální hodnotou (`owner.get`). Pohyb slideru
zavolá `owner.set(popisek, hodnota)`. Nový druh bloku = jen nový seznam `PARAMS`, UI se
nemění.

Překreslení panelu: záložky panel nemění po kouscích, ale **celý ho smažou a postaví
znovu**: `clear()` (`sidebar.py:194`, `Clear(delete_windows=True)` = vyndat prvky ze sizeru
a zároveň je zrušit), pak `add_...` a nakonec `finish()` (`sidebar.py:199`), který přepočítá
rozložení a `FitInside()` řekne posuvníku, jak vysoký je teď obsah. Je to jednodušší než
hlídat, který slider přidat nebo odebrat.

`divider` (`sidebar.py:34`): tenká čára je prostě panel 1 px vysoký (nebo široký) v barvě
okraje; druhý rozměr dopočítá sizer díky `wx.EXPAND`.

Pozn.: `wx.Choice` a `wx.TextCtrl` v panelu jsou **nativní** wx prvky, tady by vlastní
kreslení byla zbytečná práce.

---

### `sirens/ui/stack_editor.py`: seznam bloků / vrstev v panelu

`StackEditor` (`stack_editor.py:14`) není wx prvek, je to pomocník, který plní `Sidebar`.
Používá ho záložka Sound (bloky nástroje, "Add block") i Visual (vrstvy obrazu,
"Add layer"), takže stejný kód obslouží zvuk i obraz.

`show(stack, empty_hint)` (`stack_editor.py:27`): pro každý prvek seznamu přidá skupinu
s nadpisem (`Oscillator`, nebo `Oscillator (off)`) a tlačítky Off/On, Up, Down, Remove
(u Sampleru navíc Load), případně poznámku (`item.note()`), a pak slidery přes
`add_params(item)`. Prázdný seznam = nápověda. Na konci tlačítko na přidání.

`_later` (`stack_editor.py:47`): změna seznamu (`stack.toggle`, `move`, `remove`, `add`)
se provede a panel se překreslí přes `wx.CallAfter`, tedy až po skončení kliknutí.
Tlačítko, na které se kliklo, je totiž v panelu, který se teď celý smaže.

`_show_menu` (`stack_editor.py:59`): vyskakovací menu (`wx.Menu`) se všemi druhy
z katalogu. Mezi zdroje a efekty (`IS_SOURCE`) dá oddělovač. `PopupMenu` ukáže menu pod
tlačítkem a čeká na výběr; po něm se menu ručně zruší (`menu.Destroy()`).

`_load_file` (`stack_editor.py:74`): dialog pro zvukový soubor do Sampleru. Chyba při
načítání = hláška (pyo hlásí nečitelný soubor různými výjimkami, proto `except Exception`).

---

### `sirens/ui/views.py`: osciloskop, spektrum, obraz, světlo

#### `GraphView` (`views.py:23`): společný rámeček

Všechny čtyři grafy mají stejný rámeček (zaoblený, nadpis vlevo nahoře, údaj vpravo
nahoře). Ten kreslí `GraphView._on_paint` a pak zavolá `self.draw(gc, x, y, w, h)`
s vnitřní plochou. `draw` v `GraphView` nedělá nic, **podtřídy ho přepíšou**. To je
dědičnost v praxi: rámeček je napsaný jednou, vnitřek čtyřikrát.

Data se do grafu dostanou přes `show(...)`, kterou volá záložka každý snímek. `show` si
data jen uloží, nastaví text vpravo nahoře a zavolá `Refresh(False)`. Kreslí se až
v `EVT_PAINT`. Na `EVT_SIZE` se graf překreslí celý.

#### `ScopeView` (`views.py:58`): osciloskop

Tvar vlny v čase. Svisle -1 až 1 (nula uprostřed, amplituda 1 = 90 % poloviny výšky),
vodorovně úsek vzorků. Mřížka: vodorovné čáry na ±0.5 a ±1, svislé každou milisekundu.
Křivka: vzorek číslo `i` z `n` má x úměrně pořadí `x + w * i / (n - 1)`, y =
`mid - hodnota * scale` (minus, protože y roste dolů). Hodnoty se ořízou na ±1.1, aby
křivka při přebuzení neutekla z rámečku. Údaj: špička v dB, délka úseku v ms a `CLIP`,
když se špička blíží 0 dB.

#### `SpectrumView` (`views.py:105`): spektrum

Vodorovně frekvence 20 Hz až 20 kHz **logaritmicky** (`_x_of`, stejný vzorec jako
logaritmický slider, jen vyjde rovnou pixel), svisle dB od 0 (nahoře) do -90 (dole).
Mřížka s popisky 100, 1k, 10k a -20 až -80 dB. Body pod 20 Hz (i koš 0 = stejnosměrná
složka, jejíž logaritmus by nešel spočítat) se vynechají. Křivka se nakreslí dvakrát:
jednou uzavřená dolů k ose a vyplněná skoro průhlednou bílou (alfa 18 z 255), podruhé
jako čára 1.5 px (`GraphicsPenInfo`, protože `wx.Pen` umí jen celé pixely).
Samotné spektrum počítá `analyzer.py` (vlastní DFT, kapitola 30), tady se jen kreslí.

#### `VisualView` (`views.py:169`)

Obraz z `Painter.render()` (pole výška x šířka x 3 čísla 0..255) převede na `wx.Bitmap`
(`FromBuffer`) a nakreslí ho zvětšený tak, aby se celý vešel a nezdeformoval:
`scale = min(w / bw, h / bh)` a vystředí ho.

#### `LightView` (`views.py:193`)

Kruh v barvě, kterou právě svítí světlo, a nahoře hodnoty R, G, B a DMX kanály, na které
se posílají (`address` až `address + 2`).

---

## Proč vlastní kreslené prvky a ne standardní `wx.Slider` / `wx.Button`

Na tohle se tě můžou zeptat, tak upřímně:

**Důvod je vzhled.** Aplikace má vypadat jako Event Horizon / Flip: tmavá, bílé
zvýraznění, slider jako pruh s popiskem uvnitř a číslem vedle. Nativní `wx.Button` na
macOS barvu ani tvar změnit nedovolí a `wx.Slider` vypadá na každém systému jinak
(systémový táhlo s kolečkem).

Vlastní slider má navíc věci, které by se u `wx.Slider` musely stejně dopsat:
- `wx.Slider` umí jen **celá čísla**. Na hodnoty jako 0.01 s nebo 0.5 by se musel nastavit
  rozsah třeba 0..1000 a přepočítávat.
- **Logaritmický průběh** `wx.Slider` neumí vůbec, přepočet `_to_pos` / `_from_pos` by byl
  potřeba tak jako tak.
- Políčko na zapsání přesné hodnoty, dvojklik na výchozí hodnotu, jednotka.

**Jednodušší alternativa:** `wx.Slider(parent, minValue=0, maxValue=1000)` + vedle
`wx.StaticText` s číslem, v obsluze `EVT_SLIDER` přepočet `slider.GetValue() / 1000` na
polohu 0..1 a dál přes stejný vzorec `_from_pos`. Místo `PillButton` obyčejný `wx.Button`,
místo `ChoiceRow` `wx.RadioBox` nebo `wx.ToggleButton`. Fungovalo by to stejně, jen by to
vypadalo jako systémová aplikace a na macOS by tlačítka v tmavém okně působila cize.

**Cena vlastních prvků:** víc kódu (kreslení, myš, capture, psaní hodnoty) a nejsou
přístupné pro čtečky obrazovky ani ovladatelné tabulátorem. Pro tenhle projekt je to
přijatelné.

---

## Na co se tě můžou zeptat

**1. Jak funguje hlavní smyčka wxPython?**
`wx.App().MainLoop()` pořád dokola čeká na události (klik, klávesa, časovač, překreslení)
a pro každou zavolá funkci navázanou přes `Bind`. Všechen kód UI běží v té jedné smyčce,
takže nic v ní nesmí trvat dlouho, jinak okno zamrzne.

**2. Co je `Bind` a `event.Skip()`?**
`Bind(událost, funkce)` napojí funkci na událost, např. `self.Bind(wx.EVT_TIMER,
self._on_tick, self.timer)`. `Skip()` řekne, že událost má zpracovat i někdo další / wx
sám; bez něj by třeba `EVT_CLOSE` okno nezavřel.

**3. Jak se kreslí slider? Co dělá `Refresh()`?**
V obsluze `EVT_PAINT` (`_on_paint`) přes `AutoBufferedPaintDC` a `GraphicsContext`:
dráha, výplň podle hodnoty, popisek, rámeček s číslem, jednotka. `Refresh()` nekreslí,
jen označí prvek k překreslení; wx pak pošle `EVT_PAINT`. Buffer v paměti zabraňuje blikání.

**4. Jak se z polohy myši stane hodnota a proč je některý slider logaritmický?**
`(x - bx) / bw` = jaká část pruhu (0..1), `_from_pos` z toho udělá hodnotu: lineárně
`lo + pos * (hi - lo)`, logaritmicky `lo * (hi / lo) ** pos`. Pak `set_value` zaokrouhlí
na krok a ořízne do rozsahu. Log se používá u frekvencí a časů, protože výšku tónu
slyšíme v poměrech: 20 -> 200 Hz má na pruhu stejnou délku jako 200 -> 2000 Hz.

**5. Co je sizer a co znamená `Add(prvek, 1, wx.EXPAND)`?**
Sizer počítá pozice a velikosti prvků. `1` = prvek dostane podíl volného místa (`0` = jen
svoje minimum), `wx.EXPAND` = roztáhne se i do druhého směru.

**6. Jak funguje časovač a co se děje v `_on_tick`?**
`wx.Timer` posílá `EVT_TIMER` každých 33 ms (30 fps). `_on_tick` změří `dt`, každou 1/3 s
zachytí stav pro Undo, každé 2 s autosave, posune export, aktualizuje analyzátor a nechá
překreslit jen viditelnou záložku (plus fullscreen obraz a světlo vždycky).

**7. Proč `lambda n=name: ...` v cyklu?**
Lambda si pamatuje proměnnou, ne hodnotu; po cyklu by všechny lambdy viděly poslední
hodnotu. Výchozí parametr se vyhodnotí hned, takže každá lambda má svoji.

**8. Proč `wx.CallAfter` v `StackEditor` a u políčka slideru?**
Prvek nejde zrušit uprostřed obsluhy jeho vlastní události. Kliknutí na Remove smaže
celý panel včetně tlačítka Remove, proto se změna provede až po dokončení kliknutí.

**9. Jak to, že tažení slideru je v Undo jen jeden krok?**
`_snapshot` se dívá přes `wx.GetMouseState()`, jestli je stisknuté tlačítko myši. Dokud ano,
do historie nic nezapíše. Zapíše až stav po puštění.

**10. Jak pravý panel ví, jaké slidery ukázat?**
Každý blok / vrstva / světlo má `PARAMS` (seznam `Param`) a `get` / `set`.
`Sidebar.add_params` pro každý parametr vyrobí slider a napojí ho na `owner.set`. Panel
o zvuku nic neví, takže nový blok nepotřebuje žádnou změnu UI.

**11. Proč tažení slideru pokračuje, i když myš ujede mimo něj?**
`CaptureMouse()` při stisku: všechny události myši chodí slideru, dokud se při puštění
nezavolá `ReleaseMouse()`.

---

## Kde se to napojuje

Kdo volá do souborů z této kapitoly:

| Kdo | Co používá |
|---|---|
| `sirens/__main__.py:12` | vytvoří `MainFrame(engine)` |
| `sirens/ui/sound_page.py` | `Sidebar` (s pevnou částí), `divider`, `StackEditor` ("Add block"), `ScopeView`, `SpectrumView`, `StatusPill`, `confirm` (Paste sound), `theme` |
| `sirens/ui/song_page.py` | `Sidebar`, `divider`, `confirm` (Remove track), `theme`; `add_slider` (Tempo, Song length), `add_choice`, `add_dropdown`, `add_note` / `set_note` (průběh exportu) |
| `sirens/ui/visual_page.py` | `Sidebar` (pevná část s Fullscreen), `divider`, `StackEditor` ("Add layer"), `VisualView`, `theme` |
| `sirens/ui/light_page.py` | `Sidebar`, `divider`, `LightView`, `StatusPill`, `theme`; `add_text` (IP adresa) |
| `sirens/ui/piano.py`, `pattern_view.py`, `timeline_view.py` | jen barvy a písmo z `theme` |
| `sirens/param.py` | definuje `Param` a `Adjustable`, které čte `Sidebar.add_params` |

Kam volá `MainFrame`:

| Kam | Proč |
|---|---|
| `sirens/song.py` (`Song`) | data písně |
| `sirens/audio/player.py` (`Player`) | Play / Stop, tempo, pozice |
| `sirens/ui/keys.py` (`KeyboardPlayer`) | hraní na klávesnici, mezerník, kanál vybrané stopy |
| `sirens/audio/engine.py` | `engine.play(outputs)`, `engine.analyzer`, `engine.close()` |
| `sirens/session.py` | `capture`, `restore`, `read`, `write`, `AUTOSAVE` |
| `sirens/history.py` | `History`, `change_key` (Undo / Redo) |
| `sirens/audio/export.py` (`Export`) | export WAV |
| všechny čtyři `*_page.py` | `tick`, `select_track`, `refresh`, `show_export`, `fullscreen` |
