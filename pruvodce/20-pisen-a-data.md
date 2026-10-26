# 20 — Spuštění, data aplikace, píseň, přehrávač, ukládání, undo a export WAV

## Úvod: co tahle část dělá

Tahle kapitola je o "mozku" aplikace, který není vidět. Okna a tlačítka jsou jinde (ve složce `sirens/ui/`), tady jsou data a logika pod nimi:

- **spuštění programu** (`main.py`, `sirens/__main__.py`, `sirens/__init__.py`),
- **slidery obecně** (`sirens/param.py`) a **seznam věcí pod sebou** (`sirens/stack.py`),
- **píseň** jako data: stopy, patterny, noty, časová osa, automatizace (`sirens/song.py`),
- **přehrávač**, který podle těch dat posílá noty nástrojům ve správný čas (`sirens/audio/player.py`),
- **ukládání a načítání** do souboru JSON a autosave (`sirens/session.py`),
- **Undo / Redo** (`sirens/history.py`),
- **export do WAV** (`sirens/audio/export.py`).

Kde to v aplikaci uvidíš:

| Co | Kde v aplikaci |
|---|---|
| Spuštění | `python main.py` nebo `python -m sirens` |
| Píseň, stopy, patterny | záložka **Song**: editor patternu (mřížka s notami), časová osa, panel vpravo (Mode Loop / Song, tempo, délka písně, Grid, Add track, Duplicate, Remove) |
| Přehrávač | tlačítko **Play / Stop** vpravo nahoře a mezerník |
| Automatizace | v záložce Song: vybereš slider a kreslíš body na časovou osu |
| Uložení / načtení | tlačítka **Save** a **Open** v hlavičce, autosave sám na pozadí |
| Undo / Redo | šipky v hlavičce, menu **Edit** (Cmd+Z / Cmd+Shift+Z, na Windows Ctrl+Z / Ctrl+Y) |
| Export WAV | tlačítko **Export WAV** v panelu záložky Song |
| Kopírování zvuku stopy | záložka **Sound** (kopírovat / vložit zvuk), využívá `session.sound_of` a `apply_sound` |

## Jak to spolu souvisí

Data písně:

```
Song                          (sirens/song.py)
 ├─ tempo, bars
 └─ tracks: [Track, Track, ...]          až 8 stop
       ├─ instrument: Instrument         nástroj stopy (obálka + rack bloků), MIDI kanál 1..8
       ├─ patterns: {"A": Pattern, ..., "H": Pattern}
       │      └─ notes: [Note, Note, ...]      Note = (step, pitch, length, velocity)
       ├─ current: "A"                    právě editovaný pattern
       └─ arrangement: {0: "A", 1: "A", 4: "B"}   takt -> pattern (časová osa)
```

Přehrávání:

```
vlákno hodin (Player._run)
   │  každých ~40 ms (1/48 taktu) zavolá
   ▼
Player._on_tick
   ├─ vypne noty, kterým skončila délka   ──► engine.send_note(kanál, výška, 0)
   ├─ spočítá, kde v písni jsme (takt, tik v taktu)
   ├─ (režim Song) nastaví automatizované slidery  ──► owner.set(...)
   └─ zahraje noty, které na tomhle tiku začínají   ──► engine.send_note(kanál, výška, síla)
                                                           │
                                                           ▼
                                            pyo server ► Notein v Instrument ► zvuk
```

Ukládání, autosave a undo:

```
Song + Painter + LightRig ──session.capture()──► slovník (dict)
                                                   │
                ┌──────────────────────────────────┼─────────────────────────────┐
                ▼                                  ▼                             ▼
     session.write(soubor)            json.dumps + change_key()          (záložka Sound)
     Save / autosave každé 2 s        History.record() každou 1/3 s       sound_of / apply_sound
                │                                  │
                ▼                                  ▼
     session.read(soubor)             History.undo() / redo() vrátí text
                │                                  │
                └──────────► session.restore() ◄───┘
                         (postaví píseň, obraz a světlo znovu)
```

## Pojmy z Pythonu, které tu potkáš

Než půjdeme po souborech, rychlý slovníček. Každý pojem je vysvětlený ještě jednou u místa, kde se poprvé objeví.

- **Modul** = jeden `.py` soubor. **Balíček (package)** = složka s moduly a souborem `__init__.py`. `import sirens.song` načte soubor `sirens/song.py`.
- **Třída (class)** = šablona pro objekty. `Song()` vyrobí jeden konkrétní objekt (instanci). `self` je "ten objekt, se kterým metoda zrovna pracuje". `__init__` je funkce, která se zavolá při vytvoření objektu a nastaví mu výchozí hodnoty.
- **Dědičnost**: `class Rack(Stack)` znamená, že Rack umí všechno, co Stack, a může si některé metody **přepsat** (override) po svém.
- **Slovník (dict)** = tabulka klíč -> hodnota, např. `{0: "A", 1: "A"}`. **Seznam (list)** = pořadí hodnot, např. `[1, 2, 3]`. **N-tice (tuple)** = seznam, který se nedá měnit, např. `(16, 12, 24)`.
- **None** = "nic". Funkce, která nic nenašla, vrátí `None`. Zápis `Track | None` v hlavičce funkce říká "vrátí Track, nebo None".
- **Typové nápovědy** (`bars: int`, `-> float`) Python nekontroluje, jsou to jen poznámky pro čtenáře.

## Soubor po souboru

### `main.py` a `sirens/__main__.py`: spuštění

`main.py` je jen "startovací tlačítko":

```python
from sirens.__main__ import main

if __name__ == "__main__":
    main()
```

**`if __name__ == "__main__":`** Každý modul má proměnnou `__name__`. Když soubor spustíš přímo (`python main.py`), má hodnotu `"__main__"`. Když ho někdo jen importuje, má hodnotu jména modulu. Takže kód pod tou podmínkou se spustí jen při přímém spuštění, ne při importu.

**`python -m sirens`** spustí balíček `sirens` jako program. Python v tom případě hledá soubor `sirens/__main__.py`. Proto jde aplikace spustit oběma způsoby a oba skončí ve stejné funkci `main()`.

`sirens/__main__.py:12`:

```python
def main() -> None:
    app = wx.App()
    engine = AudioEngine()
    frame = MainFrame(engine)
    frame.Show()
    app.MainLoop()
```

