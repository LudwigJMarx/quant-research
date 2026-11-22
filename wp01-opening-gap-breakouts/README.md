# Working Paper No. 01: The Opening Gap and Intraday Breakouts in Nasdaq-100 Futures

Code and derived results for Working Paper No. 01 (Ludwig J. Marx, November 2026, Version 1.0).

The paper tests whether the opening gap of the Nasdaq-100 can be traded within the day. A rule enters in a chosen direction when price leaves the opening range and holds to the close. The rules were developed in R on QQQ minute bars from Financial Modeling Prep (FMP), the research model. Every reported number was then recomputed on QuantConnect (QC).

The final rule was also traded on QC with real orders in Micro Nasdaq-100 futures (MNQ). 51 variants were registered and counted. The selected candidate fails the registered hurdle (deflated Sharpe ratio 0.83 against 0.95) and fails in the test sample 2015 to 2019.

All reported numbers come from QC runs. The R scripts only evaluate QC exports, compare QC with the research model and draw the figures.

**Public backtest.** The full run with real orders in E-mini Nasdaq-100 futures (NQ) is public on QuantConnect. It covers January 2015 to November 2026 and shows the code, orders and statistics: https://www.quantconnect.cloud/backtest/737aabdee9588fffd28b21c70ea61438/. It uses `qc/nq_orb_2015_2026/main.py`.

**Paper and licence.** The paper is at https://ludwigjmarx.com/research/wp1-opening-gap-breakouts and on SSRN (abstract ID 7740185). The paper is licensed under CC BY-NC-ND 4.0. The code in this repository is licensed under MIT.

## Contents

| Path | What it is |
|---|---|
| `qc/variants/main.py` | QC algorithm: all registered variants on QC's QQQ minute bars at the trigger price, random-direction ranks, deflated Sharpe ratio, results by range fifth, day features, daily returns of the candidate |
| `qc/test_sample/main.py` | QC algorithm: the candidate (V51) in the test sample 2015 to 2019, run once. Same computation as `qc/variants`, other dates and output |
| `qc/mnq_orb_v1/` to `qc/mnq_orb_v4/` | QC algorithms: the four replication versions with real orders in MNQ (paper, table "Four versions of the replication") |
| `qc/mnq_orb_null/main.py` | QC algorithm: rule of version 4 plus the random-direction test on the same days (MNQ column of the candidate table) |
| `qc/local/` | Stand-in for QC's `AlgorithmImports` and a runner, so that `qc/variants` and `qc/test_sample` run on a CSV of minute bars without the LEAN engine |
| `R/lib.R` | Shared helpers: paths, Sharpe ratio, CAGR, drawdown, deflated Sharpe ratio, figure theme |
| `R/bt_intraday.R`, `R/bt_stop.R` | Research model: backtester for opening range breakouts and stop rules |
| `R/test_bt.R`, `R/test_stop.R` | Controls: hand-computed trades and synthetic prices with and without a built-in trend |
| `R/research_model.R` | Research model trade lists of the candidate before and after the data correction (needs FMP data) |
| `R/qc_exports.R` | Turns QC order exports into trade lists, daily equity and exposure without prices (needs your own QC exports) |
| `R/variant_numbers.R` | Numbers of sections 5, 6 and 8, Appendix A and the test sample from `results/` |
| `R/compare_replication.R` | Numbers of section 7 (replication) and of the MNQ column from `results/` |
| `R/paper_figures.R` | Figures 1 to 6 (figure 2 needs FMP data) |
| `tests/test_variants.py` | Python tests of the variant program and the local runner |
| `results/` | Derived results without prices (see below) |
| `figures/` | Figures 1, 3, 4, 5 and 6 as produced by `R/paper_figures.R` from `results/` |

Most of the code uses German identifiers. `qc/nq_orb_2015_2026` is already in English. Glossary:

| German | English |
| --- | --- |
| tag | day |
| luecke | gap |
| kerze | candle |
| spanne | range |
| einstieg | entry |
| schluss | close |
| ausstieg | exit |
| gegen | opposite edge of the range |
| mitte | middle of the range |
| richtung | direction |
| erster | first break of either side |
| zufall | random |
| rang | rank |
| hebel | leverage or exposure |
| schlupf | slippage |
| pruef | test sample |
| merkmale | day features |

## Variant names

