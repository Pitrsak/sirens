# 30 — Obraz a světlo: od zvuku k obrázku a k lampě

## Úvod

Tahle kapitola vysvětluje tu část Sirens, která se *dívá* na zvuk a podle něj kreslí obraz a řídí světlo. Sama nic nehraje. Bere zvuk, který právě vychází z aplikace, zjistí o něm pár čísel (jak je hlasitý, kolik je v něm basů, jestli právě udeřil buben) a podle těch čísel:

- **kreslí obraz** v záložce **Visual** a v okně **Fullscreen** (tlačítko v záložce Visual otevře stejný obraz přes celou obrazovku, třeba na projektor),
- **svítí světlem** v záložce **Light**: náhled je barevný kruh, a když zmáčkneš *Start sending*, hodnoty letí po síti do skutečného světla (nebo do programu jako QLC+).

Hodnoty z analýzy používá i záložka Sound: osciloskop a spektrum, které tam vidíš, kreslí `sirens/ui/sound_page.py`, ale čísla k tomu počítá stejný analyzátor, o kterém je tahle kapitola.

Soubory, o kterých to tu je:

| Soubor | Co dělá |
|---|---|
| `sirens/audio/analyzer.py` | nahrává kousky zvuku a počítá z nich spektrum (vlastní DFT), tvar vlny, hlasitost a sílu pásem |
| `sirens/visual/features.py` | z analyzátoru vybere, co potřebuje obraz, převede to na čísla 0..1 a detekuje údery (beat) |
| `sirens/visual/layers.py` | jednotlivé vrstvy obrazu: tvary (Ring, Wave, Bars, ...) a efekty (Feedback, Mirror, Glow, ...) |
| `sirens/visual/painter.py` | každý snímek projde vrstvy a složí z nich výsledný obrázek |
| `sirens/light/rig.py` | z basů, středů a výšek udělá barvu světla a hodnoty DMX kanálů |
| `sirens/light/artnet.py` | zabalí DMX hodnoty do síťového paketu Art-Net a pošle je přes UDP |

## Jak to spolu souvisí

```
  zvuk (pyo, součet všech nástrojů)
        |
        v
  Analyzer  (analyzer.py)
  - nahraje 2048 vzorků (~46 ms)
  - spočítá spektrum (vlastní DFT)
  - scope(), peak_level_db(), bands()
        |
        +-------------------------------+
        |                               |
        v                               v
  Features  (features.py)         LightRig  (rig.py)
  level, bass, mid, high,         barva R,G,B = basy, středy, výšky
  beat, wave, spectrum, time      (vyhlazená) -> 512 DMX kanálů
        |                               |
        v                               v
  Painter  (painter.py)           ArtNetSender  (artnet.py)
  projde vrstvy shora dolů        hlavička Art-Net + 512 bajtů
  (layers.py: Ring, Wave, ...,              |
   Feedback, Glow, Tint, ...)               v
        |                         UDP paket na port 6454
        v                                   |
  pole 360 x 640 x 3 (0..255)               v
        |                         světlo / QLC+ / konzole
        v
  záložka Visual + Fullscreen
```

Celé to pohání časovač v hlavním okně (`sirens/ui/main_frame.py`, metoda `_on_tick`). Tikne 30x za sekundu (`FPS = 30`) a pokaždé:

1. zavolá `analyzer.update()`, které se podívá, jestli je nahraný nový kousek zvuku,
2. když je vidět záložka Visual nebo je otevřený Fullscreen, zavolá `visual_page.tick(analyzer, dt)` a ta zavolá `painter.render(...)`,
3. vždycky (i když koukáš jinam) zavolá `light_page.tick(analyzer)`, aby světlo svítilo s hudbou pořád.

Jednomu průchodu tímhle kolečkem se říká **snímek** (frame). `dt` je čas od minulého snímku v sekundách, zhruba 0,033 s.

---

## 1. `sirens/audio/analyzer.py`: co je ve zvuku

### Pár pojmů úplně od nuly

- **Vzorek (sample)**: zvuk je v počítači řada čísel, každé říká, kde je v danou chvíli membrána reproduktoru. Hodnoty jsou mezi -1 a 1. Když se číslo dostane mimo, zvuk se „ořízne“ a chrčí.
- **Vzorkovací frekvence (sample rate)**: kolik vzorků je za sekundu. Tady 44 100 (nastavuje `sirens/audio/engine.py`).
- **Úsek**: analyzátor nebere zvuk po jednom vzorku, ale po kouscích `N = 2048` vzorků. 2048 / 44100 je asi 46 ms. To je dost krátké, aby obraz reagoval rychle, a dost dlouhé, aby šlo poznat, jaké frekvence v kousku jsou.
- **Frekvence**: kolikrát za sekundu se vlna zopakuje, v Hz. Basy jsou nízko (desítky až stovky Hz), výšky vysoko (tisíce Hz).
- **numpy**: knihovna na práci s celými poli čísel najednou. `np.zeros(5)` je pole pěti nul, `a * b` vynásobí dvě pole prvek po prvku, `M @ x` je násobení matice vektorem. Je to jen rychlá kalkulačka na pole, žádné hotové „spektrum“ z ní nevoláme.

### Nahrávání kousků zvuku (`__init__`, `update`)

```python
self.table = NewTable(length=N / sample_rate)                       # analyzer.py:33
self.recorder = TableRec(source, self.table, fadetime=0).play()     # analyzer.py:37
self.on_full = TrigFunc(self.recorder["trig"], self._mark_ready)    # analyzer.py:42
```

- `NewTable` je v pyo prázdná tabulka (pole) na vzorky. Délku chce v sekundách, proto `N / sample_rate`.
- `TableRec` do té tabulky nahrává zvuk ze `source` (to je součet všech nástrojů, ještě před hlasitostí, aby byla vlna vidět i při tichém poslechu). `fadetime=0` znamená bez stmívání na krajích. `.play()` nahrávání spustí.
- Když je tabulka plná, `TableRec` vyšle **trigger** (krátký signál „hotovo“). `TrigFunc` na něj čeká a zavolá funkci `_mark_ready`, která jen nastaví `self.ready = True`.

Proč tak složitě? pyo počítá zvuk ve **vlastním vlákně** (vlákno = kus programu, který běží souběžně s jiným). Kdybychom spektrum počítali přímo tam, mohl by se zvuk zadrhnout. Proto zvukové vlákno jen nastaví příznak a těžkou práci udělá GUI ve svém tiku:

```python
def update(self) -> bool:                                  # analyzer.py:63
    if not self.ready:
        return False
    self.ready = False
    self.samples = np.asarray(self.table.getTable(), dtype=np.float32)
    self.recorder.play()
    self._compute_spectrum()
    return True
```

`getTable()` vrátí obsah tabulky jako seznam, `np.asarray(..., dtype=np.float32)` z něj udělá numpy pole desetinných čísel. `recorder.play()` pustí nahrávání dalšího úseku od začátku tabulky. Úsek trvá ~46 ms a tik je co ~33 ms, takže nový úsek bývá zhruba každý druhý snímek. Když nový není, vrátí se `False` a všechno zůstane z minula.

### Spektrum: vlastní DFT (`_compute_spectrum`)

**Co je spektrum, intuitivně.** Každý zvuk jde rozložit na součet sinusovek (čistých tónů) s různou frekvencí a silou. Spektrum je tabulka „frekvence -> jak silně tam je“. Klavírní A4 má silnou čáru na 440 Hz a slabší na 880, 1320, ... Basový buben má sílu dole. Spektrum je to, co v záložce Sound vidíš jako křivku, a z něj se počítají basy, středy a výšky pro obraz a světlo.