Řádek po řádku:

1. `wx.App()` vytvoří wxPython aplikaci. Musí existovat dřív než jakékoli okno.
2. `AudioEngine()` nastartuje **pyo server** (to je ta část pyo, která mluví se zvukovou kartou). Musí běžet dřív, než se vytvoří první pyo objekty (bloky, nástroje), jinak pyo vyhodí chybu. Proto je engine před oknem: okno při svém vytvoření rovnou vyrábí stopu s nástrojem.
3. `MainFrame(engine)` vytvoří hlavní okno a předá mu engine.
4. `frame.Show()` okno ukáže.
5. `app.MainLoop()` je **smyčka událostí**: program tu "visí" a čeká na kliknutí, klávesy, časovače a volá na ně správné funkce. Skončí, až se zavře okno.

`sirens/__init__.py` jen dělá ze složky balíček a nese číslo verze `__version__ = "0.1.0"`.

### `sirens/param.py`: popis slideru a základ pro všechno se slidery

Problém, který to řeší: zvukové bloky, vrstvy obrazu, nástroj i světlo mají slidery. Kdyby měl každý svůj ručně psaný panel, bylo by to hodně opakovaného kódu. Místo toho každá věc jen **popíše**, jaké slidery má, a UI je vykreslí jednou společnou funkcí (`Sidebar.add_params`).

**Dataclass** (`sirens/param.py:12`): dekorátor `@dataclass` nad třídou řekne Pythonu "tohle je jen balík dat", a Python sám vyrobí `__init__` z vyjmenovaných polí. Takže `Param("Frequency", 20, 20000, 440, "Hz", log=True)` funguje, aniž bys psal `__init__`. Pole s `= ...` mají výchozí hodnotu a dají se vynechat.

Pole `Param`:

| pole | význam |
|---|---|
| `label` | popisek, zároveň klíč, pod kterým je hodnota uložená |
| `lo`, `hi` | nejmenší a největší hodnota |
| `default` | výchozí hodnota (dvojklik na slider ji vrátí) |
| `unit` | jednotka, např. `"Hz"` |
| `log` | logaritmický slider, pro frekvence a časy (aby šlo jemně nastavit malé hodnoty, třeba 20 až 200 Hz, a přitom dojet až na 20 000 Hz) |
| `help` | krátké vysvětlení pod sliderem |
| `step` | větší než 0 = slider skáče po krocích (1 = celá čísla) |
| `choices` | místo slideru řada tlačítek |

`Choice(...)` (`sirens/param.py:26`) je zkratka pro parametr s možnostmi (např. tvar vlny Sine / Saw / Square). Vrátí obyčejný `Param` od 0 do počtu možností minus 1, s krokem 1. Hodnota je tedy číslo vybrané možnosti (0 = Sine, 1 = Saw...).

`Adjustable` (`sirens/param.py:36`) je **základní třída** pro všechno, co má slidery. Dědí z ní `Instrument`, `Block`, `Layer` a `LightRig`.

```python
def __init__(self):
    self.settings = {p.label: p.default for p in self.PARAMS}
    self.automation = {}
```

- `{p.label: p.default for p in self.PARAMS}` je **dict comprehension**: zkrácený zápis "projdi všechny parametry a z každého udělej dvojici popisek -> výchozí hodnota". Výsledek je třeba `{"Attack": 0.01, "Decay": 0.3, ...}`.
- `self.PARAMS` je seznam definovaný v potomkovi (třída `Instrument` má svůj, `Block` svůj). V `Adjustable` je prázdný.
- `automation` je slovník popisek -> {takt: hodnota}, viz automatizace níže.
- `get` a `set` jen čtou a zapisují do `settings`. Potomci si `set` přepíšou, aby změna šla rovnou i do zvuku (např. `Instrument.set` při změně "Volume" posune hlasitost v pyo).

### `sirens/stack.py`: seznam věcí pod sebou

`Stack` (`sirens/stack.py:10`) je seřazený seznam prvků, které uživatel skládá pod sebe: bloky zvuku v racku nástroje a vrstvy obrazu. Umí `add`, `remove`, `clear`, `toggle` (vypnout/zapnout) a `move` (posunout nahoru/dolů). Po každé změně zavolá `self.changed()`.

V samotném `Stack` jsou `create` a `changed` skoro prázdné. Jde o **háčky (hooks)** pro potomky:

- `Rack(Stack)` (v `sirens/audio/rack.py`) přepíše `create`, protože blok potřebuje při vytvoření dostat svůj nástroj: `block_class(self.instrument)`. A přepíše `changed`, kde znovu propojí zapnuté bloky shora dolů a pošle výsledek nástroji.
- `Painter(Stack)` (v `sirens/visual/painter.py`) přepisovat nic nemusí, vrstvy se zpracují až při kreslení.

Pár detailů:

```python
def add(self, item_class):
    item = self.create(item_class)
```

`item_class` je **třída**, ne objekt (třeba `Filter`). V Pythonu se třída dá předat jako hodnota a zavolat později. Tím pádem `Stack` nemusí vědět, jaké druhy bloků existují.

```python
self.items[i], self.items[j] = self.items[j], self.items[i]
```

Prohození dvou prvků. Pravá strana se nejdřív vyhodnotí celá (vznikne dvojice), pak se přiřadí doleva. Žádná pomocná proměnná není potřeba. Podmínka `if 0 <= j < len(self.items)` hlídá, aby se prvek nahoře nedal posunout ještě výš (a dole níž).

`toggle` prvek nesmaže, jen přepne `item.enabled`. Vypnutý blok si nechá nastavení, rack ho jen přeskočí.

### `sirens/song.py`: píseň jako data

Tohle je nejdůležitější soubor kapitoly. Popisuje, **co** se má hrát. Sám nic nehraje, to dělá přehrávač.

#### Čas: takt, doba, krok, tik

Bez hudební teorie:

