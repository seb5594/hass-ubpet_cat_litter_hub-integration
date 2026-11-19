"""Record reviewed distribution files and verify source/archive integrity.

Hashes make a reviewed inventory reproducible; they do not establish copyright
ownership or permission. Recording is an explicit maintainer action, never CI.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components/ubpet_cat_litter_hub"
INVENTORY = ROOT / ".github/provenance/distribution.json"
_FORBIDDEN = {"secrets.py", "secrets.py.example", ".env"}


def verify_vendor_data(path, record):
    if record.get("path") != "vendor_app_keys.json" or record.get("project_license_grant") != "excluded_from_project_MIT":
        raise ValueError("App data requires an explicit origin record and license scope")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != record.get("sha256"):
        raise ValueError("Predefined app data differs from the documented source")
    values = json.loads(raw)
    digests = {name: hashlib.sha256(value.encode()).hexdigest() for name, value in values.items()
               if isinstance(value, str) and value}
    if len(digests) != len(values) or digests != record.get("profiles"):
        raise ValueError("Predefined app profiles differ from the origin record")


def distribution_files(folder=COMPONENT):
    result = {}
    for path in sorted(folder.rglob("*")):
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"} or path.is_dir():
            continue
        relative = path.relative_to(folder).as_posix()
        if path.name == "vendor_app_keys.json":
            if path.resolve() != (COMPONENT / "vendor_app_keys.json").resolve():
                raise ValueError("Unregistered vendor_app_keys.json")
            record = json.loads((ROOT / ".github/provenance/vendor-data.json").read_text(encoding="utf-8"))
            verify_vendor_data(path, record)
        if path.is_symlink() or path.name in _FORBIDDEN or any(part.startswith(".") for part in Path(relative).parts):
            raise ValueError(f"Unerlaubter Paketinhalt: {relative}")
        contents = path.read_bytes()
        if path.suffix != ".png" and b"\r\n" in contents:
            raise ValueError(f"LF-Zeilenenden gemäß .gitattributes erforderlich: {relative}")
        result[relative] = hashlib.sha256(contents).hexdigest()
    return result


def verify(files, inventory):
    expected = {name: item["sha256"] for name, item in inventory["files"].items()}
    extra, missing = files.keys() - expected.keys(), expected.keys() - files.keys()
    changed = {name for name in files.keys() & expected.keys() if files[name] != expected[name]}
    if extra or missing or changed:
        raise ValueError(f"Paketprüfung fehlgeschlagen: neu={sorted(extra)}, fehlt={sorted(missing)}, geändert={sorted(changed)}")


def check(archive=None):
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    verify(distribution_files(), inventory)
    if (ROOT / "LICENSE").read_bytes() != (COMPONENT / "LICENSE").read_bytes():
        raise ValueError("Repository und Installationspaket müssen denselben Lizenztext enthalten")
    if archive:
        with ZipFile(archive) as zipped:
            if len(zipped.namelist()) != len(set(zipped.namelist())) or zipped.testzip() is not None:
                raise ValueError("Das ZIP enthält doppelte Namen oder beschädigte Dateien")
            verify({name: hashlib.sha256(zipped.read(name)).hexdigest() for name in zipped.namelist()}, inventory)
    return len(inventory["files"])


def record(review):
    rows = {}
    for name, digest in distribution_files().items():
        category = "project-source"
        if name.startswith("brand/"):
            category = "project-artwork"
        elif name in {"mobile_apps.json", "providers.json", "metrics.json", "http_profile.json"}:
            category = "compatibility-data"
        elif name == "vendor_app_keys.json":
            category = "third-party-application-data"
        elif name.startswith("LICENSE"):
            category = "license-notice"
        rows[name] = {"sha256": digest, "category": category}
        if category == "third-party-application-data":
            rows[name]["project_license_grant"] = "excluded_from_project_MIT"
            rows[name]["origin_record"] = ".github/provenance/vendor-data.json"
    data = {"schema": 2, "review": review, "project_license": "MIT", "legal_clearance": "not_asserted",
            "license_exclusions": ["vendor_app_keys.json"],
            "scope": "Project source and artwork only; no grant for vendor app data or earlier upstream code.", "files": rows}
    INVENTORY.parent.mkdir(exist_ok=True)
    INVENTORY.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser(description="Geprüften Paketbestand erfassen oder gegen Quellbaum und ZIP prüfen.")
    parser.add_argument("command", choices=("check", "record"))
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--review", help="Verweis auf die dokumentierte Herkunftsprüfung; nur bei record")
    args = parser.parse_args()
    if args.command == "record":
        if not args.review:
            parser.error("record benötigt --review; eine Prüfsumme ersetzt keine Herkunftsprüfung")
        record(args.review)
    print(f"Paketbestand geprüft: {check(args.archive)} Dateien")


if __name__ == "__main__":
    main()
