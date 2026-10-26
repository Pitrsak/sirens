# 10 — Zvuk: engine, nástroj, rack, bloky

Tahle kapitola vysvětluje, jak v Sirens vzniká zvuk. Jsou to čtyři soubory:

| Soubor | Co v něm je |
|---|---|
| `sirens/audio/engine.py` | `AudioEngine`: pyo server, společný výstup do reproduktorů, posílání not |
| `sirens/audio/instrument.py` | `Instrument`: nástroj jedné stopy, přijímá noty, obálka ADSR, hlasitost |
| `sirens/audio/rack.py` | `Rack`: seznam bloků jednoho nástroje, propojuje je shora dolů |
| `sirens/audio/blocks.py` | všechny bloky: zdroje zvuku (Oscillator, Noise...) a efekty (Filter, Delay...) |

Je to jádro celé aplikace, takže to čti pomalu a měj otevřený kód vedle. Komentáře
v kódu a tahle kapitola se doplňují. Základy Pythonu a pyo jsou v [01-zaklady.md](01-zaklady.md),
tady se k nim vracím jen krátce, když na ně narazíme poprvé.

---

## Úvod: kde to v aplikaci uvidíš a uslyšíš

Všechno z téhle kapitoly ovládáš v záložce **Sound**:

- Vpravo v panelu je skupina **Output**: slider **Master** (to je `AudioEngine.set_volume`)
  a přepínač **Keys** (Play / Hold).
- Pod tím vybraná stopa a její nástroj: slidery **Attack, Decay, Sustain, Release, Volume**
  (to jsou `Instrument.PARAMS`).
- Pod nimi bloky racku, každý jako skupina sliderů s tlačítky **Off/On, Up, Down, Remove**
  (Sampler má navíc **Load**). Úplně dole tlačítko **Add block**, které otevře menu se všemi
  bloky (`CATALOG`), nahoře zdroje, pod čárou efekty.
- Vlevo pod spektrem je šedý pruh s cestou zvuku, např. `Oscillator + Noise -> Filter`.
  Ten text vyrábí `Rack.describe()`.
- Klávesami **A S D F G H J K L** (a W E T Y U O P) hraješ na nástroj vybrané stopy.

Když v záložce **Song** pustíš píseň, hraje se přes úplně stejné nástroje, jen noty
posílá přehrávač (`player.py`) místo tvých prstů.

Vyzkoušej si: nová stopa je prázdná (ticho). Dej **Add block → Oscillator**, zahraj A.
Pak **Add block → Filter**, stáhni **Cutoff** a hraj. Pak **Add block → Delay**. Při každém
kliknutí se v kódu zavolá `Rack.changed()` a celý řetězec se znovu propojí.

---

## Jak to spolu souvisí

```
  klávesnice počítače   sekvencer (player.py)   MIDI klávesnice
          \                    |                     /
           \-- engine.send_note()  -> server.addMidiEvent()
                               |
                    MIDI zpráva na kanál stopy (1..8)
                               |
   +---------------------- Instrument (jeden na stopu) -----------------------+
   |  Notein (8 hlasů) -> pitch (Hz), trigger (impuls při stisku), velocity   |
   |  MidiAdsr(velocity) -> envelope (obálka, 8 hlasů)                        |
   |                                                                          |
   |  Rack: bloky shora dolů (flow = co zrovna teče)                          |
   |    Oscillator   flow = zvuk oscilátoru                (8 hlasů)          |
   |    + Noise      flow = flow + šum                     (8 hlasů)          |
   |    -> Filter    flow = filtr(flow), každá nota zvlášť (8 hlasů)          |
   |    -> Delay     flow = ozvěna(součet hlasů)           (1 hlas)           |
   |                               |                                          |
   |  play(flow): Mix(flow, voices=1) -> [zásuvka InputFader] * Volume        |
   +--------------------------------|-----------------------------------------+
                                    | instrument.output (jeden kanál)
           výstupy všech stop ------+
                                    |
   +---------------------- AudioEngine (jeden na celou aplikaci) -------------+
   |  play(seznam výstupů): Mix(..., voices=1) -> [zásuvka InputFader]        |
   |        |                                       |                         |
   |        |                                       +-> Analyzer (scope,      |
   |        v                                           spektrum, obraz,      |
   |   * Master -> Clip(-1..1) -> Pan(2 kanály).out() -> reproduktory         |
   +--------------------------------------------------------------------------+
```

Tři věci, které si z obrázku odnes:

1. **Noty jsou vždycky MIDI zprávy.** Klávesnice, sekvencer i skutečná MIDI klávesnice
   jdou stejnou cestou, takže nástroj neví (a nezajímá ho), kdo hraje.
2. **Každý nástroj má 8 hlasů.** Až do prvního efektu, který hlasy sečte, je každá nota
   samostatný signál.
3. **Na dvou místech je „zásuvka“** (`InputFader`): v nástroji a v enginu. Díky ní jde
   za běhu vyměnit, co hraje, bez lupnutí.

---

## Soubor po souboru

### `sirens/audio/engine.py` — AudioEngine

Účel: nastartovat pyo, mít jeden pevný výstupní řetězec do reproduktorů a nabídnout pár
metod zbytku programu (`play`, `send_note`, `set_volume`, nahrávání, `close`).
Vytváří se jednou v `sirens/__main__.py`, ještě před oknem.

#### Server (`engine.py:22-31`)

```python
self.server = Server(sr=sample_rate, nchnls=2, buffersize=buffer_size, duplex=int(microphone))
self.server.setMidiInputDevice(99)
self.server.boot()
self.server.start()
```

> **Pojem: pyo Server.** „Motor“ knihovny pyo. Po `boot()` se připojí ke zvukové kartě,
> po `start()` v samostatném vlákně pořád dokola počítá další kousek zvuku ze všech pyo
> objektů, které existují. Pyo objekty jde vytvářet až po `boot()`, proto engine vzniká
> dřív než okno.

- `sr=44100`: vzorkovací frekvence, 44 100 čísel (vzorků) za sekundu.
- `nchnls=2`: dva výstupní kanály (levý a pravý reproduktor).
- `buffersize=512`: server počítá po kouscích 512 vzorků (asi 11,6 ms). Menší = menší zpoždění
  mezi stiskem a zvukem, ale víc práce.
- `duplex=0`: jen výstup, mikrofon se neotevírá (s `microphone=True` by to bylo 1).
- `setMidiInputDevice(99)`: 99 v pyo znamená „poslouchej všechna MIDI zařízení“.

#### Výstupní řetězec (`engine.py:33-46`)

