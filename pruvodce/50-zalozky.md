# 50 — Záložky: Sound, Song, Visual, piano roll, časová osa a klávesy

Tahle kapitola je o tom, co uživatel v aplikaci **vidí a na co kliká**. Hlavní okno
(`sirens/ui/main_frame.py`) má nahoře tři tlačítka záložek: **Sound**, **Song**
a **Visual**. Každá záložka je jedna třída v jednom souboru:

| Záložka | Soubor | Třída |
|---|---|---|
| Sound | `sirens/ui/sound_page.py` | `SoundPage` |
| Song | `sirens/ui/song_page.py` | `SongPage` |
| Visual | `sirens/ui/visual_page.py` | `VisualPage` (+ `FullscreenWindow`) |

A k tomu čtyři "kreslené" ovládací prvky, které si záložky vkládají dovnitř:

| Prvek | Soubor | Kde ho uvidíš |
|---|---|---|
| hraní na klávesnici počítače | `sirens/ui/keys.py` (`KeyboardPlayer`) | funguje všude, není to okno |
| klaviatura na obrazovce | `sirens/ui/piano.py` (`PianoView`) | dole v Sound |
| piano roll (editor not) | `sirens/ui/pattern_view.py` (`PatternView`) | nahoře v Song |
| časová osa | `sirens/ui/timeline_view.py` (`TimelineView`) | dole v Song |

Základy wxPythonu (co je `wx.App`, `wx.Frame`, panel, událost, `Bind`, kreslení
v `EVT_PAINT`, sizery) jsou v kapitole [40-okno-a-ovladaci-prvky.md](40-okno-a-ovladaci-prvky.md).
Základy Pythonu (třída, `self`, seznam, slovník) jsou v [01-zaklady.md](01-zaklady.md).
Data, se kterými tu pracujeme (`Song`, `Track`, `Pattern`, `Note`, přehrávač `Player`),
jsou popsaná v [20-pisen-a-data.md](20-pisen-a-data.md). Tady se je jen naučíme ukazovat a měnit myší.

---

## Úvod: co v jednotlivých záložkách uvidíš a co tam děláš

Všechny tři záložky mají stejnou kostru: **vlevo velká plocha** (grafy, editor, obraz),
**vpravo panel** (`Sidebar`) se slidery a tlačítky. Mezi nimi svislá čára
(`divider`). Hlavní okno všechny tři záložky vytvoří hned při startu a pak jen
přepíná, která je vidět (`MainFrame._select_tab` volá `page.Show(True/False)`).

### Sound: stavění zvuku a hraní

Co vidíš: nahoře graf tvaru vlny (SCOPE), pod ním spektrum (SPECTRUM), pod ním štítek
s cestou zvuku (třeba `Track 1: Oscillator -> Filter`) a úplně dole klaviaturu.
Vpravo: Master hlasitost, přepínač Keys (Play / Hold), výběr stopy, jméno, skupina
Preset (Save / Load), obálka (Attack, Decay, Sustain, Release, Volume) a bloky nástroje s tlačítkem **Add block**.

Krok za krokem:

1. **Klikneš na Add block a vybereš Oscillator.** `StackEditor` (soubor `stack_editor.py`)
   přidá blok do racku nástroje a zavolá `SoundPage.refresh`, který celý pravý panel
   smaže a postaví znovu, už s novým blokem a jeho slidery (`sirens/ui/sound_page.py:140`).
2. **Zmáčkneš na klávesnici A.** `KeyboardPlayer.FilterEvent` (`sirens/ui/keys.py:107`)
   chytí stisk, spočítá číslo noty 60 a pošle ji enginu jako MIDI zprávu. Nástroj
   vybrané stopy začne hrát. Na klaviatuře se klávesa C4 obarví, protože nota je teď
   v množině `active` a klaviatura se 30x za sekundu překresluje (`SoundPage.tick`).
3. **Pustíš A.** Přijde událost "klávesa nahoru", `KeyboardPlayer` pošle note off
   (velocity 0) a nota dozní podle Release.
4. **Přepneš Keys na Hold.** Zavolá se `keys.set_hold(True)`. Od teď první stisk notu
   zapne a nechá znít, druhý ji vypne, takže můžeš mezitím točit slidery a poslouchat.
5. **Klikneš myší na klávesu na obrazovce.** `PianoView._on_down` najde, která klávesa
   je pod myší, a zavolá `KeyboardPlayer.press`, tedy úplně stejnou cestu jako klávesnice.
6. **Copy sound / Paste sound.** Zkopíruje zvuk (obálku a bloky, ne noty) jedné stopy
   a vloží ho do jiné.
7. **Preset Save / Load.** Save uloží zvuk vybrané stopy (obálku a bloky, ne noty) do
   souboru `.json`, ve výchozím dialogu ve složce `assets/presets` (podsložky `drums`,
   `bass`, `synth`). Load vybraný soubor načte a zvuk vybrané stopy jím nahradí; noty
   a časová osa zůstanou. Je to stejný zvuk jako u Copy sound, jen v souboru, takže ho
   můžeš nahrát do jakékoli stopy a kdykoli později. Soubor, který není preset
   (třeba celá uložená píseň), se odmítne s hláškou.

### Song: noty, patterny a časová osa

Co vidíš: nahoře **piano roll** (mřížka: svisle výšky tónů, vodorovně čas), dole
**časová osa** (řádek pro každou stopu, sloupec pro každý takt). Vpravo: Loop / Song,
Tempo, Song length, nastavení stopy a patternu (Pattern A..H, Length, Grid).

Slovníček na rozjezd (podrobně v [20-pisen-a-data.md](20-pisen-a-data.md)):

- **takt** = kus času, 4 doby. Při tempu 120 bpm (doby za minutu) trvá doba 0,5 s, takt 2 s.
- **krok** = nejmenší políčko v mřížce. Normálně je mřížka po šestnáctinách (**Grid
  16ths**): **16 kroků na takt**, takže jedna doba jsou 4 kroky. Volba **Fine** dá
  **48 kroků na takt** (3 kroky na šestnáctinu) na noty, které do šestnáctin nesednou.
  Trioly jako zvláštní dělení aplikace neumí.
- **pattern** = krátký kousek s notami (1, 2 nebo 4 takty). Každá stopa jich má osm, A..H.
- **arrangement** = která stopa hraje který pattern v kterém taktu písně.

Krok za krokem:

1. **Klikneš do prázdného políčka v piano rollu.** `PatternView._on_down`
   (`sirens/ui/pattern_view.py:103`) přepočítá pixely myši na (krok, výška), vytvoří
   `Note(krok, výška, 1)`, přidá ji do patternu a hned ji krátce zahraje (`_preview`).
2. **Táhneš doprava.** `_on_motion` počítá z polohy myši, kde má nota končit, a mění
   její `length`. Nota se natahuje po krocích.
3. **Klikneš na existující notu.** Smaže se.
4. **Točíš kolečkem nad piano rollem.** Posouvají se zobrazené výšky (vidíš 24 řádků,
   tj. 2 oktávy, kolečkem se posouváš nahoru a dolů).
5. **Táhneš v pruhu Vel dole.** Měníš sílu úhozu (velocity) not na kroku pod myší.
   Výš = hlasitěji. Slabší noty se v mřížce kreslí průhledněji.
6. **Zmáčkneš mezerník.** Spustí se přehrávání (mezerník chytá taky `KeyboardPlayer`
   a volá `on_space`, což je `MainFrame._toggle_playing`). V režimu Loop se po patternu
   posouvá světlý sloupec, ukazatel přehrávání.
