"""Solar input. M1: synthetic offline profile only (PVGIS / Open-Meteo come in M2)."""
import numpy as np

from core.config import clock_labels, dt_hours, to_minutes

SUNRISE, SUNSET = "06:00", "18:00"


def synthetic_pv(cfg, season, cloud_factor=1.0):
    """Half-sine PV (kW) scaled so daily energy = kWp × seasonal yield (F10) × cloud factor.

    Label in UI: SYNTHETIC.
    """
    kwp = cfg["pv"]["kwp"]
    daily_kwh = kwp * cfg["pv"]["seasonal_kwh_per_kw_day"][season] * cloud_factor
    rise, sset = to_minutes(SUNRISE), to_minutes(SUNSET)
    mins = np.array([to_minutes(c) for c in clock_labels(cfg)]) + cfg["time"]["step_minutes"] / 2
    shape = np.where((mins > rise) & (mins < sset),
                     np.sin(np.pi * (mins - rise) / (sset - rise)), 0.0)
    return shape * daily_kwh / (shape.sum() * dt_hours(cfg))