```python
self.silence = Sig(0)
self.source = InputFader(self.silence)
self.volume = SigTo(0.5, time=0.05, init=0.5)
self.safe = Clip(self.source * self.volume, min=-1, max=1)
self.output = Pan(self.safe, outs=2, pan=0.5).out()
self.analyzer = Analyzer(self.source, sample_rate)
```

> **Pojem: pyo objekt = signál.** Každý pyo objekt (`Sig`, `Sine`, `Clip`...) není jedno číslo,
> ale proud čísel, 44 100 za sekundu. Python jen řekne, co je s čím propojené, a server to
> pak počítá sám. Parametr může být číslo i jiný signál.

> **Pojem: `Sig` a `SigTo`.** `Sig(0)` je signál, který má pořád hodnotu 0 (ticho).
> `SigTo` je totéž, ale když mu změníš hodnotu (`self.volume.value = 0.8`), nedojde k ní skokem,
> ale plynule za `time` sekund. Skok uprostřed vlny by byl slyšet jako cvaknutí.
> `init=` je hodnota, ze které začíná (bez něj by začínal od 0 a nejdřív se rozjížděl).

> **Pojem: `InputFader` („zásuvka“).** Objekt, kterému jde za běhu vyměnit vstup
> (`setInput(nový, fadetime=0.05)`). Starý a nový vstup se 50 ms prolínají, takže to necvakne.

Řádek po řádku:

- `self.source` je zásuvka, do které se strká součet všech stop.
- `self.source * self.volume`: vynásobení hlavní hlasitostí (slider Master). Tady operátor `*`
  nevadí, protože oba objekty žijí celou dobu běhu programu (proč to jinde vadí, viz níž
  „Tři pravidla proti pádům“).
- `Clip(..., min=-1, max=1)`: ořízne každý vzorek na rozsah -1..1. Je to pojistka: když hraje
  hodně hlasitých stop najednou, součet by mohl přesáhnout 1 a reproduktor by dostal nesmysl.
  Vzorek 1.7 se prostě změní na 1.0.
- `Pan(..., outs=2, pan=0.5)`: nástroje jsou mono (jeden kanál), `Pan` ho rozdělí do dvou
  kanálů, `pan=0.5` = přesně doprostřed. `.out()` znamená „tohle pošli do zvukové karty“.
  Je to jediný `.out()` v celé aplikaci.
- `Analyzer(self.source, ...)`: analýza (osciloskop, spektrum, data pro obraz a světlo) dostává
  signál **před** hlasitostí, takže obraz reaguje stejně, i když máš Master skoro dole.
  Analyzer je popsaný v kapitole 30.

#### `play(signal)` (`engine.py:48-57`)

```python
self.retired = (self.retired + [self.current])[-4:]
self.current = Mix(signal, voices=1) if signal is not None else self.silence
self.source.setInput(self.current, fadetime=FADE_TIME)
```

Volá ho hlavní okno, kdykoli se změní seznam stop (`self.song.outputs()` = seznam výstupů
všech nástrojů).

> **Pojem: `Mix`.** Sečte signály dohromady. `voices=1` = výsledek má jeden kanál.
> Dá se mu dát jeden objekt i seznam objektů.

- `self.current` drží nový součet. Musí být uložený v `self`, jinak by ho Python hned smazal.
- `self.retired`: seznam posledních čtyř starých součtů. `[-4:]` je **slice**: vezmi poslední
  čtyři prvky seznamu. Proč je držet, je vysvětlené u nástroje (stejný trik).

#### `send_note(channel, note, velocity)` (`engine.py:59-68`)

```python
status = (0x90 if velocity > 0 else 0x80) + channel - 1
self.server.addMidiEvent(status, note, velocity)
```

> **Pojem: MIDI.** Standard na posílání not, z 80. let. Jedna zpráva „nota“ jsou tři čísla:
> **status** (co se děje a na jakém kanálu), **číslo noty** (0–127, 60 = střední C) a **velocity**
> (síla úhozu 0–127). Kanálů je 16, každý nástroj poslouchá na jednom.

Status bajt: horní půlka říká typ zprávy, dolní 4 bity kanál.
`0x90` = „nota zapnuta“, `0x80` = „nota vypnuta“. Kanály se v bajtu číslují od 0, ale lidi
je číslují od 1, proto `+ channel - 1`. Příklad: kanál 3, nota zapnuta = `0x90 + 2 = 0x92`.
Velocity 0 znamená puštění klávesy.

`addMidiEvent` vloží zprávu do pyo, jako by přišla z MIDI klávesnice. Proto klávesnice
počítače a sekvencer nepotřebují žádnou zvláštní cestu do nástroje.

#### Nahrávání (`engine.py:73-81`)

`recordOptions(filename=path, fileformat=0, sampletype=1)` + `recstart()` začne zapisovat
přesně to, co jde do reproduktorů, do souboru WAV (`fileformat=0`) s 24 bity na vzorek
(`sampletype=1`). `recstop()` soubor dopíše. Používá to export písně (`export.py`, kapitola 20).

---

### `sirens/audio/instrument.py` — Instrument

Účel: jeden nástroj jedné stopy. Přijímá noty na svém MIDI kanálu, dělá z nich výšku
a obálku pro 8 hlasů, drží rack bloků a má slidery Attack, Decay, Sustain, Release, Volume.
Vytváří ho `Track` v `sirens/song.py` (`Instrument(channel)`).

#### Dědičnost od `Adjustable` a `PARAMS` (`instrument.py:30-39`)

```python
class Instrument(Adjustable):
    PARAMS = [
        Param("Attack", 0.001, 4, 0.01, "s", log=True, help="..."),
        ...
    ]
```

> **Pojem: třída a dědičnost.** Třída je šablona, objekt je konkrétní věc podle ní.
> `class Instrument(Adjustable)` znamená, že Instrument **dědí** od `Adjustable` (`sirens/param.py`):
> dostane jeho metody (`get`, `set`) a může je přepsat. Detailněji v 01.

> **Pojem: `Param` (dataclass).** `Param` je popis jednoho slideru: popisek, minimum, maximum,
> výchozí hodnota, jednotka, `log=True` (logaritmický průběh, hodí se na časy a frekvence),
> nápověda. `@dataclass` je zkratka, se kterou Python sám vyrobí konstruktor, takže jde psát
> `Param("Attack", 0.001, 4, 0.01, "s")`. UI pak umí z `PARAMS` vykreslit slidery pro cokoli.

> **Pojem: atribut třídy.** `PARAMS` je napsané přímo ve třídě, ne v `__init__`, takže je
> společné pro všechny nástroje. Je to „vlastnost druhu“, ne jednoho objektu.

Texty v `help=` jsou anglicky, protože se ukazují v UI (celé UI je anglicky).