**DFT (diskrétní Fourierova transformace)** je výpočet, který spektrum z úseku vzorků udělá. Vzorec z přednášky:

```
X[k] = sum_{n=0}^{N-1} x[n] * w[n] * e^(-j * 2*pi * k * n / N)
```

Lidsky: pro každé číslo `k` vezmeme sinusovku, která se do úseku vejde přesně `k`-krát, a změříme, „jak moc se úsek s touhle sinusovkou shoduje“: vynásobíme vzorek po vzorku a sečteme. Když v úseku ta frekvence je, součiny mají pořád stejné znaménko a součet vyjde velký. Když tam není, kladné a záporné se navzájem vyruší a vyjde skoro nula.

Protože `e^(-j*fi) = cos(fi) - j*sin(fi)`, dělá se to dvakrát: jednou s cosinem (reálná část) a jednou se sinem (imaginární část). Dvě čísla jsou potřeba, protože sinusovka v úseku může být různě posunutá, a cos a sin spolu pokryjí všechny posuny.

**Koš (bin)**: číslo `k` odpovídá frekvenci `k * sample_rate / N`. Koše jdou po 44100 / 2048 = 21,5 Hz: koš 20 je 430,7 Hz, koš 21 je 452,2 Hz. Počítáme jen `k = 0 .. N/2 - 1` (1024 košů), protože u reálného signálu je druhá půlka spektra jen zrcadlo té první. Frekvence každého koše jsou uložené v `self.freqs` (analyzer.py:56).

**Trik s maticemi.** Hodnoty cos a sin pro všechna `k` a `n` nezávisí na zvuku, takže se spočítají jednou při startu:

```python
n = np.arange(self.size)                   # 0, 1, ..., 2047
k = np.arange(self.size // 2)[:, None]     # 0, 1, ..., 1023 jako sloupec
self.cos = np.cos(2 * np.pi * k * n / self.size)   # analyzer.py:54
self.sin = np.sin(2 * np.pi * k * n / self.size)
```

`[:, None]` udělá z řady čísel sloupec. Když pak numpy počítá `k * n` (sloupec krát řádek), vyjde celá tabulka 1024 x 2048: řádek `k`, sloupec `n`. Tomuhle automatickému „roztažení“ se říká **broadcasting**. Řádek `k` matice `self.cos` je tedy jedna cosinusovka.

Samotná DFT pro nový úsek je pak:

```python
x = self.samples * self.window      # analyzer.py:78   x[n] * w[n]
re = self.cos @ x                   # analyzer.py:79   reálná část pro všechna k
im = -(self.sin @ x)                # analyzer.py:80   imaginární část (minus z e^(-j...))
```

`@` je násobení matice vektorem: každý řádek matice se vynásobí s vektorem prvek po prvku a sečte. To je přesně ta suma ze vzorce, jen pro všech 1024 frekvencí najednou.

**Okno (Hannovo okno, `self.window`, analyzer.py:52).** Úsek vystřihneme ze zvuku natvrdo, takže na začátku a konci je skok. Ten skok se ve spektru projeví jako falešné frekvence všude kolem (říká se tomu **prosakování, leakage**) a čáry se rozmažou. Proto úsek na krajích plynule ztlumíme: vynásobíme ho „kopečkem“ `0.5 - 0.5*cos(...)`, který je na krajích 0 a uprostřed 1.

**Z komplexního čísla na sílu (amplituda):**

```python
amplitude = 2 * np.sqrt(re * re + im * im) / self.window.sum()     # analyzer.py:83
```

`sqrt(re² + im²)` je délka komplexního čísla (Pythagoras). Čistá sinusovka s amplitudou `A` dá `|X[k]| = A * sum(w) / 2` (součet okna je tu 1023,5), takže vynásobením `2 / sum(w)` dostaneme zpátky přímo `A`. Sinusovka o síle 0,5 tak ve spektru ukáže 0,5.

**Decibely:**

```python
db = 20 * np.log10(np.maximum(amplitude, 1e-9))      # analyzer.py:86
```

Ucho slyší hlasitost spíš „v násobcích“ než lineárně, proto se síla zobrazuje v **decibelech (dB)**: `20 * log10(A)`. Amplituda 1 je 0 dB, 0,5 je asi -6 dB, 0,1 je -20 dB, 0,01 je -40 dB. `np.maximum(amplitude, 1e-9)` je pojistka, protože logaritmus nuly neexistuje.

**Pomalé klesání (aby spektrum neblikalo):**

```python
self.spectrum = np.maximum(np.maximum(db, DB_FLOOR), self.spectrum - FALL_DB)   # analyzer.py:89
```

Pro každý koš se vezme větší z: nové hodnoty (ale aspoň `DB_FLOOR = -90`, tišší bereme jako ticho), nebo staré hodnoty snížené o `FALL_DB = 2.5` dB. Nahoru tedy spektrum skočí hned, ale dolů padá pomalu, nejvýš o 2,5 dB za každý nový úsek. Je to jednoduchý **vyhlazovací (envelope) follower**: sleduje špičky a pomalu je pouští.

### Osciloskop s triggerem (`scope`, analyzer.py:91)

Osciloskop ukazuje tvar vlny, `SCOPE_VIEW = 512` vzorků (~11,6 ms). Kdyby každý snímek začínal na náhodném místě vlny, obraz by ujížděl doleva a doprava. Proto hledáme **průchod nulou směrem nahoru**:

```python
rising = np.nonzero((x[:-1] < 0) & (x[1:] >= 0))[0]     # analyzer.py:99
rising = rising[rising < len(x) - SCOPE_VIEW]           # analyzer.py:101
start = rising[0] + 1 if len(rising) else 0
return x[start:start + SCOPE_VIEW]
```

- `x[:-1]` jsou všechny vzorky kromě posledního, `x[1:]` všechny kromě prvního. Porovnáním dostaneme pro každou dvojici sousedů `True`, když první je pod nulou a druhý na nule nebo nad. To je místo, kde vlna jde nahoru přes nulu.
- `&` je „a zároveň“ pro celá pole, `np.nonzero(...)[0]` vrátí indexy, kde je `True`.
- Druhý řádek nechá jen průchody, za kterými je ještě aspoň 512 vzorků, aby se výřez vešel.
- Když žádný průchod není (ticho), začneme od nuly.

Vlna tak začíná pořád ve stejné fázi a stojí na místě, stejně jako na skutečném osciloskopu.

### Hlasitost, nejsilnější frekvence a pásma

- `peak_level_db()` (analyzer.py:106): největší absolutní hodnota vzorku v úseku, převedená na dB. 0 dB = hodnota 1,0 = hranice ořezu.
- `peak_frequency()` (analyzer.py:110): najde nejsilnější koš (`np.argmax`) a vrátí jeho frekvenci, nebo `None`, když je všechno pod -60 dB. Protože koše jdou po 21,5 Hz, tón 440 Hz by padl mezi koš 20 (430,7 Hz) a 21. Proto se nejsilnějším košem a jeho dvěma sousedy proloží **parabola** a vezme se její vrchol:

  ```python
  shift = 0.5 * (a - c) / (a - 2 * b + c)      # analyzer.py:125
  ```

  `a, b, c` jsou hodnoty levého souseda, vrcholu a pravého souseda. `shift` vyjde mezi -0,5 a 0,5, o tolik košů je skutečný vrchol vedle. Výsledek `(k + shift) * sample_rate / size` je frekvence v Hz. Tohle čte záložka Sound.
