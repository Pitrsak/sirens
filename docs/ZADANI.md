# MM1 - zadání a pravidla (stav k 17. 10. 2026)

Zdroj: https://cw.fel.cvut.cz/b261/courses/mm1/start a https://cw.fel.cvut.cz/b261/courses/mm1/python

## Zadání (doslovně)

> Vytvořte aplikaci, která umožní syntézu zvukového signálu, obrazu a světelného doprovodu na základě vstupu uživatele. K realizaci využijte prostředí Python s knihovnami pyo, wxpython, opencv, protokolů artnet nebo MIDI. Podporované prostředí je linux, windows nebo MAC-OS.

Jednotná úloha: "produkce procedurálně generovaného obrazu a zvuku". Dvoučlenné týmy.

## Kritéria hodnocení

1. provázanost obrazu a zvuku
2. míra interaktivity
3. vlastní operace nad zvukovým signálem
4. vlastní operace nad obrazovým signálem
5. architektura návrhu (dekompozice na třídy případně moduly)
6. komentáře v kódu

## Body

- Semestrální úloha 24 b, testy 2 x 8 b, prezentace 10 b; celkem 50 b, zápočet od 20 b.
- Body nad 30 se připočítají ke zkoušce.
- Prezentace ve 14. týdnu na cvičení.

## AI

> Použití AI modelů při vytváření dílčích částí kódu je možné pod podmínkou, že oba členové týmu budou schopni jakoukoliv část kódu vysvětlit a obhájit při prezentaci i při pohovoru u zkoušky.

## Odevzdání (ZIP, spustitelný, v zápočtovém týdnu přes dropbox/filesender)

- pouze vámi vytvořené zdrojové kódy ve vlastní adresářové struktuře
- README v kořenovém adresáři s popisem obsahu
- datové (např. zvukové) a konfigurační soubory
- video nebo screenshot běžící aplikace
- závěrečná zpráva PDF, max 5 stran: záměr + inspirace, teoretický návrh (schéma), popis řešení, návod ke spuštění, parametry a ovládání

## Prostředí

- Python 3.13 (doporučeno 3.13.15; v nouzi 3.12), VS Code, venv
- `pip install -i https://service.iim.cz/devpi/root/mm1 wxpython pyo opencv-python`
- Linux potřebuje: portaudio19-dev, libportmidi-dev, libsndfile1-dev, libgtk-3-dev, liblo-dev, libpython3-dev
- ArtNET: stačí ukázky ze cvičení (`reference/mm1-cviceni/ArtNET`); testovat proti Capture nebo QLC+ na 127.0.0.1
- Ukázky: https://gitlab.fel.cvut.cz/mm1/python-examples
