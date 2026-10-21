"""Historie změn pro Undo / Redo.

Stav aplikace je text JSON ze session.capture() (stejná data jako autosave).
Hlavní okno ho zhruba třikrát za sekundu zachytí a předá historii (record).
Historie si pamatuje poslední známý stav a dva zásobníky:

    undo  dřívější stavy, navrchu ten těsně před aktuálním
    redo  stavy, ze kterých jsme odešli přes Undo (smaže je nová změna)

Ke každému stavu patří klíč (change_key): text bez toho, co se za změnu
nepočítá. Kroky se porovnávají podle klíče, obnovuje se celý text.
"""

import json

LIMIT = 100       # kolik kroků zpět si pamatujeme


def _without(values: dict, lanes: dict) -> dict:
    """Hodnoty sliderů kromě těch, které mají automatizaci."""
    return {label: value for label, value in values.items() if label not in lanes}


def change_key(data: dict) -> str:
    """Stav (slovník ze session.capture) jako text bez toho, co není změna od uživatele:
    - view_low: kam je odrolovaný editor patternu, to je jen pohled,
    - hodnoty sliderů s automatizací: při přehrávání Song je posouvá časová osa.
      Samotná automatizace (body na časové ose) se počítá."""
    tracks = []
    for track in data["tracks"]:
        track = dict(track)            # kopie, původní slovník se ještě ukládá do autosave
        del track["view_low"]
        track["instrument"] = _without(track["instrument"], track["automation"])
        track["blocks"] = [{**block, "values": _without(block["values"], block["automation"])}
                           for block in track["blocks"]]
        tracks.append(track)
    return json.dumps({**data, "tracks": tracks})


class History:
    def __init__(self):
        self.undo_stack = []     # dvojice (text, klíč)
        self.redo_stack = []
        self.now = None          # (text, klíč) posledního známého stavu

    def record(self, text: str, key: str):
        """Zapíše aktuální stav. Liší-li se klíč od posledního, je to nový krok."""
        if self.now is not None and key == self.now[1]:
            self.now = (text, key)          # žádný krok, jen čerstvý text (např. posunutý pohled)
            return
        if self.now is not None:
            self.undo_stack.append(self.now)
            del self.undo_stack[:-LIMIT]    # nejstarší kroky zahodíme
        self.redo_stack.clear()             # po nové změně už není co opakovat
        self.now = (text, key)

    def undo(self, text: str, key: str):
        """Vrátí text předchozího stavu, nebo None. Dosud nezapsanou změnu nejdřív
        zapíše, takže ji Undo vrátí jako první a Redo ji umí obnovit."""
        self.record(text, key)
        if not self.undo_stack:
            return None
        self.redo_stack.append(self.now)
        self.now = self.undo_stack.pop()
        return self.now[0]

    def redo(self, text: str, key: str):
        """Vrátí text stavu, ze kterého odešlo poslední Undo, nebo None.
        Je-li mezitím nová změna, record() redo smaže a není co opakovat."""
        self.record(text, key)
        if not self.redo_stack:
            return None
        self.undo_stack.append(self.now)
        self.now = self.redo_stack.pop()
        return self.now[0]

    @property
    def can_undo(self) -> bool:
        return bool(self.undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self.redo_stack)