- **Doba** je jedno "ťuknutí", když počítáš do rytmu. **Tempo** v BPM (beats per minute) říká, kolik dob je za minutu. Při tempu 120 trvá doba 60 / 120 = 0,5 s.
- **Takt** je kus času o 4 dobách (`BEATS_PER_BAR = 4`). Při tempu 120 tedy 2 sekundy. Časová osa je rozdělená na takty, číslují se od 0.
- **Krok** je políčko v mřížce editoru patternu. Kolik kroků má takt, určuje **mřížka (grid)**: `GRIDS = (16, 12, 24)`.
  - 16 = 4 kroky na dobu (klasické "šestnáctiny"),
  - 12 = 3 kroky na dobu (trioly, rytmus "ta-ka-ta"),
  - 24 = 6 kroků na dobu (jemnější trioly).
- **Tik** je nejmenší jednotka času přehrávače. `TICKS_PER_BAR = 48` tiků na takt.

Proč zrovna 48? Protože je to **nejmenší číslo dělitelné 16, 12 i 24**. Díky tomu každý krok každé mřížky začíná přesně na celém tiku: u mřížky 16 je krok 3 tiky, u 12 jsou to 4 tiky, u 24 jsou to 2 tiky. Přehrávač tak může jet jedním tempem tiků a obsloužit všechny mřížky najednou (každá stopa může mít jinou).

#### `Note` (`sirens/song.py:39`)

Dataclass se čtyřmi čísly:

- `step`: na kterém kroku nota začíná (od začátku patternu),
- `pitch`: jak vysoko, jako **MIDI číslo** (60 = C4, střed klavíru; +1 = o půltón výš, +12 = o oktávu výš, tj. dvojnásobná frekvence),
- `length`: jak dlouho zní, v krocích,
- `velocity`: síla úhozu 1..127, tj. jak nahlas (MIDI standard).

#### `Pattern` (`sirens/song.py:46`)

Pattern je krátký kus hudby, 1, 2 nebo 4 takty dlouhý, se seznamem not. Má `bars` (počet taktů), `grid` (mřížka) a `notes`.

- `steps()` = `bars * grid`, kolik políček má celý pattern.
- `ticks_per_step()` = `48 // grid`. `//` je **celočíselné dělení** (bez desetinné části).
- `note_at(step, pitch)` najde notu, která na daném políčku zní (začíná tam, nebo tam ještě trvá). Používá to editor patternu, když klikneš do mřížky.

`set_grid` (`sirens/song.py:59`) je nejsložitější kousek. Když přepneš mřížku třeba z 16 na 12, noty se musí přepočítat, aby zůstaly zhruba na stejném místě v čase:

```python
old, self.grid = self.grid, grid
kept = []
for note in sorted(self.notes, key=lambda n: n.step):
    step = int(note.step * grid / old + 0.5)
    length = max(1, int(note.length * grid / old + 0.5))
    if step >= self.steps() or any(n.pitch == note.pitch and n.step == step for n in kept):
        continue
    for other in kept:
        if other.pitch == note.pitch and other.step < step < other.step + other.length:
            other.length = step - other.step
    kept.append(Note(step, note.pitch, min(length, self.steps() - step), note.velocity))
self.notes = kept
```

- `old, self.grid = self.grid, grid`: zapamatuje si starou mřížku a hned nastaví novou (zase přiřazení dvojice).
- `sorted(..., key=lambda n: n.step)`: seřadí noty podle začátku. **`lambda`** je malá bezejmenná funkce na jeden řádek; `lambda n: n.step` znamená "z noty vezmi její step". `sorted` podle toho řadí.
- `note.step * grid / old`: přepočet ve stejném poměru. Krok 4 z 16 je čtvrtina taktu, ve 12 je čtvrtina taktu krok 3.
- `int(x + 0.5)`: zaokrouhlení, kde půlka jde vždy nahoru. Proč ne `round()`? Protože Pythonové `round(2.5)` dá 2 (zaokrouhluje půlky k sudému číslu), což by noty posouvalo nepředvídatelně.
- `max(1, ...)`: délka nejméně 1 krok, jinak by krátká nota zmizela.
- `continue` přeskočí notu, která by padla za konec patternu nebo na místo, kde už stejně vysoká nota je (po zaokrouhlení můžou dvě noty splynout).
- `any(...)` vrátí True, pokud aspoň jedna položka splní podmínku.
- Vnitřní `for other in kept`: když dřívější nota stejné výšky ještě zní v místě, kde tahle začíná, zkrátí se, aby se nepřekrývaly.
- `min(length, self.steps() - step)`: délka se ořízne, aby nota nepřelezla konec patternu.

#### `Track` (`sirens/song.py:91`)

Stopa = jeden nástroj a jeho noty. V `__init__`:

- `Instrument(channel)` vytvoří nástroj na daném MIDI kanálu (každá stopa má svůj, 1..8, aby přehrávač mohl poslat notu právě jí).
- `{name: Pattern() for name in PATTERN_NAMES}`: osm prázdných patternů A až H (`PATTERN_NAMES` je řetězec `"ABCDEFGH"` a `for` přes řetězec prochází znaky).
- `current = "A"`: který pattern se edituje.
- `arrangement`: časová osa, slovník **číslo taktu -> jméno patternu**. Prázdný takt (klíč chybí) = stopa mlčí.
- `muted`: ztlumená stopa.
- `view_low = 48`: jen kam je odrolovaný editor patternu (nejnižší viditelná nota). Nic nehraje, je to pohled.

`automated_owners()` vrátí nástroj a všechny jeho bloky, tedy všechno, co může mít automatizaci.

`pattern_at_bar(bar)` (`sirens/song.py:105`) odpoví na otázku "co tahle stopa hraje v taktu `bar`, a kolikátý takt toho patternu to je?":

```python
name = self.arrangement.get(bar)
if name is None:
    return None
start = bar
while self.arrangement.get(start - 1) == name:
    start -= 1
pattern = self.patterns[name]
return pattern, (bar - start) % pattern.bars
```

- `dict.get(klíč)` vrátí hodnotu, nebo `None`, když klíč neexistuje (na rozdíl od `dict[klíč]`, které by spadlo s chybou).
- Smyčka `while` couvá doleva, dokud je v předchozím taktu stejný pattern. Tím najde `start`, kde tenhle souvislý kus začal.
- `(bar - start) % pattern.bars`: `%` je **zbytek po dělení**. Když je 2taktový pattern A položený na taktech 4, 5, 6, 7, pak takt 6 je `(6 - 4) % 2 = 0`, tedy znovu 1. takt patternu. Pattern se tak opakuje dokola, dokud na časové ose pokračuje.

