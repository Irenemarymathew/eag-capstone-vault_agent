"""Makes src/ importable from tests/ without sys.path hacks in every file."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
