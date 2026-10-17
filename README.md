# Fathom

Semestrální práce, B0B39MM1/BBB39MM1 Multimédia 1, FEL ČVUT, zimní semestr 2026/27.

Syntezátor, ze kterého vychází obraz a (později) světlo. Zvuk se tvoří
subtraktivní syntézou s vlastními vlnovými tvary, zkreslením a bitcrusherem;
analýza výstupu řídí spektrální zobrazení a abstraktní vizualizaci.

## Instalace a spuštění (macOS)

1. Nainstalovat Python 3.13 z https://www.python.org/downloads/ (instalátor pro macOS).
2. Otevřít Terminál ve složce projektu a spustit:

        python3.13 -m venv .venv
        source .venv/bin/activate
        pip install -i https://service.iim.cz/devpi/root/mm1 -r requirements.txt
        python main.py

Příště už stačí `source .venv/bin/activate` a `python main.py`.

Na Linuxu (Debian, Raspberry Pi) jde místo pip použít systémové balíčky:
`sudo apt install python3-pyo python3-wxgtk4.0 python3-opencv` a pak `python3 main.py`.

## Ovládání

- **Hraní:** klávesy `A S D F G H J K L` (bílé) a `W E T Y U O P` (černé), `Z`/`X` mění oktávu.
  Na klaviaturu dole jde klikat i myší.
- **Knoby:** táhnout myší nahoru/dolů (se Shiftem jemně), kolečko myši, dvojklik = výchozí hodnota.
- **Presety:** výběr nahoře, `Save` přepíše aktuální, `Save as...` uloží nový, `Init` vrátí výchozí zvuk.
  Presety jsou JSON soubory v `assets/presets/` a obsahují nastavení zvuku i vizualizace.
- **Záložky:** `SYNTH` (knoby zvuku), `SPECTRUM` (osciloskop, pásma, spektrogram),
  `VISUAL` (abstraktní obraz řízený zvukem, s vlastními knoby).

## Struktura

- `fathom/audio/` - zvuk: `tables.py` (vlnové tvary a křivka zkreslení), `synth.py` (hlasy a efekty),
  `analyzer.py` (banka filtrů pro spektrum), `params.py` (seznam parametrů), `engine.py` (pyo server)
- `fathom/visual/` - obraz: `spectrum.py` (analytické zobrazení), `abstract.py` (plazma, sklo, vlnky)
- `fathom/ui/` - okno a ovládací prvky: `main_frame.py`, `knob.py`, `keyboard.py`, `panels.py`, `theme.py`
- `fathom/presets.py` - ukládání presetů
- `assets/presets/` - presety
- `docs/` - zadání předmětu a závěrečná zpráva
- `reference/` - ukázky ze cvičení (NEODEVZDÁVÁ SE)

## Signálový řetězec

    OSC1 + OSC2 + šum -> filtr (MoogLP, obálka + LFO) -> ADSR      (x6 hlasů)
    součet hlasů -> drive (tanh) -> bitcrusher -> delay -> výstup
    výstup -> banka 24 pásmových filtrů -> spektrum / vizualizace (-> světla)