- `band(lo_hz, hi_hz)` (analyzer.py:128): síla jednoho pásma jako číslo 0..1.

  ```python
  inside = (self.freqs >= lo_hz) & (self.freqs < hi_hz)     # maska: které koše jsou v pásmu
  db = float(self.spectrum[inside].max())                   # nejsilnější z nich
  return min(1.0, max(0.0, (db + 60) / 60))                 # -60 dB -> 0, 0 dB -> 1
  ```

  **Maska** je pole `True/False` stejně dlouhé jako spektrum. `self.spectrum[inside]` vybere jen ty prvky, kde je `True`. Převod `(db + 60) / 60` je přímka: -60 dB dá 0, -30 dB dá 0,5, 0 dB dá 1. `min`/`max` výsledek ořízne do 0..1.
- `bands()`: tři pásma najednou, `BASS = 20–250 Hz`, `MID = 250–2000 Hz`, `HIGH = 2000–20000 Hz` (analyzer.py:25). Tohle je to hlavní číslo pro obraz i světlo.

---

## 2. `sirens/visual/features.py`: co obraz ví o zvuku

`Features` je jednoduchá „schránka“ s čísly, která se jednou za snímek přepočítají a pak je čtou všechny vrstvy. Díky tomu se analýza nedělá pro každou vrstvu znovu.

| Vlastnost | Co to je | Rozsah |
|---|---|---|
| `level` | celková hlasitost (ze `peak_level_db`, stejný převod -60..0 dB -> 0..1) | 0..1 |
| `bass`, `mid`, `high` | síla pásem z `analyzer.bands()` | 0..1 |
| `beat` | 1 v okamžiku úderu, pak klesá k 0 | 0..1 |
| `wave` | 512 vzorků z `analyzer.scope()` | asi -1..1 |
| `spectrum` | 96 hodnot spektra rozložených logaritmicky 40 Hz – 12 kHz | 0..1 |
| `time` | čas od spuštění v sekundách (součet `dt`) | s |

### Logaritmické spektrum (features.py:31 a :41)

Analyzátor má koše po 21,5 Hz, rovnoměrně. Ucho ale slyší **logaritmicky**: rozdíl 100 -> 200 Hz (oktáva) zní stejně velký jako 1000 -> 2000 Hz. Kdyby Ring nebo Bars kreslily koše rovnoměrně, basy by se nacpaly do pár bodů úplně vlevo a zbytek by byly výšky. Proto:

```python
self.freqs = np.geomspace(40, 12000, SPECTRUM_POINTS)     # features.py:31
bins = np.minimum(np.searchsorted(analyzer.freqs, self.freqs), len(analyzer.freqs) - 1)   # :41
self.spectrum = np.clip((analyzer.spectrum[bins] + 60) / 60, 0, 1)
```

- `np.geomspace(40, 12000, 96)` dá 96 čísel, kde každé je stejným násobkem předchozího (geometrická řada), takže na každou oktávu připadne stejně bodů.
- `np.searchsorted(seřazené_pole, hodnoty)` pro každou hodnotu najde index, kam by se do seřazeného pole zařadila. Tady to znamená „první koš analyzátoru, který je na té frekvenci nebo nad ní“.
- `np.minimum(..., len - 1)` je pojistka, aby index nevylezl za konec.
- `np.clip(pole, 0, 1)` ořízne všechny hodnoty do 0..1.

### Detekce úderu (`_detect_beat`, features.py:46)

Tohle je naše vlastní zpracování signálu. Myšlenka: úder bubnu = basy náhle vyskočí výrazně nad to, na co jsme byli poslední dobou zvyklí.

```python
rising = self.bass > self.bass_average * BEAT_RISE + 0.05          # features.py:54
if rising and self.time - self.last_beat > BEAT_GAP:
    self.beat = 1.0
    self.last_beat = self.time
else:
    self.beat *= BEAT_FALL
self.bass_average = 0.9 * self.bass_average + 0.1 * self.bass      # features.py:61
```

Krok po kroku:

1. **Klouzavý průměr** `bass_average`: každý snímek je to 90 % starého průměru + 10 % nové hodnoty. Takový průměr pomalu „dojíždí“ za basy a ignoruje krátké špičky (je to jednoduchý dolnopropustný filtr, odborně exponenciální klouzavý průměr).
2. **Práh**: úder je, když jsou basy větší než `průměr * 1.25 + 0.05`. `BEAT_RISE = 1.25` znamená aspoň o 25 % víc. `+ 0.05` je pojistka pro skoro ticho: při průměru 0,01 by jinak stačil nepatrný výkyv na 0,013. Příklad: průměr 0,4, práh je 0,55. Basy skočí na 0,7, je to úder.
3. **Pauza** `BEAT_GAP = 0.18` s: po úderu se dalších 0,18 s žádný nový nepočítá, jinak by jeden buben (basy jsou vysoko několik snímků po sobě) udělal sérii úderů.
4. **Doznívání**: mimo úder se `beat` každý snímek vynásobí `BEAT_FALL = 0.85`, takže plynule klesá: 1 -> 0,85 -> 0,72 -> 0,61 -> ... po 10 snímcích (~0,33 s) je kolem 0,2. Vrstvy, které reagují na Beat, tak nebliknou na jeden snímek, ale „pulsují“.
5. Průměr se aktualizuje až **po** porovnání, aby do sebe nezapočítal i ten úder, který právě testujeme.

---

## 3. Obraz v paměti: pole pixelů

Než se pustíme do vrstev, je potřeba vědět, co je obrázek pro počítač.

- **Pixel** je jeden bod obrazu. Má tři čísla: kolik červené (R), zelené (G) a modré (B). Smícháním světla těchhle tří barev vznikne jakákoli barva (R+G = žlutá, všechny tři naplno = bílá, nic = černá).
- Celý obrázek je **trojrozměrné numpy pole** tvaru `výška x šířka x 3`. U nás `WIDTH, HEIGHT = 640, 360` (layers.py:26), takže pole má tvar `(360, 640, 3)`: 360 řádků, v každém 640 pixelů, v každém 3 čísla. Pozor na pořadí: **nejdřív řádek (y), pak sloupec (x)**. `canvas[10, 20]` je pixel v 11. řádku a 21. sloupci (indexuje se od 0), `canvas[10, 20, 0]` je jeho červená složka.
- Osa **y roste dolů**: řádek 0 je nahoře. Proto se ve vzorcích občas objeví minus.
- **Dva formáty čísel:**
  - `uint8` (celé číslo bez znaménka, 8 bitů) = 0..255. Tak se obrázky ukládají a zobrazují. 255 je plná barva.
  - `float32` (desetinné číslo) = my používáme 0..1. Na tomhle se líp počítá: dá se násobit, sčítat a nic „nepřeteče“ dokola jako u `uint8`, kde 250 + 10 dá 4.
  Painter si drží obraz ve `float32` 0..1 a teprve na konci ho převede na `uint8` 0..255.
