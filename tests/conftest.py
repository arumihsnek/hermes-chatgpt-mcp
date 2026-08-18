from __future__ import annotations

import os
import sys
from pathlib import Path


# Kanban workers inject HERMES_KANBAN_DB for their own board. The multi-board
# adapter tests must resolve temporary canonical board directories instead;
# individual tests that exercise the legacy override set it explicitly.
os.environ.pop("HERMES_KANBAN_DB", None)


HERMES_ROOT = Path("/home/ubuntu/hermes-agent")
if HERMES_ROOT.is_dir() and str(HERMES_ROOT) not in sys.path:
    sys.path.insert(0, str(HERMES_ROOT))
