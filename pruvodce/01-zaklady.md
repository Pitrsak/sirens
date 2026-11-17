# 01 — Základy: Python, pyo, wxPython, numpy a zvuk

Tahle kapitola je minimum, bez kterého se v kódu nedá číst. Je tu jen to, co Sirens
opravdu používá, a každý příklad je vzatý z našeho kódu. Ostatní kapitoly sem odkazují.

---

## 1. Python

### Soubor = modul, složka = balíček

Každý `.py` soubor je **modul**. Složka se soubory (`sirens/`, `sirens/audio/`) je **balíček**.
`import` si z jiného modulu vezme, co potřebuje:

```python
from sirens.audio.rack import Rack      # z souboru sirens/audio/rack.py vezmi třídu Rack
import wx                               # celá knihovna wx, používá se jako wx.Frame, wx.Timer...
```

`if __name__ == "__main__":` (na konci `main.py` a `sirens/__main__.py`) znamená
„tohle spusť, jen když soubor spouštím přímo, ne když ho jen někdo importuje“.

### Proměnné, typy, konstanty

```python
VOICES = 8            # celé číslo (int)
FADE_TIME = 0.05      # desetinné číslo (float)
name = "Track 1"      # text (str)
playing = False       # pravda / nepravda (bool)
current = None        # "nic", ještě nic není nastavené
```

Jména VELKÝMI PÍSMENY jsou **konstanty**: nastaví se jednou nahoře v souboru a nemění se.
Je to jen zvyk, Python je nehlídá.

Zápis `def _tick_time(self) -> float` obsahuje **typové nápovědy**
(`-> float`). Python je ignoruje, jsou jen pro čtenáře: „vrací desetinné číslo“.

### Seznam, slovník, množina, n-tice

```python
self.items = []                         # seznam (list): seřazené prvky, dají se měnit
self.patterns = {"A": Pattern(), ...}   # slovník (dict): klíč -> hodnota
self.active = set()                     # množina (set): bez pořadí, každý prvek jen jednou
BAR_CHOICES = (1, 2, 4)                 # n-tice (tuple): jako seznam, ale nejde měnit
```

**Comprehension** = krátký zápis cyklu, který vyrobí seznam nebo slovník:

```python
# pro každý parametr p: klíč = jeho popisek, hodnota = výchozí hodnota
self.settings = {p.label: p.default for p in self.PARAMS}
```

je totéž co:

```python
self.settings = {}
for p in self.PARAMS:
    self.settings[p.label] = p.default
```

### Užitečné drobnosti, na které narazíš

- `a // b` celočíselné dělení (`7 // 2 == 3`), `a % b` zbytek po dělení (`7 % 2 == 1`).
  `% ` se hodí na „dokola“: `tick % loop_ticks` vrátí tik zpátky na začátek smyčky.
- `divmod(a, b)` vrátí obojí naráz: `bar, tick_in_bar = divmod(tick, 48)`.
- `f"Track {n}"` je **f-string**: do textu se dosadí hodnota proměnné.
- `lambda n=name: self._select_tab(n)` je **malá funkce bez jména**. `n=name` je trik: lambda si
  zapamatuje hodnotu `name` ve chvíli vytvoření. Bez toho by všechna tlačítka v cyklu
  ukazovala na poslední záložku.
- `try: ... except Exception: ...` chytí chybu, aby program nespadl (např. v hodinách přehrávače).
- `x if podmínka else y` je **podmíněný výraz**: `Mix(flow, voices=1) if flow is not None else Sig(0)`
  = „když něco teče, sečti to, jinak ticho“.
- **Řezy (slicing):** `seznam[-1]` poslední prvek, `seznam[1:]` všechno kromě prvního,
  `seznam[-4:]` poslední čtyři. `(self.retired + [self.current])[-4:]` = přidej a nech jen 4 nejnovější.