- **RGB, ne BGR.** OpenCV běžně ukládá barvy v pořadí B, G, R (třeba když načítá obrázek přes `cv2.imread` nebo ukazuje přes `cv2.imshow`). My ale z OpenCV používáme jen kreslicí funkce a efekty, a těm je jedno, co který kanál znamená: barvu jim prostě dáme jako tři čísla a ony je zapíšou do kanálů 0, 1, 2. My jsme se rozhodli, že kanál 0 = R, 1 = G, 2 = B, protože přesně v tomhle pořadí to chce `wx.Bitmap.FromBuffer`, který obraz zobrazí v okně. Proto `Layer.colour()` vrací `(R, G, B)` a v RGB Split je kanál 0 červená.
- **Užitečné numpy zápisy pro obraz:**
  - `canvas[:, 320:]` = všechny řádky, sloupce od 320 dál (pravá půlka). `:` znamená „všechno“.
  - `pole[::-1]` = pozpátku. `canvas[:, ::-1]` převrátí sloupce (zrcadlo zleva doprava).
  - `canvas[..., 0]` = jen kanál 0 (červená) celého obrázku. `...` znamená „všechny osy před tím“.
  - `canvas * 0.9` vynásobí každé číslo v poli, `a + b` sečte dva obrázky pixel po pixelu.

---

## 4. `sirens/visual/layers.py`: vrstvy obrazu

### Základ: třída `Layer` (layers.py:56)

Vrstva je kus kódu, který dostane obraz (`canvas`) a čísla o zvuku (`f`, objekt `Features`) a vrátí upravený obraz. Uživatel si vrstvy skládá pod sebe v záložce Visual (*Add layer*), stejně jako bloky zvuku.

- `Layer` dědí z `Adjustable` (`sirens/param.py`): to znamená, že má seznam `PARAMS` (jaké slidery ukázat) a slovník `self.settings` s jejich aktuálními hodnotami, třeba `self.settings["Size"]`. **Dědičnost** = třída převezme všechno od rodiče a jen něco přidá nebo změní.
- `NAME` je jméno v menu (a v uloženém souboru), `IS_SOURCE` říká, jestli je to tvar (kreslí) nebo efekt (mění obraz), `POST` má jen Glow (viz dál), `enabled` je vypnutí/zapnutí.
- `apply(canvas, f)` musí každá vrstva napsat po svém. V `Layer` jen vyhodí `NotImplementedError` („tohle musí udělat potomek“).

**Reakce na zvuk, `drive()` (layers.py:62).** Skoro každá vrstva má dva slidery z `react_params()`: *React to* (None, Level, Bass, Mid, High, Beat) a *Reaction* (0..2).

```python
source = REACT[round(self.settings["React to"])]     # číslo -> jméno, třeba 2 -> "Bass"
signal = {"None": 0.0, "Level": f.level, "Bass": f.bass, "Mid": f.mid,
          "High": f.high, "Beat": f.beat}[source]
return signal * self.settings["Reaction"]
```

Výběr (Choice) se ukládá jako pořadové číslo, takže `REACT[...]` z něj udělá jméno. Pak se ze **slovníku** (dict, dvojice klíč -> hodnota) vybere odpovídající číslo 0..1 a vynásobí se *Reaction*. Výsledek je 0..2. Vrstvy ho pak používají skoro vždycky jako `(1 + drive)`: bez zvuku je to 1 (normální velikost), při plných basech a Reaction 2 je to 3 (trojnásobek).

**Barva, `colour()` (layers.py:73).** Barva se nastavuje jako odstín na barevném kole (0 = červená, 120 = zelená, 240 = modrá) a jas. Tomu se říká **HSV** (hue = odstín, saturation = sytost, value = jas). Standardní modul `colorsys` to převede na RGB 0..1, my to vynásobíme 255, protože OpenCV kreslí do 8bitové vrstvy. `% 360` přetočí odstín dokola (370 = 10), `hue_shift` umožňuje dát každému sloupci nebo kolečku trochu jiný odstín.

**Míchání vrstev, `blend()` (layers.py:46).**

```python
canvas += layer8.astype(np.float32) * (1 / 255)      # layers.py:52
```

Tvary se nekreslí přímo do obrazu, ale do prázdné černé 8bitové vrstvy (`np.zeros_like(canvas, dtype=np.uint8)` = pole nul stejného tvaru jako canvas). Důvod: OpenCV umí vyhlazené čáry (`cv2.LINE_AA`, anti-aliasing = měkké okraje bez schodů) jen v 8bitovém obrázku. Pak se vrstva převede na 0..1 (`/ 255`) a **přičte** k obrazu. Sčítání je jako když svítí dva projektory na jedno plátno: červená + zelená = žlutá, překryv je vždycky světlejší, nikdy tmavší, a černé místo (0) nic nezmění. `+=` mění `canvas` přímo na místě, nevytváří kopii.

### Tvary (kreslí něco nového)

Všechny tvary kreslí kolem středu obrazu `(WIDTH / 2, HEIGHT / 2)` = `(320, 180)` nebo přes celou šířku.

Použité kreslicí funkce OpenCV:

| Funkce | Co dělá |
|---|---|
| `cv2.polylines(obr, [body], uzavřená, barva, tloušťka, cv2.LINE_AA)` | lomená čára přes seznam bodů `(x, y)`; `True` = spojí poslední bod s prvním |
| `cv2.rectangle(obr, (x0, y0), (x1, y1), barva, -1)` | obdélník mezi dvěma rohy; tloušťka `-1` = vyplněný |
| `cv2.circle(obr, (x, y), poloměr, barva, -1, cv2.LINE_AA)` | kruh; `-1` = vyplněný |

Souřadnice musí být celá čísla, proto se body převádějí `.astype(np.int32)` nebo `int(...)`.

**Ring (layers.py:90)**: uzavřená křivka kolem středu, jejíž poloměr v každém úhlu dává spektrum.

```python
levels = np.concatenate([f.spectrum, f.spectrum[::-1]])                    # 96 bodů + tytéž pozpátku = 192
angles = np.linspace(0, 2 * np.pi, len(levels), endpoint=False) - np.pi / 2
radius = HEIGHT * (s["Size"] * (1 + 0.5 * self.drive(f)) + 0.25 * s["Spectrum"] * levels)   # :111
points = np.stack([WIDTH / 2 + radius * np.cos(angles),
                   HEIGHT / 2 + radius * np.sin(angles)], axis=1).astype(np.int32)
```

- Spektrum se spojí se svým zrcadlem, aby byl kruh souměrný: pravá půlka jde od basů nahoře po výšky dole, levá je její zrcadlo.
- `np.linspace(0, 2*pi, 192, endpoint=False)` = 192 rovnoměrně rozložených úhlů dokola (v radiánech, 2π = celý kruh). `- pi/2` posune start nahoru.
- Poloměr = základ (`Size` krát výška obrazu, při zvuku až dvojnásobek) + kus podle spektra. Příklad: Size 0,2 dá 72 px, plné spektrum se Spectrum 0,5 přidá 0,125 * 360 = 45 px.
- Z úhlu a poloměru na pixely: `x = střed + r * cos(úhel)`, `y = střed + r * sin(úhel)` (**polární souřadnice** -> kartézské). `np.stack(..., axis=1)` poskládá x a y vedle sebe do tabulky 192 x 2.

**Wave (layers.py:121)**: tvar vlny přes celou šířku, jako osciloskop.

```python
x = np.linspace(0, WIDTH - 1, len(f.wave))
y = HEIGHT * s["Position"] - f.wave * HEIGHT * s["Height"] * (1 + self.drive(f))
```

512 vzorků se rozloží rovnoměrně přes 640 pixelů. `Position` určuje středovou čáru (0,5 = prostředek). Kladný vzorek má jít nahoru, a protože y roste dolů, je tam minus. Čára se nezavírá (`False`).

