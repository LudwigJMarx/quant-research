# Numbers of section 7 ("Replication") and of the MNQ column in section 8: the four replication
# versions on QuantConnect against the research model, trade by trade.
# Inputs: results/qc_mnq (trade lists without prices and run statistics, see R/qc_exports.R),
# results/research_model (trade lists of the research model on FMP data), results/qc_variants/daily_v51.txt
# (the list of development days).
# Run from the folder wp01-opening-gap-breakouts: Rscript R/compare_replication.R
source("R/lib.R")
ENDE_V3 <- as.IDate("2026-08-12")        # last trade of versions 1 to 3 (their futures data end in August 2026)

lies <- function(f) { x <- fread(f); x[, tag := as.IDate(tag)]; x[] }
q <- lapply(1:4, function(v) lies(res("qc_mnq", sprintf("trades_v%d.csv", v))))
st <- lapply(c(paste0("v", 1:4), "null"), function(v) fromJSON(res("qc_mnq", sprintf("statistics_%s.json", v))))
alt <- lies(res("research_model", "trades_d2f2_relvol5.csv"))   # volume 9:30-9:34
neu <- lies(res("research_model", "trades_v51_relvol4.csv"))    # volume 9:31-9:34 (candidate)
tage <- fread(res("qc_variants", "daily_v51.txt"), header = FALSE)$V1
tage <- as.IDate(tage)

reihe <- function(e) { r <- setNames(numeric(length(tage)), as.character(tage)); r[as.character(e$tag)] <- e$pnl; r }
r_neu <- reihe(neu); r_alt <- reihe(alt)

sink(res("compare_replication.txt"), split = TRUE)
cat("== Table: four versions of the replication on QuantConnect ==\n")
tab <- rbindlist(lapply(1:4, function(v) {
  s <- st[[v]]$statistics
  data.table(version = v, end = substr(st[[v]]$backtestEnd, 1, 10), return_pa = s[["Compounding Annual Return"]],
             sharpe_qc = s[["Sharpe Ratio"]], max_loss = s[["Drawdown"]], trades = nrow(q[[v]]),
             slippage_r = round(mean(q[[v]]$rm_q_ohne_schlupf - q[[v]]$rm_q), 3))
}))
print(tab)
cat(sprintf("research model in R (V51): return %.1f%%, Sharpe %.2f, largest loss %.1f%%, %d trades\n",
            100 * cagr(r_neu), sharpe(r_neu), 100 * max_dd(r_neu), nrow(neu)))
cat(sprintf("research model before the data correction (volume 9:30-9:34): Sharpe %.2f\n", sharpe(r_alt)))
sj <- function(rr) { j <- year(as.IDate(names(rr))); sapply(split(rr, j), function(x) round(sharpe(x), 2)) }
print(data.table(year = as.integer(names(sj(r_alt))), sharpe_930_934 = sj(r_alt), sharpe_931_934 = sj(r_neu)))

cat("\n== Fill model: slippage per trade (index points, R) ==\n")
print(rbindlist(lapply(1:4, function(v) q[[v]][, .(version = v, entry_pts = round(mean(schlupf_ein_pkt), 1),
  stop_pts = round(mean(schlupf_stop_pkt, na.rm = TRUE), 1), slippage_r = round(mean(rm_q_ohne_schlupf - rm_q), 3))])))

cat("\n== Signal source: version 1 (futures volume) against the research model (QQQ volume 9:30-9:34) ==\n")
b <- merge(alt[, .(tag, rm_r = rmult)], q[[1]][, .(tag, rm_q)], by = "tag", all = TRUE)
cat(sprintf("only in R: %d days (%.2f R); only on QuantConnect: %d days (%.2f R); common %d\n",
            b[is.na(rm_q), .N], b[is.na(rm_q), mean(rm_r)], b[is.na(rm_r), .N], b[is.na(rm_r), mean(rm_q)],
            b[!is.na(rm_r) & !is.na(rm_q), .N]))

cat("\n== Vendor data: days only in R / only on QuantConnect by year (version 3 against volume 9:30-9:34, to 12 Aug 2026) ==\n")
b <- merge(alt[tag <= ENDE_V3, .(tag, x = 1)], q[[3]][tag <= ENDE_V3, .(tag, y = 1)], by = "tag", all = TRUE)
print(b[, .(both = sum(!is.na(x) & !is.na(y)), only_R = sum(is.na(y)), only_QC = sum(is.na(x))), by = .(year = year(tag))])

cat("\n== Agreement: version 4 against the research model (V51), full period ==\n")
b <- merge(neu[, .(tag, rm_r = rmult, dir_r = dir)], q[[4]][, .(tag, rm_q, rm_q_ohne_schlupf, dir_q = dir)], by = "tag", all = TRUE)
x <- b[!is.na(rm_r) & !is.na(rm_q)]
cat(sprintf("common days %d, only R %d, only QuantConnect %d\n", nrow(x), b[is.na(rm_q), .N], b[is.na(rm_r), .N]))
cat(sprintf("common days: mean R in R %.3f, on QuantConnect %.3f (at trigger prices %.3f), correlation %.2f, same direction %.1f%%\n",
            mean(x$rm_r), mean(x$rm_q), mean(x$rm_q_ohne_schlupf), cor(x$rm_r, x$rm_q_ohne_schlupf), 100 * mean(x$dir_r == x$dir_q)))
print(b[, .(only_R = sum(is.na(rm_q)), only_QC = sum(is.na(rm_r))), by = .(year = year(tag))])

cat("\n== Section 8: candidate with real orders in MNQ (version 4) ==\n")
v4 <- q[[4]]; s4 <- st[[4]]$statistics
cat(sprintf("trades %d, return %s, Sharpe (after risk-free rate) %s, largest loss %s, hit rate %.1f%%, mean %.3f R, median %.1f R\n",
            nrow(v4), s4[["Compounding Annual Return"]], s4[["Sharpe Ratio"]], s4[["Drawdown"]],
            100 * mean(v4$rm_q > 0), mean(v4$rm_q), median(v4$rm_q)))
print(v4[, .(trades = .N, hit = round(mean(rm_q > 0), 3), mean_winner = round(mean(rm_q[rm_q > 0]), 2), mean_r = round(mean(rm_q), 3)),
         by = .(side = fifelse(dir == 1, "long", "short"))])
ns <- st[[5]]$runtimeStatistics
cat(sprintf("random direction (null-model run, trigger price, same days): rank %s, mean %s R, bootstrap lower bound %s R, %s trades\n",
            ns$nm_rang, ns$nm_r_mittel, ns$nm_r_unten, ns$nm_trades))
z <- sort(v4$rm_q, decreasing = TRUE)
cat(sprintf("concentration: ten best trades %.0f%% of total profit, best 2%% of trades %.0f%%\n",
            100 * sum(z[1:10]) / sum(z), 100 * sum(z[seq_len(ceiling(0.02 * length(z)))]) / sum(z)))
cat("mean R by year:\n"); print(v4[, .(trades = .N, mean_r = round(mean(rm_q), 3)), by = .(year = year(tag))])
sink()
