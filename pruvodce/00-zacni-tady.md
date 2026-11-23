# Průvodce kódem Sirens — začni tady

Tohle je průvodce pro člověka, který kód Sirens nikdy neviděl a potřebuje ho pochopit
tak, aby ho uměl vysvětlit a obhájit u prezentace i u ústní zkoušky. Nic se tu
nepředpokládá, všechno se vysvětluje od nuly.

## Jak to číst

| Kapitola | O čem je | Kdy ji číst |
|---|---|---|
| [00-zacni-tady.md](00-zacni-tady.md) | velký obrázek, mapa souborů, co se děje po spuštění | první |
| [01-zaklady.md](01-zaklady.md) | minimum Pythonu, pyo, wxPython, numpy a zvuku, které kód používá | druhá, pak se k ní vracej |
| [10-zvuk.md](10-zvuk.md) | jak vzniká zvuk: engine, nástroj, rack, bloky | jádro, číst pečlivě |
| [20-pisen-a-data.md](20-pisen-a-data.md) | píseň, patterny, přehrávač, ukládání | |
| [30-obraz-a-svetlo.md](30-obraz-a-svetlo.md) | analýza zvuku (DFT), obraz z vrstev | jádro, číst pečlivě |
| [40-okno-a-ovladaci-prvky.md](40-okno-a-ovladaci-prvky.md) | hlavní okno, jak funguje wxPython, vlastní slidery a tlačítka | |
| [50-zalozky.md](50-zalozky.md) | záložky Sound / Song / Visual, piano roll, časová osa, klávesy | |
| [90-otazky.md](90-otazky.md) | otázky, které můžou padnout u zkoušky, s odpověďmi | na konec, jako test |
| [99-slovnicek.md](99-slovnicek.md) | slovníček pojmů | kdykoli narazíš na neznámé slovo |

Rada: měj při čtení aplikaci spuštěnou a každou věc si v ní hned zkus. Odkazy typu
`sirens/audio/blocks.py:120` znamenají soubor a číslo řádku.

Spuštění (macOS, ve složce projektu; první dva řádky jen poprvé, viz README):

    python3.13 -m venv .venv
    .venv/bin/python -m pip install -i https://service.iim.cz/devpi/root/mm1 -r requirements.txt
    .venv/bin/python main.py

## Co Sirens je, v pěti větách

1. Sirens je desktopová aplikace v Pythonu, kde si ze zvukových bloků poskládáš nástroj (záložka **Sound**).
2. Z nástrojů pak na **Song** složíš píseň: až 8 stop, každá má patterny s notami a časovou osu.
3. Na **Visual** se z vrstev skládá abstraktní obraz, který reaguje na to, co právě hraje.
4. Zvuk jedné stopy (obálku a bloky, bez not) jde na Sound uložit jako **preset** do souboru a zase načíst (skupina Preset, tlačítka Save / Load, soubory v `assets/presets`).
5. Všechno se samo ukládá (autosave) a dá se to uložit i otevřít jako soubor.

Knihovny: **pyo** (zvuk), **wxPython** (okna a ovládání), **opencv-python** (kreslení do obrazu;
s ním se instaluje i **numpy**, na počítání s poli čísel). Zbytek je standardní knihovna Pythonu.

## Složky a soubory

```
main.py                  spouštěč: jen zavolá sirens/__main__.py
sirens/
  __main__.py            vytvoří wx aplikaci, zvukový engine a hlavní okno
  param.py               Param = popis jednoho slideru; Adjustable = cokoli, co má slidery
  stack.py               Stack = seznam prvků pod sebou (bloky zvuku, vrstvy obrazu)
  song.py                Song, Track, Pattern, Note: data písně
  session.py             převod celé práce na JSON a zpět (Save, Open, autosave, kopírování)
  audio/
    engine.py            pyo server a výstup do reproduktorů
    instrument.py        nástroj jedné stopy: noty (MIDI), obálka ADSR, rack
    rack.py              rack = bloky jednoho nástroje, propojuje je shora dolů
    blocks.py            všechny druhy bloků: zdroje zvuku a efekty
    player.py            přehrávač: hodiny, které posílají noty podle písně
    analyzer.py          analýza zvuku: osciloskop a vlastní DFT (spektrum)
  visual/
    features.py          z analýzy spočítá basy, středy, výšky, úder...
    layers.py            všechny druhy vrstev obrazu
    painter.py           poskládá vrstvy do jednoho snímku
  ui/                    všechno, co je vidět: okno, záložky, slidery, tlačítka
assets/                  uložené písně (.json) a presety zvuků (assets/presets)
```

Rozdělení je podle toho, **co** kód dělá: `audio/` nic neví o oknech, `visual/` nic neví o pyo
objektech (dostane jen čísla z analýzy), `ui/` jen ukazuje data a volá metody ostatních.
Tohle je odpověď na otázku „proč je to takhle rozdělené“: každá část jde pochopit a změnit
zvlášť, a třeba obraz by šel kreslit i z jiného zdroje zvuku.

## Co se stane po spuštění

