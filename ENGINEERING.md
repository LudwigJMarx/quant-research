# Engineering notes

Why the code in this repository looks the way it does. Each rule names the case that forced it.

## What this repository is

Code and derived results of published working papers, one folder per paper. A reader with access to the same licensed data must be able to reproduce every number and figure. The paper decides what the code does; the code is published as it ran, with comments translated, not rewritten.

## Rules

### Published code gives the published numbers

A cleaned or translated program is only published after it ran next to the original on the same data and gave identical output. For Working Paper No. 01 this was checked line by line for the variant program and the test-sample program (see the folder README). A port that "should give the same result" is not enough: a removed variant changed the position of the random number generator for every later variant, and only the comparison showed it.

### No price data in the repository

FMP and QuantConnect data are licensed. Result files hold dates, directions, returns, R multiples, slippage, exposure, equity and statistics. `scripts/check_results.py` reads the header of every result CSV and fails on any column that is not on its allow list, so a new column needs a deliberate change of the check.

### A check says what it looked at

A check that read nothing must not report "0 findings". `check_results.py` names the number of files it read and exits with 2 if it found none.

### Results are reproduced in CI

The CI runs the R scripts on the committed results and fails if their text output differs from the committed output. A number in the README that no script prints is not a reproducible number.

## Commands

```bash
python3 scripts/check_results.py
cd wp01-opening-gap-breakouts && python3 -m pytest tests --cov=qc/variants --cov=qc/local --cov-fail-under=85
cd wp01-opening-gap-breakouts && Rscript R/test_bt.R && Rscript R/test_stop.R
```

## Commits

`type(scope): subject`, subject under 72 characters, lower case. The body explains the evidence: what was claimed, what the check showed, why this way. English, because the repository is public.
