# Turns the order exports of the four replication runs on QuantConnect into derived files without
# prices: one row per trade with date, direction, result in R and slippage, plus (version 4) the daily
# account equity rebuilt from the fills and the exposure per trade.
#
# Input: the order list of each backtest as JSON (QuantConnect API, endpoint backtests/orders/read, the
# "orders" array) and the backtest result JSON (backtests/read, the "backtest" object). These files
# contain fill prices and are not part of the repository.
#
# Usage (from the folder wp01-opening-gap-breakouts):
#   Rscript R/qc_exports.R <orders_v1.json> <orders_v2.json> <orders_v3.json> <orders_v4.json> <result_v4.json>
# Output: results/qc_mnq/trades_v1.csv ... trades_v4.csv, equity_v4.csv, exposure_v4.csv
source("R/lib.R")
a <- commandArgs(trailingOnly = TRUE)
if (length(a) != 5) stop("usage: Rscript R/qc_exports.R orders_v1 orders_v2 orders_v3 orders_v4 result_v4")

# One trade per day: first order = entry (stop order), second = protective stop, market order = exit.
qc_trades <- function(datei) {
  o <- as.data.table(fromJSON(datei, flatten = TRUE))
  o[, tag_d := as.IDate(format(as.POSIXct(sub("Z$", "", createdTime), format = "%Y-%m-%dT%H:%M:%S", tz = "UTC"),
                               tz = "America/New_York", "%Y-%m-%d"))]
  setorder(o, id)
  # Shortened sessions (e.g. 24 Dec): the exit order comes on the next morning; book it to the entry day
  o[, erste := tag_d != shift(tag_d, fill = as.IDate("1900-01-01"))]
  vor <- shift(o$tag_d); w <- which(o$erste & o$type == 0); o$tag_d[w] <- vor[w]
  if (o[, .N, by = tag_d][, any(N > 3)]) stop("check the assignment of orders to days")
  e <- o[, .(dir = sign(quantity[1]), ein_status = status[1], ein_trig = stopPrice[1], ein_fill = price[1],
             stop_lvl = if (.N >= 2 && type[2] == 2) stopPrice[2] else NA_real_,
             stop_fill = if (.N >= 2 && type[2] == 2 && status[2] == 3) price[2] else NA_real_,
             schluss_fill = if (any(type == 0)) price[type == 0][1] else NA_real_), by = tag_d]
  e <- e[ein_status == 3]
  e[, aus := fifelse(!is.na(stop_fill), stop_fill, schluss_fill)]
  if (anyNA(e$aus)) stop("trade without exit in ", datei)
  e[, r_pkt := abs(ein_trig - stop_lvl)]
  # Output without price levels: result in R, result in R at the trigger prices, slippage in index points
  e[, .(tag = tag_d, dir,
        rm_q = dir * (aus - ein_fill) / r_pkt,
        rm_q_ohne_schlupf = dir * (fifelse(!is.na(stop_fill), stop_lvl, aus) - ein_trig) / r_pkt,
        schlupf_ein_pkt = dir * (ein_fill - ein_trig),
        schlupf_stop_pkt = fifelse(!is.na(stop_fill), -dir * (stop_fill - stop_lvl), NA_real_),
        ausstieg = fifelse(!is.na(stop_fill), "stop", "close"))]
}

for (v in 1:4) {
  t <- qc_trades(a[v])
  pruefe_anzahl(t, 500, paste("trades version", v))
  fwrite(t, res("qc_mnq", sprintf("trades_v%d.csv", v)))
  cat(sprintf("version %d: %d trades, mean R %.3f\n", v, nrow(t), mean(t$rm_q)))
}

# ---- version 4: daily equity from the fills (MNQ: 2 USD per point), start 100,000 USD ----
o <- as.data.table(fromJSON(a[4], flatten = FALSE))
fill <- rbindlist(lapply(o$events, function(e) {
  e <- as.data.table(e)
  e[status == "filled", .(t = time, menge = fillQuantity, px = fillPrice,
    fee = if ("orderFeeAmount" %in% names(e)) fifelse(is.na(orderFeeAmount), 0, orderFeeAmount) else 0)]
}))
fill[, tag := as.IDate(format(as.POSIXct(t, origin = "1970-01-01", tz = "UTC"), tz = "America/New_York", "%Y-%m-%d"))]
fill[, fluss := -menge * px * 2 - fee]
setorder(fill, t)
fill[, pos := cumsum(menge)]
fill[, buch := tag]; for (i in which(shift(fill$pos, fill = 0) != 0)) fill$buch[i] <- fill$buch[i - 1]   # shortened session
qe <- fill[, .(fluss = sum(fluss)), by = .(tag = buch)][order(tag)][, eq := 100000 + cumsum(fluss)]
erg <- fromJSON(a[5])
soll <- as.numeric(gsub("[$,]", "", erg$runtimeStatistics$Equity))
if (abs(tail(qe$eq, 1) - soll) > 50) stop("equity from fills does not match the final equity: ", tail(qe$eq, 1), " vs ", soll)
fwrite(qe[, .(tag, equity = round(eq, 2))], res("qc_mnq", "equity_v4.csv"))
cat(sprintf("equity from fills: %.2f (QuantConnect %.2f)\n", tail(qe$eq, 1), soll))

# ---- version 4: exposure per trade = notional at entry / equity at the prior close ----
oe <- as.data.table(fromJSON(a[4], flatten = TRUE))
oe <- oe[tag == "einstieg" & status == 3]
oe[, tag_d := as.IDate(format(as.POSIXct(sub("Z$", "", createdTime), format = "%Y-%m-%dT%H:%M:%S", tz = "UTC"), tz = "America/New_York", "%Y-%m-%d"))]
oe[, eq_vor := sapply(tag_d, function(t) { v <- qe[tag < t, eq]; if (length(v)) tail(v, 1) else 100000 })]
oe[, hebel := abs(quantity) * price * 2 / eq_vor]
fwrite(oe[, .(tag = tag_d, dir = as.integer(sign(quantity)), hebel = round(hebel, 4))], res("qc_mnq", "exposure_v4.csv"))
cat(sprintf("exposure: %d trades, median %.2f\n", nrow(oe), median(oe$hebel)))
