# Minimal stand-in for QuantConnect's AlgorithmImports, enough to run qc/variants and qc/test_sample
# outside the LEAN engine. It provides only the names these two programs use at import time.
from datetime import date, datetime, time, timedelta


class QCAlgorithm:
    pass


class Slice:
    pass


class _NS:
    def __getattr__(self, k):
        return k


TimeZones = _NS()
Resolution = _NS()
