# Fathom

Semestrální práce, B0B39MM1/BBB39MM1 Multimédia 1, FEL ČVUT, zimní semestr 2026/27.

Aplikace pro syntézu zvuku, obrazu a světelného doprovodu na základě vstupu uživatele.

## Struktura

- `fathom/` - zdrojové kódy aplikace (pouze vlastní kód)
- `main.py` - spuštění
- `assets/` - zvukové a konfigurační soubory
- `docs/` - zadání předmětu a závěrečná zpráva
- `reference/` - ukázky ze cvičení (NEODEVZDÁVÁ SE)

## Instalace a spuštění

    python3.13 -m venv .venv
    source .venv/bin/activate
    pip install -i https://service.iim.cz/devpi/root/mm1 -r requirements.txt
    python main.py
