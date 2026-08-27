"""Ensures the repository root is on sys.path so `rms`/`adapters` import
cleanly regardless of how pytest is invoked (root vs. bridge/ suites are
separate pytest runs; see tests/README.md and bridge/README.md).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
