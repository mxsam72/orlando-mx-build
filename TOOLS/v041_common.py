"""Pinned delivered v040 baseline and v041 authoring paths."""
from pathlib import Path
from v036_common import atomic, copy_exact, image_file, read, save, sha
R=Path(__file__).resolve().parents[1]
BASE=R/"V040_OUTPUT"
O=R/"V041_OUTPUT"
S=R/"V041_SOURCE"
NAME="orlandomx_2026_v041"