**Bars (layers.py:146)**: sloupce spektra. Vybere se `Count` bodů ze spektra (`np.linspace(...).astype(int)` dá rovnoměrně rozložené indexy), výška sloupce = hodnota spektra * výška obrazu * `Height` * `(1 + drive)`. Pro každý sloupec se spočítá levý a pravý okraj (s mezerou 1 px) a horní a dolní okraj podle `Place` (od spodku, nebo od prostředka na obě strany), a nakreslí se vyplněný obdélník. Odstín se zleva doprava posouvá až o 60 stupňů.

**Particles (layers.py:176)**: částice, které vyletují ze středu a hasnou. Je to malá **částicová simulace**, celá v numpy:

- Každá částice má polohu (`self.pos`, tabulka N x 2), rychlost (`self.vel`, posun v pixelech za snímek) a „život“ = jas (`self.life`, 1 -> 0).
- Kolik se jich narodí: `Amount * 40 * drive`, ale nejvýš do stropu `MAX = 800`. Když *React to* je None, `drive` je natvrdo 0,5 (stálý proud).
- Nové částice: náhodný směr `np.random.uniform(0, 2*pi, born)`, náhodná rychlost 30–100 % ze `Speed`, start uprostřed. Rychlost = `(cos(úhel), sin(úhel)) * rychlost`. `np.vstack` přidá nové řádky pod staré.
- Každý snímek: `pos = pos + vel` (pohyb), `life = life * Life` (při 0,95 o 5 % tmavší), a ty s `life <= 0.05` se zahodí přes masku `alive`.
- Každá živá částice je vyplněný kruh v barvě vynásobené jejím `life`.

**Orbit (layers.py:225)**: kolečka obíhající kolem středu.

```python
angle = f.time * s["Speed"] * 2 * math.pi + i * 2 * math.pi / count
```

První část otáčí s časem (`Speed` = otáček za sekundu, 2π = jedna otáčka), druhá rozestaví `count` koleček rovnoměrně dokola. Poloha je zase `střed + r * cos/sin`. Se zvukem roste dráha (až na dvojnásobek) i velikost koleček.

### Efekty (mění to, co už je nakreslené)

**Feedback (layers.py:256)**: obrazový „dozvuk“. Starý snímek se trochu zvětší, pootočí a ztmaví a nové tvary se kreslí přes něj. Starší tvary tak odplouvají do stran a hasnou, vypadá to jako tunel.

```python
matrix = cv2.getRotationMatrix2D((WIDTH / 2, HEIGHT / 2), s["Spin"], zoom)     # :275
canvas = cv2.warpAffine(canvas, matrix, (WIDTH, HEIGHT))                       # :277
return canvas * s["Fade"]
```

- `cv2.getRotationMatrix2D(střed, úhel, měřítko)` spočítá **afinní matici** 2 x 3: malou tabulku čísel, která říká, kam se má každý bod posunout, aby se obraz otočil o `Spin` stupňů a zvětšil `zoom`-krát kolem středu.
- `cv2.warpAffine` tu matici použije na celý obraz (pro každý pixel výsledku spočítá, odkud v původním obrazu má vzít barvu).
- `* Fade` ztmaví. Při Fade 0,9 je tvar po 22 snímcích (~0,7 s) jen na 10 % jasu.
- Aby to fungovalo, Painter musí na začátku snímku vzít **minulý** obraz místo černého. To dělá, jen když je v seznamu zapnutá vrstva Feedback (viz Painter). Proto má Feedback být nahoře.

**Mirror (layers.py:281)**: zrcadlení, čistě naše operace s polem.

```python
canvas[:, WIDTH // 2:] = canvas[:, :WIDTH // 2][:, ::-1]     # levá půlka obráceně vpravo
canvas[HEIGHT // 2:] = canvas[:HEIGHT // 2][::-1]           # horní půlka obráceně dole
```