#### `Song` (`sirens/song.py:122`)

- `tempo = 110`, `bars = 32` (délka časové osy), `tracks = []`.
- `add_track()`:

  ```python
  used = {track.instrument.channel for track in self.tracks}
  free = [ch for ch in range(1, MAX_TRACKS + 1) if ch not in used]
  ```

  První řádek je **set comprehension** (množina obsazených kanálů), druhý **list comprehension** (seznam volných kanálů 1..8). `range(1, 9)` dá čísla 1 až 8 (konec se nepočítá). Nová stopa dostane první volný kanál. Když žádný není, vrátí `None` a UI ukáže hlášku. Jméno se skládá **f-stringem** `f"Track {len(self.tracks) + 1}"`: do `{}` se dosadí hodnota výrazu.
- `remove_track()` nejdřív vyprázdní rack nástroje (tím nástroj ztichne) a pak stopu vyhodí ze seznamu.
- `last_bar()` (`sirens/song.py:142`) vrátí, kolik taktů je potřeba přehrát do konce posledního použitého taktu. Takty za délkou písně (`bar < self.bars`) se nepočítají: když píseň zkrátíš, data za koncem zůstanou, jen nehrají, a po prodloužení se vrátí. `+ 1` je tam proto, že takty se číslují od 0: když je poslední použitý takt 7, píseň má 8 taktů.
- `outputs()` vrátí zvukové výstupy všech nástrojů. Engine je sečte do jednoho mixu.

#### Automatizace a `lane_value` (`sirens/song.py:157`)

**Automatizace** = slider, který se během písně hýbe sám. Uživatel na časovou osu nakreslí body "v taktu 0 má Filter hodnotu 200, v taktu 8 hodnotu 2000". Uloží se to do `owner.automation["Frequency"] = {0: 200, 8: 2000}`. Jednomu slovníku `{takt: hodnota}` se říká **lane** (pruh).

`lane_value(lane, position)` spočítá hodnotu v libovolném místě. `position` je v taktech a může být desetinná (3.5 = půlka 4. taktu):

```python
bars = sorted(list(lane))
if position <= bars[0]:
    return lane[bars[0]]
for left, right in zip(bars, bars[1:]):
    if left <= position < right:
        t = (position - left) / (right - left)
        return lane[left] + t * (lane[right] - lane[left])
return lane[bars[-1]]
```

- `sorted(list(lane))`: seřazené takty, kde jsou body.
- Před prvním bodem platí hodnota prvního bodu, za posledním hodnota posledního (`bars[-1]` je poslední prvek seznamu).
- `zip(bars, bars[1:])` dá dvojice sousedů: pro `[0, 8, 16]` to jsou `(0, 8)` a `(8, 16)`. `bars[1:]` je seznam bez prvního prvku (**slicing**).
- **Lineární interpolace**: `t` je 0 na levém bodu a 1 na pravém. Hodnota je levá hodnota plus `t`-násobek rozdílu. V půlce mezi 200 a 2000 tedy 1100. Na grafu je to rovná čára mezi body.

### `sirens/audio/player.py`: přehrávač

Přehrávač je **hodinový strojek**. 48krát za takt "tikne" a při každém tiku se podívá, které noty mají právě začít nebo skončit, a pošle je nástrojům.

#### Proč vlastní vlákno

**Vlákno (thread)** je kus programu, který běží souběžně se zbytkem. Normálně program dělá jednu věc po druhé; s vláknem může okno překreslovat a zároveň jinde tikají hodiny.

Proč ne časovač okna (`wx.Timer`, který okno používá 30x za sekundu na překreslení)? Ten se spouští z hlavní smyčky okna, a když překreslování chvíli trvá, časovač se zpozdí. Hudba by "plavala". Vlastní vlákno jen spí a probouzí se v přesně spočítaných časech.

Proč ne `pyo.Metro` (metronom přímo v pyo, ten by byl nejpřesnější)? Protože jeho zpětné volání běží ve zvukovém vlákně pyo a noty poslané odtamtud pyo zahodí.

#### Stav přehrávače (`sirens/audio/player.py:29`)

- `mode`: `"Loop"` (každá stopa dokola hraje svůj právě editovaný pattern, na zkoušení) nebo `"Song"` (hraje se časová osa a hýbe se automatizace).
- `playing`: běží hodiny?
- `start_bar`: odkud hrát v režimu Song (klikneš do hlavičky časové osy).
- `tick`: tik, který se zahraje **příště**. `position`: tik, který **právě** hraje (podle něj UI kreslí ukazatel).
- `pending`: seznam not, které hrají a čekají na vypnutí. Každá položka je `[zbývá_tiků, kanál, výška]`.
- `once`: pro export. V režimu Song se na konci neopakuje, hodiny se zastaví.

#### Délka tiku (`sirens/audio/player.py:41`)

```python
return 60 / self.song.tempo * BEATS_PER_BAR / TICKS_PER_BAR
```

60 / tempo = délka doby v sekundách. Krát 4 = délka taktu. Děleno 48 = délka tiku. Při tempu 120: 0,5 s × 4 / 48 ≈ 0,042 s, tedy asi 42 ms. Tempo se čte při každém tiku znovu, takže `set_tempo` jen přepíše `song.tempo` a hodiny se přizpůsobí samy.

#### `play` a `stop` (`sirens/audio/player.py:51`, `:68`)

```python
self.thread = threading.Thread(target=self._run, daemon=True)
self.thread.start()
```

`threading.Thread(target=funkce)` připraví vlákno, které spustí danou funkci; `start()` ho rozjede. `daemon=True` znamená, že takové vlákno nebrání ukončení programu (když se zavře okno, nečeká se na něj).

`play(from_tick=...)`: odkud začít. Bez parametru se začne od 0 (Loop) nebo od `start_bar * 48` (Song). S parametrem pokračuje z daného místa, používá to Undo/Redo, aby hudba po vrácení změny hrála dál tam, kde byla. Pokud předchozí vlákno skončilo samo (konec exportu), `join()` na něj nejdřív počká.

`stop()` nastaví `playing = False` (smyčka v `_run` to uvidí a skončí), pak `thread.join()`. **`join()`** = "počkej, až to vlákno doběhne". Teprve potom vypne všechny noty v `pending` (pošle velocity 0), jinak by zůstaly viset a zněly donekonečna.

