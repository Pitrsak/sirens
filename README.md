# Sirens

Studio pro zvuk, obraz a světlo: nástroje, na které se hraje, píseň na časové ose,
obraz a světlo, které na hudbu reagují.

- **Sound:** nástroj vybrané stopy. Zdroje (Oscillator, Noise, Sampler)
  a efekty (Filter, Distortion, Bitcrush, Delay, Reverb) pod sebou, obálka not.
  Hraje se na klávesnici počítače, myší na klaviatuře nebo na MIDI klávesnici.
- **Song:** až 8 stop, každá s vlastním nástrojem. Patterny s notami, časová osa písně
  a automatizace sliderů v čase.
- **Visual:** obraz složený z vrstev (tvary a efekty), které reagují na zvuk. Lze i přes celou obrazovku.
- **Light:** RGB světlo řízené zvukem, posílané přes Art-Net.

Práce se ukládá sama (autosave) a otevře se při dalším spuštění; **Save / Open** ukládá do souboru.

## Instalace a spuštění

Potřeba je Python 3.13 z https://www.python.org/downloads/.

**macOS** (Terminál ve složce projektu):

    python3.13 -m venv .venv
    .venv/bin/python -m pip install -i https://service.iim.cz/devpi/root/mm1 -r requirements.txt
    .venv/bin/python main.py

**Windows** (PowerShell ve složce projektu). Python musí být 64bitový (Windows installer 64-bit):

    py -3.13 -m venv .venv
    .venv\Scripts\python -m pip install -i https://service.iim.cz/devpi/root/mm1 -r requirements.txt
    .venv\Scripts\python main.py

Příště už stačí jen poslední řádek.

## Ovládání

- Hraní: klávesy **A W S E D F T G Y H U J K** jako piano, **X / C** oktáva dolů / nahoru.
  **Keys: Hold** nechá tón znít, dokud se klávesa nestiskne znovu (zatím se dá ladit slidery).
- **Fullscreen** na záložce Visual: obraz přes celou obrazovku (s projektorem na druhé), zavře se **Esc** nebo dvojklikem.
- **Mezerník** nebo **Play** spustí a zastaví píseň (Loop = patterny dokola, Song = časová osa).
- **Add block / Add layer** přidá blok nebo vrstvu, **Off / On** ho vypne a zapne, **Up / Down** posune, **Remove** smaže.
- **Duplicate** (Song) zkopíruje stopu i se zvukem a patterny; **Copy sound / Paste sound** (Sound) přenese jen zvuk na jinou stopu.
- Pattern: klik do mřížky přidá notu, tažením se prodlouží, klik na notu ji smaže, kolečko posouvá výšky.
  Pruh **Vel** pod mřížkou nastaví sílu (hlasitost) not.
- Časová osa: klik / tažení v řádku stopy vloží její pattern, klik na **M** stopu ztlumí,
  spodní řádek kreslí automatizace vybraného slideru (pravé tlačítko bod smaže).
- **Song length** nastaví délku písně v taktech (ukáže i délku v minutách); kolečko myši nad časovou osou posouvá v čase.
- Slidery: táhnout myší, kolečko = jemný posun, dvojklik = výchozí hodnota,
  kliknutí na číslo = zapsat přesnou hodnotu.
