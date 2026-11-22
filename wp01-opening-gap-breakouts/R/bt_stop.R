# Research model: entry from the 5-minute opening range and exit with a stop rule, minute by minute.
# Long logic; a short trade runs through spiegeln() from bt_intraday.R.
# The registered trail T3 uses an unpublished in-house smoothed line and is not included here.

einstieg_long <- function(x, k = 5L) {
  mi <- x[, "min"]; or <- mi < BT$start + k
  if (sum(or) < k * 0.8) return(NULL)
  orh <- max(x[or, "high"]); orl <- min(x[or, "low"])
  kand <- which(!or & mi <= BT$letzter_einstieg & x[, "high"] >= orh)
  if (!length(kand)) return(NULL)
  i <- kand[1]
  list(i = i, fill = max(orh, x[i, "open"]), orh = orh, orl = orl)
}

# trail: "T0" none, "T1" break-even after +1 R, "T2" 1 R behind each 5-minute close after +1 R
ausstieg_long <- function(x, i, fill, stop0, trail) {
  mi <- x[, "min"]; ende <- max(which(mi <= BT$schluss))
  if (i > ende || fill <= stop0) return(NULL)
  r <- fill - stop0; st <- stop0; erreicht <- FALSE
  lo <- x[, "low"]; hi <- x[, "high"]; op <- x[, "open"]; cl <- x[, "close"]
  for (j in i:ende) {
    if (lo[j] <= st) {
      px <- if (j == i) st else min(st, op[j])
      return(list(aus_min = mi[j], exit = px, r = r, art = if (st > stop0) "nachgezogen" else "stop"))
    }
    if (hi[j] >= fill + r) erreicht <- TRUE
    if (trail == "T1" && erreicht) st <- max(st, fill)
    if ((mi[j] - BT$start) %% 5L == 4L) {
      if (trail == "T2" && erreicht) st <- max(st, cl[j] - r)
    }
  }
  list(aus_min = mi[ende], exit = cl[ende], r = r, art = "schluss")
}

# One day, one direction. stop_art "S1" opposite edge of OR5, "S2" 0.15 x ATR14 (atr as a fraction)
trade_tag <- function(x, richtung, stop_art, trail, atr) {
  if (richtung == -1L) x <- spiegeln(x)
  e <- einstieg_long(x)
  if (is.null(e)) return(NULL)
  stop0 <- if (stop_art == "S1") e$orl else e$fill - 0.15 * atr * abs(e$fill)
  a <- ausstieg_long(x, e$i, e$fill, stop0, trail)
  if (is.null(a)) return(NULL)
  list(ein_min = x[e$i, "min"], aus_min = a$aus_min, ret = (a$exit - e$fill) / abs(e$fill),
       rmult = (a$exit - e$fill) / a$r, stop_pct = a$r / abs(e$fill), art = a$art, fill = e$fill, r = a$r)
}
