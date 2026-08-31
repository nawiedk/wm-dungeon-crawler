# WM-Dungeon-Crawler

Ein rundenbasiertes Fluchtspiel: Die Spielfigur muss aus einem Fußballstadion
entkommen, dabei Hindernissen ausweichen, Gegenstände einsammeln und ihre
Ausdauer sinnvoll einteilen.

Entstanden als Abschlussprojekt (Hausarbeit) im Modul *Einführung in Python*,
HHU Düsseldorf, SoSe 2026.

## Installation

Voraussetzung: [uv](https://docs.astral.sh/uv/)

```bash
uv sync
```

## Verwendung

Grafische Oberfläche (pygame):

```bash
uv run python -m wm_dungeon_crawler.gui
```

Steuerung: Pfeiltasten/`w`/`a`/`s`/`d` gehen, zusätzlich Shift halten zum
Sprinten, `r` ausruhen, `F5`/`F9` Spielstand speichern/laden, `Esc` beenden.

Außerdem gibt es eine Text-Variante mit denselben Regeln (nützlich zum
schnellen Testen ohne Fenster):

```bash
uv run python -m wm_dungeon_crawler
```

Steuerung dort: `w`/`a`/`s`/`d` gehen, `W`/`A`/`S`/`D` sprinten, `r`
ausruhen, `save`/`load` Spielstand speichern/laden, `q` beendet.

In beiden Varianten gilt: Gegenstände werden automatisch beim Betreten
ihres Feldes eingesammelt und schließen dabei sofort alle noch
verschlossenen Türen auf. Landet die Spielfigur auf demselben Feld wie
eine Sicherheitskraft, ist die Partie verloren; wird der Ausgang erreicht,
ist sie gewonnen.

## Tests

```bash
uv run pytest
```

Führt sowohl die Unit-/Property-Tests aus `tests/` als auch alle Doctests im
Paket aus. Mit Testabdeckung:

```bash
uv run pytest --cov
```