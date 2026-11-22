# Research model: backtester for intraday breakouts from the opening range (OR) on minute bars.
# One trade per day and direction. A short trade runs through the same long logic on mirrored
# prices (sign flipped).
#
# Minutes as minute of the day (9:30 = 570). A day matrix has the columns min, open, high, low,
# close in ascending time. Identifiers are German (tag = day, luecke = gap, einstieg = entry,
# schluss = close, gegen = opposite edge, mitte = middle, be = break-even).

library(data.table)

BT <- list(start = 570L, letzter_einstieg = 690L, schluss = 955L)

# minute bars -> list of day matrices, plus the gap per day
tage_bauen <- function(m) {
  m <- copy(m)
  m[, tag := as.IDate(format(zeit, "%Y-%m-%d"))]
  m[, min := as.integer(format(zeit, "%H")) * 60L + as.integer(format(zeit, "%M"))]
  setorder(m, zeit)
  info <- m[, .(open = open[1], close = close[.N], n = .N, erste = min[1]), by = tag]
  info[, luecke := open / shift(close) - 1]
  liste <- split(m[, .(min, open, high, low, close)], m$tag)
  liste <- lapply(liste, as.matrix)
  list(info = info, tage = liste[as.character(info$tag)])
}

spiegeln <- function(x) {
  y <- x
  y[, "open"] <- -x[, "open"]; y[, "close"] <- -x[, "close"]
  y[, "high"] <- -x[, "low"];  y[, "low"] <- -x[, "high"]
  y
}

# One trade (long logic). p = list(k, einstieg = "stop"|"schluss5", stop = "gegen"|"mitte", be = TRUE/FALSE)
trade_long <- function(x, p) {
  mi <- x[, "min"]
  or <- mi < BT$start + p$k
  if (sum(or) < p$k * 0.8) return(NULL)                 # range incomplete
  orh <- max(x[or, "high"]); orl <- min(x[or, "low"])
  if (p$einstieg == "stop") {
    kand <- which(!or & mi <= BT$letzter_einstieg & x[, "high"] >= orh)
    if (!length(kand)) return(NULL)
    i <- kand[1]
    fill <- max(orh, x[i, "open"])
  } else {
    # 5-minute close: minutes 574, 579, ... close a 5-minute bar
    ende5 <- which(!or & (mi - BT$start) %% 5L == 4L & mi <= BT$letzter_einstieg & x[, "close"] > orh)
    if (!length(ende5) || ende5[1] == nrow(x)) return(NULL)
    i <- ende5[1] + 1L
    fill <- x[i, "open"]
  }
  stop0 <- if (p$stop == "gegen") orl else (orh + orl) / 2
  if (fill <= stop0) return(NULL)
  r <- fill - stop0
  ende <- max(which(mi <= BT$schluss))
  if (i > ende) return(NULL)
  j <- i:ende
  lo <- x[j, "low"]; hi <- x[j, "high"]; op <- x[j, "open"]
  t_stop <- which(lo <= stop0)[1]
  t_be <- if (p$be) which(hi >= fill + r)[1] else NA_integer_
  exit_px <- NA_real_; art <- "schluss"
  if (!is.na(t_be) && (is.na(t_stop) || t_be < t_stop)) {
    # stop at break-even from the minute after the trigger
    nach <- which(lo[-(1:t_be)] <= fill)[1]
    if (!is.na(nach)) { s <- t_be + nach; exit_px <- min(fill, op[s]); art <- "einstand"; t_aus <- s }
  } else if (!is.na(t_stop)) {
    exit_px <- if (t_stop == 1L) stop0 else min(stop0, op[t_stop]); art <- "stop"; t_aus <- t_stop
  }
  if (is.na(exit_px)) { exit_px <- x[ende, "close"]; t_aus <- length(j) }
  list(ein_min = mi[i], aus_min = mi[j[t_aus]], fill = fill, exit = exit_px, r = r, art = art,
       orh = orh, orl = orl)
}

# Both directions for all days. Result: one row per day and direction.
alle_trades <- function(td, p) {
  res <- vector("list", length(td$tage))
  for (n in seq_along(td$tage)) {
    x <- td$tage[[n]]
    l <- trade_long(x, p); s <- trade_long(spiegeln(x), p)
    z <- list()
    if (!is.null(l)) z$l <- data.table(dir = 1L, ein_min = l$ein_min, aus_min = l$aus_min,
                                       ret = (l$exit - l$fill) / l$fill, rmult = (l$exit - l$fill) / l$r,
                                       stop_pct = l$r / l$fill, art = l$art)
    if (!is.null(s)) z$s <- data.table(dir = -1L, ein_min = s$ein_min, aus_min = s$aus_min,
                                       ret = (s$exit - s$fill) / abs(s$fill), rmult = (s$exit - s$fill) / s$r,
                                       stop_pct = s$r / abs(s$fill), art = s$art)
    if (length(z)) res[[n]] <- cbind(tag = td$info$tag[n], rbindlist(z))
  }
  rbindlist(res)
}

# Daily returns for a given direction per day (vector dir_tag, 0 = no trade)
tagesrenditen <- function(tr, alle_tage, dir_tag, kosten = 1e-4, risiko = 0.01, max_hebel = 4) {
  w <- data.table(tag = alle_tage, dir = as.integer(dir_tag))
  x <- merge(w[dir != 0], tr, by = c("tag", "dir"))
  x[, hebel := pmin(risiko / stop_pct, max_hebel)]
  x[, pnl := hebel * (ret - kosten)]
  d <- merge(data.table(tag = alle_tage), x[, .(tag, pnl)], by = "tag", all.x = TRUE)
  d[is.na(pnl), pnl := 0]
  list(tage = d, trades = x)
}
