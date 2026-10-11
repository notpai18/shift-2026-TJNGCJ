"""Battery health estimated from range: km on a full charge now against when new.

Range is a rough proxy for capacity (it also depends on load, route and driving), so
the result is an estimate to be checked with a capacity test.
"""
import math

GOOD, WATCH = 0.80, 0.60   # health thresholds


def assess(chem, km_new, km_now, age_y, cost, interval_y):
    """Returns health (0..1 or None), status, action, years to 60% (or None), cost per day (or None)."""
    def num(v):
        return None if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)
    km_new, km_now, age_y, cost, interval_y = map(num, (km_new, km_now, age_y, cost, interval_y))
    per_day = cost / (interval_y * 365) if cost and interval_y else None
    if not km_new or km_now is None:
        return None, "Unknown", "Add range when new", None, per_day
    h = max(0.0, min(1.0, km_now / km_new))
    years_left = None
    if age_y and h < 1:
        fade = (1 - h) / age_y
        years_left = max(0.0, (h - WATCH) / fade)
    if h >= GOOD:
        status, action = "Good", "No action"
    elif h >= WATCH:
        status = "Watch"
        action = "Plan replacement; pack can go to second-life storage" if chem == "Lithium" else "Plan replacement"
    else:
        status = "Replace"
        action = "Replace; too worn for second life, recycle" if chem == "Lithium" else "Replace; recycle (lead-acid)"
    return h, status, action, years_left, per_day
