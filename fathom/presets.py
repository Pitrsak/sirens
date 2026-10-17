"""Ukládání a načítání presetů jako JSON souborů v assets/presets/.

Preset obsahuje nastavení syntezátoru i vizualizace:
    {"synth": {"cutoff": 800, ...}, "visual": {"speed": 1.0, ...}}
"""

import json
import re
from pathlib import Path

PRESET_DIR = Path(__file__).resolve().parent.parent / "assets" / "presets"


def _file_name(name: str) -> str:
    """Z názvu presetu udělá bezpečný název souboru (jen písmena, čísla, mezery, - a _)."""
    clean = re.sub(r"[^\w \-]", "", name).strip()
    return (clean or "preset") + ".json"


class PresetStore:
    def __init__(self, folder: Path = PRESET_DIR):
        self.folder = folder
        self.folder.mkdir(parents=True, exist_ok=True)

    def names(self) -> list[str]:
        return sorted(path.stem for path in self.folder.glob("*.json"))

    def load(self, name: str) -> dict:
        with open(self.folder / _file_name(name), encoding="utf-8") as f:
            return json.load(f)

    def save(self, name: str, data: dict) -> str:
        """Uloží preset a vrátí název, pod kterým byl skutečně uložen."""
        path = self.folder / _file_name(name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return path.stem