```
main.py
 └─ sirens/__main__.py: main()
     1. wx.App()             připraví wxPython (bez toho nejde vytvořit žádné okno)
     2. AudioEngine()        nastartuje pyo server: od teď běží zvukové vlákno
     3. MainFrame(engine)    hlavní okno: vytvoří Song s jednou stopou, Player,
                             záložky, načte autosave, spustí časovač 30x za sekundu
     4. frame.Show()         ukáže okno
     5. app.MainLoop()       smyčka událostí: čeká na klik, klávesu, časovač... dokud okno nezavřeš
```

Proč engine dřív než okno: pyo objekty (oscilátory, filtry...) jde vytvořit až ve chvíli,
kdy server běží, a okno je hned vytváří (nástroj první stopy).

## Tři věci, které běží zároveň

Tohle je asi nejdůležitější věc na pochopení celé aplikace. Běží v ní tři „vlákna“
(vlákno = kus programu, který běží souběžně s ostatními):

| Kdo | Jak často | Co dělá | Kde |
|---|---|---|---|
| **zvukové vlákno pyo** | pořád, po kouscích 512 vzorků (~11,6 ms) | počítá samotný zvuk ze všech pyo objektů a posílá ho do repro | uvnitř knihovny pyo (v C) |
| **hodiny přehrávače** | 48x za takt (při 110 BPM asi 20x za s) | když hraje píseň, posílá nástrojům noty | `sirens/audio/player.py` |
| **hlavní vlákno wx** | při každé události + časovač 30x za s | reaguje na myš a klávesy, překresluje, počítá obraz, autosave | `sirens/ui/main_frame.py`, `_on_tick` |

Python kód nikdy nepočítá jednotlivé vzorky zvuku. Python jen **postaví síť pyo objektů**
(„tenhle oscilátor jde do tohohle filtru“) a mění jejich parametry. Vzorky pak počítá
pyo ve svém vlákně samo. Proto je zvuk plynulý, i když okno zrovna překresluje.

## Cesta jedné noty: od klávesy k reproduktoru

```
stiskneš A na klávesnici počítače
  -> ui/keys.py               klávesa A = nota číslo 60 (střední C) + aktuální oktáva
  -> engine.send_note()        pošle MIDI zprávu "nota 60 zapnuta, síla 100" na kanál stopy
  -> pyo Notein (instrument)   nástroj na tom kanálu ji chytí, dá jí volný hlas (max 4 noty naráz)
                               výška noty -> Hz (60 -> 261,6 Hz), síla -> obálka ADSR
  -> rack, bloky shora dolů    zdroje (Oscillator, Noise...) vyrobí signál pro každý hlas,
                               efekty (Filter, Delay...) ho upraví
  -> instrument.output         všechny hlasy sečtené do jednoho kanálu, krát hlasitost stopy
  -> engine                    sečte všechny stopy, krát hlavní hlasitost, ořízne na -1..1
  -> Pan(...).out()            do levého i pravého reproduktoru
```

Sekvencer (přehrávač písně) jde úplně stejnou cestou, jen místo klávesy posílá noty
`player.py` podle patternů. MIDI klávesnice taky, jen zprávu posílá přímo zařízení.

## Cesta zvuku do obrazu

```
engine.source (součet všech stop)
  -> audio/analyzer.py     nahrává posledních 2048 vzorků do tabulky,
                           počítá z nich spektrum vlastní DFT
  -> visual/features.py    z toho: hlasitost, basy, středy, výšky, úder (beat), tvar vlny
  -> visual/painter.py     projde vrstvy shora dolů, každá kreslí / upravuje obraz (numpy pole)
  -> ui/visual_page.py     ukáže obrázek v okně (nebo přes celou obrazovku)
```

Všechno tohle se děje v `MainFrame._on_tick` 30x za sekundu.

## Kde je „naše vlastní“ zpracování signálu

Hodnotí se vlastní operace se zvukem a obrazem, ne jen poskládané hotové funkce knihovny.
Podrobně je to rozepsané v kapitolách, tady jen kde hledat:

- **Spektrum zvuku:** vlastní DFT podle vzorce z přednášky, `sirens/audio/analyzer.py` (kapitola 30).
- **Vlastnosti zvuku pro obraz:** pásma, vyhlazování, detekce úderu, `sirens/visual/features.py` (kapitola 30).
- **Obraz:** vrstvy počítají s poli pixelů (míchání, posuny, zpětná vazba, záře), `sirens/visual/layers.py` (kapitola 30).
- **Zvuk:** bloky, kde si tvar vlny, zkreslení nebo ořez počítáme sami do tabulek, `sirens/audio/blocks.py` (kapitola 10).

## Jak se to učit

1. Přečti 01, aspoň zběžně.
2. Přečti 10 a u toho otevři `sirens/audio/blocks.py`. Komentáře v kódu jsou psané tak, aby šlo číst kód a průvodce vedle sebe.
3. Pak 30 (analýza zvuku a obraz), na tu část se nejspíš budou ptát nejvíc.
4. 20, 40 a 50 stačí pochopit v principu: co kde je a proč.
5. Nakonec 90 jako test. Na co neumíš odpovědět, vrať se do kapitoly.

Nejlepší způsob, jak kód pochopit: **něco v něm schválně změň a sleduj, co se stane**
(třeba `FPS = 30` v `main_frame.py` na 5, nebo `VOICES = 4` v `instrument.py` na 1).
Pak to vrať zpátky (`git checkout -- soubor`).