`//` je celočíselné dělení (640 // 2 = 320). Vezmeme levou polovinu, obrátíme pořadí sloupců a zapíšeme ji do pravé poloviny. Stejně pro řádky. Režim Both udělá obojí, takže z jedné čtvrtiny vznikne celý souměrný obraz.

**Glow (layers.py:297)**: záře kolem světlých míst.

```python
return cv2.GaussianBlur(canvas, (0, 0), s["Radius"]) * s["Amount"] * (1 + self.drive(f))   # :320
```

`cv2.GaussianBlur` obraz rozmaže: každý pixel nahradí váženým průměrem svého okolí, kde bližší pixely mají větší váhu (váhy mají tvar zvonu, Gaussovy křivky). `Radius` je šířka toho zvonu (sigma), `(0, 0)` znamená „velikost okolí si dopočítej sám“. Rozmazaná kopie se zesílí a **přičte** navrch, takže světlé věci „svítí do okolí“.

Glow má `POST = True`: jeho záře se přidá jen k tomu, co se ukáže na obrazovce, ale **ne** do paměti obrazu, ze které vychází Feedback. Jinak by se záře přičítala každý snímek znovu a znovu a za chvíli by byl celý obraz bílý. Glow proto nemá `apply`, ale `halo`, a Painter s ním zachází zvlášť.

**Warp (layers.py:323)**: vlnění obrazu.

```python
self.xs, self.ys = np.meshgrid(np.arange(WIDTH, dtype=np.float32), np.arange(HEIGHT, dtype=np.float32))  # :338
dx = amount * np.sin(2 * np.pi * s["Waves"] * self.ys / HEIGHT + phase)
dy = amount * np.sin(2 * np.pi * s["Waves"] * self.xs / WIDTH + phase * 1.3)
return cv2.remap(canvas, self.xs + dx, self.ys + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
```

- `np.meshgrid` vytvoří dvě pole velká jako obraz: v `xs` je v každém pixelu jeho x, v `ys` jeho y. Každý pixel tak „zná svou polohu“. Počítá se jednou v `__init__`.
- `dx` (vodorovný posun) se mění se sinusem podle řádku, `dy` podle sloupce. `phase` roste s časem, takže se vlny pohybují.
- `cv2.remap(obraz, mapa_x, mapa_y, ...)` postaví nový obraz tak, že pixel `[y, x]` vezme z místa `[mapa_y[y, x], mapa_x[y, x]]` původního. Když to místo padne mezi pixely, `INTER_LINEAR` dopočítá barvu z okolních čtyř. `BORDER_REFLECT` = když bychom brali z místa mimo obraz, vezme se zrcadlově zevnitř, aby na krajích nebyly černé díry.

**RGB Split (layers.py:352)**: glitch efekt, rozjeté barvy.

```python
canvas[..., 0] = np.roll(canvas[..., 0], shift, axis=1)      # červená doprava
canvas[..., 2] = np.roll(canvas[..., 2], -shift, axis=1)     # modrá doleva
```

`np.roll` posune pole o `shift` míst podél osy 1 (sloupce, tedy vodorovně) a co vyjede na jednom konci, vrátí se na druhém. Červený kanál jde doprava, modrý doleva, zelený zůstane. Bílé tvary tak dostanou červený a modrý okraj. Se zvukem až pětinásobný posun.

**Pixelate (layers.py:367)**: zhrubnutí na čtverečky.

```python
small = cv2.resize(canvas, (WIDTH // size, HEIGHT // size), interpolation=cv2.INTER_AREA)
return cv2.resize(small, (WIDTH, HEIGHT), interpolation=cv2.INTER_NEAREST)
```

Obraz se zmenší (`INTER_AREA` = každý nový pixel je průměr čtverce `size x size` původních) a zase zvětší na původní velikost s `INTER_NEAREST` (každý pixel se jen zkopíruje z nejbližšího, žádné vyhlazování). Výsledek: velké ostré čtverce.

**Tint (layers.py:382)**: přebarvení podle jasu, naše vlastní operace.

```python
lum = np.clip(canvas.mean(axis=2, keepdims=True), 0, 1)       # jas pixelu
tinted = (dark * (1 - lum) + light * lum) * lum               # :400
return canvas * (1 - s["Amount"]) + tinted * s["Amount"]
```

- `canvas.mean(axis=2)` = průměr R, G, B každého pixelu = jeho jas 0..1. `keepdims=True` nechá tvar `(360, 640, 1)`, aby se to dalo násobit s barvou o třech složkách (broadcasting).
- `dark * (1 - lum) + light * lum` je **lineární interpolace**: tmavé pixely dostanou barvu `Dark`, světlé barvu `Light`, mezi tím plynulý přechod. Celé se to ještě vynásobí `lum`, aby černá zůstala černá (jinak by se černé pozadí obarvilo na `Dark`).
- Poslední řádek smíchá originál a přebarvený obraz podle `Amount`. Tomuhle se obecně říká **crossfade / lineární míchání**: `a * (1 - t) + b * t`.

### `CATALOG` (layers.py:405)

Seznam všech druhů vrstev. Z něj se staví menu *Add layer* (`sirens/ui/visual_page.py`) a podle jejich `NAME` se vrstvy hledají při načítání uloženého souboru (`sirens/session.py`, `LAYERS_BY_NAME`).

---

## 5. `sirens/visual/painter.py`: skládání snímku

`Painter` dědí ze `Stack` (`sirens/stack.py`): to je obecný seřazený seznam, který umí přidat, smazat, posunout a vypnout prvek. Stejnou věc používají bloky zvuku. `Painter.layers` jsou prostě položky toho seznamu.

`self.canvas` (painter.py:23) je **paměť obrazu**: pole `360 x 640 x 3` ve `float32`, které přežívá mezi snímky. Na něj navazuje Feedback.

Metoda `render(analyzer, dt)` (painter.py:31), řádek po řádku:

```python
self.features.update(analyzer, dt)                                       # 1. co je ve zvuku
layers = [layer for layer in self.layers if layer.enabled]               # jen zapnuté vrstvy
keep = any(isinstance(layer, FeedbackLayer) for layer in layers)         # je tam Feedback?
canvas = self.canvas if keep else np.zeros_like(self.canvas)             # 2. minulý snímek, nebo černá
halos = []
for layer in layers:                                                     # 3. vrstvy shora dolů
    if layer.POST:
        halos.append(layer.halo(canvas, self.features))                  #    Glow jen spočítá záři
    else:
        canvas = layer.apply(canvas, self.features)                      #    ostatní mění canvas
self.canvas = np.clip(canvas, 0, 1).astype(np.float32)                   #    zapamatovat (oříznuté)
shown = self.canvas + sum(halos) if halos else self.canvas               # 4. záře navrch
return (np.clip(shown, 0, 1) * 255).astype(np.uint8)                     # 5. 0..1 -> 0..255
```

- `[x for x in seznam if podmínka]` je **list comprehension**: krátký zápis „udělej nový seznam z prvků, které splní podmínku“.
- `any(...)` vrátí `True`, když aspoň jeden prvek je pravdivý. `isinstance(objekt, Třída)` se ptá „je tohle objekt dané třídy?“.
- Záře (halo) se počítá z toho, co je na plátně v okamžiku, kdy na Glow v seznamu dojde řada, tedy z vrstev nad ním.
- `np.clip(canvas, 0, 1)`: po sčítání vrstev můžou být hodnoty nad 1, tady se ořežou. Oříznutá verze se uloží do paměti.
- `sum(halos)` sečte všechna pole záře (může jich být víc, když je víc Glow vrstev).
- Na konci se oříznutý obraz vynásobí 255 a převede na `uint8`. Tohle pole vezme `VisualView.show()` v `sirens/ui/views.py` a přes `wx.Bitmap.FromBuffer(šířka, výška, pole)` z něj udělá obrázek pro wx, který se zvětší do okna se zachováním poměru stran. Fullscreen (`sirens/ui/visual_page.py`) dostane úplně stejné pole.

---

## 6. `sirens/light/rig.py`: barva světla

### DMX od nuly

**DMX** je standard, kterým se ovládají divadelní a klubová světla. Jedno vedení (jedno **universe**) přenáší **512 kanálů**, každý je číslo 0..255. Co kanál znamená, záleží na světle: u jednoduchého RGB LED reflektoru (LED par) je to typicky kanál pro červenou, zelenou a modrou za sebou. Světlu se nastaví **adresa** = číslo jeho prvního kanálu. Když má adresu 1, poslouchá na kanálech 1, 2, 3.

### Třída `LightRig` (rig.py:12)

Je to `Adjustable`, takže má slidery: `Brightness` (maximální jas), `Smoothing` (jak pomalu se mění), `Address` (kanál červené, 1..510, aby se G a B vešly do 512) a `Universe` (0..15).

`self.rgb` je aktuální barva, tři čísla 0..1.

**Vyhlazení, `update(bands)` (rig.py:25):**

```python
keep = self.settings["Smoothing"]
self.rgb = [keep * old + (1 - keep) * new for old, new in zip(self.rgb, bands)]    # rig.py:34
```

`bands` jsou (basy, středy, výšky) z analyzátoru. `zip` je spáruje s (R, G, B): basy -> červená, středy -> zelená, výšky -> modrá. Nová barva = `keep` díl staré + `(1 - keep)` díl cílové. Při Smoothing 0,6 a skoku cíle z 0 na 1 jde barva 0 -> 0,4 -> 0,64 -> 0,78 -> ... tedy plynule. Je to stejný typ filtru jako klouzavý průměr basů u detekce úderu. Smoothing 0 = světlo skáče okamžitě (ostré záblesky), 0,95 = velmi pomalé přechody. Volá se každý snímek z `LightPage.tick`.

**`values()` (rig.py:36)**: `round(c * brightness * 255)` udělá z 0..1 celé číslo 0..255.

**`channels()` (rig.py:48)**: celé universe jako seznam 512 čísel.

```python
frame = [0] * DMX_CHANNELS                # 512 nul
start = self.address() - 1                # DMX čísluje od 1, Python od 0
frame[start:start + 3] = self.values()    # na místo světla zapíše R, G, B
```

`[0] * 512` je seznam 512 nul. Přiřazení do výřezu `frame[a:a+3] = [r, g, b]` přepíše tři prvky za sebou.

---

## 7. `sirens/light/artnet.py`: posílání po síti

### Síť od nuly

- **IP adresa** (např. `127.0.0.1`, `2.0.0.10`) určuje počítač nebo zařízení v síti. `127.0.0.1` je vždycky „tenhle počítač“, takže se dá testovat proti programu (QLC+, Capture) na stejném počítači.
- **Port** (číslo 0..65535) určuje, kterému programu na tom počítači zpráva patří. Art-Net má pevně port **6454**.
- **UDP** je způsob posílání: zabalíš data do **paketu** (datagramu) a pošleš. Nečeká se na potvrzení a nenavazuje se spojení (na rozdíl od TCP). Když se paket ztratí, nevadí, za 33 ms letí další s aktuálními hodnotami. Pro světla v reálném čase je to ideální.
- **Socket** je v programu „zásuvka do sítě“: objekt, přes který se posílá a přijímá. `socket.socket(socket.AF_INET, socket.SOCK_DGRAM)` = socket pro IPv4 adresy (`AF_INET`) a UDP (`SOCK_DGRAM`).
- **Broadcast**: `setsockopt(SOL_SOCKET, SO_BROADCAST, 1)` povolí posílat i na adresu, která znamená „všem v síti“ (třeba `2.255.255.255`). Bez toho by systém takové odeslání odmítl.
- **Bajt** = 8 bitů = číslo 0..255. Síťový paket je jen řada bajtů. Python typ `bytes` je přesně taková řada. `bytes([1, 2, 255])` udělá 3 bajty. Proto musí DMX hodnoty být 0..255: jinak `bytes()` vyhodí chybu.

### Paket ArtDmx

**Art-Net** je protokol, který přenáší DMX po běžné síti (Ethernet/Wi-Fi). Paket s hodnotami kanálů se jmenuje ArtDmx a skládá se z 18bajtové hlavičky a dat:

| Pole | Bajtů | Hodnota u nás | Pozn. |
|---|---|---|---|
| ID | 8 | `"Art-Net\0"` | text + nulový bajt, podle toho příjemce pozná Art-Net |
| OpCode | 2 | `0x5000` | „tohle je ArtDmx“; little-endian |
| ProtVer | 2 | 14 | verze protokolu; big-endian |
| Sequence | 1 | 1..255 | pořadí paketu; 0 by znamenalo „nesleduj pořadí“ |
| Physical | 1 | 0 | číslo fyzického portu, nepoužíváme |
| SubUni | 1 | spodních 8 bitů universa | |
| Net | 1 | dalších 7 bitů universa | |
| Length | 2 | 512 | počet kanálů; big-endian |
| Data | 512 | hodnoty kanálů | |

**Endianita (endian)**: číslo větší než 255 se nevejde do jednoho bajtu, takže zabere dva. Otázka je, který bajt jde první. **Big-endian** = vyšší bajt první, **little-endian** = nižší bajt první. 512 je šestnáctkově `0x0200`: big-endian `02 00`, little-endian `00 02`. Art-Net to má schválně napůl: OpCode little-endian, verze a délka big-endian. (Šestnáctková soustava, hex: `0x` na začátku, číslice 0–9 a a–f; `0xFF` = 255, jeden bajt jsou přesně dvě hex číslice.)

### `send()` (artnet.py:35)

```python
data = bytes(channels)
header = (struct.pack("<8sH", b"Art-Net\0", 0x5000)
          + struct.pack(">HBBBBH", 14, self.sequence, 0,
                        universe & 0xFF, (universe >> 8) & 0x7F, len(data)))
self.sock.sendto(header + data, (ip, PORT))
self.sequence = self.sequence % 255 + 1
```

- `struct.pack(formát, hodnoty...)` ze standardní knihovny poskládá čísla do bajtů podle **formátovacího řetězce**: první znak je pořadí bajtů (`<` little, `>` big), pak pro každou hodnotu jedno písmeno: `8s` = 8 bajtů textu, `H` = 2bajtové číslo bez znaménka, `B` = 1bajtové číslo.
- `b"Art-Net\0"` je bajtový řetězec, `\0` je ten nulový bajt na konci.
- `universe & 0xFF` = **bitový AND** s 255, nechá jen spodních 8 bitů. `universe >> 8` = posun o 8 bitů doprava (vydělení 256), `& 0x7F` (127) nechá 7 bitů. Číslo universa tak rozdělíme na dva bajty. U nás je universe max 15, takže Net je vždycky 0.
- `header + data` spojí dvě řady bajtů, `sendto(bajty, (ip, port))` je pošle jako jeden UDP paket.
- `self.sequence % 255 + 1`: `%` je zbytek po dělení. Výsledek jde 1, 2, ..., 255, 1, ... a nikdy není 0. Podle sequence příjemce pozná, když mu nějaký paket přijde pozdě (starší než poslední).

Takhle vypadá začátek skutečného paketu pro universe 0, sequence 1 (hex):

```
41 72 74 2d 4e 65 74 00   00 50   00 0e   01   00   00 00   02 00   [512 bajtů dat]
A  r  t  -  N  e  t  \0   OpCode  verze  seq  phys  SubUni,Net  délka
```

Celý paket má 18 + 512 = 530 bajtů.

Když síť nefunguje (třeba neexistující síťová karta), `sendto` vyhodí `OSError`. `send` ho nechytá, chytá ho až `LightPage._send` v `sirens/ui/light_page.py` a ukáže chybu ve stavovém štítku. Tam se taky před odesláním kontroluje, že zadaná IP je platná adresa (`ipaddress.IPv4Address`).

---

## Vlastní zpracování signálu a obrazu

Tohle je místo, kde kód **sám** počítá se signálem, a ne jen volá hotovou funkci knihovny. Dobré to mít v hlavě na obhajobu.

**Zvukový signál:**

1. **Vlastní DFT** (`analyzer.py:52–89`): okno, matice cos/sin, výpočet reálné a imaginární části, amplituda, převod na dB. Nepoužíváme `np.fft` ani pyo `Spectrum`, numpy jen násobí pole.
2. **Hannovo okno** (`analyzer.py:52`) proti prosakování.
3. **Pomalé klesání spektra** (`analyzer.py:89`): špičkový follower s poklesem 2,5 dB na úsek.
4. **Trigger osciloskopu** (`analyzer.py:91–104`): hledání průchodu nulou směrem nahoru.
5. **Parabolická interpolace vrcholu** (`analyzer.py:110–126`): přesnější frekvence než rozlišení košů.
6. **Síla pásem** (`analyzer.py:128–136`): výběr košů maskou, maximum, převod dB -> 0..1.
7. **Logaritmické převzorkování spektra** (`features.py:31, 41`).
8. **Detekce úderu** (`features.py:46–61`): klouzavý průměr, práh, minimální pauza, doznívání.
9. **Vyhlazení světla** (`rig.py:34`): stejný typ jednopólového filtru (stará hodnota * keep + nová * (1 - keep)).

**Obrazový signál:**

1. **Aditivní míchání vrstev** (`layers.py:52`, `blend`) a ořez + převod na 8 bitů (`painter.py:45–47`).
2. **Výpočet geometrie tvarů** z dat o zvuku: Ring (polární souřadnice ze spektra), Wave (vzorky -> body), Bars (spektrum -> obdélníky), Orbit (pohyb po kružnici v čase). OpenCV tu jen kreslí čáry a kruhy podle našich bodů.
3. **Částicová simulace** (`layers.py:197–222`): vznik, pohyb, stárnutí a zánik částic ve vektorech numpy.
4. **Feedback** (`layers.py:271–278`): paměť minulého snímku + ztmavení násobením; matici a transformaci dělá OpenCV, ale samotný princip zpětné vazby (painter si drží `self.canvas`) je náš.
5. **Mirror** (`layers.py:288–294`): zrcadlení přímo přes výřezy pole.
6. **RGB Split** (`layers.py:359–364`): posun jednotlivých barevných kanálů.
7. **Tint** (`layers.py:393–401`): výpočet jasu, lineární interpolace mezi dvěma barvami, míchání s originálem.
8. **Warp** (`layers.py:340–349`): posunová mapa ze sinusovek počítáme sami, OpenCV `remap` ji jen použije.
9. **Glow** (`layers.py:313–320`): rozmazání je `GaussianBlur` z OpenCV, ale zesílení, přičtení a to, že se nedává do paměti (POST), je naše logika v `painter.py`.

Čistě knihovní operace jsou: kreslicí funkce `cv2.polylines/rectangle/circle`, `cv2.getRotationMatrix2D` + `cv2.warpAffine`, `cv2.GaussianBlur`, `cv2.remap`, `cv2.resize`. I ty ale pokaždé dostávají parametry spočítané ze zvuku.

---

## Kde se to napojuje

- `sirens/audio/engine.py`, `AudioEngine.__init__`: vytvoří `self.analyzer = Analyzer(self.source, sample_rate)`. `source` je součet všech nástrojů před hlasitostí.
- `sirens/ui/main_frame.py`, `_on_tick` (30x za sekundu): `analyzer.update()`, pak `sound_page.tick(analyzer, fresh)`, `visual_page.tick(analyzer, dt)` (když je Visual vidět nebo je otevřený Fullscreen) a vždycky `light_page.tick(analyzer)`.
- `sirens/ui/sound_page.py`, `tick`: čte `analyzer.scope()`, `peak_level_db()`, `freqs`, `spectrum`, `peak_frequency()` a konstantu `SCOPE_VIEW` pro osciloskop a spektrum v záložce Sound.
- `sirens/ui/visual_page.py`: vytvoří `Painter()`, menu vrstev staví z `layers.CATALOG`, v `tick` volá `painter.render(analyzer, dt)` a výsledek pošle do `VisualView` a `FullscreenWindow`.
- `sirens/ui/views.py`, `VisualView.show`: převede pole z Painteru na `wx.Bitmap`. `LightView` kreslí náhled barvy světla.
- `sirens/ui/light_page.py`: vytvoří `LightRig()` a `ArtNetSender()`. V `tick` volá `rig.update(analyzer.bands())`, v `_send` pak `sender.send(ip, rig.universe(), rig.channels())`, při zavření `sender.close()`.
- `sirens/session.py`: `capture` ukládá `painter.layers` (jméno, hodnoty sliderů, zapnuto) a `rig.settings`, `restore` je zase vytvoří přes `LAYERS_BY_NAME` (z `layers.CATALOG`).
- Uvnitř této části: `painter.py` importuje `Features`, `HEIGHT`, `WIDTH` a `FeedbackLayer`. Obě `layers.py` i `rig.py` stavějí na `sirens/param.py` (`Adjustable`, `Param`, `Choice`), `painter.py` na `sirens/stack.py`.

---

## Drobnosti, které je dobré znát

Nejsou to chyby, ale když se zeptají „proč to dělá tohle“, hodí se to vědět:

- Spektrum se nepočítá každý snímek, ale jen když je hotový nový úsek (zhruba každý druhý snímek). Features a světlo se ale přepočítávají každý snímek, takže občas pracují se stejnými daty dvakrát. Úseky taky nejdou plynule za sebou: nahrávání dalšího se spustí až v tiku, takže kousek zvuku mezi nimi se neanalyzuje. Pro obraz a světlo to nevadí.
- Rozlišení spektra je 21,5 Hz, takže u nejnižších bodů logaritmického spektra (pod ~350 Hz) připadá na jeden koš analyzátoru víc bodů a Bars/Ring tam ukazují „schody“ (několik stejných sloupců vedle sebe).
- Vyhlazení světla i doznívání beatu jsou „za snímek“, ne „za sekundu“. Kdyby aplikace běžela na jiném FPS, reagovaly by trochu jinak rychle.
- Glow počítá záři z toho, co je nakreslené **nad ním** v seznamu. Když ho dáš úplně nahoru, září jen paměť z minulého snímku (nebo nic).

---

## Na co se tě můžou zeptat

**1. Jak počítáte spektrum? Používáte FFT z knihovny?**
Ne. Je to vlastní DFT podle definice. Předem si spočítám matice cos a sin pro všechny frekvence (koše) a všechny vzorky. Pro nový úsek vynásobím vzorky Hannovým oknem, pak maticí cos (reálná část) a sin (imaginární část), z toho přes Pythagora amplitudu a z ní decibely. Numpy jen rychle násobí matice.

**2. K čemu je okno (Hann)?**
Úsek je vystřižený natvrdo, na krajích je skok a ten ve spektru udělá falešné frekvence (prosakování). Okno úsek na krajích plynule ztlumí do nuly, takže čáry ve spektru jsou ostré.

**3. Jaké je rozlišení spektra a proč?**
44 100 / 2048 = 21,5 Hz na koš. Delší úsek = jemnější rozlišení, ale pomalejší reakce. 2048 vzorků (~46 ms) je kompromis.

**4. Jak funguje detekce beatu?**
Sleduju klouzavý průměr basů (90 % starého + 10 % nového). Úder je, když basy vyskočí aspoň o 25 % (a o 0,05) nad průměr a od minulého úderu uběhlo aspoň 0,18 s. Pak je beat 1 a každý snímek se násobí 0,85, takže plynule dozní.

**5. Jak vypadá obraz v paměti a proč float 0..1?**
Numpy pole 360 x 640 x 3 (řádky, sloupce, R/G/B). Počítám ve `float32` 0..1, protože se dá násobit a sčítat bez přetečení. Na konci se ořízne na 0..1, vynásobí 255 a převede na `uint8`, to chce wx pro zobrazení.

**6. Jak se vrstvy skládají dohromady?**
Shora dolů, každá dostane obraz a vrátí upravený. Tvary kreslí do černé 8bitové vrstvy a ta se k obrazu přičte (aditivně, jako světlo projektorů). Efekty mění celý obraz. Glow se přičte až na konec a neukládá se do paměti.

**7. Jak funguje Feedback a proč se Glow nedává do paměti?**
Painter si pamatuje poslední snímek. Když je v seznamu Feedback, začne se od něj místo od černé; Feedback ho zvětší, otočí (afinní transformace) a ztmaví, takže starší tvary odplouvají a hasnou. Kdyby se do té paměti přičítala i záře, sčítala by se každý snímek znovu a obraz by zbělal.

**8. Která vrstva je čistě vaše operace nad obrazem? Vysvětli ji.**
Třeba Tint: spočítám jas každého pixelu jako průměr R, G, B, podle něj míchám mezi tmavou a světlou barvou (lineární interpolace), vynásobím jasem, aby černá zůstala černá, a smíchám s originálem podle Amount. Nebo Mirror: levou půlku pole obrátím (`[:, ::-1]`) a zapíšu do pravé.

**9. Co posíláte do světla a jak?**
Basy, středy a výšky (0..1) vyhladím a použiju jako R, G, B. Vynásobím jasem a 255, zapíšu na kanály Address, Address+1, Address+2 do seznamu 512 DMX kanálů. Ten zabalím do paketu Art-Net (ArtDmx: hlavička 18 bajtů + 512 bajtů dat) a pošlu UDP na port 6454.

**10. Proč UDP a co je v hlavičce Art-Net?**
UDP nečeká na potvrzení, je rychlé a ztracený paket nevadí, protože za 33 ms letí nový. Hlavička: „Art-Net\0“, OpCode 0x5000 (little-endian), verze 14 (big-endian), sequence 1..255, physical 0, universe ve dvou bajtech, délka dat (big-endian). Skládá se přes `struct.pack`.

**11. Jak jste to testovali bez skutečného světla?**
Záložka Light má náhled (barevný kruh s hodnotami R, G, B). Pakety se dají posílat na `127.0.0.1` a zobrazit v QLC+ nebo Capture na stejném počítači.