7. **Klikneš / táhneš v řádku stopy na časové ose.** `TimelineView._on_down` zapíše do
   `track.arrangement[takt]` jméno právě editovaného patternu. Klik na takt, kde ten
   pattern už je, ho naopak smaže.
8. **Přepneš Mode na Song a pustíš.** Hraje celá časová osa, svislá čára ukazatele
   jede po taktech a pohled se sám posouvá.
9. **Přepneš Grid na Fine.** `SongPage._set_grid` přepočítá noty patternu (z 16 na 48 kroků
   na takt všechny pozice a délky krát 3), takže znějí úplně stejně, jen se teď dají
   klikat po jemnějších krocích. Zpátky na 16ths se pozice dělí třemi a zaokrouhlí,
   takže noty mezi šestnáctinami se posunou na nejbližší. Když tím dvě noty skončí na stejném
   kroku a stejné výšce, nechá se jen první. U Fine kreslí piano roll čáry jen po
   šestnáctinách, aby mřížka nebyla šedá kaše.

### Visual: obraz z vrstev

Co vidíš: vlevo obraz, který se hýbe se zvukem, vpravo vrstvy (Ring, Particles,
efekty...) se slidery, tlačítko **Add layer** a nahoře **Fullscreen**.

1. **Add layer -> Ring.** Stejný `StackEditor` jako u bloků zvuku přidá vrstvu do
   `Painter` (soubor `sirens/visual/painter.py`) a panel se postaví znovu.
2. **Každý snímek** (30x za sekundu) `VisualPage.tick` řekne Painteru "spočítej další
   obrázek" a ukáže ho.
3. **Fullscreen.** Otevře se nové okno `FullscreenWindow` přes celou obrazovku, a když
   je připojený projektor (druhá obrazovka), otevře se na něm. Esc nebo dvojklik ho zavře.

Jak se obraz počítá, je v [30-obraz-a-svetlo.md](30-obraz-a-svetlo.md). Tady je jen jeho zobrazení.

---

## Jak to spolu souvisí

### Klávesa -> zvuk

```
 stisk klávesy "S" na klávesnici počítače
        |
        v
 wx.EventFilter  (KeyboardPlayer.FilterEvent, keys.py:107)
        |   key = "S", NOTE_KEYS["S"] = 2, octave = 4
        |   note = 12 * (4 + 1) + 2 = 62          (D4)
        v
 KeyboardPlayer.press(62)  -> note_on(62)
        |   active.add(62)                       (klaviatura ji obarví)
        v
 engine.send_note(channel, 62, 100)              (sirens/audio/engine.py)
        |   MIDI zpráva: 0x90 + kanál - 1, nota 62, síla 100
        v
 pyo Notein nástroje na tom kanálu               (sirens/audio/instrument.py)
        |   62 -> frekvence v Hz, obálka MidiAdsr se spustí
        v
 bloky v racku (Oscillator, Filter, ...) -> mix -> reproduktory
```

Puštění klávesy jde stejnou cestou, jen s velocity 0 (= note off).

### Myš na klaviatuře -> zvuk

```
 klik na klávesu na obrazovce
        |
 PianoView._on_down (piano.py:70) -> _note_at(x, y) najde notu
        |
 KeyboardPlayer.press(nota)  ...  a dál úplně stejně jako nahoře
```

### Klik v piano rollu -> nota v datech -> přehrávač

```
 klik do mřížky (x, y)
        |
 PatternView._on_down (pattern_view.py:103)
        |   _at(x, y) -> (krok, výška)
        |   Note(krok, výška, 1) -> pattern.notes.append(...)
        |   preview(výška) -> SongPage._preview -> engine.send_note (krátce zahraje)
        v
 data: track.patterns["A"].notes  (sirens/song.py)
        ^
        |  čte je každý tik
 Player._on_tick -> _play_notes (sirens/audio/player.py, vlastní vlákno)
        |
 engine.send_note(kanál, nota.pitch, nota.velocity) -> nástroj hraje
```

Důležité: piano roll **nic nepřehrává**. Jen mění data (seznam not). Přehrávač
(`Player`) si ta data čte sám ve svém vlákně. Proto se při přehrávání dá klikat
a změna se hned ozve.

### Časová osa -> data -> přehrávač

```
 klik / tažení v řádku stopy
        |
 TimelineView._on_down / _on_motion -> _paint(takt)
        |   track.arrangement[takt] = "A"      (nebo pop = smazat)
        v
 Player v režimu Song: track.pattern_at_bar(takt) -> který pattern a jeho kolikátý takt
```

### Kdo koho volá při výběru stopy

```
 klik na jméno stopy v timeline        výběr v dropdownu Edit (Sound)
        |                                       |
 SongPage._select_from_timeline         SoundPage._choose_track
        \                                     /
         -----> MainFrame.select_track <-----
                    |  keys.set_channel(kanál stopy)   klávesnice teď hraje na její nástroj
                    |  sound_page.select_track(track)
                    |  song_page.select_track(track)
```

Záložky o sobě navzájem nevědí. Domlouvají se přes hlavní okno, které jim při
vytvoření předá funkce (callbacky) jako `on_track_change`. To je dobrá architektura:
každá stránka se dá pochopit samostatně.

### Časovač: co se děje 30x za sekundu

```
 MainFrame._on_tick  (wx.Timer, 30 FPS)
    |- sound_page.tick(analyzer, fresh)    jen když je Sound vidět: klaviatura, grafy
    |- song_page.tick()                    jen když je Song vidět: posun ukazatele
    |- visual_page.tick(analyzer, dt)      když je Visual vidět nebo je otevřený fullscreen
```

---

## Čísla not, oktávy a frekvence (bez hudební teorie)

Tohle je nejdůležitější "fyzika" celé kapitoly, ptají se na to rádi.

- Každá nota je **celé číslo 0 až 127** (tzv. MIDI číslo). Čím vyšší číslo, tím vyšší tón.
- **+1 = o půltón výš.** Půltón je nejmenší krok, jaký piano umí: další klávesa vpravo,
  ať bílá nebo černá.
- **+12 = o oktávu výš.** Oktáva má 12 půltónů. Fyzikálně je tón o oktávu výš
  přesně **dvakrát vyšší frekvence**: A4 = 440 Hz, A5 = 880 Hz, A3 = 220 Hz.
- **60 = C4**, "prostřední C" na pianu (asi 261,6 Hz). **69 = A4 = 440 Hz**, ladička.
- Převod na frekvenci: `f = 440 * 2 ** ((n - 69) / 12)`. Každý půltón násobí frekvenci
  číslem 2^(1/12), asi 1,0595, takže 12 půltónů dá dohromady přesně 2x. Tenhle převod
  v kódu nepíšeme, dělá ho pyo `Notein` v nástroji (vrací rovnou Hz).

Jména: v oktávě je 12 půltónů, `NOTE_NAMES = ("C", "C#", "D", ..., "A#", "B")`
(`sirens/ui/keys.py:31`). Pozor, **anglické B je české H**. Proto komentáře píšou
"C D E F G A H" a v aplikaci vidíš "B".

Funkce `note_name` (`sirens/ui/keys.py:34`) dělá z čísla text:

```python
return f"{NOTE_NAMES[note % 12]}{note // 12 - 1}"
```

- `note % 12` je **zbytek po dělení 12** (operátor `%`, modulo). 60 % 12 = 0, 62 % 12 = 2.
  Je to "kolikátý půltón v oktávě", 0 = C, 2 = D.