`toggle()` je zkratka: když hraje, zastav, jinak spusť.

#### Hodiny: `_run` (`sirens/audio/player.py:87`)

```python
next_time = time.perf_counter()
while self.playing:
    try:
        self._on_tick()
    except Exception:
        traceback.print_exc()
    next_time += self._tick_time()
    delay = next_time - time.perf_counter()
    if delay > 0:
        time.sleep(delay)
```

- `time.perf_counter()` jsou nejpřesnější hodiny, které Python má, vhodné na měření krátkých úseků.
- **Klíčový trik**: čas dalšího tiku se počítá jako "minulý plánovaný čas + délka tiku", ne "teď + délka tiku". Kdyby se počítalo od "teď", každé malé zpoždění (třeba 1 ms, než se `_on_tick` provede) by se přičetlo k dalšímu a za minutu by hudba ujela. Takhle se zpoždění nesčítají: když jeden tik přijde o 1 ms později, další spánek je o 1 ms kratší.
- `if delay > 0`: když jsme pozadu, nespí se vůbec a tik se dotáhne hned.
- **`try / except`**: když v `_on_tick` nastane chyba, program nespadne; `except` ji chytí, `traceback.print_exc()` ji vypíše do terminálu a hodiny jedou dál.

#### Jeden tik: `_on_tick` (`sirens/audio/player.py:104`)

Má tři kroky.

**1) Vypnout doznělé noty** (`:107`). Každé položce v `pending` ubere jeden tik. Když dojde na 0, pošle note-off (`send_note(kanál, výška, 0)`), jinak ji nechá v seznamu `still`. Vypínání je schválně **před** zapínáním: když po notě hned navazuje stejně vysoká nota, nejdřív se stará vypne a pak nová zapne, a nová tak nezanikne.

**2) Kde jsme** (`:117`):

```python
if self.mode == "Loop":
    self.tick %= self.loop_ticks()
elif self.tick >= self.song.last_bar() * TICKS_PER_BAR:
    if self.once:
        self._finish()
        return
    self.tick = self.start_bar * TICKS_PER_BAR if self.start_bar < self.song.last_bar() else 0
bar, tick_in_bar = divmod(self.tick, TICKS_PER_BAR)
```

- V Loop se tik "zabalí" zbytkem po dělení délkou smyčky (`loop_ticks()` = nejdelší z právě editovaných patternů). Takže po posledním tiku smyčky přijde zase 0.
- V Song: když jsme za koncem písně, buď končíme (export, `once`), nebo skočíme zpátky na `start_bar` (pokud ještě leží v písni, jinak na 0).
- **`divmod(a, b)`** vrátí najednou celočíselný podíl a zbytek. Tik 100 → `divmod(100, 48) = (2, 4)`: takt 2, tik 4 v tom taktu.
- Zápis `x if podmínka else y` je **podmíněný výraz**: hodnota x, když podmínka platí, jinak y.

**3) Zahrát noty** (`:129`): pro každou stopu se spočítá `tick_in_pattern`, tedy kolikátý tik od začátku patternu teď je.

- Loop: `self.tick % (pattern.bars * 48)`. Kratší pattern se ve smyčce opakuje (1taktový se ve 4taktové smyčce zahraje čtyřikrát).
- Song: nejdřív `_automate` nastaví automatizované slidery podle přesné pozice `bar + tick_in_bar / 48` (takže se hýbou plynule i uvnitř taktu, ne skokem po taktech). Pak `pattern_at_bar(bar)` řekne, co stopa v tomhle taktu hraje; když nic, `continue` přeskočí na další stopu. `tick_in_pattern = bar_in_pattern * 48 + tick_in_bar`.
- Ztlumená stopa (`muted`) noty nehraje, ale automatizace se u ní počítá dál.

Nakonec `position = tick` (pro UI) a `tick += 1`.

#### `_play_notes` (`sirens/audio/player.py:161`)

```python
per_step = pattern.ticks_per_step()
step, rest = divmod(tick_in_pattern, per_step)
if rest:
    return
...
for note in list(pattern.notes):
    if note.step == step:
        self.engine.send_note(channel, note.pitch, note.velocity)
        self.pending.append([note.length * per_step, channel, note.pitch])
```

- Tik, který nepadne přesně na začátek kroku (zbytek `rest` není 0), nic nespouští. U mřížky 16 se tedy noty spouští jen na tikách 0, 3, 6, 9...
- `list(pattern.notes)` udělá kopii seznamu. Proč? Uživatel může zrovna v okně kreslit noty (jiné vlákno mění seznam) a procházet seznam, který se pod rukama mění, je nebezpečné.
- `send_note` pošle notu nástroji jako **MIDI zprávu** (stejnou, jako by přišla z MIDI klávesnice). Nástroj v pyo (`Notein`) ji přijme na svém kanálu.
- Do `pending` se zapíše, za kolik tiků notu vypnout: délka v krocích × tiků na krok.

#### `_finish` (`sirens/audio/player.py:148`)

Konec písně při exportu. Volá se **ve vlákně hodin**, takže nesmí volat `stop()`: ten dělá `join()` na vlákno hodin, tedy by čekal sám na sebe (Python to nedovolí a vyhodí chybu). Proto jen vypne čekající noty a nastaví `playing = False`. Smyčka v `_run` pak skončí sama a okno si toho všimne ve svém časovači.

#### `_automate` (`sirens/audio/player.py:177`)

Projde nástroj a bloky stopy, pro každou lane spočítá `lane_value` a pokud se hodnota opravdu změnila (o víc než `1e-6`, tj. 0,000001, malá rezerva kvůli nepřesnosti desetinných čísel), zavolá `owner.set(...)`. Tím se změní nastavení i zvuk. `list(owner.automation.items())` je zase kopie, protože uživatel může zrovna kreslit body.

### `sirens/session.py`: ukládání, načítání, autosave, kopírování

#### Co je JSON

**JSON** je textový formát na data. Vypadá skoro jako slovníky a seznamy v Pythonu: `{"tempo": 110, "tracks": [...]}`. Modul `json` umí `json.dumps(data)` (Python → text) a `json.loads(text)` (text → Python). Omezení: **klíče slovníku musí být text**. Proto se takty v aranžmá a v automatizaci ukládají jako `"3"` místo `3` a při načtení se zase převádí `int(bar)`.

