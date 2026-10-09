"""Immutable user-tested v038 baseline for the sign-only correction."""
from v036_common import atomic, copy_exact, image_file, read, save, sha
from pathlib import Path

R = Path(__file__).resolve().parents[1]
S = R/'V039_SOURCE'
BASE = R/'V038_OUTPUT'
O = R/'V039_OUTPUT'
NAME = 'orlandomx_2026_v039'
