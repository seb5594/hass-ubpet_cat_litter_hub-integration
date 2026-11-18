"""The shared workflow checks the reviewed package inventory without regenerating it."""

import runpy
from pathlib import Path

module = runpy.run_path(str(Path(__file__).resolve().parents[2] / "tools/provenance.py"))
print(f"Reviewed distribution inventory: {module['check']()} files")
