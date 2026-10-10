"""Time-of-day grid tariff for UP's LMV-11 EV charging category (SOURCE F3)."""
import numpy as np

from core.config import clock_labels, to_minutes


def tariff_vector(cfg):
    """₹/kWh per step: 20% discount inside solar hours, full LMV-11 rate otherwise."""
    t = cfg["tariff"]
    base = t["lmv11_energy_inr_per_kwh"]
    lo, hi = (to_minutes(x) for x in t["solar_hours"])
    discounted = round(base * (1 - t["solar_hour_discount"]), 2)
    return np.array([discounted if lo <= to_minutes(c) < hi else base
                     for c in clock_labels(cfg)])
