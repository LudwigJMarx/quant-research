# Numbers of sections 5, 6, 8, the limits and Appendix A of the paper from the QuantConnect variant run
# (results/qc_variants) and the test-sample run (results/qc_test_sample): base rules, filters, stop
# rules, candidate, deflated Sharpe ratio, day features, Sharpe by year, test sample, and the comparison
# of the 51 Sharpe ratios on QuantConnect data with the research model on FMP data.
# Run from the folder wp01-opening-gap-breakouts: Rscript R/variant_numbers.R
source("R/lib.R")

v <- fread(res("qc_variants", "var_qc.txt"), header = FALSE,
           col.names = c("name", "sharpe", "cagr", "max_dd", "trades", "mean_r", "median_r", "hit",
                         "rank_random", "random_95", "sharpe_first_break"))
pruefe_anzahl(v, 51, "variants")
tg <- fread(res("qc_variants", "daily_v51.txt"), header = FALSE, col.names = c("tag", "r"))
pruefe_anzahl(tg, 1700, "development days")

sink(res("variant_numbers.txt"), split = TRUE)
cat("QuantConnect QQQ minute bars,", format(min(tg$tag)), "to", format(max(tg$tag)), ",", nrow(tg), "days\n")

b <- v[startsWith(name, "B_")]
cat("\n== Section 5: 24 base rules, direction = gap ==\n")
print(b[order(-sharpe), .(name, sharpe, max_dd, mean_r, median_r, rank_random, sharpe_first_break)])
cat(sprintf("best Sharpe %.2f (largest loss %.1f%%); rank > 0.95 in %d of 24 variants, their Sharpe <= %.2f\n",
            max(b$sharpe), 100 * b[which.max(sharpe), max_dd], b[rank_random > 0.95, .N], b[rank_random > 0.95, max(sharpe)]))
cat(sprintf("ranks of the five best: %.2f to %.2f; mean R per trade %.2f to %.2f\n",
            min(b[order(-sharpe)][1:5, rank_random]), max(b[order(-sharpe)][1:5, rank_random]), min(b$mean_r), max(b$mean_r)))
cat(sprintf("first break of either side, 30-minute range (stop order, opposite edge): %.2f against %.2f\n",
            b[name == "B_30_stop_gegen_F", sharpe_first_break], b[name == "B_30_stop_gegen_F", sharpe]))

cat("\n== Section 6: 18 filter variants ==\n")
print(v[startsWith(name, "F_")][order(-sharpe), .(name, sharpe, cagr, max_dd, trades, rank_random)])

cat("\n== Section 6: day features (bp per day: gap rule | first break of either side) ==\n")
print(fread(text = log_zeilen(res("qc_variants", "log_summary.txt"), "MERK"), header = FALSE,
            col.names = c("feature", "level", "days", "bp_gap_rule", "bp_first_break")))

cat("\n== Section 6 (Stops): stop rules on the selected filter ==\n")
print(v[startsWith(name, "S_")][, .(name, sharpe, max_dd, mean_r, rank_random)])
cat("S1/T3 and S2/T3 use an unpublished smoothed line; their code is not included, their results are.\n")

dsr <- strsplit(log_zeilen(res("qc_variants", "log_summary.txt"), "DSR"), " ")[[1]]
cat("\n== Candidate V51 and deflated Sharpe ratio ==\n")
print(v[name == "V51_relvol4"])
cat(sprintf("DSR over %s variants: %s (normal), %s (skewness %s, kurtosis %s); D2+F2 at 42 variants: %s\n",
            dsr[6], dsr[2], dsr[3], dsr[4], dsr[5], dsr[9]))
# recomputed here from the 51 published Sharpe ratios as a cross-check of the log line
sr_tag <- v$sharpe / sqrt(252); s <- v[name == "V51_relvol4", sharpe] / sqrt(252)
x <- tg$r; z <- (x - mean(x)) / sqrt(mean((x - mean(x))^2))
cat(sprintf("recomputed in R: %.4f (normal), %.4f (with skewness and kurtosis)\n",
            deflated_sharpe(s, nrow(tg), nrow(v), var(sr_tag)),
            deflated_sharpe(s, nrow(tg), nrow(v), var(sr_tag), mean(z^3), mean(z^4))))
cat(sprintf("days without a trade: %.0f%%\n", 100 * mean(tg$r == 0)))
cat("Sharpe ratio by year (trigger price):\n")
print(tg[, .(sharpe = round(sharpe(r), 2)), by = .(year = year(as.IDate(tag)))])

cat("\n== QuantConnect data against the research model on FMP data (51 Sharpe ratios) ==\n")
rr <- fread(res("research_model", "variants_r.csv"))
xx <- merge(rr, v[, .(name, sr_qc = sharpe)], by = "name")
pruefe_anzahl(xx, 51, "matched variants")
cat(sprintf("correlation %.2f, mean difference QC - R %.3f; V51: QC %.3f, R %.3f\n",
            cor(xx$sr_qc, xx$sr_r), mean(xx$sr_qc - xx$sr_r), xx[name == "V51_relvol4", sr_qc], xx[name == "V51_relvol4", sr_r]))

cat("\n== Test sample 2015-2019 (candidate only) ==\n")
cat(readLines(res("qc_test_sample", "test_sample.txt")), sep = "\n")
sink()
