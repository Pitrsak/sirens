# Sirens

Studio pro zvuk, obraz a světlo. Zvuk se skládá z bloků, obraz a světlo na něj reagují.

- **Sound:** zdroje (Sine, Harmonics, Sweep, Noise) se sčítají, efekty (Low-pass, High-pass,
  Delay, Distortion, Bitcrush) zpracují vše, co je nad nimi. Výsledek ukazuje osciloskop a spektrum.
- **Visual:** abstraktní obraz, který se hýbe podle zvuku.
- **Light:** RGB světlo řízené zvukem, posílané přes Art-Net.

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

- Záložky **Sound / Visual / Light** nahoře, **Stop / Play** vpravo ztlumí výstup.
- **Add block** přidá blok, **Up / Down** ho posune, **Remove** smaže. Zvuk teče shora dolů.
- Slidery: táhnout myší, kolečko = jemný posun, dvojklik = výchozí hodnota,
  kliknutí na číslo = zapsat přesnou hodnotu.
- Light: zadat IP adresu Art-Net zařízení a **Start sending**.
