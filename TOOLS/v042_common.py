"""Pinned delivered v041 baseline and separate v042 authoring paths."""
from pathlib import Path
from v036_common import atomic, copy_exact, image_file, read, save, sha
R = Path(__file__).resolve().parents[1]
BASE = R / 'V041_OUTPUT'
O = R / 'V042_OUTPUT'
S = R / 'V042_SOURCE'
NAME = 'orlandomx_2026_v042'