#### Konstruktor (`instrument.py:41-58`)

```python
super().__init__()
self.notes = Notein(poly=VOICES, scale=1, first=0, last=127, channel=channel)
self.pitch = self.notes["pitch"]
self.trigger = self.notes["trigon"]
self.envelope = MidiAdsr(self.notes["velocity"], attack=s["Attack"], ...)
self.volume = SigTo(s["Volume"], time=0.03, init=s["Volume"])
self.socket = InputFader(Sig(0))
self.output = self.socket * self.volume
self.rack = Rack(self)
```

> **Pojem: `super().__init__()`.** Zavolá konstruktor rodiče (tady `Adjustable`). Ten vyrobí
> `self.settings`: slovník „popisek slideru -> výchozí hodnota“. Hned na dalších řádcích se
> z něj berou počáteční hodnoty (`s["Attack"]`).

> **Pojem: `Notein`.** Pyo objekt, který poslouchá MIDI noty na jednom kanálu.
> `poly=8` = umí 8 not naráz (8 **hlasů**). Každá nová nota dostane volný hlas.
> `scale=1` = výšku chceme rovnou v Hz, ne jako číslo noty (pyo přepočítá 60 -> 261,6 Hz).

Z `Notein` se berou tři signály, každý má 8 proudů (jeden na hlas):

- `pitch`: frekvence noty v Hz. Frekvence = kolikrát za sekundu se vlna zopakuje = jak vysoko
  to zní. Dvojnásobná frekvence = o oktávu výš.
- `trigon`: krátký impuls (jeden vzorek s hodnotou 1) ve chvíli stisku. Používá ho Pitch drop
  a Sampler, aby věděly, kdy začít.
- `velocity`: síla úhozu 0..1, dokud je klávesa dole, po puštění 0.

> **Pojem: víc hlasů = víc proudů.** Když objekt dostane jako parametr signál s 8 proudy,
> sám se rozdělí na 8 proudů. Proto jeden `LFO(freq=pitch)` hraje akord a nemusíme psát cyklus.
> `len(objekt)` vrací, kolik proudů objekt má.

> **Pojem: obálka ADSR (`MidiAdsr`).** Obálka říká, jak se hlasitost noty mění v čase.
> Dostane `velocity`: když přestane být 0 (stisk), obálka se rozjede, když spadne na 0
> (puštění), začne doznívat.
>
> ```
> hlasitost
>   1 |   /\
>     |  /  \______________          A = Attack: náběh od 0 nahoru
>   S | /                  \         D = Decay: pokles na úroveň Sustain
>     |/                    \__      S = Sustain: úroveň, dokud držíš klávesu
>   0 +--A--D------S--------R---> čas    R = Release: doznění po puštění
>     stisk              puštění
> ```
>
> Krátký Attack = tvrdý začátek (bicí, pluck), dlouhý = pomalý náběh (plochy).
> Sustain 0 = nota sama odezní i při držené klávese (bicí, struny).

Obálka je signál mezi 0 a 1 pro každý hlas. Zdroje jím násobí svou hlasitost, takže když
žádná nota nehraje, obálka je 0 a nástroj mlčí.

- `self.socket = InputFader(Sig(0))`: zásuvka nástroje, na začátku je v ní ticho.
- `self.output = self.socket * self.volume`: výstup nástroje = co je v zásuvce krát Volume.
  Tohle `output` pak engine sčítá se všemi stopami.
- `self.rack = Rack(self)`: rack dostane odkaz na svůj nástroj (bloky si od nástroje berou
  `pitch`, `trigger` a `envelope`).

#### `set(label, value)` (`instrument.py:60-65`)

```python
super().set(label, value)
if label == "Volume":
    self.volume.value = value
elif label in ("Attack", "Decay", "Sustain", "Release"):
    setattr(self.envelope, label.lower(), value)
```

Volá ho slider (UI zavolá `owner.set(popisek, hodnota)`) a automatizace v písni.
`super().set` uloží hodnotu do `settings` (kvůli ukládání). Pak se změna pošle do pyo objektu.
`setattr(objekt, "attack", value)` je totéž jako `self.envelope.attack = value`, jen jméno
atributu je v proměnné. `"Attack".lower()` = `"attack"`. Ušetří to čtyři skoro stejné `if`.

#### `play(flow)` (`instrument.py:67-78`)

```python
self.retired = (self.retired + [self.current])[-4:]
self.current = Mix(flow, voices=1) if flow is not None else Sig(0)
self.socket.setInput(self.current, fadetime=FADE_TIME)
```

Volá ho rack po každé změně. `flow` je to, co vyteklo z posledního bloku (8 hlasů nebo 1),
nebo `None`, když v racku nic nehraje.

- `Mix(flow, voices=1)` sečte všech 8 hlasů do jednoho kanálu.
- `setInput(..., fadetime=0.05)` zásuvka 50 ms prolíná ze starého zvuku na nový.
- **Proč `retired`:** zásuvka si v Pythonu pamatuje jen ten nový zvuk. Starý zvuk by Python
  hned smazal (nic na něj neukazuje), jenže zvukové vlákno z něj ještě 50 ms čte. Čtení
  smazané paměti = pád programu. Proto si poslední čtyři staré zvuky necháme v seznamu,
  než doprolínají. Starší než čtyři výměny zpátky už dávno dohrály a můžou zmizet.

---

### `sirens/audio/rack.py` — Rack

Účel: seznam bloků jednoho nástroje. Umí je propojit shora dolů a popsat cestu zvuku textem.

```python
class Rack(Stack):
    def __init__(self, instrument):
        super().__init__()
        self.instrument = instrument
```

`Rack` dědí od `Stack` (`sirens/stack.py`). Stack je obecný „seznam prvků pod sebou“
(`self.items`) a umí `add`, `remove`, `clear`, `toggle` (vypnout/zapnout), `move` (nahoru/dolů).
Po každé z těch operací zavolá `self.changed()`. Ve Stacku `changed()` nedělá nic, Rack ji
**přepíše** a propojí zvuk. Stejný Stack používají i vrstvy obrazu, proto je to napsané jen jednou.

> **Pojem: `@property`.**
> ```python
> @property
> def blocks(self):
>     return self.items
> ```
> Dovolí psát `rack.blocks` bez závorek, jako by to byl obyčejný atribut. Je to jen hezčí jméno
> pro `items`.

`create(block_class)` (`rack.py:21`): Stack vytváří prvky jako `item_class()`, ale blok potřebuje
vědět, čí je, proto ho Rack vytvoří jako `block_class(self.instrument)`.

