"""Checks for the rolling re-planner. Run with:  python -m pytest tests"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import live  # noqa: E402
from scheduler import Battery, Storage, base_load, random_fleet, simulate_smart, slot_times, solar_kw  # noqa: E402

TIMES = slot_times()
FLEET = random_fleet(10, 7)
BASE = base_load(TIMES, 10, 0.15)
SUN = solar_kw(TIMES, 5.0)


def night(sp=None, limit=7.0, solar_first=False):
    return live.LiveNight(FLEET, sp or live.Surprises(), Battery(), BASE, limit, 0.95, SUN, 5.0, Storage(), solar_first)


def test_restart_from_state_matches_full_run():
    """Re-planning mid-night from the measured state, with nothing changed, carries on exactly as before."""
    full = simulate_smart(FLEET, Battery(), BASE, 7.0, 0.95, solar=SUN, storage=Storage())
    k = 80
    part = simulate_smart(FLEET, Battery(), BASE, 7.0, 0.95, solar=SUN, storage=Storage(),
                          start_k=k, soc0=full.soc[:, k], energy0=full.store_kwh[k - 1])
    assert np.allclose(part.load_kw[k:], full.load_kw[k:])
    assert np.allclose(part.soc_leave, full.soc_leave)


def test_calm_night_plan_holds():
    n = night()
    assert n.outcome(n.done)["ready"] == n.outcome(n.fixed)["ready"] == len(FLEET)
    assert len(n.log) == 1


def test_surprises_are_logged_and_replanning_does_no_worse():
    sp = live.Surprises(no_show="R2", late="R4", late_h=1.5, early="R1", early_h=2.0, sun=0.5)
    n = night(sp)
    text = " ".join(e[1] for e in n.log)
    assert "R2 not here" in text and "R4 plugged in" in text and "R1 unplugged" in text
    assert len(n.came) == len(FLEET) - 1
    assert n.outcome(n.done)["ready"] >= n.outcome(n.fixed)["ready"]


def test_never_over_sanctioned_load():
    sp = live.Surprises(late="R3", late_h=3.0, sun=0.5)
    n = night(sp, limit=5.0, solar_first=True)
    assert n.done.grid_try_kw.max() <= 5.0 * 0.95 + 1e-6


def test_forecast_to_kw():
    fc = {"ghi": [0.0] * 6 + [500.0] * 12 + [0.0] * 30, "cloud": [0.0] * 48}
    kw = live.forecast_kw(fc, TIMES, 4.0)
    assert np.isclose(kw[TIMES == 12.0][0], 4.0 * 0.5 * live.PR)
    assert kw[TIMES == 20.0][0] == 0
