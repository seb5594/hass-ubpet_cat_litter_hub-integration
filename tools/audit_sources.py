"""Report source overlap with immutable research snapshots, without executing them.

This is a review aid, not a license or clean-room certificate. Only locations and
hashes are reported; upstream implementation text stays in the ignored cache.
"""

from __future__ import annotations

import argparse
import io
import json
import subprocess
import tokenize
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOTS = ROOT / ".github/provenance/sources.json"
IGNORED_TOKENS = {tokenize.COMMENT, tokenize.ENCODING, tokenize.NL, tokenize.NEWLINE,
                  tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER}


def git(folder, *args):
    return subprocess.check_output(["git", "-C", str(folder), *args], stderr=subprocess.DEVNULL)


def code_tokens(source):
    return [(token.string, token.start[0]) for token in tokenize.generate_tokens(io.StringIO(source).readline)
            if token.type not in IGNORED_TOKENS]


def text_values(data, prefix=""):
    if isinstance(data, dict):
        for key, value in data.items():
            yield from text_values(value, f"{prefix}.{key}".strip("."))
    elif isinstance(data, str):
        yield prefix, data


def load_corpus(source_root, fetch=False):
    snapshots = json.loads(SNAPSHOTS.read_text(encoding="utf-8"))["snapshots"]
    corpus, texts = {}, defaultdict(list)
    for snapshot in snapshots:
        repository, revision = snapshot["repository"], snapshot["sha"]
        folder = source_root / repository.replace("/", "__")
        if fetch:
            source_root.mkdir(parents=True, exist_ok=True)
            if not folder.exists():
                subprocess.run(["git", "clone", "--quiet", "--no-checkout", f"https://github.com/{repository}.git", str(folder)], check=True)
            subprocess.run(["git", "-C", str(folder), "fetch", "--quiet", "--no-tags", "origin", revision], check=True)
        rows = git(folder, "ls-tree", "-r", "--format=%(objectname) %(path)", revision).decode().splitlines()
        for row in rows:
            blob, path = row.split(" ", 1)
            if "custom_components/" not in path:
                continue
            if path.endswith(".py") and blob not in corpus:
                source = git(folder, "show", f"{revision}:{path}").decode("utf-8-sig")
                corpus[blob] = {"repository": repository, "sha": revision, "path": path, "tokens": code_tokens(source)}
            elif path.endswith(".json") and ("translations/" in path or path.endswith("/strings.json")):
                data = json.loads(git(folder, "show", f"{revision}:{path}").decode("utf-8-sig"))
                for key, value in text_values(data):
                    if len(value) >= 50:
                        texts[value].append({"repository": repository, "sha": revision, "path": path, "key": key})
    return snapshots, corpus, texts


def compare(corpus, component, width=35):
    index = defaultdict(list)
    for blob, source in corpus.items():
        tokens = source["tokens"]
        for offset in range(len(tokens) - width + 1):
            index[hash(tuple(token[0] for token in tokens[offset:offset + width]))].append((blob, offset))
    findings = []
    for path in sorted(component.glob("*.py")):
        current = code_tokens(path.read_text(encoding="utf-8"))
        runs = {}
        for offset in range(len(current) - width + 1):
            window = tuple(token[0] for token in current[offset:offset + width])
            for blob, old in index.get(hash(window), ()):
                original = corpus[blob]["tokens"]
                if window != tuple(token[0] for token in original[old:old + width]):
                    continue
                intervals = runs.setdefault((blob, old - offset), [])
                if intervals and intervals[-1][1] == offset + width - 1:
                    intervals[-1][1] += 1
                else:
                    intervals.append([offset, offset + width])
        for (blob, delta), intervals in runs.items():
            source = corpus[blob]
            for first, end in intervals:
                if current[end - 1][1] - current[first][1] < 3:
                    continue
                findings.append({"file": path.relative_to(ROOT).as_posix(), "line": current[first][1],
                                 "end_line": current[end - 1][1], "tokens": end - first,
                                 "source": {key: value for key, value in source.items() if key != "tokens"},
                                 "source_blob": blob, "source_line": source["tokens"][first + delta][1]})
    return findings


def run(source_root, fetch=False):
    snapshots, corpus, texts = load_corpus(source_root, fetch)
    component = ROOT / "custom_components/ubpet_cat_litter_hub"
    findings = compare(corpus, component)
    translations = []
    for path in sorted(component.rglob("*.json")):
        for key, value in text_values(json.loads(path.read_text(encoding="utf-8"))):
            if value in texts:
                translations.append({"file": path.relative_to(ROOT).as_posix(), "key": key, "source": texts[value][0]})
    return {"schema": 1, "snapshot_count": len(snapshots), "python_source_blobs": len(corpus),
            "criteria": {"consecutive_python_tokens": 35, "minimum_line_span": 4, "matching_text_characters": 50},
            "python_matches": findings, "translation_matches": translations,
            "legal_clearance": "not_asserted", "limitations": [
                "Matching tests cannot establish authorship or licensing rights.",
                "Shorter, renamed, reordered or otherwise transformed derivations require manual review.",
                "Only the listed public snapshots are covered; this is not a clean-room claim.",
            ]}


def main():
    parser = argparse.ArgumentParser(description="Quellüberlappungen mit festgehaltenen Recherche-Ständen melden.")
    parser.add_argument("--sources-root", type=Path, required=True)
    parser.add_argument("--fetch", action="store_true", help="Öffentliche Quellstände im Recherche-Cache abrufen")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.sources_root, args.fetch)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"{result['snapshot_count']} Stände, {result['python_source_blobs']} Python-Blobs; "
          f"{len(result['python_matches'])} Python- und {len(result['translation_matches'])} Textfundstellen")


if __name__ == "__main__":
    main()
