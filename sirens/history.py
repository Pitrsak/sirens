"""Historie změn pro Undo / Redo.

Stav aplikace je text JSON ze session.capture() (stejný data jako autosave).
Hlavní okno ho zhruba třikrát za sekundu zachytí a předá historii (record).
Historie si pamatuje poslední známej stav a dva zásobníky (stack = hromádka,
bere se vždycky z vrchu):

    undo  dřívější stavy, navrchu ten těsně před aktuálním
    redo  stavy, ze kterých jsme odešli přes Undo (nová změna je smaže)

Ke každýmu stavu patří klíč (change_key): ten samej text, jen bez toho, co se
za změnu nepočítá. Kroky se porovnávaj podle klíče, ale obnovuje se celej text.
"""

import json

LIMIT = 100       # kolik kroků zpátky si pamatujeme, ať to nežere paměť donekonečna


def _without(values: dict, lanes: dict) -> dict:
    """Hodnoty sliderů kromě těch, který maj automatizaci."""
    return {label: value for label, value in values.items() if label not in lanes}


def change_key(data: dict) -> str:
    """Stav (slovník ze session.capture) jako text bez toho, co není změna od uživatele:
    - view_low: kam je odrolovanej editor patternu, to je jen pohled,
    - hodnoty sliderů s automatizací: při přehrávání Song je posouvá časová osa sama.
      Samotná automatizace (body na časový ose) se ale počítá."""
    tracks = []
    for track in data["tracks"]:
        track = dict(track)            # kopie, původní slovník se ještě ukládá do autosave, ten nesmím rozbít
        del track["view_low"]
        track["instrument"] = _without(track["instrument"], track["automation"])
        # {**block, "values": ...} = kopie bloku, jen "values" se přepíše
        track["blocks"] = [{**block, "values": _without(block["values"], block["automation"])}
                           for block in track["blocks"]]
        tracks.append(track)
    return json.dumps({**data, "tracks": tracks})


class History:
    def __init__(self):
        self.undo_stack = []     # dvojice (text, klíč)
        self.redo_stack = []
        self.now = None          # (text, klíč) posledního známýho stavu

    def record(self, text: str, key: str):
        """Zapíše aktuální stav. Když se klíč liší od posledního, je to novej krok."""
        if self.now is not None and key == self.now[1]:
            self.now = (text, key)          # žádnej krok, jen čerstvej text (např. posunutej pohled)
            return
        if self.now is not None:
            self.undo_stack.append(self.now)
            del self.undo_stack[:-LIMIT]    # nejstarší kroky zahodíme (nechá se jen posledních LIMIT)
        self.redo_stack.clear()             # po nový změně už není co opakovat
        self.now = (text, key)

    def undo(self, text: str, key: str):
        """Vrátí text předchozího stavu, nebo None. Změnu, co ještě není zapsaná,
        nejdřív zapíše, takže ji Undo vrátí jako první a Redo ji pak umí obnovit."""
        self.record(text, key)
        if not self.undo_stack:
            return None
        self.redo_stack.append(self.now)    # odkud odcházíme, to jde na redo
        self.now = self.undo_stack.pop()
        return self.now[0]

    def redo(self, text: str, key: str):
        """Vrátí text stavu, ze kterýho odešlo poslední Undo, nebo None.
        Když je mezitím nová změna, record() redo smaže a není co opakovat."""
        self.record(text, key)
        if not self.redo_stack:
            return None
        self.undo_stack.append(self.now)
        self.now = self.redo_stack.pop()
        return self.now[0]

    # @property: čte se jako proměnná (history.can_undo), bez závorek
    @property
    def can_undo(self) -> bool:
        return bool(self.undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self.redo_stack)
