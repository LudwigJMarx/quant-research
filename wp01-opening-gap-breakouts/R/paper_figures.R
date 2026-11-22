# Figures 1 to 6 of the paper. Reads only the files in results/, except figure 2, which needs the FMP
# minute bars (set FMP_QQQ_DIR; without it figure 2 is skipped with a message).
# Titles, subtitles and sources are set in the paper, not in the images.
# Run from the folder wp01-opening-gap-breakouts: Rscript R/paper_figures.R
source("R/lib.R")
theme_set(thema())
f <- farben

# ---- Figure 1: the 24 gap rules by fifth of days, sorted by the day's range / ATR (QuantConnect) ----
q1 <- fread(res("qc_variants", "q1_qc.txt"), header = FALSE)
pruefe_anzahl(q1, 24, "base variants")
bq <- melt(q1[, v := .I], id.vars = c("V1", "v"), variable.name = "fuenftel", value.name = "bp")[, fuenftel := as.integer(sub("V", "", fuenftel)) - 1L]
med <- bq[, .(bp = median(bp)), by = fuenftel]
p <- ggplot(bq, aes(factor(fuenftel), bp, group = v)) +
  geom_hline(yintercept = 0, colour = f[["gedaempft"]], linewidth = 0.3) +
  geom_line(colour = f[["linie"]], linewidth = 0.4) +
  geom_line(data = med, aes(factor(fuenftel), bp, group = 1), inherit.aes = FALSE, colour = f[["petrol"]], linewidth = 1) +
  geom_point(data = med, aes(factor(fuenftel), bp), inherit.aes = FALSE, colour = f[["petrol"]], size = 2) +
  scale_x_discrete(labels = c("1\nquietest", "2", "3", "4", "5\nwidest")) +
  labs(x = "Fifth of days by the day's range relative to ATR (known only after the close)", y = "Basis points per day")
speichern(p, figs("fig1_range.png"), h = 8)
cat("Base rules by range (median of the 24 variants, bp per day):\n"); print(med[order(fuenftel)])

# ---- Figure 3: growth of 1 USD, QQQ at the trigger price (V51) and MNQ real orders (version 4) ----
vq <- fread(res("qc_variants", "daily_v51.txt"), header = FALSE, col.names = c("tag", "pnl"))[, tag := as.IDate(tag)]
qe <- fread(res("qc_mnq", "equity_v4.csv"))[, tag := as.IDate(tag)]
soll <- as.numeric(gsub("[$,]", "", fromJSON(res("qc_mnq", "statistics_v4.json"))$runtimeStatistics$Equity))
if (abs(tail(qe$equity, 1) - soll) > 50) stop("equity curve does not match the final equity of the run")
kr <- vq[, .(tag, w = cumprod(1 + pnl))]
qr <- merge(vq[, .(tag)], qe, by = "tag", all.x = TRUE)[, eq := nafill(nafill(equity, "locf"), fill = 100000)][, .(tag, w = eq / 100000)]
kurve <- rbind(kr[, .(tag, w, s = "QQQ minute bars, trigger price")], qr[, .(tag, w, s = "MNQ futures, real orders")])
kurve[, s := factor(s, c("MNQ futures, real orders", "QQQ minute bars, trigger price"))]
p <- ggplot(kurve, aes(as.Date(tag), w, colour = s)) + geom_line(linewidth = 0.6) +
  scale_colour_manual(values = c(f[["petrol"]], f[["kupfer"]])) + scale_y_log10() +
  labs(x = NULL, y = "Growth of 1 USD (log scale)")
speichern(p, figs("fig3_equity.png"))

# ---- Figure 4: mean R per trade by year, MNQ real orders ----
q <- fread(res("qc_mnq", "trades_v4.csv"))[, tag := as.IDate(tag)]
j <- q[, .(r = mean(rm_q), n = .N), by = .(jahr = year(tag))]
p <- ggplot(j, aes(factor(jahr), r)) + geom_col(width = 0.6, fill = f[["petrol"]]) +
  geom_hline(yintercept = 0, colour = f[["gedaempft"]], linewidth = 0.3) +
  labs(x = NULL, y = "R per trade")
