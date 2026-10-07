#!/usr/bin/env python3
"""draw_circuit.py - plain English (or circuit lingo) -> circuit lingo + diagram files.

    python scripts/draw_circuit.py "12 V battery, a 4 ohm and a 2 ohm in series, that pair in parallel with a 6 ohm, then a 3 ohm"
    python scripts/draw_circuit.py --lingo "source: 12 V\\ncircuit: (4 + 2) || 6 + 3" --out figures/problem1
    python scripts/draw_circuit.py --file description.txt --solve --standard IEC

Prints ONE json object to stdout.  Exit codes:
    0  drawn           2  the rules could not read the sentence (message names the word: write the lingo
    3  invalid lingo      yourself and rerun with --lingo)     4  drawing failed     5  missing package

Settings (symbol standard, label style, formats, dpi, ...) come from config.json next to this folder;
--config points at another file, and --standard / --labels / --formats / --solve override single values.
No AI is used here: the same words always give the same lingo and the same picture.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

try:
    import schemdraw  # noqa: F401
    import matplotlib  # noqa: F401
except ImportError as e:   # pragma: no cover
    print(json.dumps({"ok": False, "error": f"missing package: {e.name}. Run:  pip install -r {ROOT / 'requirements.txt'}"}))
    sys.exit(5)

import lingo            # noqa: E402
import render_worker    # noqa: E402

DEFAULTS = {"symbol_standard": "US", "labels": "name_and_value", "formats": ["png", "svg", "pdf"], "dpi": 220,
            "font_size": 12, "output_dir": "circuits", "solve": False}


def load_config(path: str | None) -> dict:
    cfg = dict(DEFAULTS)
    file = Path(path) if path else ROOT / "config.json"
    if file.exists():
        data = json.loads(file.read_text(encoding="utf-8"))
        cfg.update({k: v for k, v in data.items() if not k.startswith("_")})
    elif path:
        raise FileNotFoundError(f"config file not found: {file}")
    cfg["symbol_standard"] = str(cfg["symbol_standard"]).upper()
    if cfg["symbol_standard"] not in ("US", "IEC"):
        raise ValueError(f"symbol_standard must be US or IEC, not {cfg['symbol_standard']!r}")
    cfg["formats"] = [str(f).lower() for f in cfg["formats"]]
    bad = [f for f in cfg["formats"] if f not in ("png", "svg", "pdf")]
    if bad:
        raise ValueError(f"formats may only contain png, svg, pdf; not {bad}")
    return cfg


def looks_like_lingo(text: str) -> bool:
    return any(line.strip().lower().startswith(("source:", "circuit:", "source ", "circuit ")) for line in text.splitlines())


def fail(code: int, **info) -> None:
    print(json.dumps({"ok": False, **info}, ensure_ascii=False, indent=2))
    sys.exit(code)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("text", nargs="?", help="plain-English description, or circuit lingo")
    ap.add_argument("--lingo", help="circuit lingo (skips the English rules)")
    ap.add_argument("--file", help="read the description or lingo from this file")
    ap.add_argument("--out", help="output path without extension, e.g. figures/problem1 (default: <output_dir>/circuit)")
    ap.add_argument("--config", help="settings file (default: config.json in the skill folder)")
    ap.add_argument("--standard", choices=["US", "IEC", "us", "iec"], help="override symbol_standard")
    ap.add_argument("--labels", choices=["name_and_value", "value", "name"], help="override labels")
    ap.add_argument("--formats", help="override formats, e.g. png,svg")
    ap.add_argument("--solve", action="store_true", help="also write the answers and worked solution")
    ap.add_argument("--show-code", action="store_true", help="include the generated Schemdraw code in the output")
    a = ap.parse_args(argv)

    try:
        cfg = load_config(a.config)
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as e:
        fail(3, error=f"config: {e}")
    if a.standard:
        cfg["symbol_standard"] = a.standard.upper()
    if a.labels:
        cfg["labels"] = a.labels
    if a.formats:
        cfg["formats"] = [f.strip().lower() for f in a.formats.split(",") if f.strip()]
    solve = a.solve or bool(cfg.get("solve"))

    sources = [s for s in (a.text, a.lingo, a.file) if s]
    if len(sources) != 1:
        fail(3, error="give exactly one of: a description, --lingo, or --file")
    text = Path(a.file).read_text(encoding="utf-8") if a.file else (a.lingo or a.text)
    text = text.replace("\\n", "\n").strip()

    # 1. English -> lingo (rules only), unless lingo was given
    if a.lingo or looks_like_lingo(text):
        lingo_text, how, english = text, "given", None
    else:
        english = text
        try:
            lingo_text, how = lingo.translate(text), "rules"
        except lingo.LingoError as e:
            fail(2, stage="translate", error=str(e), input=text,
                 hint="The fixed rules could not read this sentence. Write the circuit lingo yourself (see "
                      "SKILL.md) and rerun with --lingo, or reword the sentence.")

    # 2. lingo -> problem
    try:
        prob = lingo.parse(lingo_text)
        code = lingo.draw_code(prob, cfg["symbol_standard"], cfg["labels"], cfg["font_size"])
    except lingo.LingoError as e:
        fail(3, stage="parse", error=str(e), lingo=lingo_text)

    # 3. draw
    out = Path(a.out) if a.out else Path(cfg["output_dir"]) / "circuit"
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        info = render_worker.render_files(code, tmp, cfg["dpi"], tuple(cfg["formats"]))
        if not info.get("ok"):
            fail(4, stage="draw", error=info.get("error"), lingo=lingo_text)
        files = {}
        for ext in cfg["formats"]:
            dest = out.with_suffix(f".{ext}")
            shutil.move(os.path.join(tmp, f"diagram.{ext}"), dest)
            files[ext] = str(dest)
    lingo_file = out.with_suffix(".lingo.txt")
    lingo_file.write_text((f"# {english}\n" if english else "") + lingo_text + "\n", encoding="utf-8")
    files["lingo"] = str(lingo_file)

    result = {"ok": True, "translated_by": how, "lingo": lingo_text, "question": lingo.question_text(prob),
              "parts": [{"name": q.name, "kind": q.what, "value": q.value, "hidden": q.hidden,
                         **({"closed": q.closed} if q.kind == "S" else {})} for q in prob.parts()],
              "settings": {k: cfg[k] for k in ("symbol_standard", "labels", "formats", "dpi", "font_size")},
              "files": files}
    if english:
        result["english"] = english

    # 4. optional: answers and worked solution
    if solve:
        try:
            res = lingo.solve(prob)
            result["answers"] = lingo.answers(prob, res)
            md = f"**Question.** {lingo.question_text(prob)}\n\n" + lingo.solution_markdown(prob, res)
            sol = out.with_suffix(".solution.md")
            sol.write_text(md, encoding="utf-8")
            files["solution"] = str(sol)
        except lingo.LingoError as e:
            result["solve_error"] = str(e)
    if a.show_code:
        result["schemdraw_code"] = code
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