| Name | Meaning |
|---|---|
| `B_<k>_<entry>_<stop>_<be>` | 24 base rules, direction = sign of the gap. k = opening range in minutes (5, 15, 30). entry = `stop` (stop order at the range edge) or `schluss5` (first 5-minute close beyond the edge, filled in the next minute). stop = `gegen` (opposite edge) or `mitte` (middle). be = `T` stop to break-even after +1 R, `F` not |
| `F_<direction>_<filter>` | 18 filter rules on the 5-minute range with a stop order. Direction D1 gap, D2 first 5-minute candle, D3 first break of either side. Filter F0 none, F1 first candle in gap direction, F2 opening volume 9:30-9:34 at least the 14-day mean, F3 gap at least 0.1 ATR, F4 no Federal Reserve decision, F5 = F1 and F2 and F4 |
| `S_<initial>_<trail>` | 8 stop rules on D2+F2. Initial stop S1 opposite edge, S2 0.15 x ATR14. Trail T0 none, T1 break-even after +1 R, T2 1 R behind each 5-minute close after +1 R, T3 along a smoothed price line on 5-minute bars |
| `V51_relvol4` | The candidate: D2+F2 with S1/T0 and opening volume 9:31-9:34 (data correction) |

## Which file produces which number

Paths below are relative to this folder. "Log line" means a line of the QC log with the given prefix; the published lines are in `results/`.

| Number or figure in the paper | Produced by | Read from |
|---|---|---|
| Base rules: best Sharpe 0.67, largest loss -16%; gap beats random in 4 of 24 (Sharpe 0.40 or less); ranks 0.66 to 0.80 of the five best; first break 0.88; mean R 0.01 to 0.09 | `qc/variants/main.py` (VAR) | `results/qc_variants/var_qc.txt`, printed by `R/variant_numbers.R` |
| Figure 1; -27 and +37 basis points in the quietest and widest fifth | `qc/variants/main.py` (Q1) | `results/qc_variants/q1_qc.txt`, `R/paper_figures.R` |
| Day features: +14 against -2, +18 against -7, +15 against +4, Fed -51, 15-minute width +47 against -19; 1,732 days | `qc/variants/main.py` (MERK) | `results/qc_variants/log_summary.txt`, `R/variant_numbers.R` |
| Filters: D2+F2 0.84, 99.5% of random runs, DSR 0.74 at 42 variants; D2+F3 1.03 | `qc/variants/main.py` (VAR, DSR) | `results/qc_variants/var_qc.txt`, `log_summary.txt` |
| Stop rules: 0.85 against 0.84, largest loss -19% to -13%, trail by 1 R 0.15 to 0.48, smoothed line 0.60 to 0.73 | `qc/variants/main.py` (VAR); T3 rows see "Not included" | `results/qc_variants/var_qc.txt` |
| Candidate at the trigger price: 648 trades, 18.6% a year, Sharpe 1.00 (0.997), largest loss -17.6%, hit rate 34.0%, mean 0.241 R, median -1.0 R, 99.8% of random runs | `qc/variants/main.py` (VAR V51_relvol4) | `results/qc_variants/var_qc.txt` |
| Deflated Sharpe ratio 0.83 (51 variants), 0.86 with skewness and kurtosis | `qc/variants/main.py` (DSR), recomputed in `R/variant_numbers.R` | `results/qc_variants/log_summary.txt`, `daily_v51.txt` |
| Sharpe ratio by year at the trigger price (2020 0.18 to 2026 -0.10); 63% of days without a trade | `qc/variants/main.py` (TAG) | `results/qc_variants/daily_v51.txt`, `R/variant_numbers.R` |
| 51 variants 0.14 higher in Sharpe on QC data; the research model's Sharpe ratios | `R/variant_numbers.R` | `results/qc_variants/var_qc.txt`, `results/research_model/variants_r.csv` |
| Test sample: 1,258 days, 426 trades, Sharpe -0.18, -3.6% a year, largest loss -33%, mean -0.005 R, lower bound -0.14 R, 30% of random runs, Sharpe by year | `qc/test_sample/main.py` (PRUEF, JAHR, TAG) | `results/qc_test_sample/` |
| Table of the four replication versions (return, Sharpe, largest loss, trades, slippage) | `qc/mnq_orb_v1` to `v4`, `R/qc_exports.R` | `results/qc_mnq/statistics_v*.json`, `trades_v*.csv`, `R/compare_replication.R` |
| Research model row of that table: 16.2%, 0.90, -23.9%, 645 trades; 0.95 before the correction; 2026 1.54 to 0.66 | `R/research_model.R` | `results/research_model/trades_*.csv`, `R/compare_replication.R` |
| Fill model: 7.6 and 4.4 points, 0.16 R (version 2); 1.3 and 1.6 points, 0.04 R (version 3) | `R/qc_exports.R` | `results/qc_mnq/trades_v2.csv`, `trades_v3.csv`, `R/compare_replication.R` |
| Signal source: 192 days only in R (+0.44 R), 408 only on QC (-0.08 R) | `R/compare_replication.R` | `results/qc_mnq/trades_v1.csv`, `results/research_model/trades_d2f2_relvol5.csv` |
| Vendor data: 23 trades only in R and 28 only on QC in 2025 | `R/compare_replication.R` | `results/qc_mnq/trades_v3.csv`, `results/research_model/trades_d2f2_relvol5.csv` |
| Figure 2 (volume of the opening bar) | `R/paper_figures.R` | FMP minute bars (not included) |
| Agreement: 620 common days, 25 only in R, 29 only on QC, 0.212 R in both, correlation 0.96, same direction 98% | `R/compare_replication.R` | `results/qc_mnq/trades_v4.csv`, `results/research_model/trades_v51_relvol4.csv` |
| Figure 3 (growth of 1 USD) | `R/paper_figures.R` | `results/qc_variants/daily_v51.txt`, `results/qc_mnq/equity_v4.csv` |
| Candidate with real orders: 649 trades, 16.8% a year, Sharpe 0.63, largest loss -16.6%, hit rate 33.6%, mean 0.210 R, median -1.0 R; 331 long and 318 short trades, hit rates 34% and 33%, winners 2.56 and 2.70 R | `qc/mnq_orb_v4/main.py` | `results/qc_mnq/statistics_v4.json`, `trades_v4.csv`, `R/compare_replication.R` |
| Real orders better than 99.7% of random runs; mean 0.25 R, bootstrap lower bound 0.12 R | `qc/mnq_orb_null/main.py` (runtime statistics nm_*) | `results/qc_mnq/statistics_null.json` |
| Figure 4, figure 5 (ten best trades 66%, best 2% of trades 78%) | `R/paper_figures.R`, `R/compare_replication.R` | `results/qc_mnq/trades_v4.csv` |
| Figure 6; exposure 2.4 times in the median (2.5 long, 2.4 short), 25% and 21% above 3.5 times | `R/paper_figures.R` | `results/qc_mnq/exposure_v4.csv` |
| Test sample with real orders in NQ: 426 trades, -4.0% a year, largest loss -31.7%, Sharpe -0.33 | `qc/nq_orb_test_sample/main.py` | `results/qc_mnq/statistics_nq_test_sample.json` |
| Full run 2015 to Nov 2026 in NQ (public backtest): 1,073 trades, 8.5% a year, largest loss -31.7%, Sharpe 0.31 | `qc/nq_orb_2015_2026/main.py` | `results/qc_mnq/statistics_nq_2015_2026.json` |
| Controls: seven hand-computed trades, synthetic prices Sharpe 5.98 with trend and 0.59 without | `R/test_bt.R` | none |
| The QC program reproduces the research model's Sharpe ratios on FMP data | `qc/local/run_local.py` with `qc/variants` on an FMP CSV | your FMP data, `results/research_model/variants_r.csv` |

