from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = REPO_ROOT / "notebooks" / "simapwatch_marimo.py"
MODE = "edit"  # "edit" fuer Notebook-Editor, "run" fuer App-Ansicht


def main() -> int:
    if not NOTEBOOK_PATH.exists():
        print(f"Notebook nicht gefunden: {NOTEBOOK_PATH}")
        return 1

    command = [sys.executable, "-m", "marimo", MODE, str(NOTEBOOK_PATH)]
    print("Starte marimo:")
    print(" ".join(command))
    return subprocess.call(command, cwd=str(REPO_ROOT))


if __name__ == "__main__":
    raise SystemExit(main())