- **Rozbalení:** `f(*seznam)` předá prvky seznamu jako jednotlivé argumenty (`Note(*[4, 60, 2])` = `Note(4, 60, 2)`),
  `{**slovnik, "x": 1}` vloží celý slovník do nového.
- `a, b = b, a` prohodí dvě hodnoty naráz.
- `slovnik.get("klíč", výchozí)` vrátí hodnotu, nebo výchozí, když klíč chybí (hodí se u starších uložených souborů).
- `setattr(obj, "attack", 0.1)` je totéž co `obj.attack = 0.1`, jen jméno atributu je v proměnné.
- `raise NotImplementedError` v metodě rodiče znamená „tohle musí každý potomek napsat po svém“
  (tak je udělané `Block.connect`).
- Třída se dá předat jako hodnota: `rack.add(FilterBlock)` dostane *druh* bloku a objekt si vytvoří sám.

### Funkce

```python
def lane_value(lane: dict, position: float):
    """Tohle je docstring: popis funkce v trojitých uvozovkách."""
    ...
    return hodnota
```

`def` vytvoří funkci, `return` vrátí výsledek. Parametr s `=` má výchozí hodnotu
(`def __init__(self, bars: int = 1)` → `Pattern()` je totéž co `Pattern(1)`).

### Třídy a objekty (tohle je důležité)

**Třída** je šablona, **objekt** je konkrétní věc podle šablony. `Track` je třída, každá
stopa v písni je jeden objekt třídy `Track`.

```python
class Track:
    def __init__(self, name: str, channel: int):   # konstruktor: volá se při Track("Bass", 2)
        self.name = name                            # self = ten konkrétní objekt
        self.instrument = Instrument(channel)       # každá stopa má vlastní nástroj
        self.muted = False

    def pattern_at_bar(self, bar: int):             # metoda = funkce patřící objektu
        ...

track = Track("Bass", 2)      # vytvoření objektu
track.muted = True            # změna jeho atributu
```

- `__init__` je **konstruktor**, nastaví objektu výchozí stav.
- `self` je odkaz na objekt, se kterým se zrovna pracuje. `self.name` = jméno *této* stopy.
- Metody se jménem začínajícím `_` (`_on_tick`, `_build_header`) jsou „vnitřní“: zvyk říká,
  že je volá jen třída sama, ne ostatní soubory.

### Dědičnost: `class Rack(Stack)`

Třída může **dědit** od jiné: dostane všechny její metody a může některé přepsat.

```python
class Stack:                    # sirens/stack.py: obecný seznam prvků pod sebou
    def add(self, item_class): ...
    def remove(self, item): ...
    def changed(self):
        pass                    # obecný Stack po změně nic nedělá

class Rack(Stack):              # sirens/audio/rack.py: rack bloků zvuku JE Stack
    def changed(self):          # přepsaná metoda: po změně znovu propojí bloky
        ...
```

`Rack` i `Painter` (vrstvy obrazu) dědí od `Stack`, takže přidávání, mazání a posouvání
je napsané jen jednou. Liší se jen tím, co udělají po změně.

Stejně tak všechny bloky zvuku dědí od `Block`, zdroje od `SourceBlock`, efekty od
`EffectBlock`. Každý konkrétní blok pak doplní jen to svoje.

`super().__init__()` zavolá konstruktor rodiče: „nejdřív udělej, co dělá Stack, pak já přidám svoje“.

**Atribut třídy** (napsaný přímo ve třídě, ne v `__init__`) mají všechny objekty společný:

```python
class OscillatorBlock(SourceBlock):
    NAME = "Oscillator"            # jméno pro UI, stejné pro všechny oscilátory
    PARAMS = [Param(...), ...]     # jaké slidery blok má
```

Pozor na rozdíl: atribut třídy platí, dokud objekt nedostane vlastní. `Block` má `enabled = True`
ve třídě; když `Stack.toggle` udělá `block.enabled = False`, vznikne atribut jen u toho jednoho bloku
a ostatní bloky mají dál `True` ze třídy.