> **Pojem: třída jako hodnota.** V Pythonu jde třídu (ne objekt) poslat jako parametr.
> Menu „Add block“ pošle třeba `FilterBlock` a rack z ní vyrobí nový objekt zavoláním
> `FilterBlock(nástroj)`.

#### `changed()` — srdce racku (`rack.py:25-37`)

```python
flow = None
for block in self.blocks:
    if block.enabled:
        flow = block.connect(flow)
    elif not block.IS_SOURCE:
        block.output = None
self.instrument.play(flow)
```

`flow` je „to, co zrovna teče rackem“. Na začátku nic (`None`). Každý zapnutý blok dostane
flow shora a vrátí, co teče dál dolů. Co vyteče z posledního bloku, jde do nástroje.

Příklad pro rack `Oscillator, Noise, Filter`:

```
flow = None
flow = Oscillator.connect(None)      -> zvuk oscilátoru
flow = Noise.connect(flow)           -> oscilátor + šum
flow = Filter.connect(flow)          -> filtr(oscilátor + šum)
instrument.play(flow)
```

Tomu, že rack volá `block.connect(flow)` a je mu jedno, jaký je to blok, se říká
**polymorfismus**: každá třída si `connect` udělá po svém.

Vypnutý blok se přeskočí (zůstane v seznamu i s nastavením). U vypnutého efektu se navíc
zahodí jeho starý výstup, ať ho pyo zbytečně nepočítá.

`describe()` (`rack.py:39`) poskládá text: první zapnutý blok jménem, za každým dalším
zdrojem `+`, za efektem `->`. Proto `Oscillator + Noise -> Filter`.

---

### `sirens/audio/blocks.py` — bloky

Největší soubor. Struktura tříd:

```
Adjustable (param.py)
 └─ Block                       společný základ: slidery jako SigTo signály
     ├─ SourceBlock             zdroj: přičte svůj zvuk k flow
     │   ├─ OscillatorBlock     sinus / pila / obdélník / trojúhelník
     │   ├─ SupersawBlock       7 rozladěných pil
     │   ├─ FMBlock             frekvenční modulace
     │   ├─ AdditiveBlock       7 sinusovek, harmonické nastavuješ ručně
     │   ├─ NoiseBlock          bílý šum
     │   └─ SamplerBlock        přehraje zvukový soubor
     └─ EffectBlock             efekt: zpracuje flow
         ├─ FilterBlock         filtr + obálka + wobble
         ├─ ShaperBlock         vlastní křivka y = f(x) v tabulce
         │   ├─ DistortionBlock   tanh
         │   └─ BitcrushBlock     schody
         ├─ ChorusBlock
         ├─ DelayBlock
         └─ ReverbBlock
```

#### Začátek souboru: tabulky a `keep()` (`blocks.py:35-58`)

> **Pojem: tabulka (`DataTable`, `NewTable`, `SndTable`).** Kus paměti s řadou čísel,
> ze kterého pyo objekty čtou. Může v ní být křivka (pokles výšky, křivka zkreslení) nebo
> celý nahraný zvuk (`SndTable` načte WAV ze souboru).

```python
TABLES = []
SOUNDS = {}

def keep(table):
    TABLES.append(table)
    return table
```

`TABLES` je seznam na úrovni modulu (globální), který žije celou dobu běhu programu.
Každá tabulka, kterou bloky vyrobí, se do něj přidá, a tím ji Python nikdy nesmaže.
Proč: objekt, který z tabulky čte (`TrigEnv`, `Lookup`), si nedrží tabulku samotnou, jen
ukazatel na její data. Když smažeš stopu, Python smaže nástroj i bloky naráz v náhodném
pořadí. Kdyby tabulka zmizela dřív než její čtenář, zvukové vlákno by četlo smazanou paměť
a program by spadl. Tabulek je pár, takže to paměť nezatíží.

`load_sound(path)`: načte soubor jen jednou, podruhé ho vezme ze slovníku `SOUNDS`
(cesta -> tabulka). `chnl=0` = jen první kanál, nástroje jsou mono.

#### `Block` (`blocks.py:62-105`)

```python
class Block(Adjustable):
    NAME = ""
    IS_SOURCE = True
    enabled = True

    def __init__(self, instrument):
        self.instrument = instrument
        self.values = {p.label: SigTo(p.default, time=SMOOTH_TIME, init=p.default)
                       for p in self.PARAMS}
        self.automation = {}
        self.output = None
```

> **Pojem: dict comprehension.** `{klíč: hodnota for p in seznam}` je krátký zápis cyklu,
> který vyrobí slovník. Tady: pro každý slider bloku jeden `SigTo` s jeho výchozí hodnotou,
> pod klíčem jeho popisku. Takže `self.values["Cutoff"]` je signál, který rovnou jde do filtru.

Rozdíl proti `Instrument`: blok **nevolá** `super().__init__()`, takže nemá slovník `settings`.
Hodnoty sliderů drží jako pyo signály ve `values` a `get`/`set` jsou přepsané, aby četly
a psaly do nich. Výhoda: slider bloku je rovnou signál, který jde zapojit do pyo objektu,
a díky `SigTo` se mění plynule (30 ms), takže pohyb sliderem necvaká.

- `NAME`: jméno v menu a v nadpisu bloku.
- `IS_SOURCE`: zdroj nebo efekt (podle toho rack a menu bloky rozlišují).
- `enabled = True` je atribut třídy, tedy výchozí hodnota. Když blok vypneš, `Stack.toggle`
  nastaví `item.enabled = False` na tom jednom objektu a ostatní bloky to neovlivní.
- `connect(flow)` je v `Block` jen `raise NotImplementedError`: „tohle musí potomek napsat sám“.
- `note()`, `extra()`, `load_extra()` dělají něco jen u Sampleru (jméno souboru, ukládání cesty).

#### Zdroje: `SourceBlock` (`blocks.py:135-202`)

Společné slidery na výšku (`PITCH_PARAMS`, `blocks.py:111`) mají všechny zdroje kromě
Noise a Sampleru: **Octave**, **Detune**, **Pitch drop**, **Drop time**. Plus **Level** (hlasitost).

> **Pojem: `*seznam` uvnitř seznamu.** `PARAMS = [Choice(...), *PITCH_PARAMS, LEVEL]`
> „vysype“ prvky `PITCH_PARAMS` na to místo. Výsledkem je jeden plochý seznam sliderů.

**Výška zdroje: `_ratio()`** (`blocks.py:160`)

```python
return 2 ** (round(self.get("Octave")) + self.get("Detune") / 1200)
```

