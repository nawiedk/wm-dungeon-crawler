"""Profiling der Sprite-Ladepipeline mit cProfile.

Wendet die im Skript beschriebene wissenschaftliche Methode an: messen →
Hypothese → optimieren → verifizieren. Ausgangshypothese war, dass
`_strip_background_and_crop` in `gui.py` der Flaschenhals sei, da es Pixel für
Pixel in einer reinen Python-Schleife über jedes der zehn Icons iteriert
(128×128 Pixel pro Icon) statt vektorisiert zu arbeiten. Die Messung
widerlegt das: `pygame.image.load` dominiert mit ca. 70% der Gesamtzeit,
während die ~155.000 `get_at`/`set_at`-Aufrufe der Pixelschleife trotz ihrer
hohen Anzahl kaum ins Gewicht fallen. Ursache: die als Rohmaterial genutzten
KI-generierten PNGs sind mit bis zu ~1,9 MB pro Datei weit größer, als für
das finale 32×32-Pixel-Ergebnis nötig wäre — eine Optimierung müsste also bei
den Quelldateien ansetzen (kleiner vorrendern), nicht bei der Crop-Schleife.

Separates Modul statt Teil von `gui.py`, da Profiling ein einmaliger
Analyseschritt ist, keine Laufzeitfunktionalität des Spiels.

Aufruf: ``uv run python -m wm_dungeon_crawler.profiling``
"""

from __future__ import annotations

import cProfile
import pstats

import pygame

from wm_dungeon_crawler.gui import _load_sprites

PROFILE_OUTPUT_PATH = "sprites.prof"


def main() -> None:
    """Profiled das Laden aller Sprites und gibt die teuersten Funktionen aus.

    Schreibt die Rohdaten zusätzlich nach `sprites.prof` (siehe
    `PROFILE_OUTPUT_PATH`), z.B. zur visuellen Analyse mit SnakeViz.
    """
    pygame.init()
    pygame.display.set_mode((1, 1))  # convert_alpha() braucht einen Anzeigemodus

    profiler = cProfile.Profile()
    profiler.enable()
    _load_sprites()
    profiler.disable()

    pygame.quit()

    stats = pstats.Stats(profiler)
    stats.dump_stats(PROFILE_OUTPUT_PATH)
    stats.sort_stats("cumulative")
    stats.print_stats(15)


if __name__ == "__main__":
    main()