Numbers about the data download (2,990 days, 1.16 million bars) describe the FMP files and have no script here.

## Data you need

The repository contains no price data. Both sources are licensed.

- **QuantConnect.** An account with access to US equity minute data (QQQ) and US futures data (MNQ in second resolution). The algorithms in `qc/` run unchanged as QC Python projects, one folder per project. The paper used QC's data for January 2020 to 20 November 2026 and October 2014 to December 2019 for the test sample.
- **FMP minute bars** for the research model and figure 2: QQQ one-minute bars of the regular session, 9:30 to 15:59 New York time. The R scripts read one file per year, `qqq_1min_<year>.fst` or `qqq_1min_<year>.csv`, with the columns `zeit` (timestamp in America/New_York), `open`, `high`, `low`, `close`, `volume`. Set the folder with `FMP_QQQ_DIR`. FMP returns the last available days when a request contains no trading day, so keep only rows inside the requested window when you download.

## How to run

R 4.6 with the packages data.table, ggplot2 and jsonlite (and fst for .fst files). Python 3.12 or later with numpy; pytest and pytest-cov for the tests. Run all commands from this folder.

From the published results, without any price data:

```bash
Rscript R/test_bt.R                 # controls of the research backtester
Rscript R/test_stop.R
Rscript R/variant_numbers.R         # writes results/variant_numbers.txt
Rscript R/compare_replication.R     # writes results/compare_replication.txt
Rscript R/paper_figures.R           # writes figures/ (figure 2 is skipped without FMP data)
python3 -m pytest tests
```

With your own data:

