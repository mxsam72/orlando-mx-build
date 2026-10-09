"""Pinned delivered v042 baseline and separate v043 authoring paths."""
from pathlib import Path
from v036_common import atomic, copy_exact, image_file, read, save, sha
R = Path(__file__).resolve().parents[1]
BASE = R / 'V042_OUTPUT'
O = R / 'V043_OUTPUT'
S = R / 'V043_SOURCE'
NAME = 'orlandomx_2026_v043'