Fyzika: o oktávu výš = dvojnásobná frekvence. Oktáva má 12 půltónů a půltón má 100 centů,
takže oktáva = 1200 centů. Octave +1 a Detune 0 dá `2 ** 1 = 2` (dvakrát vyšší frekvence),
Octave -1 dá `0.5`, Detune +100 dá `2 ** (1/12)` ≈ 1,059 (o půltón výš).
`self.ratio` je `SigTo` s touhle hodnotou. Když hneš Octave nebo Detune, přepočítá se v `set`.

**Frekvence a hlasitost pro každý hlas: `freq()` a `amp()`** (`blocks.py:178-190`)

```python
shifted = Sig(self.instrument.pitch, mul=self.ratio)        # výška noty * ratio
return Sig(shifted, mul=self.bend)                         # * pokles výšky (jen když je)

return Sig(self.instrument.envelope, mul=self.values["Level"])   # obálka * Level
```

> **Pojem: `mul=` a `add=`.** Skoro každý pyo objekt má parametry `mul` a `add`: výstup objektu
> se vynásobí `mul` a přičte se `add`. `Sig(x, mul=y)` je tedy „x krát y“. `Sig(x, mul=y, add=1)`
> je „1 + x krát y“. Proč takhle a ne `x * y`, viz „Tři pravidla proti pádům“.

`amp()` je důvod, proč zdroje mlčí, když nehraješ: obálka je 0, krát cokoli je 0.

**Pitch drop** (`blocks.py:142-149`, `drop_curve` na `blocks.py:124`)

Pitch drop dělá, že nota začne výš a rychle spadne na svou výšku. Z obyčejného sinusu
tak vznikne kopák (bicí), z vyšších tónů laserové „píu“.

```python
self.curve = keep(DataTable(size=DROP_POINTS, init=drop_curve()))
self.drop = TrigEnv(instrument.trigger, self.curve, dur=self.values["Drop time"], interp=1)
self.amount = SigTo(self._amount(), ...)
self.bend = Sig(self.drop, mul=self.amount, add=1)
```

1. `drop_curve()` spočítá 512 čísel křivky, která jde z 1 rychle k 0 (exponenciála e^(-6x),
   jako tlumený kmit blány bubnu). Upraví ji tak, aby končila přesně v 0, jinak by nota zůstala
   trochu rozladěná.
2. `TrigEnv` při každém impulsu `trigger` (stisk klávesy) jednou projede tabulku za `Drop time`
   sekund a pak dává 0. `interp=1` = bez interpolace (s ní by na konci skočila zpátky k 1).
3. `_amount()`: Pitch drop 12 půltónů = začni o oktávu výš = 2x vyšší frekvence, tj. o 1 víc.
   Obecně `2 ** (půltóny / 12) - 1`.
4. `bend = 1 + amount * křivka`: na začátku noty `1 + amount` (např. 2), na konci 1.
   Frekvence = výška noty * ratio * bend.

> **Pojem: `TrigEnv`.** Pyo objekt, který při každém impulsu (trigger) přehraje tabulku
> jednou od začátku do konce za `dur` sekund. Normálně se tak hrají obálky.

**Napojení zdroje: `connect(flow)`** (`blocks.py:192-202`)

```python
if flow is None:
    self.flow = self.output
else:
    self.flow = Mix([flow, self.output], voices=len(self.output))
```

Když shora nic neteče, dál teče jen zvuk zdroje. Jinak se sečte to, co teče shora, se zvukem
zdroje, ale **s 8 hlasy** (`voices=len(self.output)`), ne s jedním. Hlas 1 shora se sečte
s hlasem 1 zdroje atd., takže noty zůstanou oddělené a filtr pod tím je může zpracovat každou
zvlášť (každou s vlastní obálkou).

#### Jednotlivé zdroje

**OscillatorBlock** (`blocks.py:209`): základní oscilátor. Používá pyo `LFO`, který umí
víc tvarů vlny a je **pásmově omezený** (nevyrábí frekvence nad hranicí, kterou zvuková
karta umí přehrát; jinak by se odrážely zpátky jako nepříjemné pískání, tzv. aliasing).
Tvar vlny = barva tónu: sinus čistý a měkký, pila (saw) ostrá a bzučivá, obdélník (square)
dutý, trojúhelník mezi nimi. `LFO_TYPES = (7, 0, 2, 3)` jsou čísla těch tvarů v pyo.
`Brightness` je parametr `sharp` (jak ostrá je vlna). Tvar se nedá zadat signálem, jen číslem,
proto se v `set` přepíná přímo `self.osc.type`.

**SupersawBlock** (`blocks.py:239`): pyo `SuperSaw`, sedm pil lehce rozladěných proti sobě.
Protože se navzájem rozcházejí, zvuk se vlní a je „tlustý“. `Spread` = jak moc rozladěné,
`Center` = poměr prostřední pily k ostatním.

**FMBlock** (`blocks.py:259`): frekvenční modulace. Jeden sinus (modulátor) rychle mění
frekvenci druhého (nosná vlna = tvoje nota). `Ratio` = kolikrát rychleji kmitá modulátor než
nota, `Index` = jak moc s výškou cloumá. Vzniknou tím nové frekvence kolem tónu: při celých
Ratio to zní „hudebně“, jinak kovově (zvony, plechy).

**AdditiveBlock** (`blocks.py:281`): aditivní syntéza, barvu tónu si skládáš sám ze sinusovek.

```python
self.partials = [Sine(freq=freq * n, mul=amp * self.values[f"Harmonic {n}"])
                 for n in range(1, self.COUNT + 1)]
total = self.partials[0]
for partial in self.partials[1:]:
    total = total + partial
self.output = total * 0.4
```

Každý tón je ve skutečnosti součet sinusovek na násobcích základní frekvence f, 2f, 3f...
(**harmonické**). Kolik je které, určuje barvu. Tady je jich 7, každá se svým sliderem.
Výchozí hlasitosti jsou 1, 1/2, 1/3... (to dá přibližně pilu); když necháš jen liché
(1, 3, 5, 7), vznikne skoro obdélník. Součet všech výchozích hlasitostí je asi 2,6, proto
se na konci ztiší `* 0.4`. Tady operátory `*` a `+` používat jde, protože vlevo je vždycky
nový objekt tohoto bloku (viz pravidla níž).

`range(1, self.COUNT + 1)` = čísla 1 až 7. `f"Harmonic {n}"` je f-string (do textu se dosadí n).

**NoiseBlock** (`blocks.py:309`): bílý šum, náhodná čísla. Šum není tón: nemá výšku, obsahuje
všechny frekvence naráz a zní jako „šššš“. Výška noty ho nezajímá, používá jen obálku
(kdy a jak hlasitě). S filtrem dělá vítr, hi-hat, šumění.