#### Uložení: `capture` (`sirens/session.py:67`)

`capture(song, painter, rig)` posbírá celý stav aplikace do jednoho slovníku: tempo, délka, stopy, vrstvy obrazu a nastavení světla. Ukládá se jen to, co uživatel vytvořil, ne pyo objekty (ty se při načtení postaví znovu).

Stopu převádí `_track` (`:52`), zvuk stopy `sound_of` (`:37`):

```python
return {
    "name": track.name,
    ...
    **sound_of(track),
    "patterns": {name: {"bars": pattern.bars, "grid": pattern.grid,
                        "notes": [[n.step, n.pitch, n.length, n.velocity] for n in pattern.notes]}
                 for name, pattern in track.patterns.items()},
    "arrangement": {str(bar): name for bar, name in track.arrangement.items()},
}
```

- **`**slovník`** uvnitř `{...}` "vysype" všechny dvojice z jiného slovníku do tohohle. `sound_of` vrací `{"instrument": ..., "automation": ..., "blocks": [...]}` a ty tři klíče se tak stanou součástí slovníku stopy.
- `.items()` dává dvojice (klíč, hodnota) ze slovníku.
- Nota se ukládá jako seznam čtyř čísel `[krok, výška, délka, síla]`, je to kratší než slovník.
- `dict(instrument.settings)` dělá **kopii**. Bez ní by se do výsledku dostal odkaz na živé nastavení a pozdější změna slideru by změnila i "uložený" stav.
- `_lanes` (`:30`) převede automatizace na textové klíče a prázdné lane vynechá.
- `block.extra()` je místo pro data mimo slidery (např. cesta k načtenému zvukovému souboru).

#### Načtení: `restore` (`sirens/session.py:149`)

Postaví aplikaci podle slovníku:

1. Smaže všechny stopy. `for track in list(song.tracks)`: prochází **kopii** seznamu, protože z originálu během cyklu maže (mazat ze seznamu, přes který zrovna jdeš, přeskakuje prvky).
2. Nastaví tempo a délku. `min(MAX_BARS, max(MIN_BARS, ...))` je ořez do rozsahu 4..512.
3. Pro každou uloženou stopu vytvoří novou (`add_track`) a naplní ji (`_restore_track`). Když se nic nenačte, přidá aspoň jednu prázdnou stopu.
4. Vyprázdní obraz a přidá vrstvy podle jména (`LAYERS_BY_NAME`), nastaví světlo.

Odolnost proti starým nebo poškozeným souborům:

- Všude se používá `data.get(klíč, výchozí)`. Když klíč v souboru chybí, nespadne to a vezme se výchozí hodnota.
- `_set_values` (`:81`) nastaví jen slidery, které objekt opravdu má. Neznámé (ze starší verze) přeskočí.
- Blok nebo vrstva s neznámým jménem se vynechá (`if block_class is None: continue`).
- `_list` (`:143`) vezme ze souboru jen položky, které jsou slovníky; cokoli jiného bere jako prázdný seznam.
- Starší soubory neměly `"grid"` (pak 16) a noty měly jen 3 čísla. `Note(*note)` funguje pro oba případy: **`*seznam`** rozbalí seznam do argumentů funkce, takže `Note(*[0, 60, 4])` je totéž co `Note(0, 60, 4)` a `velocity` dostane výchozích 100.

`BLOCKS_BY_NAME` (`:24`) je slovník jméno → třída, např. `{"Filter": FilterBlock, ...}`. Díky němu se z textu v souboru dá zase vyrobit správný blok.

`apply_sound` (`:94`) nastaví stopě zvuk ze slovníku: vyprázdní rack, nastaví obálku, přidá bloky a na konci zavolá `rack.changed()`, aby se bloky znovu propojily (některé mohly být uložené vypnuté a `add` je propojil ještě jako zapnuté).

`duplicate` (`:129`) je hezký trik: stopu převede na slovník (`_track`), změní jméno, vymaže aranžmá a nahraje to do nové stopy (`_restore_track`). Kopie tedy zadarmo. Aranžmá je prázdné schválně: kdyby kopie hrála ve stejných taktech, jen by zdvojnásobila hlasitost.

#### Bezpečný zápis: `write` (`sirens/session.py:173`)

```python
path.parent.mkdir(parents=True, exist_ok=True)
temp = path.with_suffix(".tmp")
temp.write_text(json.dumps(data, indent=1), encoding="utf-8")
os.replace(temp, path)
```

- **`Path`** (z modulu `pathlib`) je objekt pro cestu k souboru. Cesty se skládají operátorem `/`: `Path.home() / ".sirens" / "autosave.json"` je `~/.sirens/autosave.json` v domovské složce. `path.parent` je složka, `path.name` jméno souboru.
- `mkdir(parents=True, exist_ok=True)` vytvoří složku (i nadřazené), a nevadí, když už existuje.
- Nejdřív se zapisuje do **dočasného souboru** `.tmp`, a teprve celý hotový se `os.replace` přejmenuje na cílové jméno. Přejmenování je jeden krok (atomická operace): buď proběhne celé, nebo vůbec. Kdyby program spadl uprostřed zápisu, poškodí se jen `.tmp` a starý soubor zůstane celý.
- `indent=1` dělá odsazený, čitelný JSON. `encoding="utf-8"` kvůli diakritice.

`read` (`:185`) přečte text a `json.loads` z něj udělá slovník.

#### Autosave

Řídí ho hlavní okno (`sirens/ui/main_frame.py`): každé 2 sekundy zavolá `capture`, převede na text a **jen když se text liší** od posledního uloženého, zapíše ho `session.write(session.AUTOSAVE, ...)`. Při spuštění autosave načte. Když je soubor poškozený, začne s prázdnou písní. Při zavření okna se uloží ještě jednou.

### `sirens/history.py`: Undo / Redo

#### Princip: snímky celého stavu

Undo tu nefunguje tak, že by si program pamatoval jednotlivé akce ("přidal notu", "posunul slider"). Místo toho si pamatuje **celý stav** jako JSON text (ten samý, co jde do autosave). Undo = načti předchozí text přes `session.restore`. Výhoda: funguje to automaticky pro úplně každou změnu, nikde se nemusí nic dopisovat.