speichern(p, figs("fig4_years.png"))

# ---- Figure 5: concentration on few trades ----
x <- sort(q$rm_q, decreasing = TRUE)
kz <- data.table(anteil = seq_along(x) / length(x), kum = cumsum(x) / sum(x))
p <- ggplot(kz, aes(100 * anteil, 100 * kum)) + geom_hline(yintercept = 100, colour = f[["linie"]]) +
  geom_line(linewidth = 0.7, colour = f[["petrol"]]) +
  labs(x = "Share of trades (%)", y = "Share of total profit (%)")
speichern(p, figs("fig5_concentration.png"))

# ---- Figure 6: exposure per trade (notional at entry / equity at the prior close) ----
oe <- fread(res("qc_mnq", "exposure_v4.csv"))
oe[, klasse := cut(hebel, c(0, 1, 1.5, 2, 2.5, 3, 3.5, Inf), right = FALSE,
                   labels = c("under 1", "1–1.5", "1.5–2", "2–2.5", "2.5–3", "3–3.5", "3.5 and more"))]
oe[, seite := factor(fifelse(dir > 0, "Long", "Short"), c("Long", "Short"))]
hv <- oe[, .N, by = .(seite, klasse)][, anteil := N / sum(N), by = seite]
p <- ggplot(hv, aes(klasse, 100 * anteil, fill = seite)) + geom_col(position = position_dodge(0.8), width = 0.75) +
  scale_fill_manual(values = c(f[["petrol"]], f[["kupfer"]])) +
  labs(x = "Exposure per trade, multiple of account equity", y = "Share of trades (%)")
speichern(p, figs("fig6_leverage.png"), h = 8)
cat(sprintf("Exposure: median %.2f (long %.2f, short %.2f), mean %.2f, share >= 3.5: long %.2f short %.2f, n %d\n",
            median(oe$hebel), oe[dir > 0, median(hebel)], oe[dir < 0, median(hebel)], mean(oe$hebel),
            oe[dir > 0, mean(hebel >= 3.5)], oe[dir < 0, mean(hebel >= 3.5)], nrow(oe)))

# ---- Figure 2: volume of the vendor's opening bar (needs FMP minute bars, Jan 2019 to Nov 2026) ----
if (is.null(fmp_dir())) {
  message("Figure 2 skipped: it needs FMP QQQ minute bars, which are not included. ",
          "Set FMP_QQQ_DIR to a folder with qqq_1min_<year>.fst or .csv files and run again.")
} else {
  jahre <- as.integer(Sys.getenv("FMP_FIRST_YEAR", "2019")):2026
  m <- fmp_lesen(jahre)
  m[, tag := as.IDate(format(zeit, "%Y-%m-%d", tz = "America/New_York"))]; m[, hm := format(zeit, "%H:%M", tz = "America/New_York")]
  v <- m[hm >= "09:30" & hm <= "09:34", .(v930 = sum(volume[hm == "09:30"]), v4 = sum(volume[hm != "09:30"]) / 4), by = tag]
  vm <- v[, .(`Opening bar` = median(v930), `Mean of the next four bars` = median(v4)), by = .(monat = as.Date(format(tag, "%Y-%m-01")))]
  vm <- melt(vm, id.vars = "monat")
  p <- ggplot(vm, aes(monat, value / 1e6, colour = variable)) + geom_line(linewidth = 0.7) +
    scale_colour_manual(values = c(f[["kupfer"]], f[["petrol"]])) + scale_y_log10() +
    labs(x = NULL, y = "Million shares per bar (log scale)")
  speichern(p, figs("fig2_volume_break.png"))
}
