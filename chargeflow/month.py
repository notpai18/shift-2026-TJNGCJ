"""Thirty nights in a row: real Varanasi sunshine and a fleet that varies night to night.

Each night the same drivers come back, but not exactly as usual: about one in ten
doesn't come, times move by up to an hour, and charge on arrival varies. Sunshine
for each day comes from the Open-Meteo history archive (daily irradiance), so cloudy
and monsoon days are real ones.
"""
import json
import urllib.request
from dataclasses import replace
from datetime import date, timedelta

import numpy as np

from live import PR, VARANASI
from scheduler import (END_H, NIGHT_H, base_load, simulate_smart, simulate_uncontrolled, slot_times,
                       solar_kw, summarize)

NIGHTS = 30
ARCHIVE = ("https://archive-api.open-meteo.com/v1/archive?latitude={0}&longitude={1}&start_date={2}"
           "&end_date={3}&daily=shortwave_radiation_sum&timezone=Asia%2FKolkata")


def periods(today):
    """Label, first day. Each run needs 31 days of sun: the day before each night and its morning."""
    recent = today - timedelta(days=6 + NIGHTS)     # the archive runs about five days behind
    return {"recent": ("Last 30 days", recent),
            "monsoon": ("Monsoon, July 2025", date(2025, 7, 1)),
            "winter": ("Winter, December 2025", date(2025, 12, 1))}


def fetch_sun(start, lat=VARANASI[0], lon=VARANASI[1], timeout=8):
    """Daily solar yield in kWh per kW of panels (irradiance x performance ratio) for 31 days. None if offline."""
    end = start + timedelta(days=NIGHTS)
    try:
        with urllib.request.urlopen(ARCHIVE.format(lat, lon, start, end), timeout=timeout) as resp:
            d = json.load(resp)["daily"]
        mj = d["shortwave_radiation_sum"]
    except Exception:
        return None
    if len(mj) < NIGHTS + 1 or any(v is None for v in mj[:NIGHTS + 1]):
        return None
    return [v / 3.6 * PR for v in mj[:NIGHTS + 1]]     # MJ/m² -> kWh/m² -> kWh/kWp


def vary(fleet, rng, no_show=0.1, jitter_h=0.5):
    """Tonight's version of the usual fleet."""
    q = lambda h: round(h * 4) / 4
    out = []
    for r in fleet:
        if rng.random() < no_show:
            continue
        a = q(np.clip(r.arrive_h + rng.normal(0, jitter_h), NIGHT_H, END_H - 1))
        b = q(np.clip(r.leave_h + rng.normal(0, jitter_h / 2), a + 1, END_H))
        soc = round(float(np.clip(r.soc_arrive + rng.normal(0, 0.08), 0.05, 0.9)), 2)
        out.append(replace(r, arrive_h=a, leave_h=b, soc_arrive=soc))
    return out or [fleet[0]]


def run(fleet, batt, kw_room, limit_kw, target, kwp, storage, solar_first, trips, reset_min, sun, seed=7):
    """One row per night with the three strategies side by side.
    sun: daily yield (kWh/kWp) for NIGHTS + 1 days."""
    times = slot_times()
    base = base_load(times, len(fleet), kw_room)     # the rooms are lived in whoever charges
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(NIGHTS):
        tonight = vary(fleet, rng)
        f0, f1 = sun[i] / 4.0, sun[i + 1] / 4.0      # solar_kw's clear day yields 4 kWh/kWp
        pv = np.where(times < 24, solar_kw(times, kwp, f0), solar_kw(times, kwp, f1))
        sims = {
            "uncontrolled": simulate_uncontrolled(tonight, batt, base, limit_kw, trips, reset_min),
            "grid": simulate_smart(tonight, batt, base, limit_kw, target, trips=trips, reset_min=reset_min),
            "solar": simulate_smart(tonight, batt, base, limit_kw, target, trips=trips, reset_min=reset_min,
                                    solar=pv, storage=storage, solar_first=solar_first, sun_factor=f1),
        }
        row = {"night": i, "vehicles": len(tonight), "sun": sun[i]}
        for k, res in sims.items():
            s = summarize(res, limit_kw, target)
            row[k] = {m: s[m] for m in ("ready", "trips", "over_min", "peak_kw", "grid_night_kwh",
                                        "solar_night_share", "avg_soc_leave")}
        rows.append(row)
    return rows


def totals(rows, key):
    vn = sum(r["vehicles"] for r in rows)
    return {
        "all_ready": sum(r[key]["ready"] == r["vehicles"] for r in rows),
        "ready_share": sum(r[key]["ready"] for r in rows) / vn,
        "vehicle_nights": vn,
        "trips": sum(r[key]["trips"] for r in rows),
        "over_min": sum(r[key]["over_min"] for r in rows),
        "over_nights": sum(r[key]["over_min"] > 0 for r in rows),
        "grid_kwh": sum(r[key]["grid_night_kwh"] for r in rows),
        "solar_share": float(np.mean([r[key]["solar_night_share"] for r in rows])),
        "worst_peak": max(r[key]["peak_kw"] for r in rows),
    }