**SamplerBlock** (`blocks.py:326`): přehraje zvukový soubor při každé notě.

```python
speed = Max(self.instrument.pitch, 1) / ROOT_HZ * self.shift
self.player = TrigEnv(self.instrument.trigger, self.table, dur=self.table.getDur() / speed,
                      mul=self.values["Level"])
```

Trik: `TrigEnv` normálně přehrává obálku, ale v tabulce může být klidně celý zvuk. Rychlost
přehrávání se řídí délkou `dur`:

- `speed` = výška noty / výška C4 (261,63 Hz) * posun sliderem Pitch. Na C4 je speed 1,
  o oktávu výš 2.
- `dur = délka souboru / speed`: na C4 hraje soubor ve své délce, o oktávu výš za polovinu času.
  Rychlejší přehrání = vyšší zvuk (jako gramofon puštěný rychleji).
- `Max(pitch, 1)`: než zahraješ první notu, je pitch 0 a dělit nulou nejde.
- Sampler používá jen `Level`, ne obálku nástroje. Soubor hraje celý, puštění klávesy ho
  neutne (dobré pro bicí).

`load(path)` (`blocks.py:363`): načte nový soubor, postaví **nový** přehrávač a nechá rack
znovu propojit. Nepoužívá se výměna tabulky ve starém přehrávači (`setTable`), protože ta by
mohla smazat starý zvuk, zatímco ho zvukové vlákno čte. Prázdný Sampler má 0,1 s ticha
(`NewTable(0.1)`). Volá ho tlačítko **Load** a při otevření projektu `load_extra`
(jen když soubor pořád existuje: `Path(...).exists()`).

#### Efekty: `EffectBlock` (`blocks.py:388-400`)

```python
def connect(self, flow):
    self.output = self.process(flow) if flow is not None else None
    return self.output
```

Efekt zpracuje, co přitéká. Když nic nepřitéká, nic nevydá. Konkrétní efekty píšou jen
`process(flow)`. Při každé změně racku se efekt postaví znovu s novým vstupem.

**Dva druhy efektů:**

- **Filter, Distortion, Bitcrush** zpracují 8 hlasů zvlášť (výsledek má zase 8 hlasů).
- **Chorus, Delay, Reverb** nejdřív udělají `Mix(flow, voices=1)` a pracují s jedním signálem.
  Důvod: ozvěna nebo dozvuk má být jeden pro všechny noty (jinak 8x víc počítání),
  a u ozvěny noty stejně doznívají přes sebe.

#### FilterBlock (`blocks.py:406-449`)

Filtr nechá projít jen část frekvencí: **Low-pass** propustí hloubky (zvuk ztmavne),
**High-pass** výšky (zvuk zeslábne, zprůhlední), **Band-pass** jen pásmo kolem Cutoff.
**Resonance** zesílí frekvence přímo u Cutoff (při vysokých hodnotách filtr „píská“).
Používá pyo `SVF`, kde typ jde plynule: 0 = LP, 0,5 = BP, 1 = HP. Proto `Mode / 2`.

Cutoff (hraniční frekvence) se tu skládá ze tří věcí:

```python
self.env_amount = Sig(self.values["Envelope"], mul=8)                 # v __init__
self.opening = Sig(self.instrument.envelope, mul=self.env_amount, add=1)

self.lfo = Sine(freq=self.values["Wobble rate"], mul=self.values["Wobble"], add=1)   # v process
self.moving = Sig(self.lfo, mul=self.values["Cutoff"])
if len(flow) == len(self.instrument.envelope):
    self.opened = Sig(self.moving, mul=self.opening)
self.cutoff = Clip(cutoff, 20, 18000)
return SVF(flow, freq=self.cutoff, q=self.values["Resonance"], type=self.mode)
```

1. **Wobble**: pomalý sinus kolem 1. Při Wobble 0,5 kmitá mezi 0,5 a 1,5 a tím násobí Cutoff,
   takže filtr se rytmicky otevírá a zavírá („wub wub“). Wobble jde max do 0,9, aby násobek
   nikdy nebyl záporný.
2. **Envelope**: `opening = 1 + Envelope * 8 * obálka`. Při stisku obálka vyskočí k 1 a filtr
   se otevře až 9x výš, pak se s obálkou zase zavře. Tak vzniká „pluck“ nebo „wah“.
   Funguje jen, když má flow stejný počet hlasů jako obálka (`len(flow) == len(envelope)`),
   tedy když nad filtrem není Chorus/Delay/Reverb, který hlasy sečetl. Každá nota má pak
   vlastní filtr se svou obálkou.
3. `Clip(cutoff, 20, 18000)`: pojistka, ať se hraniční frekvence nedostane mimo rozumný rozsah.

#### ShaperBlock: vlastní křivka (`blocks.py:452-487`)

Tohle je **naše vlastní zpracování signálu** (waveshaping). Každý vzorek x (číslo -1..1)
projde funkcí y = curve(x), kterou si počítáme sami.

```python
def _draw_curve(self):
    amount = self.get(self.SHAPE)
    xs = [2 * i / (self.TABLE_SIZE - 1) - 1 for i in range(self.TABLE_SIZE)]
    self.table.replace([self.curve(x, amount) for x in xs])

def process(self, flow):
    self.shaped = Lookup(self.table, index=Clip(flow, -1, 1))
    return Interp(flow, self.shaped, interp=self.values["Mix"])
```

- `xs`: 4096 rovnoměrně rozložených x od -1 do 1 (i = 0 dá -1, poslední i dá 1).
- Pro každé x spočítáme y vlastní funkcí `curve` a uložíme do tabulky (`replace`).
- `Lookup` pak pro každý vzorek zvuku jen najde v tabulce hodnotu na pozici x.
  Proč tabulka a ne počítat funkci přímo: Python nemůže počítat 44 100 vzorků za sekundu
  pro 8 hlasů ve zvukovém vlákně, ale vyhledat číslo v tabulce pyo zvládne bez problému.
  Křivku tedy počítáme my, pyo ji jen „přikládá“ ke zvuku.
- `Clip(flow, -1, 1)`: Lookup bere pozici jen -1..1, hlasitější vzorky by koukaly mimo tabulku.
- `Interp(původní, upravený, interp=Mix)`: prolnutí, Mix 0 = jen původní, 1 = jen upravený.
- Když se pohne sliderem, který mění tvar (`SHAPE`), tabulka se přepočítá (`set`).
- `curve` je v ShaperBlock jen `raise NotImplementedError`, konkrétní křivku dodají potomci.

**DistortionBlock** (`blocks.py:490`):

```python
return math.tanh(drive * x) / math.tanh(drive)
```

