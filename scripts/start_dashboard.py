from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from simapwatch.dashboard.server import serve_dashboard


DB_PATH = SRC_ROOT / "simapwatch.db"
HOST = "127.0.0.1"
PORT = 8050


def main() -> int:
    serve_dashboard(db_path=str(DB_PATH), host=HOST, port=PORT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