`IS_SOURCE`, `NAME`, `PARAMS`, `POST`... jsou takové „vlastnosti druhu“, podle kterých
s blokem nebo vrstvou zachází zbytek programu, aniž by musel znát konkrétní třídu.
Tomu se říká **polymorfismus**: rack zavolá `block.connect(flow)` a je mu jedno, jestli je to
filtr nebo oscilátor, každý si to udělá po svém.

### Dekorátory `@property` a `@dataclass`

```python
class Rack(Stack):
    @property
    def blocks(self):
        return self.items
```

`@property` dovolí psát `rack.blocks` (bez závorek), jako by to byl atribut, i když je to metoda.
Tady je to jen hezčí jméno: v racku jsou „bloky“, ve Stacku obecně „items“.

```python
@dataclass
class Note:
    step: int
    pitch: int
    length: int
    velocity: int = 100
```

`@dataclass` je zkratka: Python sám vyrobí `__init__`, takže jde psát `Note(4, 60, 2)`
a dostaneš objekt s `note.step == 4`, `note.pitch == 60`... Hodí se na třídy, které jen nesou data.

### Vlákna (`threading`)

Normálně program dělá jednu věc po druhé. **Vlákno** je druhý „pracovník“, který běží
souběžně. `player.py` si pustí vlastní vlákno s hodinami, aby noty chodily přesně,
i když okno zrovna něco kreslí. Když dvě vlákna sahají na stejná data, je potřeba opatrnost
(proto v kódu uvidíš `list(pattern.notes)`: udělá se kopie seznamu, aby nevadilo,
že ho uživatel zrovna myší mění).

---

## 2. pyo — knihovna na zvuk

### Server

```python
self.server = Server(sr=44100, nchnls=2, buffersize=512, duplex=0)
self.server.boot()      # připojí se ke zvukové kartě
self.server.start()     # rozběhne zvukové vlákno
```

Server je „motor“: běží ve vlastním vlákně a pořád dokola počítá další kousek zvuku
(512 vzorků) ze všech pyo objektů, které existují. Pyo objekty jdou tvořit až po `boot()`.

### Pyo objekt = signál, ne číslo

```python
osc = Sine(freq=440)          # sinusovka 440 Hz: NE jedno číslo, ale proud vzorků
filtr = SVF(osc, freq=1000)   # filtr, který zpracovává výstup oscilátoru
filtr.out()                   # pošli to do reproduktorů
```

Každý pyo objekt je **signál**: proud čísel, 44 100 za sekundu. Python jen řekne,
co je s čím propojené. Jakmile objekt vznikne, server ho počítá. Parametry jako `freq=`
můžou být číslo i jiný signál (tak se dělá modulace).

Objekty, které Sirens používá nejčastěji:

| Objekt | Co dělá |
|---|---|
| `Sig(x)` | signál s konstantní hodnotou x |
| `SigTo(x, time=0.03)` | jako Sig, ale při změně hodnoty k ní plynule dojede (za 30 ms), takže slider necvaká |
| `Mix(seznam, voices=1)` | sečte víc signálů do jednoho |
| `InputFader(signal)` | „zásuvka“: vstup jde vyměnit za jiný s krátkým prolnutím (`setInput`) |
| `Notein`, `MidiAdsr` | přijímá MIDI noty, obálka noty (viz kapitola 10) |
| `Sine`, `Noise`, `SndTable` | zdroje zvuku |
| `SVF`, `Delay`, `Freeverb`, `Clip`, `Lookup` | úpravy zvuku |
| `DataTable`, `NewTable` | tabulka čísel v paměti (křivka, nahraný zvuk) |
| `TableRec` | nahrává signál do tabulky (pro analýzu) |

### Víc hlasů = víc proudů v jednom objektu

Když `Notein(poly=8)` umí hrát 8 not naráz, `notes["pitch"]` není jeden signál, ale **8 proudů**
(jeden na hlas). Oscilátor, který tenhle signál dostane jako `freq`, se taky sám rozdělí na 8 proudů.
Tak jeden blok hraje akord, aniž bychom psali cyklus.

