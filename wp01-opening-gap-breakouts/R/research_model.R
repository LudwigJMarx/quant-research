# Research model in R on FMP QQQ minute bars: the selected rule before and after the data correction.
#   D2+F2 (S1/T0): direction of the first 5-minute candle, opening volume 9:30-9:34 >= mean of the
#                  14 previous sessions, stop order at the edge of the 5-minute range, stop at the
#                  opposite edge, exit 15:55
#   V51:           the same rule with opening volume 9:31-9:34 (the candidate)
# Writes the trade lists (no prices) and a summary with the numbers of section 7 of the paper
# (research model: 645 trades, Sharpe 0.90, 16.2% a year, largest loss -23.9%; Sharpe 0.95 before the
# correction; Sharpe by year).
#
# Needs FMP minute bars (not included): set FMP_QQQ_DIR to a folder with qqq_1min_<year>.fst or .csv.
# The paper used June 2019 to 20 November 2026; days before 2020 serve only as warm-up for the 14-day
# averages. FMP_FIRST_YEAR (default 2019) can restrict the files that are read.
# Run from the folder wp01-opening-gap-breakouts: Rscript R/research_model.R
source("R/lib.R"); source("R/bt_intraday.R"); source("R/bt_stop.R")
if (is.null(fmp_dir())) stop("FMP_QQQ_DIR is not set; the research model needs FMP minute bars")

ENTW_START <- as.IDate("2020-01-01"); ENTW_ENDE <- as.IDate("2026-11-20")
erstes <- as.integer(Sys.getenv("FMP_FIRST_YEAR", "2019"))
m <- fmp_lesen(erstes:2026)
m <- m[zeit >= as.POSIXct("2019-06-01", tz = "America/New_York")]
m[, tag := as.IDate(format(zeit, "%Y-%m-%d", tz = "America/New_York"))]
m[, min := as.integer(format(zeit, "%H", tz = "America/New_York")) * 60L + as.integer(format(zeit, "%M", tz = "America/New_York"))]
m <- m[tag <= ENTW_ENDE]
setorder(m, zeit)

# ---- day features known at 9:35: ATR14 of the previous days, direction and volume of the opening range ----
d <- m[, .(open = open[1], high = max(high), low = min(low), close = close[.N]), by = tag]
setorder(d, tag)
d[, vc := shift(close)]
d[, tr := (pmax(high, vc) - pmin(low, vc)) / vc]
d[, atr14 := shift(frollmean(tr, 14))]
o5 <- m[min < 575L, .(v5 = sum(volume), o = open[1], c = close[.N]), by = tag]
setorder(o5, tag)
o5[, `:=`(relvol5 = v5 / shift(frollmean(v5, 14)), or_richtung5 = sign(c - o))]
v4 <- m[min >= 570L & min < 960L, .(v4 = sum(volume[min %in% 571:574])), by = tag]
setorder(v4, tag)
v4[, relvol4 := v4 / shift(frollmean(v4, 14))]
mk <- Reduce(function(a, b) merge(a, b, by = "tag"), list(d[, .(tag, atr14)], o5[, .(tag, relvol5, or_richtung5)], v4[, .(tag, relvol4)]))
mk <- mk[tag >= ENTW_START]
if (min(mk$tag) < ENTW_START) stop("test sample touched")
pruefe_anzahl(mk, 400, "development days")
alle_tage <- mk$tag
mt <- split(m[tag >= ENTW_START], by = "tag", keep.by = FALSE)

regel <- function(tage) {
  res <- rbindlist(lapply(seq_len(nrow(tage)), function(n) {
    z <- tage[n]; dm <- mt[[as.character(z$tag)]]
    x <- as.matrix(dm[, .(min, open, high, low, close)])
    rbindlist(lapply(c(1L, -1L), function(rr) {
      t <- trade_tag(x, rr, "S1", "T0", z$atr14)
      if (is.null(t)) NULL else data.table(tag = z$tag, dir = rr, rmult = t$rmult, ret = t$ret,
                                            stop_pct = t$stop_pct, art = t$art, ein_min = t$ein_min, aus_min = t$aus_min)
    }))
  }))
  res[, pnl := pmin(0.01 / stop_pct, 4) * (ret - 1e-4)]
  echt <- merge(tage[, .(tag, dir)], res, by = c("tag", "dir"))
  r <- setNames(numeric(length(alle_tage)), as.character(alle_tage)); r[as.character(echt$tag)] <- echt$pnl
  # random direction on the same days, 1,000 runs
  ft <- as.character(tage$tag)
  pl <- setNames(numeric(length(ft)), ft); ps <- pl
  wl <- res[dir == 1, setNames(pnl, as.character(tag))]; ws <- res[dir == -1, setNames(pnl, as.character(tag))]
  pl[intersect(names(wl), ft)] <- wl[intersect(names(wl), ft)]; ps[intersect(names(ws), ft)] <- ws[intersect(names(ws), ft)]
  set.seed(7)
  sr_z <- replicate(1000, { dd <- sample(c(1, -1), length(ft), TRUE); rr <- setNames(numeric(length(alle_tage)), as.character(alle_tage))
    rr[ft] <- ifelse(dd == 1, pl, ps); sharpe(rr) })
  list(trades = echt, r = r, sr_z = sr_z)
}

alt <- regel(mk[relvol5 >= 1 & or_richtung5 != 0, .(tag, dir = as.integer(or_richtung5), atr14)])
neu <- regel(mk[relvol4 >= 1 & or_richtung5 != 0, .(tag, dir = as.integer(or_richtung5), atr14)])
dir.create(res("research_model"), showWarnings = FALSE)
fwrite(alt$trades, res("research_model", "trades_d2f2_relvol5.csv"))
fwrite(neu$trades, res("research_model", "trades_v51_relvol4.csv"))

zus <- function(x, name) data.table(rule = name, days = length(x$r), trades = nrow(x$trades),
  sharpe = round(sharpe(x$r), 3), cagr_pct = round(100 * cagr(x$r), 1), max_dd_pct = round(100 * max_dd(x$r), 1),
  mean_r = round(mean(x$trades$rmult), 3), hit = round(mean(x$trades$ret > 1e-4), 3),
  rank_random = round(mean(x$sr_z < sharpe(x$r)), 3), random_95 = round(quantile(x$sr_z, 0.95), 2))
sj <- function(rr) { j <- year(as.IDate(names(rr))); sapply(split(rr, j), function(x) round(sharpe(x), 2)) }
sink(res("research_model", "research_model.txt"), split = TRUE)
cat("Research model (R, FMP QQQ minute bars),", format(min(alle_tage)), "to", format(max(alle_tage)), "\n\n")
print(rbind(zus(alt, "D2+F2 S1/T0, volume 9:30-9:34"), zus(neu, "V51, volume 9:31-9:34")))
cat("\nSharpe ratio by year\n")
print(data.table(year = as.integer(names(sj(alt$r))), volume_930_934 = sj(alt$r), volume_931_934 = sj(neu$r)))
sink()
