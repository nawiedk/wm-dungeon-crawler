"""Bestenliste: die wenigsten benötigten Runden bis zum Sieg.

Separates Modul statt Teil von `persistence.py`, da dort ausschließlich der
vollständige Spielzustand fürs Speichern/Laden einer einzelnen Partie
gespiegelt wird; die Bestenliste ist ein eigenständiges, viel einfacheres
Konzept (nur eine Rundenzahl pro Eintrag), das über einzelne Partien hinweg
bestehen bleibt.

Anders als bei `persistence.save_game`/`load_game` gilt eine fehlende oder
beschädigte Bestenlisten-Datei nicht als Fehler: die Bestenliste ist reine
Kür, kein kritischer Spielzustand. In beiden Fällen wird deshalb einfach mit
einer leeren Liste weitergemacht, statt eine Exception zu werfen.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field, ValidationError

DEFAULT_HIGHSCORE_PATH: Path = Path("highscores.json")
MAX_ENTRIES = 3


class _HighscoreData(BaseModel):
    """Pydantic-Validierungsschema für die Bestenlisten-Datei."""

    turns: list[Annotated[int, Field(ge=0)]] = Field(default_factory=list)


def load_highscores(path: Path = DEFAULT_HIGHSCORE_PATH) -> list[int]:
    """Lädt die Bestenliste (aufsteigend, wenige Runden zuerst).

    Liefert eine leere Liste, wenn die Datei fehlt oder beschädigt ist
    (siehe Modul-Docstring). Sortiert und kürzt defensiv auf `MAX_ENTRIES`,
    auch falls die Datei von Hand verändert wurde.

    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     load_highscores(Path(tmp) / "does_not_exist.json")
    []
    """
    try:
        raw = path.read_text(encoding="utf-8")
        data = _HighscoreData.model_validate_json(raw)
    except (FileNotFoundError, ValidationError):
        return []
    return sorted(data.turns)[:MAX_ENTRIES]


def record_attempt(turns: int, path: Path = DEFAULT_HIGHSCORE_PATH) -> list[int]:
    """Trägt einen neuen Versuch in die Bestenliste ein und speichert sie.

    Behält nur die `MAX_ENTRIES` wenigsten Rundenzahlen. Gibt die
    aktualisierte Bestenliste zurück.

    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     save_path = Path(tmp) / "highscores.json"
    ...     record_attempt(10, save_path)
    ...     record_attempt(5, save_path)
    ...     record_attempt(8, save_path)
    ...     record_attempt(20, save_path)
    [10]
    [5, 10]
    [5, 8, 10]
    [5, 8, 10]
    """
    scores = sorted([*load_highscores(path), turns])[:MAX_ENTRIES]
    path.write_text(
        _HighscoreData(turns=scores).model_dump_json(indent=2), encoding="utf-8"
    )
    return scores