### Počítání se signály: `*`, `+` a `mul=`

`a * b` dvou pyo signálů vyrobí nový signál (násobení vzorek po vzorku), `a + b` je sčítá.
Na hlasitost se ale v Sirens většinou používá parametr **`mul=`**, který má každý pyo objekt:
`Sine(freq=440, mul=0.5)` je sinus s poloviční amplitudou. Proč ne prostě `*`: pyo si výsledek
`a * b` uloží k objektu vlevo (`a`), a když `a` žije dlouho a `b` se zahodí, výsledek
by běžel dál a četl uvolněnou paměť. Podrobně v kapitole 10, „Tři pravidla proti pádům“.

`len(signal)` u pyo objektu = kolik má proudů (hlasů). `Mix(signal, voices=1)` je všechny sečte do jednoho.

### Objekt žije, dokud na něj něco ukazuje

Python objekt smaže (a pyo ho přestane počítat), jakmile na něj nevede žádná proměnná.
Proto kód ukládá věci do `self.něco`: kdyby oscilátor byl jen v lokální proměnné, po
skončení funkce by zmizel a zvuk s ním. Opačný problém (něco zmizí moc brzy, zatímco ho
zvukové vlákno ještě čte) způsoboval pády; kapitola 10 vysvětluje, jak se tomu kód brání
(`retired`, `keep()` u tabulek, `mul=` místo `*`).

### MIDI

MIDI je standard na posílání not. Zpráva „nota zapnuta“ má tři čísla:
**status** (0x90 + kanál), **číslo noty** (0–127, 60 = střední C) a **sílu** (velocity 0–127,
0 = puštění). Sirens posílá MIDI zprávy i sám sobě (`server.addMidiEvent`), takže klávesnice
počítače, sekvencer i skutečná MIDI klávesnice jdou do nástroje stejnou cestou.

---

## 3. wxPython — okna a ovládání

Podrobně v kapitole 40. Tady jen slovník:

| Pojem | Co to je |
|---|---|
| `wx.App` + `MainLoop()` | aplikace a nekonečná smyčka, která čeká na události (klik, klávesa, časovač) |
| `wx.Frame` | okno s titulkem (`MainFrame`) |
| `wx.Panel` | obdélník uvnitř okna, do kterého se dávají další prvky |
| **sizer** (`wx.BoxSizer`) | rozvržení: skládá prvky pod sebe nebo vedle sebe a řeší jejich velikost |
| **událost** + `Bind` | `self.Bind(wx.EVT_TIMER, self._on_tick, self.timer)` = „když tikne časovač, zavolej `_on_tick`“ |
| `wx.Timer` | budík, který volá funkci pravidelně (Sirens: 30x za sekundu) |
| `EVT_PAINT` + DC | když se má prvek nakreslit, wx zavolá funkci a dá jí „plátno“ (DC), na které se kreslí čáry, obdélníky, text |
| `Refresh()` | „překresli se“: wx brzy pošle EVT_PAINT |

Celé okno je **řízené událostmi**: program sám nic nedělá, jen reaguje. Proto je v kódu
tolik metod `_on_něco`.

---

## 4. numpy — počítání s poli čísel

numpy umí počítat s celými poli čísel naráz, bez psaní cyklu v Pythonu (a stokrát rychleji).

```python
import numpy as np
a = np.zeros(512)                 # 512 nul
b = a * 2 + 1                     # každý prvek krát 2 plus 1, naráz
obraz = np.zeros((360, 640, 3))   # obraz: výška x šířka x 3 barvy (Sirens kreslí v 640 x 360)
obraz[:, :, 0] = 1.0              # celý první barevný kanál na maximum
```

- **Obraz je pole čísel**: řádky × sloupce × 3 barvy. V Sirens se počítá s desetinnými čísly
  0..1 a až na konci se převede na 0..255 (8 bitů, `uint8`) pro zobrazení.