`tanh` (hyperbolický tangens) je funkce, která malá čísla skoro nemění a velká zaobleně
„stlačí“ k ±1. Když vlnu nejdřív zesílíš (`drive * x`) a pak protáhneš tanh, vrcholy vlny se
zploští. Zploštělá vlna má víc vyšších harmonických, takže zní drsněji. Dělení `tanh(drive)`
zajistí, že x = 1 dá zase přesně 1 (maximální hlasitost se nezmění).
Příklad pro Drive 5: x = 0,2 dá tanh(1)/tanh(5) ≈ 0,76. Tichá místa vlny se hodně zesílí,
hlasitá narazí na strop.

**BitcrushBlock** (`blocks.py:507`):

```python
levels = 2 ** round(bits) / 2
return round(x * levels) / levels
```

Snížení bitové hloubky: vlna smí mít jen pár povolených úrovní, každý vzorek se zaokrouhlí
na nejbližší. Z hladké vlny jsou schody, zní to rozbitě a digitálně. Bits 4: `levels` = 8 úrovní
na každou stranu od nuly, takže povolené hodnoty jsou -1, -7/8, ..., 0, ..., 7/8, 1.

#### Chorus, Delay, Reverb (`blocks.py:523-571`)

Všechny tři nejdřív sečtou hlasy (`Mix(flow, voices=1)`) a pak použijí hotový pyo efekt:

- **Chorus**: několik lehce zpožděných kopií, jejichž zpoždění se pomalu houpe (tím se jim
  trochu mění výška). Zvuk je širší, jako víc hráčů naráz. `bal` = poměr původní / kopie.
- **Delay**: ozvěna. `Delay` zpozdí zvuk o `Time` a část výstupu (`Feedback`) pošle zpátky
  na vstup, takže se ozvěna opakuje a pokaždé je slabší. Feedback max 0,95 (při 1 by nikdy
  neutichla). `maxdelay=2` = Delay si připraví paměť na 2 s, proto Time jde max do 2.
  Výstup: `self.mixed + self.echo * self.values["Mix"]` = původní zvuk + ozvěny ztlumené Mixem.
- **Reverb** (`Freeverb`): dozvuk místnosti, hustá síť odrazů, které doznívají. `Size` = velikost
  místnosti (délka dozvuku), `Damping` = jak rychle v dozvuku mizí výšky.

#### `CATALOG` (`blocks.py:574`)

Seznam tříd bloků v pořadí, v jakém jsou v menu **Add block**. UI mezi poslední zdroj a první
efekt vloží čáru (podle `IS_SOURCE`). Ukládání (`session.py`) z něj dělá slovník
„jméno -> třída“, aby při otevření projektu našlo třídu podle uloženého jména.

---

## Tři pravidla proti pádům

Python maže objekty, na které už nic neukazuje. Zvukové vlákno pyo ale běží souběžně
a čte data objektů přímo v paměti. Když Python něco smaže, zatímco to vlákno ještě čte,
program spadne. V kódu jsou proti tomu tři opatření. U zkoušky je dobré je umět vysvětlit,
protože vypadají „divně“.

1. **`mul=` místo `*` u dlouho žijících signálů.** V pyo `a * b` vytvoří nový objekt
   a **natrvalo ho připojí k levému objektu `a`**, pravý `b` si nepamatuje. Kdyby vlevo byl
   signál, který žije pořád (výška noty, slider), a vpravo kus racku, který se při přestavbě
   zahodí, výsledek by u `a` visel dál, četl smazanou paměť (pád) a s každou přestavbou by
   jich přibývalo (zpomalování). Proto se píše `Sig(a, mul=b)`: nový objekt, který patří
   bloku a zahodí se s ním. Operátory jsou v kódu jen tam, kde vlevo je nový objekt
   (`AdditiveBlock`, `DelayBlock`) nebo kde oba žijí stejně dlouho (`engine.py`, `instrument.py`).
2. **`retired` v `Instrument.play` a `AudioEngine.play`.** Zásuvka 50 ms prolíná ze starého
   zvuku, ale Python odkaz drží jen na nový. Poslední čtyři staré zvuky si proto necháme.
3. **`keep()` u tabulek.** Tabulky se nikdy nemažou (seznam `TABLES`), protože čtenář
   tabulky drží jen ukazatel na data, ne tabulku.

A jedno pravidlo proti cvakání: všechno, co se mění za běhu (slidery, Volume, Master), je
`SigTo`, který dojede k nové hodnotě za 30–50 ms, a výměny zvuku jdou přes `InputFader`
s prolnutím.

---

## Vlastní zpracování signálu

Tady kód zvuk opravdu počítá sám, nejen skládá hotové efekty knihovny:

| Kde | Co počítáme sami |
|---|---|
| `ShaperBlock._draw_curve`, `blocks.py:475` | přenosová křivka y = f(x) pro každý vzorek, počítaná v Pythonu do tabulky 4096 bodů |
| `DistortionBlock.curve`, `blocks.py:501` | zkreslení funkcí tanh s normalizací, aby se nezměnila maximální hlasitost |
| `BitcrushBlock.curve`, `blocks.py:518` | kvantování (zaokrouhlení) vzorku na 2^bits úrovní |
| `drop_curve`, `blocks.py:124` | exponenciální křivka poklesu výšky, upravená, aby končila přesně v 0 |
| `SourceBlock.freq`, `_ratio`, `_amount` | výpočet frekvence každého hlasu: nota * 2^(oktáva + centy/1200) * (1 + amount * křivka) |
| `AdditiveBlock` | vlastní aditivní syntéza: tón složený ze 7 sinusovek na násobcích f |
| `SamplerBlock._build` | změna výšky vzorku přes rychlost přehrávání: dur = délka / (f / f_C4 * 2^(posun/12)) |
| `FilterBlock.process` | vlastní modulace hraniční frekvence: Cutoff * (1 + Wobble * sin) * (1 + 8 * Envelope * obálka), zvlášť pro každou notu |
| `SourceBlock.connect`, `Rack.changed` | vlastní směrování signálu: sčítání hlasů zdrojů se zachováním polyfonie, řetězení efektů |
| `AudioEngine` | ochranný ořez -1..1 a míchání stop |

Hotové z pyo jsou oscilátory (LFO, SuperSaw, FM, Sine, Noise), filtr SVF a efekty Chorus,
Delay a Freeverb. To je v pořádku, ale u zkoušky ukazuj hlavně na ShaperBlock (tam je
matematika celá naše) a na výpočty frekvence a cutoffu.

---

## Na co se tě můžou zeptat

