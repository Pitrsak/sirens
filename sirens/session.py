"""Ukládání a načítání práce do souboru JSON.

Ukládá se jen to, co uživatel sám vytvořil: stopy (nástroj, bloky, patterny,
aranžmá) a vrstvy obrazu. JSON je obyčejnej
text, dá se klidně otevřít i v textovým editoru.

Autosave: hlavní okno každý 2 s zapíše aktuální stav do AUTOSAVE (když se
změnil) a při spuštění ho zase načte. Po zavření nebo pádu se tak nic neztratí.

Stejnej převod na slovník a zpátky slouží i ke kopírování: zvuk jedný stopy
na jinou (sound_of / apply_sound) a zdvojení celý stopy (duplicate).
"""

import json
import os
from pathlib import Path

from sirens.audio.blocks import CATALOG as BLOCKS
from sirens.song import MAX_BARS, MIN_BARS, STEPS_PER_BAR, Note, Pattern
from sirens.visual.layers import CATALOG as LAYERS

AUTOSAVE = Path.home() / ".sirens" / "autosave.json"      # ~/.sirens/autosave.json, v domovský složce
# jméno -> třída, ať se dá ze jména v souboru ("Filter") zase vyrobit blok / vrstva
BLOCKS_BY_NAME = {block_class.NAME: block_class for block_class in BLOCKS}
LAYERS_BY_NAME = {layer_class.NAME: layer_class for layer_class in LAYERS}


# ---- UKLÁDÁNÍ ----

def sound_of(track) -> dict:
    """Zvuk stopy: obálka a bloky nástroje se slidery."""
    instrument = track.instrument
    return {
        "instrument": dict(instrument.settings),    # dict(): kopie, ne odkaz na živý nastavení
        "blocks": [{"block": block.NAME,
                    "values": {p.label: block.get(p.label) for p in block.PARAMS},
                    "extra": block.extra(),         # něco navíc mimo slidery (např. cesta k samplu)
                    "enabled": block.enabled}
                   for block in instrument.rack.blocks],
    }


def _track(track) -> dict:
    return {
        "name": track.name,
        "muted": track.muted,
        "current": track.current,
        "view_low": track.view_low,
        **sound_of(track),          # ** vysype sem všechny klíče ze sound_of (instrument, blocks)
        # nota jako [krok, výška, délka, síla]; krok = šestnáctina (16 na takt)
        "patterns": {name: {"bars": pattern.bars,
                            "notes": [[n.step, n.pitch, n.length, n.velocity] for n in pattern.notes]}
                     for name, pattern in track.patterns.items()},
        "arrangement": {str(bar): name for bar, name in track.arrangement.items()},
    }


def capture(song, painter) -> dict:
    """Aktuální stav aplikace jako slovník (ready pro JSON)."""
    return {
        "tempo": song.tempo,
        "bars": song.bars,
        "tracks": [_track(track) for track in song.tracks],
        "visual": [{"layer": layer.NAME, "values": dict(layer.settings), "enabled": layer.enabled}
                   for layer in painter.layers],
    }


# ---- NAČTENÍ ----

def _set_values(owner, values: dict):
    """Nastaví slidery; neznámý (např. ze starší verze programu) přeskočí."""
    for label, value in values.items():
        if any(p.label == label for p in owner.PARAMS):
            owner.set(label, value)


def apply_sound(track, data: dict):
    """Nastaví stopě zvuk ze slovníku (viz sound_of), její dosavadní bloky zahodí."""
    instrument = track.instrument
    instrument.rack.clear()
    # .get(klíč, výchozí): když klíč v souboru chybí, nespadne to, vezme se výchozí
    _set_values(instrument, data.get("instrument", {}))
    for item in data.get("blocks", []):
        block_class = BLOCKS_BY_NAME.get(item.get("block"))
        if block_class is None:
            continue                 # blok, kterej už neexistuje, prostě vynechám
        block = instrument.rack.add(block_class)
        _set_values(block, item.get("values", {}))
        block.load_extra(item.get("extra", {}))
        block.enabled = item.get("enabled", True)
    instrument.rack.changed()        # znovu propojit, některý bloky mohly bejt uložený vypnutý


def _restore_track(track, data: dict):
    track.name = data.get("name", track.name)
    track.muted = data.get("muted", False)
    track.current = data.get("current", "A")
    track.view_low = data.get("view_low", track.view_low)
    apply_sound(track, data)
    for name, item in data.get("patterns", {}).items():
        if name in track.patterns:
            # starší soubory: bez "grid" (= šestnáctiny) a noty jen [krok, výška, délka] (síla pak 100)
            pattern = Pattern(item.get("bars", 1))
            # trioly už nejsou, starý soubor s gridem 12 nebo 24 přepočítáme na šestnáctiny
            old_grid = item.get("grid", 16)
            scale = STEPS_PER_BAR / old_grid
            # Note(*note): seznam [krok, výška, délka, síla] se rozbalí do argumentů
            pattern.notes = [Note(round(n[0] * scale), n[1], max(1, round(n[2] * scale)), *n[3:])
                             for n in item.get("notes", [])]
            track.patterns[name] = pattern
    track.arrangement = {int(bar): name for bar, name in data.get("arrangement", {}).items()}


def duplicate(song, track):
    """Nová stopa se stejným zvukem a patternama. Na časový ose je ale prázdná:
    kdyby hrála ve stejných taktech, jen by zdvojila hlasitost.
    Vrací novou stopu, nebo None, když už je stop maximum."""
    copy = song.add_track()
    if copy is not None:
        # trik: stopu převedu na slovník a hned ho nahraju do nový, kopírování zadarmo
        data = _track(track)
        data["name"] = f"{track.name} copy"
        data["arrangement"] = {}
        _restore_track(copy, data)
    return copy


def _list(data: dict, key: str) -> list:
    """Seznam slovníků ze souboru; cokoli jinýho (např. ze starší verze) bere jako prázdnej seznam."""
    items = data.get(key, [])
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def restore(data: dict, song, painter):
    """Nastaví aplikaci podle uloženýho slovníku (píseň má vždycky aspoň jednu stopu)."""
    for track in list(song.tracks):      # list(): kopie, protože ze song.tracks během cyklu mažu
        song.remove_track(track)
    song.tempo = data.get("tempo", song.tempo)
    # délku písně ořízneme do povolenýho rozsahu MIN_BARS..MAX_BARS
    song.bars = min(MAX_BARS, max(MIN_BARS, int(data.get("bars", 32))))
    for item in _list(data, "tracks"):
        track = song.add_track()
        if track is not None:
            _restore_track(track, item)
    if not song.tracks:
        song.add_track()

    painter.clear()
    for item in _list(data, "visual"):
        layer_class = LAYERS_BY_NAME.get(item.get("layer"))
        if layer_class is not None:
            layer = painter.add(layer_class)
            _set_values(layer, item.get("values", {}))
            layer.enabled = item.get("enabled", True)


def write(path: Path, data: dict):
    """Zapíše stav do souboru.

    Nejdřív do dočasnýho souboru a pak ho jedním krokem přejmenuje (os.replace).
    Kdyby program spadl uprostřed zápisu, zůstane starej soubor celej.
    """
    path.parent.mkdir(parents=True, exist_ok=True)     # složka (např. ~/.sirens) nemusí ještě existovat
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=1), encoding="utf-8")   # indent=1: čitelný odsazení
    os.replace(temp, path)


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
