# Shared helpers for the R scripts of this folder: paths, statistics, figure theme.
# Every script starts with source("R/lib.R") and runs from the folder wp01-opening-gap-breakouts.

suppressPackageStartupMessages({
  library(data.table)
  library(ggplot2)
  library(jsonlite)
})

options(width = 160)
if (!file.exists(file.path("R", "lib.R")))
  stop("Run the R scripts from the folder wp01-opening-gap-breakouts, e.g. Rscript R/paper_figures.R")

res  <- function(...) file.path("results", ...)
figs <- function(...) file.path("figures", ...)

# Folder with FMP QQQ minute bars, one file per year (qqq_1min_<year>.fst or .csv). Not part of the
# repository. Set it with the environment variable FMP_QQQ_DIR. Returns NULL if it is not set.
fmp_dir <- function() {
  d <- Sys.getenv("FMP_QQQ_DIR")
  if (!nzchar(d)) return(NULL)
  if (!dir.exists(d)) stop("FMP_QQQ_DIR does not exist: ", d)
  d
}

# Reads the FMP minute bars of the given years. Columns: zeit (POSIXct, America/New_York), open, high,
# low, close, volume. A .csv file needs the column zeit as "YYYY-MM-DD HH:MM:SS" in New York time.
fmp_lesen <- function(jahre) {
  d <- fmp_dir()
  rbindlist(lapply(jahre, function(j) {
    f <- file.path(d, sprintf("qqq_1min_%d", j))
    if (file.exists(paste0(f, ".fst"))) return(fst::read_fst(paste0(f, ".fst"), as.data.table = TRUE))
    if (file.exists(paste0(f, ".csv"))) {
      x <- fread(paste0(f, ".csv"))
      x[, zeit := as.POSIXct(as.character(zeit), tz = "America/New_York")]
      return(x)
    }
    stop("missing file for ", j, " in ", d)
  }))
}

# Stops loudly if fewer rows than expected, so that an empty input never looks like a result.
pruefe_anzahl <- function(x, min, was = deparse(substitute(x))) {
  n <- if (is.data.frame(x)) nrow(x) else length(x)
  if (n < min) stop(sprintf("%s: only %d, expected at least %d", was, n, min))
  invisible(n)
}

# ---- statistics (simple daily returns, 252 days a year) ----
sharpe <- function(r, p = 252) mean(r, na.rm = TRUE) / sd(r, na.rm = TRUE) * sqrt(p)
cagr   <- function(r, p = 252) { r <- r[!is.na(r)]; prod(1 + r)^(p / length(r)) - 1 }
max_dd <- function(r) { w <- cumprod(1 + r[!is.na(r)]); min(w / cummax(w) - 1) }

# Deflated Sharpe ratio (Bailey and Lopez de Prado 2014). sr and sr_var in daily units.
deflated_sharpe <- function(sr, n_obs, n_versuche, sr_var, schiefe = 0, kurtosis = 3) {
  g <- 0.5772156649
  sr0 <- sqrt(sr_var) * ((1 - g) * qnorm(1 - 1 / n_versuche) + g * qnorm(1 - 1 / (n_versuche * exp(1))))
  pnorm((sr - sr0) * sqrt(n_obs - 1) / sqrt(1 - schiefe * sr + (kurtosis - 1) / 4 * sr^2))
}

# ---- figures ----
farben <- c(flaeche = "#FFFFFF", tinte = "#13262B", gedaempft = "#51666B", linie = "#D5DEDF",
            raster = "#E6ECEC", petrol = "#1B6F7E", kupfer = "#B87333")

thema <- function(basis = 10) {
  theme_minimal(base_size = basis) +
    theme(plot.background = element_rect(fill = farben[["flaeche"]], colour = NA),
          panel.background = element_rect(fill = farben[["flaeche"]], colour = NA),
          panel.grid.minor = element_blank(), panel.grid.major.x = element_blank(),
          panel.grid.major.y = element_line(colour = farben[["raster"]], linewidth = 0.35),
          axis.text = element_text(colour = farben[["gedaempft"]]),
          axis.title = element_text(colour = farben[["gedaempft"]], size = rel(0.9)),
          axis.ticks = element_blank(),
          plot.title = element_blank(), plot.subtitle = element_blank(), plot.caption = element_blank(),
          legend.position = "top", legend.justification = "left", legend.title = element_blank(),
          legend.text = element_text(colour = farben[["gedaempft"]]),
          plot.margin = margin(12, 14, 16, 10))
}

speichern <- function(p, datei, b = 16, h = 9) {
  dir.create(dirname(datei), showWarnings = FALSE, recursive = TRUE)
  ggsave(datei, p, width = b, height = h, units = "cm", dpi = 300)
  cat("written:", datei, "\n")
}

# ---- QuantConnect outputs ----
# Log lines with a given prefix ("VAR", "TAG", ...) from a log file or an extract, split into fields.
log_zeilen <- function(datei, praefix) {
  z <- readLines(datei)
  z <- grep(paste0("(^| )", praefix, " "), z, value = TRUE)
  sub(paste0("^.*?(^| )", praefix, " "), "", z, perl = TRUE)
}
