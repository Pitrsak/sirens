# Sirens

Semestrální práce, B0B39MM1/BBB39MM1 Multimédia 1, FEL ČVUT, zimní semestr 2026/27.

Syntezátor, ze kterého vychází obraz a (později) světlo. Zvuk stavím krok po kroku
podle cvičení v souboru `sirens/sound.py`; aplikace k němu dává slidery, osciloskop
a spektrum (vlastní DFT) a po uložení souboru zvuk hned načte znovu.

## Instalace a spuštění (macOS)

1. Nainstalovat Python 3.13 z https://www.python.org/downloads/ (instalátor pro macOS).
2. Otevřít Terminál ve složce projektu a spustit:

        python3.13 -m venv .venv
        source .venv/bin/activate
        pip install -i https://service.iim.cz/devpi/root/mm1 -r requirements.txt
        python main.py

Příště už stačí `source .venv/bin/activate` a `python main.py`.

## Instalace a spuštění (Windows)

1. Nainstalovat Python 3.13 z https://www.python.org/downloads/windows/, verzi
   **Windows installer (64-bit)**. pyo pro Windows existuje jen 64bitový, takže 32bitový
   Python nepůjde. Na počítači s ARM procesorem taky vzít 64-bit (x64), ne ARM64.
2. Otevřít PowerShell ve složce projektu (v Průzkumníku Shift + pravé tlačítko
   -> "Otevřít okno PowerShellu zde") a spustit:

        py -3.13 -m venv .venv
        .venv\Scripts\python -m pip install -i https://service.iim.cz/devpi/root/mm1 -r requirements.txt
        .venv\Scripts\python main.py

Příště už stačí `.venv\Scripts\python main.py`. (Prostředí se schválně neaktivuje přes
`Activate.ps1`, protože to PowerShell ve výchozím nastavení blokuje.)

Když se ozve zvuk do špatného výstupu, přepnout výchozí zařízení ve Windows
(ikona reproduktoru na liště) a aplikaci spustit znovu.

Na Linuxu (Debian, Raspberry Pi) jde místo pip použít systémové balíčky:
`sudo apt install python3-pyo python3-wxgtk4.0 python3-opencv` a pak `python3 main.py`.

## Ovládání

- **Zvuk:** píše se do `sirens/sound.py` (návod je přímo v souboru). Po uložení se načte sám,
  ručně `Reload` nebo `Cmd+R` (na Windows `Ctrl+R`). Chyba v kódu se ukáže dole pod grafy i s číslem řádku.
- **Slidery:** kliknout / táhnout v pruhu, kolečko myši = jemný posun, dvojklik = výchozí hodnota,
  kliknutí na číslo = zapsat přesnou hodnotu (Enter potvrdí, Esc zruší).
- **Stop / Play** vpravo nahoře ztlumí výstup, `Master` je celková hlasitost.

## Struktura

- `sirens/sound.py` - můj zvuk, funkce `build(ui)` (krok po kroku podle cv2.py a cv3.py)
- `sirens/live.py` - načítání `sound.py` za běhu a `ui.slider()` / `ui.group()`
- `sirens/audio/` - `engine.py` (pyo server, výstup, ořez), `analyzer.py` (osciloskop a vlastní DFT)
- `sirens/ui/` - okno: `main_frame.py`, `sidebar.py` (pravý panel), `slider.py`, `views.py`
  (osciloskop a spektrum), `widgets.py` (nadpis, tlačítka), `theme.py` (barvy podle Event Horizon / Flip)
- `docs/` - zadání předmětu a závěrečná zpráva
- `reference/` - ukázky ze cvičení (NEODEVZDÁVÁ SE)

První verze s hotovým syntezátorem, presety a vizualizací je uložená ve větvi `demo-v1`.

## Signálový řetězec

    sound.py -> hlasitost (Master) -> Stop/Play -> ořez -1..1 -> obě repro
             \-> analýza: osciloskop (trigger na průchod nulou), spektrum (DFT, Hannovo okno)