- `note // 12` je **celočíselné dělení** (operátor `//`): dělí a zahodí desetinnou část.
  60 // 12 = 5, 71 // 12 = 5, 72 // 12 = 6. Je to "kolikátá oktáva".
- `- 1`: MIDI čísla 0..11 jsou podle konvence oktáva -1, takže číslo oktávy je o jedna menší.
  Výsledek: 60 -> `C4`, 62 -> `D4`, 72 -> `C5`.
- `f"..."` je **f-string**: text, do kterého se ve složených závorkách dosadí hodnoty.

Černé klávesy jsou v každé oktávě na půltónech 1, 3, 6, 8, 10 (C#, D#, F#, G#, A#).
Proto `pitch % 12 in BLACK` (`sirens/ui/pattern_view.py:32`) pozná černou klávesu
u libovolné noty.

---

## Pojmy z Pythonu a wx, které tu potkáš

Každý je vysvětlený tady jednou, v textu dál už jen odkaz.

**Python**

- **`//` a `%`**: celočíselné dělení a zbytek (viz výše). S desetinnými čísly `//` taky
  zaokrouhluje dolů, ale výsledek je pořád float (`156.0 // 53.5 = 2.0`), proto kód píše
  `int(... // ...)`.
- **`divmod(a, b)`**: obojí naráz, vrátí dvojici `(a // b, a % b)`. `divmod(5, 4)` = `(1, 1)`.
- **`enumerate(seznam)`**: při procházení cyklem dává pořadí i prvek:
  `for row, track in enumerate(tracks)` -> `row` = 0, 1, 2..., `track` = stopa.
- **`reversed(seznam)`**: projde seznam od konce.
- **Rozbalení (unpacking)**: `w, h = self.GetClientSize()` dá šířku do `w` a výšku do `h`.
  `path.MoveToPoint(*points[0])`: hvězdička rozbalí dvojici `(x, y)` na dva argumenty.
- **`lambda`**: malá funkce bez jména na jeden řádek. `lambda i: keys.set_hold(i == 1)`
  je totéž jako `def f(i): return keys.set_hold(i == 1)`. Hodí se, když chceš někomu
  předat "co má udělat".
- **Callback**: funkce předaná jako parametr, kterou někdo jiný zavolá později.
  `SoundPage(..., on_track_change)` dostane funkci a zavolá ji, když uživatel vybere stopu.
- **Uzávěr (closure)**: `lambda i: keys.set_hold(i == 1)` (`sirens/ui/sound_page.py:74`)
  si pamatuje proměnnou `keys` z místa, kde vznikla. Když ji panel později zavolá, pořád
  ví, na jaký `KeyboardPlayer` se má ptát, a nikdo jí ho nemusí posílat znovu.
- **Podmíněný výraz** `a if podmínka else b`: `"Unmute" if self.track.muted else "Mute"`.
- **Řetězené porovnání** `0 <= step < n` znamená `0 <= step and step < n`.
- **Ořezání do rozsahu** `min(horní, max(dolní, x))`: `max` nepustí pod dolní mez, `min` nad horní.
- **Seznam z cyklu (list comprehension)**: `[track.name for track in self.song.tracks]`
  vyrobí seznam jmen. Může mít i `if` (`[n for n in pattern.notes if n.step < pattern.steps()]` v `song_page.py`, `_set_length`).
- **Slovník**: `d.get(k)` vrátí hodnotu nebo `None` (nespadne, když klíč chybí);
  `d.pop(k, None)` hodnotu vyndá a smaže; `d.setdefault(k, {})` vrátí hodnotu, a když
  klíč chybí, nejdřív tam dá `{}`.
- **Množina (set)**: každý prvek nejvýš jednou. `add` přidá, `discard` odebere
  (a nespadne, když tam prvek není, na rozdíl od `remove`).
- **`list(x)`**: kopie seznamu. Používá se, když se původní seznam může během procházení
  měnit (mazání v cyklu, nebo jiné vlákno).
- **`is` vs `==`**: `is` = ten samý objekt, `==` = stejná hodnota. `track is self.selected`
  se ptá "je to přesně tahle stopa?".
- **`a or b`**: když je `a` prázdné (prázdný text, 0, None), vezme se `b`.
  `text or self.track.name` = prázdné jméno nepovolím, nechám staré.
- **`try / except`**: zkus to, a když to spadne s danou chybou, udělej tohle místo pádu
  programu (`sound_page.py:124`, načtení presetu).
- **`isinstance(x, Třída)`**: je `x` objekt téhle třídy?
- **`chr(65)`** = `"A"`: číslo znaku na znak.
- **Formát v f-stringu**: `{seconds % 60:02d}` = celé číslo, aspoň 2 číslice, doplnit nulou
  (`5` -> `05`); `{TAIL:.0f}` = desetinné číslo bez desetinných míst.

**wxPython** (základy v [40-okno-a-ovladaci-prvky.md](40-okno-a-ovladaci-prvky.md))

- **Vlastní prvek z `wx.Control`**: `PianoView`, `PatternView`, `TimelineView` nejsou
  hotové widgety, celé se kreslí samy v `_on_paint` a samy reagují na myš.
- **Události myši**: `EVT_LEFT_DOWN` (stisk), `EVT_LEFT_UP` (puštění), `EVT_MOTION`
  (pohyb), `EVT_RIGHT_DOWN`, `EVT_MOUSEWHEEL` (kolečko). `event.GetX()`, `event.GetY()`
  je poloha myši v pixelech **uvnitř prvku**, (0, 0) je levý horní roh, `y` roste dolů.
- **`event.Dragging()`**: pohyb myši se stisknutým tlačítkem.
- **`CaptureMouse()` / `ReleaseMouse()` / `HasCapture()`**: "chytit myš". Po stisku si
  prvek myš přivlastní, takže dostává pohyb i puštění tlačítka, **i když myš vyjede
  z prvku ven**. Bez toho by tažení noty přes okraj nebo puštění klávesy mimo klaviaturu
  nedoběhlo a nota by zůstala viset.
- **`Refresh()`**: "překresli se, až budeš mít čas". wx pak zavolá `_on_paint`.
  `Refresh(False)` = nemazat předem pozadí (méně blikání, stejně kreslíme všechno).
- **`wx.CallAfter(f, args)`**: zavolej `f` až po dokončení právě zpracovávané události.
  Používá se, když kliknutí na tlačítko v panelu má ten samý panel smazat a postavit
  znovu: tlačítko nejde zrušit uprostřed jeho vlastní události.
- **`wx.CallLater(ms, f, args)`**: zavolej `f` za tolik milisekund, mezitím program běží dál.
- **`wx.EventFilter`**: objekt, kterému wx ukáže **každou** událost v aplikaci dřív než
  komukoli jinému. Vrací `Event_Skip` (pusť dál) nebo `Event_Processed` (vyřízeno).
- **`event.Skip()`** v obsluze události: "nech to zpracovat i dál", např. aby se okno
  po našem `_on_close` opravdu zavřelo.
- **`GraphicsContext`**: kreslení s vyhlazováním a průhledností; `gc.Clip(...)` omezí
  kreslení na obdélník, `gc.CreatePath()` vyrobí lomenou čáru.

---

## Soubor po souboru

### `sirens/ui/keys.py`: klávesnice počítače jako piano

**Účel:** převést stisky kláves A, W, S, E... na noty a poslat je nástroji vybrané stopy.
Navíc X / C mění oktávu a mezerník spouští přehrávání.

**Rozložení kláves** (`NOTE_KEYS`, `keys.py:26`) kopíruje piano: spodní řada písmen
(A S D F G H J K L) jsou bílé klávesy, horní řada (W E, T Y U, O P) černé. Hodnota je
"o kolik půltónů nad C":

```python
NOTE_KEYS = {"A": 0, "W": 1, "S": 2, "E": 3, "D": 4, "F": 5, "T": 6, "G": 7,
             "Y": 8, "Z": 8,    # na český klávesnici je Y a Z prohozený, fungujou obě
             "H": 9, "U": 10, "J": 11, "K": 12, "O": 13, "L": 14, "P": 15}
```

Mezi D (E) a F (F) chybí černá, mezi J (H) a K (C) taky, přesně jako na pianu. K, O, L, P
už jsou v další oktávě (12 = zase C, o oktávu výš).

**Třída `KeyboardPlayer(wx.EventFilter)`** (`keys.py:47`). V `__init__` si drží:

- `channel` - MIDI kanál nástroje, na který se hraje (každá stopa má svůj, 1..8),
- `octave` - aktuální oktáva, začíná na 4, takže A = C4 = 60,
- `held` - slovník "držená klávesa -> nota",
- `active` - množina not, které právě znějí (podle ní klaviatura barví klávesy),
- `on_space` - funkce pro mezerník (hlavní okno sem dá `_toggle_playing`),
- `hold` - režim Hold.

Na konci `wx.EvtHandler.AddFilter(self)` se filtr přihlásí do wx. Od té chvíle wx volá
`FilterEvent` pro každou událost v aplikaci.

**`note_on` / `note_off`** (`keys.py:59`, `:64`) jsou jediná místa, kde se opravdu posílá
nota. Note off je stejná zpráva s velocity 0:

```python
self.engine.send_note(self.channel, note, VELOCITY)   # note on, síla 100
self.engine.send_note(self.channel, note, 0)          # note off
```

**`press` / `release`** (`keys.py:69`, `:76`) přidávají logiku režimu Hold:

```python
def press(self, note):
    if self.hold and note in self.active:
        self.note_off(note)           # v Hold druhej stisk notu vypne
    else:
        self.note_on(note)

def release(self, note):
    if not self.hold:
        self.note_off(note)
```

V normálním režimu: stisk = zapnout, puštění = vypnout. V Hold: puštění nedělá nic,
a stisk noty, která už zní, ji vypne. To je celý Hold. (Aby nota v Hold opravdu zněla dál,
musí mít obálka Sustain nad 0, jinak dozní sama, proto to říká nápověda u přepínače.)

**`FilterEvent`** (`keys.py:107`) je srdce souboru. Postupně:

1. Není to stisk ani puštění klávesy? `Event_Skip`, ať si to zpracuje kdokoli jiný.
2. Píše se do textového políčka (`isinstance(..., wx.TextCtrl)`), nebo je držený
   Cmd / Ctrl / Shift (`HasAnyModifiers`)? `Event_Skip`. Jinak by nešlo psát jméno
   stopy a nefungovalo by Cmd+Z (Z je zároveň nota).
3. `key = chr(code) if 32 <= code < 128 else ""` - kód klávesy na znak. Písmena
   chodí jako velká (A = 65), cokoli jiného (šipky, F1...) dá prázdný text.
4. **Puštění klávesy**: když byla v `held`, `self.held.pop(key)` vrátí její notu
   a zároveň ji ze slovníku vyhodí, a zavolá se `release`.
5. **Stisk klávesy s notou**:

   ```python
   if key not in self.held:        # držená klávesa posílá opakovaný stisky, ty ignoruju
       note = 12 * (self.octave + 1) + NOTE_KEYS[key]
       self.held[key] = note
       self.press(note)
   ```

   Proč `if key not in self.held`? Když klávesu držíš, operační systém po chvíli posílá
   opakované stisky (jako když držíš písmeno v textu a píše se "aaaaa"). Bez té kontroly
   by se nota pořád znovu spouštěla.

   Proč si pamatujeme notu v `held`, a ne jen klávesu? Kdybys podržel A, zmáčkl C (oktáva
   nahoru) a pak pustil A, musí se vypnout **ta nota, která se zapnula** (60), ne nová (72).

   Vzorec `12 * (octave + 1) + posun`: C oktávy 4 je 12 * 5 = 60. S (posun 2) -> 62 = D4.
6. **X / C**: oktáva dolů / nahoru, ohlídaná na rozsah 1..7. V normálním režimu se před
   změnou všechno umlčí (`release_all`), v Hold noty zní dál.
7. **Mezerník**: zavolá `on_space`.

**`focus_lost`** (`keys.py:86`): když přepneš do jiné aplikace s drženou klávesou,
událost "puštění" už nikdy nepřijde (dostane ji jiná aplikace). Proto hlavní okno při
ztrátě fokusu volá `focus_lost` a ta noty vypne. V Hold noty na klávesách nezávisí,
takže se jen zapomene `held`.

**`release_all`**: `for note in list(self.active)`. Proč `list()`? `note_off` z množiny
`active` maže, a procházet množinu, která se zrovna mění, Python nedovolí (spadne).
Kopie to řeší.

**`set_channel`**: při výběru jiné stopy nejdřív umlčí všechno, aby nezůstala znít nota
na předchozím nástroji, pak přepne kanál.

### `sirens/ui/piano.py`: klaviatura na obrazovce

**Účel:** ukázat, co právě hraje, a umožnit hrát myší. Kreslí 3 oktávy od oktávy,
na kterou je nastavená klávesnice (A = první C vlevo).

**Konstanty** (`piano.py:14-18`):

- `WHITE_STEPS = (0, 2, 4, 5, 7, 9, 11)` - půltóny bílých kláves v oktávě (C D E F G A H).
- `BLACK_STEPS = {0: 1, 1: 3, 3: 6, 4: 8, 5: 10}` - "za bílou č. 0 (C) je černá s půltónem 1 (C#)",
  za bílou č. 1 (D) černá 3 (D#) atd. Za bílou 2 (E) a 6 (H) žádná černá není.

**`PianoView.__init__`**: pozor, parametr `player` je tady `KeyboardPlayer`, **ne** přehrávač
písně. Klaviatura hraje přes stejný objekt jako klávesnice, takže myš i klávesnice dělají
totéž a Hold platí pro obojí.

**`_keys()`** (`piano.py:40`) spočítá obdélník každé klávesy: `(nota, x, y, šířka, výška, je_černá)`.

```python
white_w = w / (7 * OCTAVES)                       # 21 bílých kláves na celou šířku
for octave in range(OCTAVES):
    base = self._first_note() + 12 * octave       # C téhle oktávy
    for i, step in enumerate(WHITE_STEPS):
        x = (octave * 7 + i) * white_w            # kolikátá bílá zleva krát šířka
        whites.append((base + step, x, top, white_w, h - top, False))
        if i in BLACK_STEPS:
            bx = x + white_w * 0.68
            blacks.append((base + BLACK_STEPS[i], bx, top, white_w * 0.64, (h - top) * 0.6, True))
return whites + blacks
```

Příklad: okno 840 px široké -> bílá klávesa 40 px. Třetí bílá druhé oktávy (`octave=1`,
`i=2`, tj. E) má x = (7 + 2) * 40 = 360. Černá je široká 0,64 bílé (25,6 px), začíná
na 0,68 šířky bílé, takže sahá od 0,68 do 1,32 a sedí přesně přes hranici dvou bílých
(střed na 1,0). Je kratší (60 % výšky). Černé jsou v seznamu **až za bílými**, protože
se kreslí v tomhle pořadí a černé musí být navrchu.

**`_note_at(x, y)`** (`piano.py:63`) je **hit-test**, tedy otázka "na co jsem klikl?":

```python
for note, kx, ky, kw, kh, black in reversed(self._keys()):   # nejdřív černý (jsou navrchu)
    if kx <= x < kx + kw and ky <= y < ky + kh:
        return note
```

Projde obdélníky a vrátí první, ve kterém leží bod myši. `reversed` = od konce, tedy
nejdřív černé. Kdyby šel od začátku, klik na černou klávesu by našel bílou pod ní.

**Myš:**

- `_on_down`: najde notu, zavolá `player.press` a `CaptureMouse()`.
- `_on_up`: pustí myš, zavolá `player.release`.
- `_on_motion`: když táhneš po klávesách (a není Hold), při přechodu na jinou klávesu
  vypne starou notu a zapne novou. V Hold se tažením nehraje, protože každý stisk notu
  přepíná, a tažení by noty náhodně zapínalo a vypínalo.

**`_on_paint`**: nahoře nápověda (včetně "A is now C4" přes `note_name`), pak klávesy.
Klávesa, jejíž nota je v `player.active`, je šedá. Klaviatura sama neví, kdy se něco
změní, proto ji `SoundPage.tick` každý snímek překreslí.

### `sirens/ui/pattern_view.py`: piano roll

**Účel:** editor not jednoho patternu. Svisle výška tónu (nahoře vysoko), vodorovně čas
v krocích. Nota = obdélník: kde začíná = kdy zazní, jak je dlouhý = jak dlouho zní.

**Rozměry** (`pattern_view.py:27-32`):

```
 0,0 +--------+--------------------------------------------+
     |        |  1.1     1.2     1.3     1.4                |  HEADER_H = 20 (čísla dob)
     +--------+--------------------------------------------+
     |  C4    |  řádek 0 = nejvyšší zobrazená nota          |
     |        |  ...                                       |  24 řádků (ROWS)
     |  C3    |  řádek 23 = view_low                       |
     +--------+--------------------------------------------+
     |        |  mezera VEL_GAP = 6                        |
     +--------+--------------------------------------------+
     |  Vel   |  sloupky síly úhozu                        |  VEL_H = 44
     +--------+--------------------------------------------+
      LABEL_W = 44
```

`track.view_low` (v `Track`, výchozí 48 = C3) je nejnižší zobrazená nota. Zobrazuje se
24 výšek, tedy 2 oktávy, od `view_low` do `view_low + 23`.

**Převod pixely <-> buňka.** Tohle je jádro celého souboru a typická otázka u zkoušky.

```python
def _cell(self):                                         # pattern_view.py:62
    w, _ = self.GetClientSize()
    grid_h = self._vel_top() - VEL_GAP - HEADER_H
    return (w - LABEL_W) / self.pattern().steps(), grid_h / ROWS
```

Šířka buňky = šířka mřížky / počet kroků, výška buňky = výška mřížky / 24. Obojí je
desetinné číslo, aby mřížka přesně vyplnila prostor. Když se okno zvětší, buňky se
zvětší (prvek se při `EVT_SIZE` překreslí).

```python
def _step_at(self, x):                                   # pattern_view.py:69
    cell_w, _ = self._cell()
    return int((x - LABEL_W) // cell_w)
```

`x - LABEL_W` = kolik pixelů od začátku mřížky. `// cell_w` = kolik celých buněk se tam
vejde = číslo kroku.

```python
def _at(self, x, y):                                     # pattern_view.py:79
    _, cell_h = self._cell()
    step = self._step_at(x)
    row = int((y - HEADER_H) // cell_h)
    if x < LABEL_W or y < HEADER_H or not (0 <= step < self.pattern().steps()) or not (0 <= row < ROWS):
        return None
    return step, self.track.view_low + ROWS - 1 - row
```

Řádek se počítá stejně jako krok, jen svisle. Pak se **otočí**: řádek 0 je nahoře
a nahoře má být nejvyšší nota. Proto `view_low + 23 - row`: řádek 0 -> `view_low + 23`,
řádek 23 -> `view_low`.

Spočítaný příklad: prvek 900 x 500 px, mřížka 16 kroků, `view_low = 48`.

- `cell_w = (900 - 44) / 16 = 53,5`, `_vel_top = 500 - 44 = 456`,
  `grid_h = 456 - 6 - 20 = 430`, `cell_h = 430 / 24 = 17,9`.
- Klik na (200, 100): `step = (200 - 44) // 53,5 = 156 // 53,5 = 2`,
  `row = (100 - 20) // 17,9 = 4`, `pitch = 48 + 23 - 4 = 67`.
- 67 = G4 (67 % 12 = 7 = G, 67 // 12 - 1 = 4). Nota tedy začne na 3. kroku (krok 2,
  počítá se od 0) a bude to G4.

Kreslení dělá přesný opak: krok -> `x = LABEL_W + step * cell_w`, nota -> řádek
`view_low + ROWS - 1 - pitch` -> `y = HEADER_H + row * cell_h`.

**`_on_down`** (`pattern_view.py:103`):

1. Klik v pruhu Vel (`y >= _vel_top()`) -> začne tažení síly úhozu.
2. Jinak `_at` -> (krok, výška). Mimo mřížku nic.
3. `pattern.note_at(step, pitch)` (v `song.py`) vrátí notu, která na tom místě **zní**,
   tedy i když klikneš doprostřed dlouhé noty. Pokud existuje, smaže se.
4. Jinak se vytvoří `Note(step, pitch, 1)` (délka 1 krok), přidá se, zahraje se
   (`self.preview(pitch)`) a začne tažení (`drag_note`, `CaptureMouse`).

**`_on_motion`** (`pattern_view.py:127`), prodlužování tažením:

```python
step = self._step_at(event.GetX())
end = min(max(step, self.drag_note.step), self.pattern().steps() - 1)
self.drag_note.length = end - self.drag_note.step + 1
```

Konec noty je krok pod myší, ale `max` ho nepustí před začátek noty (táhneš doleva)
a `min` ne za konec patternu. Délka je `konec - začátek + 1`, protože i krok, na kterém
nota začíná, patří do ní (nota od kroku 2 do kroku 5 je dlouhá 4 kroky: 2, 3, 4, 5).

**`_set_velocity`** (`pattern_view.py:90`), síla úhozu z výšky myši:

```python
unit = min(1.0, max(0.0, 1 - (y - self._vel_top()) / VEL_H))
velocity = round(1 + unit * 126)
```

`(y - _vel_top) / VEL_H` je 0 nahoře pruhu a 1 dole. `1 - ...` to otočí (nahoře 1),
`min/max` ořízne, když myš vyjede z pruhu. Pak se 0..1 roztáhne na 1..127. Nula se
nepoužívá, protože velocity 0 znamená v MIDI "vypni notu". Nastaví se všem notám, které
na tom kroku **začínají**, takže akord se změní celý.

**`_on_wheel`**: kolečko nahoru = `view_low + 1` (vidíš o půltón výš), dolů o půltón níž,
ohlídané na rozsah.

**`_on_paint`** (`pattern_view.py:154`) kreslí po vrstvách:

1. Řádky černých kláves tmavší (`pitch % 12 in BLACK`), u každého C jméno a čára.
2. Svislé čáry: slabě každá šestnáctina, víc každá doba, nejvíc každý takt.
   `per_beat = pattern.grid // BEATS_PER_BAR` = kroků na dobu (16 // 4 = 4, u Fine 48 // 4 = 12).
   `per_16th = pattern.grid // STEPS_PER_BAR` = kroků na šestnáctinu (1, u Fine 3):
   `if step % per_16th: continue` přeskočí kroky, které nejsou na šestnáctině, takže
   u Fine se nekreslí čára u každého z 48 kroků.
   Popisek doby: `bar, beat = divmod(step // per_beat, BEATS_PER_BAR)`.
   Např. krok 20: 20 // 4 = 5. doba (od 0), `divmod(5, 4) = (1, 1)`,
   napíše se `2.2` (2. takt, 2. doba, +1 protože lidi počítají od 1).
3. Ukazatel přehrávání (jen v Loop):
   `step = self.player.position // pattern.ticks_per_step() % pattern.steps()`.
   Přehrávač počítá v **tikách** (48 na takt). V mřížce 16 trvá krok 3 tiky (u Fine 1 tik). Tik 50 -> krok
   16, `% 16` -> krok 0 (pattern o 1 taktu je u druhého průchodu zase na začátku).
4. Noty: průhlednost `alpha = 60 + round(195 * velocity / 127)`, tedy od 60 (skoro
   průhledná) do 255 (plná).
5. Sloupky síly úhozu dole, výška úměrná velocity.

### `sirens/ui/timeline_view.py`: časová osa

**Účel:** řádek pro každou stopu, sloupec pro každý takt. Do taktu se "maluje" pattern.
Nahoře čísla taktů (klik = odsud začne Song), vlevo jména stop a `M` (mute).

**Rozměry** (`timeline_view.py:24-28`): sloupec jmen `NAME_W = 130`, hlavička 22, řádek
stopy 30. Takt je široký aspoň `MIN_BAR_W = 14` px.

**Převod x <-> takt:**

```python
def _bar_w(self):                                         # timeline_view.py:56
    return max(MIN_BAR_W, (self.GetClientSize()[0] - NAME_W) / self.song.bars)

def _x(self, bar):                                        # timeline_view.py:68
    return NAME_W + (bar - self.first_bar) * self._bar_w()

def _bar_at(self, x):                                     # timeline_view.py:72
    bar = self.first_bar + int((x - NAME_W) // self._bar_w())
    return bar if x >= NAME_W and 0 <= bar < self.song.bars else None
```

- Šířka taktu = dostupná šířka / počet taktů. Při 512 taktech by vyšlo pod 2 px, do toho
  se nedá kliknout, proto aspoň 14 px. Pak se celá píseň nevejde a ukazuje se jen
  **výřez** od taktu `first_bar`.
- `_x` a `_bar_at` jsou navzájem opačné. `first_bar` posouvá výřez: když je `first_bar = 8`,
  takt 8 je vidět hned u levého okraje.
- `_x` bere i desetinné číslo (`3.5` = půlka 4. taktu), to se hodí pro ukazatel přehrávání.

Příklad: šířka 1000 px, 32 taktů: `bar_w = 870 / 32 = 27,2`. Klik na x = 300:
`(300 - 130) // 27,2 = 6` -> takt 6, tedy sedmý takt písně (v kódu se takty počítají
od 0, v aplikaci se čísla píšou od 1, a to jen u každého čtvrtého: 1, 5, 9...).

**`_row_at(y)`** stejně převádí y na stopu: `(y - HEADER_H) // ROW_H`.

**`_on_down`** (`timeline_view.py:84`) rozhoduje podle toho, kam se kliklo:

1. `y < HEADER_H` (hlavička): `player.start_bar = bar`.
2. Jinak řádek stopy. Vlevo ve sloupci jmen: posledních 28 px je `M` (přepne `muted`),
   zbytek vybere stopu (`on_select`).
3. Vpravo v taktech: **malování**.

   ```python
   erase = track.arrangement.get(bar) == track.current
   self.paint_row = (track, None if erase else track.current)
   ```

   Při prvním kliku se rozhodne, jestli se maže, nebo vkládá, a to pak platí pro celé
   tažení (`paint_row`). Takže tažením přes několik taktů buď všechny vyplníš, nebo
   všechny smažeš, a nepřepíná se to takt po taktu.

**`_paint(bar)`**: `track.arrangement[bar] = name` nebo `track.arrangement.pop(bar, None)`.
`arrangement` je obyčejný slovník "číslo taktu -> jméno patternu".

**Kolečko** (`_on_wheel`, `timeline_view.py:134`):

```python
rotation = event.GetWheelRotation()
if event.GetWheelAxis() == wx.MOUSE_WHEEL_VERTICAL:
    rotation = -rotation
self.wheel += rotation
steps = int(self.wheel / event.GetWheelDelta())
if steps:
    self.wheel -= steps * event.GetWheelDelta()
    self._scroll_to(self.first_bar + steps * WHEEL_BARS)
```

Myš posílá na jeden "cvak" kolečka hodnotu `GetWheelDelta()` (obvykle 120). Touchpad posílá
spoustu malých hodnot (třeba 10). Proto se otočení **sčítá** do `self.wheel` a posune se,
až je ho dost na celý cvak; zbytek zůstane na příště. Otočení dolů je záporné, a dolů
má znamenat "dál v písni", proto se svislé otočení obrací. Jeden cvak = 4 takty.

**`_on_paint`** (`timeline_view.py:152`):

1. Při přehrávání v Song: takt přehrávání = `player.position // TICKS_PER_BAR`. Když
   uteče z výřezu, `_scroll_to(play_bar)` "otočí stránku".
2. `gc.Clip(NAME_W, 0, ...)` - všechno o taktech se kreslí jen vpravo od jmen, nic
   nepřeteče přes jména.
3. Čáry taktů, číslo u každého 4. taktu, značka `start_bar`.
4. Patterny: obdélník v každém taktu. Když předchozí takt má stejný pattern (`continues`),
   kreslí se bez mezery a bez písmenka, takže 4 takty patternu A vypadají jako jeden blok.
5. Ukazatel přehrávání: svislá čára na `_x(position / TICKS_PER_BAR)`, tady obyčejné dělení,
   takže se čára posouvá plynule i uvnitř taktu.
6. Tenký posuvník nahoře ukazuje, jakou část písně výřez zobrazuje.
7. Jména stop a `M` (červené, když je stopa ztlumená).

### `sirens/ui/sound_page.py`: záložka Sound

**`SoundPage(wx.Panel)`** (`sound_page.py:42`), parametry: `engine`, `song`, `keys`
(`KeyboardPlayer`), `on_track_change` (callback do hlavního okna).

**`__init__`**: vlevo sloupec (`wx.BoxSizer(wx.VERTICAL)`) se `ScopeView`, `SpectrumView`,
`StatusPill` a `PianoView`. Vpravo `Sidebar(self, with_fixed=True)`: horní **pevná** část
(Output, Master, Keys) se při `clear()` nemaže, zbytek ano. Přepínač Keys:

```python
self.sidebar.add_choice("Keys", ("Play", "Hold"), 0, lambda i: keys.set_hold(i == 1), fixed=True, ...)
```

`add_choice` zavolá funkci s pořadím vybrané možnosti (0 nebo 1). `lambda i: keys.set_hold(i == 1)`
z toho udělá `True` pro Hold a `False` pro Play.

`self.editor = StackEditor(self.sidebar, "Add block", CATALOG, self.refresh)` - editor bloků
(společný se záložkou Visual), po každé změně zavolá `self.refresh`.

**`refresh`** (`sound_page.py:140`) - vzor, který uvidíš ve všech záložkách: **smaž panel
a postav ho znovu** podle aktuálního stavu. Je to jednodušší, než hlídat, co se změnilo.
Postaví skupinu Track (Copy / Paste, dropdown stop, jméno), skupinu Preset (Save / Load), Envelope (slidery nástroje
přes `add_params`) a bloky přes `editor.show`. Nakonec štítek s cestou zvuku
(`rack.describe()`).

**`_choose_track`** volá `on_track_change` přes `wx.CallAfter`: dropdown, ve kterém
uživatel právě vybírá, je v panelu, který se kvůli tomu smaže a postaví znovu.

**`_save_preset`** (`sound_page.py:109`) a **`_load_preset`** (`sound_page.py:118`): tlačítka
skupiny Preset. Složka je `PRESET_FOLDER` (`assets/presets`, řádek 38) a jde do dialogu
`wx.FileDialog` jako výchozí. Save zapíše `session.sound_of(self.track)` přes
`session.write`, tedy slovník s obálkou (`"instrument"`) a bloky (`"blocks"`). Preset je
jen zvuk, žádné noty. Load soubor přečte (`session.read`), chyby čtení (`OSError`,
`ValueError`) ukáže v hlášce místo pádu, a když ve slovníku chybí klíč `"blocks"`
(například je to celá píseň ze Save v hlavičce), řekne "This file is not a sound
preset." Jinak zvuk nahraje `session.apply_sound` a panel se přestaví (`wx.CallAfter`).
Je to tatáž funkce, kterou používá Paste sound.

**`tick`** (`sound_page.py:170`): každý snímek překreslí klaviaturu; grafy jen když
analyzér má nový úsek zvuku (`fresh`). `duration_ms = SCOPE_VIEW / sample_rate * 1000`
= kolik milisekund zvuku graf vlny ukazuje (počet vzorků / vzorky za sekundu).

### `sirens/ui/song_page.py`: záložka Song

**`SongPage(wx.Panel)`** (`song_page.py:28`) poskládá `PatternView` a `TimelineView`
a vpravo panel. Sama na myš nereaguje, to dělají ty dva prvky.

**`__init__`**: `PatternView(self, player, self._preview)` - piano roll dostane funkci
na přehrání noty. `TimelineView(self, song, player, self._select_from_timeline)`
- timeline dostane funkci na výběr stopy.

**`select_track`** (`song_page.py:53`) nastaví stopu do obou prvků a přestaví panel.

**`refresh`** (`song_page.py:65`) postaví panel:

- Playback: Mode (Loop / Song), Tempo (40..200 bpm), Song length (4..512 taktů po 4),
  délka v minutách.
- Skupina se jménem stopy: Mute / Duplicate / Remove, Pattern A..H, Length (1, 2, 4 takty),
  Grid (16ths / Fine), Clear pattern, Add track.

**`_show_duration`** (`song_page.py:125`):

```python
seconds = round(self.song.bars * BEATS_PER_BAR * 60 / self.song.tempo)
```

Tempo je v dobách za minutu, takže doba trvá `60 / tempo` sekund. Takty x 4 doby x délka
doby. Příklad: 32 taktů při 110 bpm = 32 * 4 * 60 / 110 = 69,8 -> 70 s -> `1:10`
(`seconds // 60` = minuty, `seconds % 60` = zbylé sekundy).

**`_set_mode`**: zastaví přehrávač, přepne režim a když předtím hrálo, zase pustí.

**`_set_length`**: změní počet taktů patternu a vyhodí noty, které začínají za novým koncem.

**`_set_grid`** (`song_page.py:153`): volba Grid vybírá z `GRIDS = (16, 48)` podle pořadí
(`GRIDS[index]`). Poměr `scale = new_grid / pattern.grid` je 3 (16 -> 48) nebo 1/3
(48 -> 16). Každá nota se přepočítá: `step = round(n.step * scale)`, délka podobně
(aspoň 1). Nové noty se skládají do slovníku s klíčem `(krok, výška)` přes
`notes.setdefault(...)`: `setdefault` přidá notu jen když tam ještě nic není, takže když
dvě noty po zaokrouhlení padnou na stejný krok a výšku, zůstane ta první (jinak by
zněly dvakrát nahlas). Nakonec se přepíše `pattern.grid` a `pattern.notes`.

**`_preview`** (`song_page.py:204`):

```python
self.engine.send_note(channel, pitch, 100)
wx.CallLater(200, self.engine.send_note, channel, pitch, 0)
```

Zapne notu a za 200 ms ji vypne. `CallLater` nečeká (neblokuje), jen si naplánuje
budoucí volání, aplikace mezitím normálně běží.

**`tick`**: když přehrávač hraje, překreslí piano roll i časovou osu (aby se hýbal ukazatel).

### `sirens/ui/visual_page.py`: záložka Visual

**`VisualPage(wx.Panel)`** (`visual_page.py:82`): drží `Painter` (počítá obraz z vrstev),
`VisualView` (náhled) a případně otevřené `FullscreenWindow`. Panel vpravo je zase
`StackEditor`, tentokrát s katalogem vrstev.

**`tick(analyzer, dt)`** (`visual_page.py:119`): `image = self.painter.render(analyzer, dt)`
spočítá snímek (pole pixelů výška x šířka x 3 barvy, čísla 0..255) a pošle ho do náhledu
(jen když je záložka vidět) a do fullscreenu (když je otevřený). `dt` je čas od minulého
snímku v sekundách, aby se věci hýbaly stejně rychle, i když snímky nechodí přesně.

**`FullscreenWindow(wx.Frame)`** (`visual_page.py:19`) je samostatné okno:

- Výběr obrazovky: `wx.Display.GetFromWindow(main_window)` = číslo obrazovky s hlavním oknem.
  Cyklus najde první jinou obrazovku (projektor). Když žádná není, zůstane ta hlavní.
  `max(target, 0)` pojistí případ, kdy wx vrátí -1 (nenašlo).
- `Show()` a pak `ShowFullScreen(True)`: na macOS nejde dát přes celou obrazovku skryté okno.
- `show(image)`: `wx.Bitmap.FromBuffer(width, height, image)` udělá z pole pixelů obrázek pro wx.
- `_on_paint`: zvětšení bez deformace.

  ```python
  scale = min(w / bw, h / bh)
  gc.DrawBitmap(self.bitmap, (w - bw * scale) / 2, (h - bh * scale) / 2, bw * scale, bh * scale)
  ```

  Menší z obou poměrů zaručí, že se obrázek vejde celý. Pak se vycentruje, zbytek
  je černý (pruhy nahoře / dole nebo po stranách).
- Esc (`EVT_CHAR_HOOK`) nebo dvojklik okno zavře. `_on_close` dá vědět stránce
  (`on_close` -> `VisualPage._fullscreen_closed` -> `self.fullscreen = None`) a `event.Skip()`
  nechá wx okno opravdu zavřít.

---

## Společné vzory (dobré umět vysvětlit obecně)

1. **Kostra záložky**: vlevo obsah, svislá čára, vpravo `Sidebar`. Vodorovný `BoxSizer`.
2. **`refresh()` = smaž a postav znovu.** Pravý panel se nikdy neupravuje po kouskách.
3. **`wx.CallAfter` u akcí z panelu**, které panel přestaví (prvek nejde zrušit uprostřed jeho události).
4. **`tick()` volané z časovače hlavního okna**, 30x za sekundu. Kreslí se jen to, co je vidět.
5. **Vlastní kreslené prvky**: data -> `_on_paint` je nakreslí; myš -> převod pixelů na data
   -> změna dat -> `Refresh()`. Prvek si nic "nepamatuje" o obrázku, vždy kreslí z dat.
6. **Callbacky místo přímých odkazů**: stránky neznají hlavní okno, jen funkce, které dostaly.

---

## Na co se tě můžou zeptat

**1. Jak se z klávesy S stane zvuk?**
Filtr událostí `KeyboardPlayer.FilterEvent` chytí stisk, z `NOTE_KEYS` zjistí posun 2,
spočítá `12 * (oktáva + 1) + 2 = 62`, uloží si to do `held` a zavolá `press` -> `note_on`
-> `engine.send_note(kanál, 62, 100)`. Engine z toho udělá MIDI zprávu, pyo `Notein`
nástroje na tom kanálu spustí hlas s frekvencí D4 a obálku.

**2. Proč je číslo noty 60 zrovna C4 a co je o oktávu výš?**
Taková je MIDI konvence: C oktávy n je `12 * (n + 1)`, takže C4 = 60. O oktávu výš je
+12 = 72, a fyzikálně je to dvojnásobná frekvence (A4 440 Hz, A5 880 Hz).

**3. Jak funguje režim Hold?**
V `press`: když je Hold zapnutý a nota už zní (je v `active`), stisk ji vypne, jinak zapne.
V `release`: v Hold se nic neděje. Nota tedy zní, dokud ji nezmáčkneš znovu.

**4. Proč filtr událostí, a ne obyčejné `Bind(wx.EVT_KEY_DOWN)`?**
Stisk klávesy dostane jen prvek, který má fokus (třeba slider, na který jsi zrovna klikl).
Filtr vidí všechny události v aplikaci dřív než prvky, takže hraní funguje, ať je kurzor
kdekoli. Výjimka jsou textová políčka a zkratky s Cmd/Ctrl, ty filtr pouští dál.

**5. Jak piano roll pozná, kam jsem klikl?**
Spočítá velikost buňky (`_cell`): šířka mřížky / počet kroků, výška / 24 řádků.
Krok = `(x - LABEL_W) // šířka_buňky`, řádek = `(y - HEADER_H) // výška_buňky`,
výška tónu = `view_low + 23 - řádek` (otočení, protože nahoře jsou vysoké tóny).

**6. K čemu je `CaptureMouse`?**
Aby prvek dostal pohyb a puštění tlačítka i ve chvíli, kdy myš při tažení vyjede z prvku.
Jinak by tažení noty přes okraj přestalo fungovat a puštění klávesy na klaviatuře mimo ni
by nepřišlo, takže by nota zůstala znít.

**7. Hraje piano roll noty, když přehrávám?**
Ne. Piano roll jen mění data (`pattern.notes`). Hraje přehrávač `Player` ve svém vlákně,
který každý tik projde noty a pošle ty, které na daném kroku začínají. Piano roll jen
zahraje krátký náhled (`_preview`) při přidání noty.

**8. Co je takt, krok a tik a jak se mezi nimi převádí?**
Takt = kus času, 4 doby. Krok = políčko mřížky (16 na takt, u Fine 48). Tik = jednotka
přehrávače, 48 na takt (krok šestnáctiny jsou 3 tiky, krok Fine 1 tik). Ukazatel v piano rollu:
`position // ticks_per_step % steps`; v časové ose `position / TICKS_PER_BAR`.

**9. Proč se pravý panel pokaždé celý maže a staví znovu a proč `wx.CallAfter`?**
Je to jednodušší a spolehlivější než hlídat jednotlivé změny. `CallAfter` je tam proto,
že tlačítko, na které jsi klikl, je v tom panelu, a prvek nejde zničit uprostřed zpracování
jeho vlastní události. Proto se přestavba odloží, až událost doběhne.

**10. K čemu je volba Grid a co se stane s notami, když ji přepnu?**
16ths = 16 kroků na takt, Fine = 48 kroků na takt (krok = 1 tik přehrávače), pro noty
hrané "od ruky". `_set_grid` pozice a délky násobí třemi (16 -> 48, přesně), nebo dělí třemi
a zaokrouhlí (48 -> 16). Dvě noty na stejném kroku a výšce se sloučí do první (`setdefault`).
Pattern si grid pamatuje (`pattern.grid`) a ukládá se do souboru.

**11. Co je preset zvuku a čím se liší od uložené písně?**
Preset je soubor `.json` se zvukem jedné stopy: slovník ze `session.sound_of` (obálka
a bloky), bez not a bez časové osy. Save ho zapíše přes `session.write`, Load ho přes
`session.apply_sound` nahraje do vybrané stopy. Celá píseň (Save v hlavičce) je
`session.capture` s tempem, stopami, patterny a obrazem. Load presetu proto odmítne
soubor bez klíče `"blocks"`.

---

## Kde se to napojuje

**Kdo volá moje soubory:**

- `sirens/ui/main_frame.py` (`MainFrame.__init__`) vytváří `KeyboardPlayer`, `SoundPage`,
  `SongPage`, `VisualPage`; nastavuje `keys.on_space = self._toggle_playing`.
- `MainFrame.select_track` volá `keys.set_channel`, `sound_page.select_track`, `song_page.select_track`.
- `MainFrame._on_tick` (časovač 30 FPS) volá `tick` stránek, které jsou vidět.
- `MainFrame._on_activate` volá `keys.focus_lost`;
  `MainFrame._on_close` volá `keys.close` a zavírá fullscreen.
- Open souboru (`MainFrame._apply`) volá `visual_page.refresh` a `select_track`, který přestaví panely Sound a Song.
- `sound_page.py` vkládá `PianoView`; `song_page.py` vkládá `PatternView` a `TimelineView`.
- `piano.py` a `pattern_view.py` berou `note_name` z `keys.py`.

**Co volají moje soubory:**

- `sirens/audio/engine.py`: `send_note` (klávesy, náhled noty), `set_volume` (Master).
- `sirens/song.py`: `Note`, `Pattern`, `BEATS_PER_BAR`, `STEPS_PER_BAR`, `TICKS_PER_BAR`,
  `PATTERN_NAMES`, `MAX_TRACKS`, `MIN_BARS`, `MAX_BARS`, `GRIDS`; atribut `pattern.grid`,
  metody `note_at`, `steps`, `ticks_per_step`, `add_track`, `remove_track`.
- `sirens/audio/player.py` (`Player`): `playing`, `mode`, `position`, `start_bar`,
  `play`, `stop`, `set_tempo`.
- `sirens/session.py`: `sound_of`, `apply_sound` (Copy / Paste sound a presety), `write`, `read` (presety), `duplicate`.
- `sirens/audio/analyzer.py`: `scope`, `spectrum`, `freqs`, `peak_level_db`,
  `peak_frequency`, `SCOPE_VIEW`.
- `sirens/audio/blocks.py` a `sirens/visual/layers.py`: `CATALOG` (co jde přidat).
- `sirens/visual/painter.py`: `Painter.render`.
- `sirens/ui/sidebar.py`, `stack_editor.py`, `views.py`, `widgets.py`, `theme.py`:
  panel, editor bloků/vrstev, grafy, tlačítka, barvy a písma.
