"""Pinned v039 baseline and v040 authoring paths."""
from pathlib import Path
from v036_common import atomic, copy_exact, image_file, read, save, sha
R=Path(__file__).resolve().parents[1]
BASE=R/'V039_OUTPUT'
O=R/'V040_OUTPUT'
S=R/'V040_SOURCE'
NAME='orlandomx_2026_v040'
