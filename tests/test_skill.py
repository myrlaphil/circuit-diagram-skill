"""End-to-end tests of the skill script.  Run:  python -m pytest"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "draw_circuit.py"
sys.path.insert(0, str(ROOT / "scripts"))
import lingo  # noqa: E402

EN = "12 V battery, a 4 ohm and a 2 ohm in series, that pair in parallel with a 6 ohm, then a 3 ohm. Find the current through the 2 ohm resistor."


def run(*args, cwd):
    p = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, cwd=cwd)
    return p.returncode, json.loads(p.stdout)


def test_english_to_files(tmp_path):
    code, out = run(EN, "--out", "figs/p1", cwd=tmp_path)
    assert code == 0 and out["ok"] and out["translated_by"] == "rules"
    assert out["lingo"] == "source: 12 V\ncircuit: (4 + 2) || 6 + 3\nask: current through R2"
    for ext in ("png", "svg", "pdf"):
        f = tmp_path / "figs" / f"p1.{ext}"
        assert f.exists() and f.stat().st_size > 1000, ext
    assert (tmp_path / "figs" / "p1.lingo.txt").read_text().startswith(f"# {EN}\nsource: 12 V")
    assert "2.00 Ω resistor (R2)" in out["question"] and "answers" not in out
    assert [p["name"] for p in out["parts"]] == ["R1", "R2", "R3", "R4"]


def test_lingo_input_solve_and_overrides(tmp_path):
    code, out = run("--lingo", "source: 12 V\\ncircuit: A1 + (4 + S1=closed) || 6 + 3 || V1\\nask: reading of A1, reading of V1",
                    "--solve", "--standard", "IEC", "--labels", "value", "--formats", "png", "--show-code", cwd=tmp_path)
    assert code == 0 and out["translated_by"] == "given"
    assert out["answers"] == ["A1 reads 2.22 A", "V1 reads 6.67 V"]
    assert out["settings"] == {"symbol_standard": "IEC", "labels": "value", "formats": ["png"], "dpi": 220, "font_size": 12}
    assert "STYLE_IEC" in out["schemdraw_code"] and "elm.MeterA()" in out["schemdraw_code"]
    assert set(out["files"]) == {"png", "lingo", "solution"}
    assert (tmp_path / "circuits" / "circuit.png").exists() and not (tmp_path / "circuits" / "circuit.svg").exists()
    assert "Reduce the circuit" in (tmp_path / "circuits" / "circuit.solution.md").read_text()


def test_unreadable_sentence_names_the_word(tmp_path):
    code, out = run("12 V battery, 4 and 2 in series, then a thermistor", cwd=tmp_path)
    assert code == 2 and out["stage"] == "translate" and "'thermistor'" in out["error"] and "--lingo" in out["hint"]
    code, out = run("--lingo", "source: 12 V\\ncircuit: (4 + 2", cwd=tmp_path)
    assert code == 3 and "never closed" in out["error"]


def test_config_file_and_file_input(tmp_path):
    (tmp_path / "my.json").write_text(json.dumps({"symbol_standard": "iec", "formats": ["svg"], "dpi": 100,
                                                  "font_size": 14, "output_dir": "out", "solve": True}))
    (tmp_path / "desc.txt").write_text("9 V battery, a 3 ohm and a 6 ohm in parallel, then a 4 ohm. Find the total current.")
    code, out = run("--file", "desc.txt", "--config", "my.json", "--show-code", cwd=tmp_path)
    assert code == 0 and out["settings"]["symbol_standard"] == "IEC" and out["settings"]["dpi"] == 100
    assert out["answers"] == ["Total current from the battery = 1.50 A"] and "fontsize=14" in out["schemdraw_code"]
    assert (tmp_path / "out" / "circuit.svg").exists() and not (tmp_path / "out" / "circuit.png").exists()
    code, out = run(EN, "--config", "missing.json", cwd=tmp_path)
    assert code == 3 and "not found" in out["error"]
    (tmp_path / "bad.json").write_text(json.dumps({"formats": ["gif"]}))
    code, out = run(EN, "--config", "bad.json", cwd=tmp_path)
    assert code == 3 and "gif" in out["error"]


def test_default_config_is_valid_and_examples_translate():
    cfg = json.loads((ROOT / "config.json").read_text())
    assert cfg["symbol_standard"] in ("US", "IEC") and set(cfg["formats"]) <= {"png", "svg", "pdf"}
    for en, want in [("a 2 uF and a 6 uF capacitor in parallel, then a 4 uF capacitor in series with that pair, 12 V battery",
                      "circuit: 4uF + 2uF || 6uF"),
                     ("12 V battery, an ammeter, then a 4 ohm in series with a closed switch, that pair in parallel with a "
                      "6 ohm, then a 3 ohm, a voltmeter across the 3 ohm", "circuit: A1 + (4 + S1=closed) || 6 + 3 || V1")]:
        assert want in lingo.translate(en)
