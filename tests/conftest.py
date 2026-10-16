import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for sub in ("guards", "jobs", "operators"):
    sys.path.insert(0, str(ROOT / sub))
