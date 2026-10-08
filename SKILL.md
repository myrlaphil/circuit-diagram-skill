---
name: circuit-diagram-skill
description: Use for ANY request about a DC circuit made of a battery and resistors, capacitors, switches, ammeters or voltmeters - drawing it, making a worksheet or exam problem, or finding a current, voltage, power, charge, meter reading, equivalent resistance or capacitance - even when the user does not ask for a picture. It translates the description into "circuit lingo" with fixed rules, draws the diagram with Schemdraw (PNG, SVG, PDF) and computes the answers and a worked solution deterministically, so do not solve such circuits in your head. Also handles circuit lingo like "(4 + 2) || 6 + 3".
---

# Circuit diagram from plain English

## What happens
1. Fixed rules (no AI) turn the English into **circuit lingo**, e.g. `circuit: (4 + 2) || 6 + 3`.
2. The lingo is parsed, laid out like a textbook figure and drawn with [Schemdraw](https://schemdraw.readthedocs.io/).
3. You get back JSON with the lingo, the files written, the question wording, and (with `--solve`) the answers.

Settings live in `config.json` in this folder: `symbol_standard` (US or IEC), `labels`, `formats`, `dpi`,
`font_size`, `output_dir`, `solve`. Edit the file to change the defaults for every drawing; use the flags below
to change one drawing.

## Steps
0. Use this skill even for a plain question like "find the total current": run the script with `--solve`, give the
   answer from `answers`, and show the figure - the user gets a drawing and a worked solution for free, and the
   numbers are computed, not guessed.
1. Nothing to install by hand: on the first run the script creates a private `.venv` inside this folder and
   installs schemdraw and matplotlib into it (about a minute, needs internet). Later runs are instant.
2. Run from the user's working directory, so files land where they work:
   ```
   python "<this folder>/scripts/draw_circuit.py" "<the user's description>" --out figures/problem1
   ```
   - `--solve` when the user wants answers or a worked solution (also written to `<out>.solution.md`)
   - `--standard IEC` for box-style resistors, `--labels value` for values without names, `--formats png`
   - `--lingo "<lingo>"` to pass circuit lingo instead of English; `--file x.txt` to read either from a file
   - `--show-code` if the user asks how the figure was drawn (returns the Schemdraw code)
   - **Random problems:** `--random "<type>" --solve` makes a problem of that type with its own English
     description (in the JSON as `english`), lingo, figure and answers; `--seed N` repeats a problem.
     Types: `Mixed series-parallel`, `Simple series`, `Simple parallel`, `Unknown resistor`, `Capacitors`,
     `Switch (open or closed)`, `Meters (ammeter and voltmeter readings)`, or `any`. Use this whenever the
     user asks for "a random / another / a practice problem" - do not invent values yourself.
   - **Editing a problem:** when the user asks to change something ("make the 6 ohm a 10 ohm", "add a
     voltmeter across R3", "ask for the power instead"), edit the previous lingo accordingly and rerun with
     `--lingo`; show the new lingo. Keep everything else exactly as it was.
3. Read the JSON on stdout and act on the exit code:
   - **0** - show the user the `lingo` so they can check the circuit is what they meant, and the PNG path
     (open or embed it). If they asked for a problem, quote `question` and, with `--solve`, `answers`.
   - **2** - the rules could not read a word; the message names it. Write the lingo yourself using the
     reference below and rerun with `--lingo`. Tell the user the rules could not read their sentence and show
     the lingo you wrote so they can check it. Keep their values; never invent or change a value silently.
   - **3** - the lingo is invalid; the message says what is wrong. Fix it and rerun.
   - **4 / 5** - drawing failed or a package is missing. Show the message.
4. Always draw through the script. Do not write Schemdraw code yourself: the script's layout, numbering and
   answers are consistent with each other and with the lingo the user sees.

## Circuit lingo reference
```
source: 12 V
circuit: (4 + 2) || 6 + 3
ask: current through R2, voltage across R2
```
| Write | Meaning |
|---|---|
| `+` | series |
| `\|\|` | parallel - binds tighter than `+`, like × before + |
| `( )` | grouping |
| `4` · `4.7k` · `2 kohm` | a resistor (ohms). Resistors are named R1, R2 ... in reading order |
| `R3=6` | a resistor with your own name |
| `4uF` · `470nF` · `2.2 microfarad` | a capacitor (units F, mF, uF/µF, nF, pF); named C1, C2 ... |
| `S1=open` · `S1=closed` | a switch (a `switch: S1 closed` line also works) |
| `A1` | an ideal ammeter, in series with what it measures |
| `V1` | an ideal voltmeter, in parallel with what it measures: `6 \|\| V1` |
| `6?` · `R3=6?` | the value is hidden on the figure ("R3 = ?"); the answer key still knows it |
| `ask:` | `current through R2`, `voltage across R2`, `power in R2`, `resistance of R3`, `charge on C1`, `energy in C1`, `reading of A1`, `total current`, `equivalent resistance`, `equivalent capacitance`; several separated by commas; `the 2 ohm resistor` works as a target |
| `hide: R3` | same as `?` |
| `text: ...` | your own wording of the question |
| `title: ...` | a title kept with the problem |

**Layout rule:** parts are drawn in the order written. Parts before the last `+` go on the top rail, left to
right; the last series part goes on the bottom rail; parallel branches stack top to bottom. To move a part,
move it in the text: `3 + (4 + 2) || 6` puts the 3 Ω top-left instead of on the bottom.

## English the rules understand
- battery: `12 V battery`, `a 9 volt source`
- connections: `a 4 ohm and a 2 ohm in series`, `a 4 ohm in series with a 2 ohm`, `2, 4 and 6 ohms in parallel`,
  `..., all in series`
- back-references: `that pair in parallel with a 6 ohm`, `a 6 ohm across that pair` (the 6 is drawn first because
  it is said first), `that whole group` = everything so far, `them`, `the combination`
- sequence: `then a 3 ohm`, `followed by`, `next`, `finally`
- counts and words: `two 4 ohm resistors`, `3 resistors of 6 ohms`, `twelve volt`, `4.7 kilo-ohm`, `2.2k`
- unknown: `an unknown 6 ohm`, `the 3 ohm is unknown`
- capacitors: `a 4 uF capacitor`, `a 4 microfarad and a 2 microfarad capacitor in series`
- switches and meters: `a closed switch`, `an open switch`, `the switch is closed`, `an ammeter, then ...`,
  `a voltmeter across the 3 ohm`, `a voltmeter across that pair`
- questions: `Find the current through and the voltage across the 2 ohm resistor`, `What is the power in R3`,
  `the charge on the 4 uF`, `the energy stored in each capacitor`, `what does the ammeter read`,
  `the total current`, `the equivalent resistance / capacitance`, `the resistance of R3`
- One connection per phrase: say `a 4 ohm and a 2 ohm in series, that pair in parallel with a 6 ohm`, not
  `4 and 2 in series with 6 in parallel`.

## Physics and limits
One battery, DC, steady state ("the switch has been closed a long time"). Capacitors and ideal voltmeters carry no
current; closed switches and ideal ammeters are wires. Capacitors in series share the same charge, in parallel the
same voltage (Q = CV, U = ½CV²). Not supported: more than one battery, bridge circuits, RC time constants,
inductors, AC. If a user asks for one of those, say so instead of approximating.
