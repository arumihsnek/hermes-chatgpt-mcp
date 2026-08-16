from __future__ import annotations

import sys
from pathlib import Path


HERMES_ROOT = Path("/home/ubuntu/hermes-agent")
if HERMES_ROOT.is_dir() and str(HERMES_ROOT) not in sys.path:
    sys.path.insert(0, str(HERMES_ROOT))