Hlavní okno každou 1/3 sekundy (`SNAPSHOT_EVERY = 10` snímků při 30 FPS) zavolá `history.record(text, klíč)`. Když je zmáčknuté tlačítko myši, čeká se: celé tažení slideru nebo noty je pak jeden krok, ne desítky.

#### Dva zásobníky

**Zásobník (stack)** je seznam, kam se přidává navrch a bere se z vrchu (`append` a `pop`). Jako hromádka talířů.

- `undo_stack`: dřívější stavy, navrchu ten těsně před aktuálním.
- `redo_stack`: stavy, ze kterých jsme odešli přes Undo.
- `now`: poslední známý stav jako dvojice `(text, klíč)`.

`record` (`sirens/history.py:48`):

```python
if self.now is not None and key == self.now[1]:
    self.now = (text, key)
    return
if self.now is not None:
    self.undo_stack.append(self.now)
    del self.undo_stack[:-LIMIT]
self.redo_stack.clear()
self.now = (text, key)
```

- Když se klíč nezměnil, žádný nový krok, jen se obnoví text (třeba se posunul pohled).
- Jinak se dosavadní stav dá na undo zásobník. `del self.undo_stack[:-LIMIT]` smaže všechno kromě posledních 100 (`[:-100]` = "od začátku až po 100. prvek od konce").
- Nová změna smaže redo: po nové úpravě už není co "znovu udělat".

`undo` (`:59`): nejdřív zavolá `record` s aktuálním stavem. Proč? Aby se zapsala i změna, která se ještě nestihla zachytit (snímek je jen každou 1/3 s). Pak přesune `now` na redo zásobník a z undo vytáhne předchozí stav. Vrátí jeho text (nebo `None`, když není kam jít). `redo` (`:69`) je zrcadlově obráceně.

`can_undo` a `can_redo` jsou **`@property`**: metoda, která se čte jako proměnná, bez závorek (`history.can_undo`). Okno podle nich zapíná a vypíná šipky. `bool(seznam)` je False pro prázdný seznam, True jinak.

#### Klíč změny: `change_key` (`sirens/history.py:25`)

Ne každá změna stavu je změna od uživatele. Klíč je stejný JSON text, jen bez dvou věcí:

- `view_low`: kam je odrolovaný editor patternu. To je jen pohled, nechceme kvůli rolování vytvářet kroky Undo.
- **hodnoty sliderů, které mají automatizaci**: při přehrávání v režimu Song je posouvá přehrávač. Bez tohohle by se při přehrávání plnila historie stovkami "změn". Body automatizace samotné ale v klíči jsou, takže jejich kreslení se do Undo počítá.

```python
track = dict(track)
del track["view_low"]
track["instrument"] = _without(track["instrument"], track["automation"])
track["blocks"] = [{**block, "values": _without(block["values"], block["automation"])}
                   for block in track["blocks"]]
```

- `dict(track)` je kopie. Originál se ještě ukládá do autosave, tam `view_low` být má.
- `{**block, "values": ...}`: kopie slovníku bloku, ve které se přepíše jen klíč `"values"` (pozdější klíč vyhraje).
- `_without` (`:20`) vrátí hodnoty sliderů kromě těch, které mají lane.

Kroky se **porovnávají podle klíče**, ale **obnovuje se celý text** (i s pohledem).

### `sirens/audio/export.py`: export do WAV

#### Princip

pyo může mít v programu jen jeden server a ten hraje v reálném čase. Píseň se proto nevykresluje "offline" (rychleji, než trvá), ale prostě se **jednou přehraje a nahraje**: od 1. taktu do konce posledního použitého taktu, v režimu Song. Nahrává se výstup serveru, tedy přesně to, co jde do reproduktorů (i s hlasitostí). Po konci se ještě `TAIL = 3` sekundy nahrává, aby se neuřízl dozvuk a doznívání not.

**WAV** je nekomprimovaný zvukový soubor: jen dlouhá řada čísel (vzorků), 44 100 za sekundu. Engine zapisuje 24 bitů na vzorek.

#### Průběh

`Export.__init__` (`sirens/audio/export.py:30`):

1. zapamatuje si původní režim přehrávače (`old_mode`),
2. zastaví přehrávač, přepne na Song a zapne `once`,
3. `engine.start_recording(...)` začne nahrávat,
4. `player.play(from_tick=0)` spustí píseň od začátku (`start_bar` se ignoruje).

Pak hlavní okno 30x za sekundu volá `tick()` (`:49`):

```python
now = time.monotonic()
if self.tail_end is None and not self.player.playing:
    self.tail_end = now + TAIL
if self.tail_end is not None and now >= self.tail_end:
    self._end()
    ...
    return True
```

- `time.monotonic()` jsou hodiny, které nikdy nejdou pozpátku (ani když se v počítači změní čas), vhodné na měření, kolik uplynulo.
- Když přehrávač přestal hrát (jeho hodiny na konci písně samy shodily `playing`, viz `_finish`), nastaví se čas konce dozvuku.
- Když ten čas uplyne, `_end()` export dokončí a `tick` vrátí True. Okno pak export zahodí.
- Jinak se jen aktualizuje text `status` ("Recording 0:12 / 1:05..."), který okno ukazuje pod tlačítkem.

Všechno důležité (stop, konec nahrávání) se děje ve vlákně okna, ne ve vlákně hodin. Vlákno hodin jen shodí `playing`. Je to bezpečnější, protože se dvě vlákna nehádají o stejné věci.

`cancel()` (`:66`) = Stop nebo mezerník během exportu. Ukončí nahrávání, co se stihlo nahrát, v souboru zůstane.

`_end()` (`:73`): zastaví přehrávač (ten počká na hodiny a vypne noty), ukončí nahrávání (tím se WAV dopíše a zavře), vypne `once` a vrátí původní režim.

`clock(seconds)` (`:22`) formátuje čas jako `m:ss`: `seconds // 60` jsou celé minuty, `seconds % 60` zbylé sekundy, `:02d` ve f-stringu znamená "celé číslo, vždy dvě číslice" (07, ne 7).

`song_seconds()` (`:44`) spočítá délku písně: `last_bar() * 4 * 60 / tempo`. Při 8 taktech a tempu 120 je to 8 × 4 × 0,5 = 16 s.

