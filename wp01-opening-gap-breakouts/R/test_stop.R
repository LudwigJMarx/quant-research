# Hand-computed cases for the stop rules (bt_stop.R).
# Run from the folder wp01-opening-gap-breakouts: Rscript R/test_stop.R
source("R/lib.R"); source("R/bt_intraday.R"); source("R/bt_stop.R")
ok <- function(x, msg) { if (!isTRUE(x)) stop("FAILED: ", msg); cat("ok  ", msg, "\n") }
nahe <- function(a, b) isTRUE(all.equal(unname(a), unname(b), tolerance = 1e-9))

# Day: OR5 99..101, breakout 9:40 at 101, rise to 105 by 10:30, fall to 102.5 at 11:00
tag_bauen <- function() {
  mi <- 570:959; n <- length(mi)
  px <- rep(100, n)
  px[mi >= 580] <- 101
  steig <- mi >= 581 & mi <= 630; px[steig] <- seq(101, 105, length.out = sum(steig))
  px[mi > 630 & mi < 660] <- 105
  px[mi >= 660] <- 102.5
  x <- cbind(min = mi, open = px, high = px + 0.05, low = px - 0.05, close = px)
  x[mi < 575, "high"] <- 101; x[mi < 575, "low"] <- 99
  x[mi == 580, "high"] <- 101.2
  x
}
x <- tag_bauen()

t0 <- trade_tag(x, 1L, "S1", "T0", 0.01)
ok(t0$fill == 101 && t0$art == "schluss" && nahe(t0$rmult, 0.75), "T0: held to the close, +0.75 R")
t1 <- trade_tag(x, 1L, "S1", "T1", 0.01)
ok(t1$art == "schluss" && nahe(t1$rmult, 0.75), "T1: break-even level not touched")
t2 <- trade_tag(x, 1L, "S1", "T2", 0.01)
# highest 5-minute close 105 -> stop 103; the fall to 102.5 hits it, fill at the open 102.5
ok(t2$art == "nachgezogen" && nahe(t2$rmult, (102.5 - 101) / 2) && t2$aus_min == 660, "T2: trailed, fill at the open below the stop")
s2 <- trade_tag(x, 1L, "S2", "T0", 0.01)
ok(nahe(s2$stop_pct, 0.0015) && nahe(s2$r, 0.15 * 0.01 * 101), "S2: stop at 0.15 ATR")
# short trade on mirrored prices gives the same result as the long trade
xs <- x; for (s in c("open", "close")) xs[, s] <- 200 - x[, s]
xs[, "high"] <- 200 - x[, "low"]; xs[, "low"] <- 200 - x[, "high"]
ts <- trade_tag(xs, -1L, "S1", "T2", 0.01)
ok(ts$art == "nachgezogen" && nahe(ts$rmult, t2$rmult), "short mirrored equals long (T2)")
cat("\nStop rules checked.\n")
