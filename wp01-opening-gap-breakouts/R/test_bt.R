# Controls for the research backtester (bt_intraday.R): seven hand-computed trades and synthetic prices
# with and without a built-in trend in the gap direction (paper, section "Method", Controls).
# Run from the folder wp01-opening-gap-breakouts: Rscript R/test_bt.R
source("R/lib.R"); source("R/bt_intraday.R")
ok <- function(x, msg) { if (!isTRUE(x)) stop("FAILED: ", msg); cat("ok  ", msg, "\n") }
nahe <- function(a, b) isTRUE(all.equal(unname(a), unname(b), tolerance = 1e-9))

flach <- function() {
  mi <- 570:959
  x <- cbind(min = mi, open = 100, high = 100.2, low = 99.8, close = 100)
  x[mi < 575, "high"] <- 101; x[mi < 575, "low"] <- 99
  x
}
p <- list(k = 5, einstieg = "stop", stop = "gegen", be = FALSE)

# 1: breakout 9:40, close 103 -> +1 R
x <- flach(); x[x[, "min"] == 580, "high"] <- 101.5; x[x[, "min"] >= 600, c("open", "high", "low", "close")] <- 103
x[x[, "min"] >= 600, "low"] <- 102.9
t1 <- trade_long(x, p)
ok(t1$ein_min == 580 && t1$fill == 101 && t1$exit == 103 && nahe(t1$r, 2) && t1$art == "schluss", "long held to the close")

# 2: stop at the opposite edge, open of the stop minute above the stop
x <- flach(); x[x[, "min"] == 580, "high"] <- 101.5; x[x[, "min"] == 600, "low"] <- 98.5
t2 <- trade_long(x, p)
ok(t2$exit == 99 && t2$art == "stop" && t2$aus_min == 600, "stop at the opposite edge")

# 3: gap through the stop: fill at the worse open
x <- flach(); x[x[, "min"] == 580, "high"] <- 101.5; x[x[, "min"] == 600, c("open", "low")] <- c(98, 97.5)
ok(trade_long(x, p)$exit == 98, "stop through a price gap fills at the open")

# 4: break-even after +1 R
x <- flach(); x[x[, "min"] == 580, "high"] <- 101.5
nach <- x[, "min"] > 580
x[nach, "open"] <- 102; x[nach, "close"] <- 102; x[nach, "high"] <- 102.2; x[nach, "low"] <- 101.8
x[x[, "min"] == 590, "high"] <- 103.5
x[x[, "min"] == 600, "low"] <- 100.8
t4 <- trade_long(x, modifyList(p, list(be = TRUE)))
ok(t4$exit == 101 && t4$art == "einstand", "stop moved to break-even")
ok(trade_long(x, p)$art == "schluss", "without break-even the same trade runs to the close")

# 5: short trade via mirrored prices
x <- flach(); x[x[, "min"] == 580, "low"] <- 98.5; x[x[, "min"] >= 600, c("open", "high", "low", "close")] <- 97
x[x[, "min"] >= 600, "high"] <- 97.1
s5 <- trade_long(spiegeln(x), p)
ok(-s5$fill == 99 && -s5$exit == 97 && nahe((s5$exit - s5$fill) / s5$r, 1), "short held to the close = +1 R")

# 6: 5-minute close: signal 9:44 (minute 584), entry 9:45 at the open
x <- flach(); x[x[, "min"] == 584, c("high", "close")] <- c(101.6, 101.5); x[x[, "min"] == 585, "open"] <- 101.4
t6 <- trade_long(x, modifyList(p, list(einstieg = "schluss5")))
ok(t6$ein_min == 585 && t6$fill == 101.4, "entry after a 5-minute close")

# 7: no entry after 11:30
x <- flach(); x[x[, "min"] == 700, "high"] <- 102
ok(is.null(trade_long(x, p)), "no entry after 11:30")

# ---- synthetic prices ----
kuenstlich <- function(n_tage, drift, seed) {
  set.seed(seed)
  mi <- 570:959; vorher <- 100
  rbindlist(lapply(seq_len(n_tage), function(d) {
    luecke <- rnorm(1, 0, 0.006)
    mu <- c(rep(0, 5), rep(drift * sign(luecke), length(mi) - 5))
    r <- rnorm(length(mi), mu, 0.0006)
    cl <- vorher * (1 + luecke) * cumprod(1 + r)
    op <- c(vorher * (1 + luecke), head(cl, -1))
    hi <- pmax(op, cl) * (1 + abs(rnorm(length(mi), 0, 0.0002)))
    lo <- pmin(op, cl) * (1 - abs(rnorm(length(mi), 0, 0.0002)))
    vorher <<- tail(cl, 1)
    data.table(zeit = as.POSIXct("2001-01-01 00:00", tz = "America/New_York") + (d - 1) * 86400 + mi * 60,
               open = op, high = hi, low = lo, close = cl)
  }))
}
pk <- function(drift) {
  td <- tage_bauen(kuenstlich(1000, drift, 7))
  tr <- alle_trades(td, list(k = 15, einstieg = "stop", stop = "gegen", be = FALSE))
  dir_luecke <- sign(td$info$luecke); dir_luecke[is.na(dir_luecke)] <- 0
  set.seed(3); dir_zufall <- sample(c(-1, 1), length(dir_luecke), TRUE)
  c(luecke = sharpe(tagesrenditen(tr, td$info$tag, dir_luecke)$tage$pnl),
    zufall = sharpe(tagesrenditen(tr, td$info$tag, dir_zufall)$tage$pnl))
}
mit <- pk(0.00004); ohne <- pk(0)
cat(sprintf("synthetic, with trend:    Sharpe gap direction %.2f, random direction %.2f\n", mit["luecke"], mit["zufall"]))
cat(sprintf("synthetic, without trend: Sharpe gap direction %.2f, random direction %.2f\n", ohne["luecke"], ohne["zufall"]))
ok(mit["luecke"] > 1.5 && mit["zufall"] < mit["luecke"] - 1, "built-in trend is found")
ok(abs(ohne["luecke"]) < 1, "no edge without trend")
cat("\nAll controls passed.\n")