## Na co se tě můžou zeptat

**1. Proč je na takt zrovna 48 tiků?**
Protože 48 je nejmenší číslo dělitelné 16, 12 i 24, což jsou počty kroků v mřížkách. Každý krok každé mřížky pak začíná přesně na celém tiku (3, 4 nebo 2 tiky na krok), takže jedny hodiny obslouží stopy s různými mřížkami najednou.

**2. Jak se spočítá délka tiku a jak se tempo projeví za běhu?**
`60 / tempo` je délka doby, krát 4 doby na takt, děleno 48 tiků. Hodiny si délku tiku počítají při každém tiku znovu, takže změna tempa se projeví hned u dalšího tiku.

**3. Proč přehrávač běží ve vlastním vlákně a ne na časovači okna nebo na pyo Metro?**
Časovač okna kolísá podle toho, jak dlouho trvá překreslení, takže by rytmus nebyl pravidelný. Pyo Metro by bylo přesné, ale noty poslané z jeho zpětného volání (ve zvukovém vlákně pyo) pyo zahodí. Vlastní vlákno jen spí do přesně spočítaného času.

**4. Jak to, že rytmus "neujíždí"?**
Čas dalšího tiku se počítá od minulého plánovaného času (`next_time += délka tiku`), ne od aktuálního času. Drobná zpoždění se tedy nesčítají; když jeden tik přijde pozdě, další spánek je kratší.

**5. Jak přehrávač pozná, kdy notu vypnout?**
Při zapnutí si ji zapíše do `pending` s počtem tiků do konce (délka v krocích × tiky na krok). Každý tik se u všech čekajících not ubere jeden; když dojde na nulu, pošle se nota s velocity 0 (puštění klávesy). Při Stop se vypnou všechny čekající.

**6. Jak funguje automatizace?**
Ke každému slideru může být slovník takt → hodnota. Přehrávač v režimu Song při každém tiku spočítá přesnou pozici v taktech (třeba 3,25) a `lane_value` mezi dvěma sousedními body lineárně dopočítá hodnotu. Před prvním a za posledním bodem drží krajní hodnotu.

**7. Jak funguje Undo a proč tam je "klíč"?**
Okno každou 1/3 s zachytí celý stav jako JSON text. Když se liší od posledního, starý jde na undo zásobník. Undo vytáhne předchozí text a aplikace se podle něj postaví znovu (`session.restore`). Klíč je ten text bez věcí, které nejsou změnou od uživatele (rolování editoru, slidery hýbané automatizací), aby se historie nezaplňovala zbytečnými kroky.

**8. Co se stane, když program spadne při ukládání?**
Nic zlého: zapisuje se do dočasného `.tmp` souboru a až hotový se jedním krokem přejmenuje (`os.replace`) na cílový. Starý soubor zůstane celý. Navíc autosave každé 2 s ukládá do `~/.sirens/autosave.json` a při startu se načte.

**9. Proč se takty v JSON ukládají jako text "3"?**
Protože JSON dovoluje jako klíče slovníku jen text. Při načtení se převádí zpátky přes `int(bar)`.

**10. Jak funguje export do WAV, když pyo neumí renderovat rychleji než realtime?**
Píseň se jednou přehraje v režimu Song s příznakem `once` a nahrává se výstup serveru. Na konci písně se hodiny samy zastaví, nahrává se ještě 3 s dozvuku a pak se soubor uzavře a přehrávač vrátí do původního režimu.

**Bonus: proč `_finish` nevolá `stop()`?**
Protože `_finish` běží ve vlákně hodin a `stop()` dělá `join()` na vlákno hodin, tedy by čekal sám na sebe. Proto jen vypne noty a shodí `playing`.

## Kde se to napojuje

Kdo volá do souborů z téhle kapitoly:

- **`sirens/ui/main_frame.py`** (hlavní okno) je hlavní uživatel:
  - vytváří `Song()`, první stopu (`add_track`), `Player(engine, song)` a `History()`,
  - Play / Stop / mezerník volá `player.toggle()`,
  - `_capture` → `session.capture`, `_apply` → `session.restore` (při Open, autosave a Undo/Redo),
  - Save / Open → `session.write` / `session.read`, autosave → `session.AUTOSAVE`,
  - `_snapshot` (každou 1/3 s) → `history.record(json.dumps(data), change_key(data))`, Undo/Redo → `history.undo` / `history.redo`, po Undo pokračuje `player.play(from_tick=player.tick)`,
  - Export WAV → `Export(engine, player, path)`, každý snímek `export.tick()`, Stop → `export.cancel()`,
  - při zavření okna `player.close()`.
- **`sirens/ui/song_page.py`** (záložka Song): režim Loop/Song (`player.mode`, zakázáno během exportu přes `player.once`), tempo `player.set_tempo`, `Pattern.set_grid`, `Song.add_track` / `remove_track`, `session.duplicate`, konstanty `GRIDS`, `MAX_TRACKS`, `MIN_BARS`, `MAX_BARS`, `PATTERN_NAMES`.
- **`sirens/ui/pattern_view.py`** (editor patternu): `Pattern.note_at`, `Note`, `track.view_low`, ukazatel přehrávání z `player.position`.
- **`sirens/ui/timeline_view.py`** (časová osa): zapisuje `track.arrangement` a body automatizace do `owner.automation`, nastavuje `player.start_bar`, kreslí ukazatel z `player.position / TICKS_PER_BAR`.
- **`sirens/ui/sound_page.py`** (záložka Sound): kopírování zvuku stopy přes `session.sound_of` a `session.apply_sound`.
- **Dědí z `Adjustable`**: `Instrument` (`sirens/audio/instrument.py`), `Block` (`sirens/audio/blocks.py`), `Layer` (`sirens/visual/layers.py`), `LightRig` (`sirens/light/rig.py`). `Param` a `Choice` používají všechny tyhle soubory pro své slidery.
- **Dědí ze `Stack`**: `Rack` (`sirens/audio/rack.py`) a `Painter` (`sirens/visual/painter.py`).
- **Přehrávač volá ven**: `engine.send_note` (`sirens/audio/engine.py`), který notu pošle do pyo jako MIDI zprávu; export volá `engine.start_recording` / `stop_recording`.
