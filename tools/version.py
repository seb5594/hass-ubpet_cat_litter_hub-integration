"""Select the next Berlin calendar-day build and update the version source."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description="Prepare the next daily build (Europe/Berlin).")
parser.add_argument("--date", help="calendar day YYYY-MM-DD; default: today in Europe/Berlin")
parser.add_argument("--build", type=int, help="explicit build of the day: 0 is the first one without a suffix, then 1, 2, ...")
args = parser.parse_args()
day = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else datetime.now(ZoneInfo("Europe/Berlin")).date()
prefix = day.strftime("%Y.%m.%d")
path = ROOT / "custom_components/ubpet_cat_litter_hub/manifest.json"
manifest = json.loads(path.read_text(encoding="utf-8"))
tags = subprocess.check_output(["git", "tag", "--list", f"{prefix}", f"{prefix}.*", f"v{prefix}", f"v{prefix}.*"],
                               cwd=ROOT, text=True).splitlines()
pattern = re.compile(re.escape(prefix) + r"(?:\.(\d+))?")
# The first build of a day has no suffix and counts as build 0; later builds carry .1, .2, ...
previous = [int(m[1] or 0) for tag in [manifest["version"], *tags] if (m := pattern.fullmatch(tag.removeprefix("v")))]
build = args.build if args.build is not None else max(previous, default=-1) + 1
if build < 0:
    parser.error("The build number must not be negative")
version = prefix if build == 0 else f"{prefix}.{build}"
if version in tags or f"v{version}" in tags:
    parser.error("A Git tag for this version already exists")
manifest["version"] = version
path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
print(version)