**1. Co se stane od stisku klávesy po zvuk z repráku?**
Klávesnice zavolá `engine.send_note`, ten pošle MIDI zprávu (0x90 + kanál, nota, síla) přes
`server.addMidiEvent`. `Notein` nástroje na tom kanálu dá notě volný hlas a vydá její frekvenci,
impuls a sílu. `MidiAdsr` z ní udělá obálku. Bloky v racku vyrobí pro ten hlas signál (frekvence
z `pitch`, hlasitost z obálky), efekty ho upraví, nástroj sečte hlasy, vynásobí Volume, engine
sečte stopy, vynásobí Master, ořízne na -1..1 a pošle do obou repráků.

**2. Jaký je rozdíl mezi zdrojem a efektem v racku?**
Zdroj (`SourceBlock.connect`) k tomu, co teče shora, **přičte** svůj zvuk. Efekt
(`EffectBlock.connect`) to, co teče shora, **zpracuje**. Rack jde shora dolů a předává si
proměnnou `flow`. Proto „Oscillator + Noise -> Filter“ filtruje oba zdroje.

**3. Proč jsou hodnoty sliderů `SigTo` a ne obyčejná čísla?**
Aby se daly přímo zapojit do pyo objektů jako signál a aby se při změně neskákalo:
skok hodnoty uprostřed vlny je slyšet jako cvaknutí, SigTo dojede k nové hodnotě za 30 ms.

**4. Jak funguje Distortion? Co z toho je vaše práce?**
Každý vzorek x projde funkcí tanh(drive · x) / tanh(drive). Křivku počítáme sami v Pythonu do
tabulky 4096 bodů pro x od -1 do 1, pyo `Lookup` pak jen pro každý vzorek najde hodnotu.
Tanh zaoblí vrcholy, přibudou vyšší harmonické, zvuk je drsnější. Dělení tanh(drive) drží
maximum na 1.

**5. Proč píšete `Sig(a, mul=b)` místo `a * b`?**
Protože v pyo `a * b` připojí výsledek natrvalo k objektu `a`. Kdyby `a` žil dlouho a `b` se
zahodil při přestavbě racku, výsledek by četl smazanou paměť (pád) a hromadil by se.
`Sig(..., mul=...)` je nový objekt, který zanikne s blokem.

**6. Proč se tabulky nikdy neuvolňují a k čemu je `retired`?**
Obojí brání pádům: zvukové vlákno čte data souběžně s Pythonem. Čtenář tabulky drží jen
ukazatel na data, takže tabulka nesmí zmizet dřív. `retired` drží staré zvuky, ze kterých
zásuvka ještě 50 ms prolíná, protože Python by je jinak hned smazal.

**7. Jak se počítá výška zdroje s Octave a Detune?**
`frekvence noty * 2^(octave + detune/1200)`. Oktáva = dvojnásobná frekvence, 1200 centů = oktáva.

**8. Jak Sampler hraje vzorek v jiné výšce?**
Přehraje ho rychleji nebo pomaleji: `dur = délka souboru / (frekvence noty / 261,63 * posun)`.
Na C4 v původní délce, o oktávu výš za poloviční čas, a tím o oktávu výš.

**9. Proč Chorus, Delay a Reverb sčítají hlasy, ale Filter ne?**
Filtr má mít pro každou notu vlastní obálku (Envelope otevírá filtr při každém stisku), takže
zpracuje 8 hlasů zvlášť. Ozvěna a dozvuk stačí jedna pro všechny noty a ušetří to výpočet.

**10. K čemu je na konci enginu `Clip(-1, 1)` a proč je analýza před Master?**
Clip je pojistka, aby součet hodně hlasitých stop nepřekročil rozsah, který reproduktor
umí (vzorky mimo -1..1 se oříznou). Analýza je před hlasitostí, aby osciloskop a obraz
reagovaly stejně i při tichém poslechu.

**11. Co znamená status bajt 0x90?**
MIDI „nota zapnuta“. Horní polovina bajtu je typ zprávy (9 = note on, 8 = note off),
dolní 4 bity kanál (0 = kanál 1). Velocity 0 = puštění klávesy.

**12. Co je obálka ADSR?**
Jak se hlasitost noty mění v čase: Attack (náběh), Decay (pokles), Sustain (úroveň při
držení), Release (doznění po puštění). Dělá ji `MidiAdsr` z velocity, zdroje jí násobí hlasitost.

---

## Kde se to napojuje

Kdo volá do těchto čtyř souborů (hledej podle jména funkce, čísla řádků v ostatních souborech
se můžou posunout):

| Kde | Co volá |
|---|---|
| `sirens/__main__.py`, `main()` | `AudioEngine()`: vznikne jednou, před oknem |
| `sirens/ui/main_frame.py` | `engine.play(self.song.outputs())` po startu, po přidání/smazání stopy a po otevření projektu; `engine.analyzer` pro obraz a světlo; `engine.close()` při zavření okna |
| `sirens/song.py`, `Track.__init__` | `Instrument(channel)`: každá stopa má svůj nástroj na volném kanálu 1–8 |
| `sirens/song.py`, `Song.outputs`, `Song.remove_track`, `Track.automated_owners` | seznam `instrument.output` pro engine; `rack.clear()` při smazání stopy; nástroj + bloky jako vlastníci automatizace |
| `sirens/ui/sound_page.py` | `CATALOG` do menu Add block; slider Master -> `engine.set_volume`; slidery nástroje; `rack.describe()` do pruhu s cestou zvuku |
| `sirens/ui/stack_editor.py` | tlačítka On/Off, Up, Down, Remove a menu Add block -> `Stack.toggle/move/remove/add` (a tím `Rack.changed`); tlačítko Load -> `SamplerBlock.load`; `block.note()` pod nadpisem |
| `sirens/ui/sidebar.py`, `add_params` | pohyb slideru -> `owner.set(popisek, hodnota)` (nástroj i blok) |
| `sirens/ui/keys.py`, `note_on` / `note_off` | `engine.send_note` z klávesnice počítače |
| `sirens/ui/song_page.py` | `engine.send_note` při kliknutí do piano rollu (krátká ukázka noty) |
| `sirens/audio/player.py` | `engine.send_note` při přehrávání písně; `owner.set` pro automatizaci sliderů |
| `sirens/audio/export.py` | `engine.start_recording` / `stop_recording` při exportu WAV |
| `sirens/session.py` | ukládání: `block.get`, `block.extra()`, `block.enabled`; načítání: `rack.add`, `block.set`, `block.load_extra`, nakonec `rack.changed()` |
| `sirens/audio/analyzer.py` | dostává `engine.source` (součet stop před Master) |
| `sirens/ui/timeline_view.py` | zapisuje do `block.automation` / `instrument.automation` |
