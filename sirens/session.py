"""Ukládání a načítání práce do souboru JSON.

Ukládá se jen to, co uživatel vytvořil: stopy (nástroj, bloky, patterny,
aranžmá, automatizace), vrstvy obrazu a nastavení světla. JSON je obyčejný
text, dá se otevřít i v textovém editoru.

Autosave: hlavní okno každé 2 s zapíše aktuální stav do AUTOSAVE (když se
změnil) a při spuštění ho načte. Po zavření nebo pádu se tak nic neztratí.
"""

import json
import os
from pathlib import Path

from sirens.audio.blocks import CATALOG as BLOCKS
from sirens.song import MAX_BARS, MIN_BARS, Note, Pattern
from sirens.visual.layers import CATALOG as LAYERS

AUTOSAVE = Path.home() / ".sirens" / "autosave.json"
BLOCKS_BY_NAME = {block_class.NAME: block_class for block_class in BLOCKS}
LAYERS_BY_NAME = {layer_class.NAME: layer_class for layer_class in LAYERS}


# --- uložení ---

def _lanes(automation: dict) -> dict:
    """Automatizace pro JSON: klíče slovníku musí být text, takže takt jako "3"."""
    return {label: {str(bar): value for bar, value in lane.items()}
            for label, lane in automation.items() if lane}


def _track(track) -> dict:
    instrument = track.instrument
    return {
        "name": track.name,
        "muted": track.muted,
        "current": track.current,
        "view_low": track.view_low,
        "instrument": dict(instrument.settings),
        "automation": _lanes(instrument.automation),
        "blocks": [{"block": block.NAME,
                    "values": {p.label: block.get(p.label) for p in block.PARAMS},
                    "extra": block.extra(),
                    "automation": _lanes(block.automation)}
                   for block in instrument.rack.blocks],
        "patterns": {name: {"bars": pattern.bars,
                            "notes": [[n.step, n.pitch, n.length] for n in pattern.notes]}
                     for name, pattern in track.patterns.items()},
        "arrangement": {str(bar): name for bar, name in track.arrangement.items()},
    }


def capture(song, painter, rig) -> dict:
    """Aktuální stav aplikace jako slovník (připravený pro JSON)."""
    return {
        "tempo": song.tempo,
        "bars": song.bars,
        "tracks": [_track(track) for track in song.tracks],
        "visual": [{"layer": layer.NAME, "values": dict(layer.settings)} for layer in painter.layers],
        "light": dict(rig.settings),
    }


# --- načtení ---

def _set_values(owner, values: dict):
    """Nastaví slidery; neznámé (např. ze starší verze programu) přeskočí."""
    for label, value in values.items():
        if any(p.label == label for p in owner.PARAMS):
            owner.set(label, value)


def _set_lanes(owner, lanes: dict):
    owner.automation = {label: {int(bar): value for bar, value in lane.items()}
                        for label, lane in lanes.items()}


def _restore_track(track, data: dict):
    track.name = data.get("name", track.name)
    track.muted = data.get("muted", False)
    track.current = data.get("current", "A")
    track.view_low = data.get("view_low", track.view_low)
    instrument = track.instrument
    _set_values(instrument, data.get("instrument", {}))
    _set_lanes(instrument, data.get("automation", {}))
    for item in data.get("blocks", []):
        block_class = BLOCKS_BY_NAME.get(item.get("block"))
        if block_class is None:
            continue
        block = instrument.rack.add(block_class)
        _set_values(block, item.get("values", {}))
        block.load_extra(item.get("extra", {}))
        _set_lanes(block, item.get("automation", {}))
    for name, item in data.get("patterns", {}).items():
        if name in track.patterns:
            pattern = Pattern(item.get("bars", 1))
            pattern.notes = [Note(*note) for note in item.get("notes", [])]
            track.patterns[name] = pattern
    track.arrangement = {int(bar): name for bar, name in data.get("arrangement", {}).items()}


def _list(data: dict, key: str) -> list:
    """Seznam slovníků ze souboru; cokoli jiného (např. ze starší verze) jako prázdný seznam."""
    items = data.get(key, [])
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def restore(data: dict, song, painter, rig):
    """Nastaví aplikaci podle uloženého slovníku (píseň vždy aspoň s jednou stopou)."""
    for track in list(song.tracks):
        song.remove_track(track)
    song.tempo = data.get("tempo", song.tempo)
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
    _set_values(rig, data.get("light", {}))


def write(path: Path, data: dict):
    """Zapíše stav do souboru.

    Nejdřív do dočasného souboru a pak ho jedním krokem přejmenuje (os.replace).
    Kdyby program spadl uprostřed zápisu, zůstane starý soubor celý.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=1), encoding="utf-8")
    os.replace(temp, path)


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
