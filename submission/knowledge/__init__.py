"""Put the kit harness on sys.path so `contract` imports work under the scorer and under tests."""
import sys
from pathlib import Path

_HARNESS = Path(__file__).resolve().parents[2] / "harness"
if _HARNESS.is_dir() and str(_HARNESS) not in sys.path:
    sys.path.insert(0, str(_HARNESS))