- **Zvuk je taky pole čísel**: vzorky mezi -1 a 1.
- `.shape` je rozměr pole, `.dtype` typ čísel (`float32`, `uint8`).
- `np.clip(x, 0, 1)` ořízne hodnoty do rozsahu.
- Obraz je v Sirens v pořadí **RGB** (kanál 0 = červená). Pozor, opencv jinak běžně používá BGR,
  ale tady se obraz nikdy nenačítá ani neukazuje přes opencv, takže je to všude konzistentně RGB.
- Souřadnice: pole se indexuje `[řádek, sloupec]` = `[y, x]` a osa y jde **dolů** (řádek 0 je nahoře).

### Vyhlazování („kus starého + kus nového“)

Na víc místech (analýza, obraz) uvidíš něco jako:

```python
# sirens/visual/features.py: průměr basů = 90 % starého + 10 % nového
self.bass_average = 0.9 * self.bass_average + 0.1 * self.bass
# podobný princip: beat po úderu hasne, každý snímek zůstane 85 % (BEAT_FALL)
self.beat *= BEAT_FALL
```

Hodnota se nepřepne hned na novou, ale každý snímek se k ní kousek přiblíží. Výsledek je plynulý
a nebliká. Čím větší první číslo, tím pomaleji reaguje. U beatu je to stejná myšlenka, jen bez
nového kusu: po úderu se každý snímek vynásobí 0,85, takže hodnota plynule klesá k nule
místo toho, aby zhasla naráz. Protože se to děje „za snímek“,
rychlost závisí na tom, kolik snímků za sekundu běží (Sirens: 30).

opencv (`cv2`) v Sirens kreslí do těchhle polí tvary (kruhy, čáry), rozmazává a podobně.
Detaily v kapitole 30.

---

## 5. Zvuk fyzikálně (bez hudební teorie)

- **Zvuk** je chvění vzduchu. V počítači je to řada čísel (**vzorků**), každé říká, kde je
  membrána reproduktoru v danou chvíli. Rozsah je -1 až 1; co je mimo, se ořízne a chrčí.
- **Vzorkovací frekvence** 44 100 Hz = 44 100 vzorků za sekundu.
- **Buffer** 512 vzorků = kousek, který server spočítá naráz (≈ 11,6 ms). Menší = menší zpoždění, ale větší zátěž.
- **Frekvence** (Hz) = kolikrát za sekundu se vlna zopakuje = **jak vysoko** tón zní.
  Dvojnásobná frekvence = o **oktávu** výš. 440 Hz je komorní A.
- **MIDI číslo noty**: 60 = střední C (≈ 261,6 Hz), +1 = o půltón výš, +12 = o oktávu výš.
  Převod na Hz: `f = 440 · 2^((n − 69) / 12)` (dělá ho pyo `Notein`).
- **Amplituda** = jak velké je chvění = **jak hlasitě**.
- **Tón vs. šum**: tón je pravidelná vlna (má výšku), šum jsou náhodná čísla (žádnou výšku nemá,
  zní jako „šššš“). Bicí se dělají hlavně ze šumu a krátkých tónů.
- **Tvar vlny** určuje **barvu** zvuku: sinus je čistý a měkký, pila (saw) ostrá a bzučivá,
  obdélník (square) dutý.
- **Spektrum** = rozklad zvuku na frekvence: kolik je v něm basů, středů, výšek.
  Počítá se Fourierovou transformací (DFT), viz kapitola 30.
- **dB (decibely)** = hlasitost v logaritmickém měřítku: -6 dB ≈ poloviční amplituda.
- **Obálka (ADSR)** = jak se hlasitost noty mění v čase: náběh, pokles, držení, doznění.
- **Tempo (BPM)** = počet dob za minutu. **Takt** = 4 doby. Při 120 BPM trvá takt 2 sekundy.
