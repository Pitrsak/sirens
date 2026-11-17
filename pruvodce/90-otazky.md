# 90 — Otázky na zkoušku

Každá kapitola má na konci vlastní sekci **„Na co se tě můžou zeptat“** s otázkami k jejím souborům:
[10 zvuk](10-zvuk.md), [20 píseň a data](20-pisen-a-data.md), [30 obraz](30-obraz-a-svetlo.md),
[40 okno](40-okno-a-ovladaci-prvky.md), [50 záložky](50-zalozky.md).

Tady jsou otázky **přes celou aplikaci**, ty nejpravděpodobnější. Nejdřív si zkus odpovědět sám,
pak teprve čti odpověď.

---

**1. Popiš architekturu aplikace. Proč je rozdělená takhle?**

Čtyři části podle toho, co dělají: `audio/` (zvuk: engine, nástroj, bloky, přehrávač, analýza),
`visual/` (obraz z vrstev), datová část (`song.py`, `session.py`) a `ui/` (okno). Zvuk ani obraz nic neví o oknech, UI jen ukazuje data a volá jejich metody.
Každá část jde pochopit, vyzkoušet a změnit zvlášť.

**2. Co se stane, když stisknu klávesu A?**

`keys.py` ji přeloží na MIDI notu 60 (+ oktáva), `engine.send_note` pošle MIDI zprávu na kanál
vybrané stopy, `Notein` v nástroji jí přidělí hlas, výšku převede na Hz a sílu pošle do obálky ADSR,
bloky v racku z toho vyrobí zvuk, nástroj ho pošle do enginu, ten sečte všechny stopy, ořízne a pošle
do repro. Viz [00, cesta jedné noty](00-zacni-tady.md).

**3. Kolik vláken aplikace má a proč?**

Tři: zvukové vlákno pyo (počítá vzorky), hodiny přehrávače (posílají noty, vlastní vlákno kvůli přesnému
rytmu) a hlavní vlákno wx (události a časovač 30x za sekundu: obraz, autosave).

**4. Kde děláte vlastní zpracování zvuku, ne jen knihovní funkci?**

Vlastní DFT ve `analyzer.py` (podle vzorce z přednášky), vlastní křivky zkreslení a bitcrush
spočítané do tabulek (`ShaperBlock` v `blocks.py`), křivka poklesu výšky (Pitch drop),
pásma basy/středy/výšky a detekce úderu ve `features.py`. Podrobně v kapitolách 10 a 30.

**5. Kde děláte vlastní zpracování obrazu?**

Celý obraz je numpy pole, které vrstvy postupně mění: míchání vrstev, zpětná vazba (Feedback,
obraz minulého snímku se znovu použije), záře (Glow), vlnění posunem pixelů (Warp),
zrcadlení (Mirror) a částicová simulace (Particles).
opencv používáme na kreslení tvarů a na pár operací (rozmazání, otočení); kdy co, je v kapitole 30.

**6. Jak spolu souvisí zvuk a obraz?**

Analyzér 30x za sekundu vezme posledních 2048 vzorků výstupu, spočítá spektrum, `Features`
z něj udělá čísla 0..1 (hlasitost, basy, středy, výšky, úder) a vrstvy obrazu podle nich mění
velikost, barvu, rychlost (slider „React to“ určuje, na co vrstva reaguje).

**7. Jak funguje DFT a proč okno (Hann)?**

DFT rozloží úsek zvuku na frekvence: pro každou frekvenci k sečte součin vzorků se sinusem a kosinem
té frekvence; velký výsledek = ta frekvence ve zvuku je. Okno ztlumí kraje úseku, protože useknutý
úsek by jinak do spektra přidal falešné frekvence. Viz kapitola 30.

**8. Proč se program dřív padal při mazání stopy a jak je to vyřešené?**

Pyo objekt, který čte z tabulky, si drží jen ukazatel na její data. Když Python uvolnil tabulku
dřív než čtenáře, zvukové vlákno četlo uvolněnou paměť. Řešení: tabulky se za běhu neuvolňují
(`keep()`), staré zvuky chvíli doznívají v `retired`, a násobí se přes `mul=` místo `*`.
Kapitola 10, „Tři pravidla proti pádům“.

**9. Jak funguje přehrávač a proč 48 tiků na takt?**

Hodiny ve vlastním vlákně tikají 48x za takt. Pattern má mřížku po šestnáctinách (16 kroků na takt),
jeden krok jsou 3 tiky, takže 16 * 3 = 48 (jemná mřížka má 48 kroků, krok = 1 tik, viz otázka 12).
Tik je nejmenší jednotka přehrávače, na každém tiku
pošle noty, které začínají, a vypne ty, kterým skončila délka. Čas dalšího tiku se přičítá
k minulému, ne k „teď“, takže rytmus neujíždí. Kapitola 20.

**10. Jak funguje ukládání a autosave?**

`session.py` převede celou práci na slovník a ten na JSON text. Save ho zapíše do souboru, autosave
každé 2 s do `~/.sirens/autosave.json` (přes dočasný soubor, aby se při pádu nepoškodil). Při startu
se autosave načte, když existuje. Kapitola 20.

**11. Jak fungují presety zvuku?**

Zvuk stopy (obálka a bloky se slidery) umí `session.sound_of(track)` převést na slovník. Tlačítko
Save ve skupině Preset (záložka Sound) ho zapíše do souboru přes `session.write`, Load ho přečte
a nastaví stopě přes `session.apply_sound` (smaže její bloky a postaví je podle uložených jmen).
Soubor bez klíče `"blocks"` se odmítne, takže se omylem nenačte celá píseň. Noty zůstanou, mění se
jen zvuk. Hotové presety jsou v `assets/presets/` (drums, bass, synth). Stejný slovník používá
i Copy / Paste sound. Kapitola 10.

**12. K čemu je u patternu volba Grid (16ths / Fine) a co se stane při přepnutí?**

Šestnáctiny mají 16 kroků na takt (krok = 3 tiky), jemná mřížka 48 (krok = 1 tik, `Pattern.ticks_per_step()`
= 48 // grid), aby šly dát noty mimo šestnáctiny. `_set_grid` v `song_page.py` přepočítá noty,
aby zněly stejně: z 16 na 48 vynásobí kroky třemi (přesně), z 48 na 16 vydělí třemi a zaokrouhlí.
Když pak dvě noty skončí na stejném místě a výšce, `setdefault` nechá jen tu první. Piano roll
u jemné mřížky kreslí čáry jen po šestnáctinách, jinak by byla šedá kaše.

**13. Proč máte vlastní kreslené slidery místo wx.Slider?**

Kvůli vzhledu (tmavý pruh s popiskem, hodnotou a jednotkou, logaritmická stupnice, dvojklik = výchozí
hodnota). Jednodušší alternativa by byl standardní `wx.Slider` + `wx.StaticText`. Kapitola 40.

**14. Co byste zlepšili?**

Dobré mít připravené upřímně. Pár věcí, které jsou známé:
- efekty na celý mix (master) chybí,
- analýza obrazu běží i nad stejnými daty dvakrát po sobě (časovač je rychlejší než nové úseky),
- vyhlazování je „za snímek“, takže rychlost reakce závisí na FPS,
- kolečko myši nehýbe slidery s velkým krokem (např. Octave), protože posun 1 % se zaokrouhlí zpátky.