```bash
# research model and figure 2 on FMP data
FMP_QQQ_DIR=/path/to/fmp Rscript R/research_model.R
FMP_QQQ_DIR=/path/to/fmp Rscript R/paper_figures.R

# the QC variant program on a CSV of minute bars (columns tag,min,open,high,low,close,volume;
# min = minute of the day of the bar start, 570 to 959)
python3 -I qc/local/run_local.py qc/variants bars.csv out.txt

# after running the four replication versions on QC: rebuild the trade lists from the order exports
Rscript R/qc_exports.R orders_v1.json orders_v2.json orders_v3.json orders_v4.json result_v4.json
```

On QC, read the log of `qc/variants` (prefixes VAR, DSR, Q1, MERK, TAG) and of `qc/test_sample` (PRUEF, JAHR, TAG). `results/qc_variants/var_qc.txt` and `q1_qc.txt` are the VAR and Q1 lines without the prefix.

## Results folder

| File | Content |
|---|---|
| `qc_variants/var_qc.txt` | 51 rows: name, Sharpe, CAGR, max drawdown, trades, mean R, median R, hit rate, rank against random directions, 95% quantile of the random runs, Sharpe of the first break (base rules only) |
| `qc_variants/q1_qc.txt` | 24 rows: base rule, mean basis points per day in fifths 1 to 5 of the day's range / ATR |
| `qc_variants/log_summary.txt` | VAR, DSR, Q1 and MERK lines of the QC run |
| `qc_variants/daily_v51.txt` | Date and daily return of the candidate, 1,732 development days |
| `qc_variants/statistics.json` | Runtime and summary statistics of the QC run |
| `qc_test_sample/test_sample.txt`, `daily_v51_2015_2019.txt`, `statistics.json` | The same for the test sample |
| `qc_mnq/trades_v1.csv` to `trades_v4.csv` | One row per trade: date, direction, R, R at the trigger prices, entry and stop slippage in index points, exit type |
| `qc_mnq/equity_v4.csv`, `exposure_v4.csv` | Version 4: daily account equity rebuilt from the fills (matches the final equity of the run to the dollar), exposure per trade |
| `qc_mnq/statistics_*.json` | Runtime and summary statistics of the replication runs and the null-model run |
| `research_model/trades_*.csv` | Research model trades: date, direction, R, return, stop distance as a fraction of price, exit type, entry and exit minute, daily return |
| `research_model/variants_r.csv` | Sharpe ratios of all 51 variants in the research model |
| `variant_numbers.txt`, `compare_replication.txt` | Output of the two R scripts |

`scripts/check_results.py` in the repository root checks that no result file has a price column.

## Not included, and why

- **Price data.** FMP and QC data are licensed. The repository has no minute bars, no price series and no order fill prices. The QC order exports, logs with volumes and QC state files are not included. Trade lists hold dates, directions, R multiples, returns and slippage only.
- **Two stop variants.** Two of the 51 registered variants (S1/T3 and S2/T3) use an unpublished in-house smoothed line, so their code is not included. Their results are in the published variant table (`results/qc_variants/var_qc.txt`), and the deflated Sharpe ratio is computed from all 51 values. `qc/variants/main.py` therefore carries the two QC Sharpe ratios as constants for the deflated Sharpe ratio. To keep the published random-direction ranks identical, it also draws and discards the random numbers of these two variants. On other data, the DSR line of a local run uses these QC values and so differs from a run of the full program.
- **The research model's full variant pipeline in R.** It computed the 51 variants on FMP data. `qc/variants/main.py` is a port of it and reproduces its Sharpe ratios on the same FMP data (paper, section "Method"); run it through `qc/local/run_local.py`. `R/research_model.R` keeps the part that section 7 needs: the candidate before and after the data correction.
- **An earlier QC program** that computed only the 51 Sharpe ratios and the DSR. `qc/variants` gives the same values and more.

## Verification done before publication

- `qc/variants/main.py` and the unpublished full program both ran through `qc/local/run_local.py` on the same CSV of FMP minute bars for 2020 and 2021. One run started the evaluation on 2 January 2020, the other on 1 February 2020 with January as warm-up. All 49 published variants gave identical VAR lines (every field), and the Q1, MERK and TAG lines were identical too. `qc/test_sample/main.py` gave identical output to its full counterpart on the same data.
- `R/research_model.R` on FMP data from 2020 reproduces the published research model trade lists exactly from February 2020 on. The published lists used a warm-up from June 2019.
- `R/qc_exports.R` rebuilds the four trade lists of the replication from the QC order exports with identical R multiples. The equity curve of version 4 matches the final equity of the run.

## License

MIT, see `LICENSE` in the repository root. The license covers the code. The paper itself is published separately.
