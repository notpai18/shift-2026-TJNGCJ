"""Live re-planning: a solar forecast and a rolling 15-minute re-plan.

The controller never sees the future. Every 15 minutes it re-plans the rest of the
night from what it can measure now (who is plugged in, each pack's charge, the
storage level, the sun so far) and what it was told (each driver's usual times and
the weather forecast). Only the first 15 minutes of each plan are carried out; then
it measures again and re-plans (a receding horizon, as in model predictive control).
"""
import json
import urllib.request
from dataclasses import dataclass, replace

import numpy as np

from scheduler import (CHARGING, END_H, IDLE, NIGHT_H, SLOT_H, START_H, SUN_H, _run, simulate_smart,
                       slot_times, solar_kw, summarize)

VARANASI = (25.32, 82.99)
PR = 0.78        # performance ratio: inverter, heat, dust and wiring losses
GRACE_H = 1.0    # a driver this late is planned without until they plug in
K_NIGHT = int((NIGHT_H - START_H) / SLOT_H)

URL = ("https://api.open-meteo.com/v1/forecast?latitude={0}&longitude={1}"
       "&hourly=shortwave_radiation,cloud_cover&timezone=Asia%2FKolkata&forecast_days=2")


def fetch_forecast(lat=VARANASI[0], lon=VARANASI[1], timeout=6):
    """Hourly irradiance (W/m², mean over the preceding hour) and cloud cover (%) for
    today and tomorrow from Open-Meteo (free, no key). None when offline."""
    try:
        with urllib.request.urlopen(URL.format(lat, lon), timeout=timeout) as resp:
            h = json.load(resp)["hourly"]
        ghi = [float(v or 0) for v in h["shortwave_radiation"]]
        cloud = [float(v or 0) for v in h["cloud_cover"]]
    except Exception:
        return None
    return {"ghi": ghi, "cloud": cloud} if len(ghi) >= 36 else None


def forecast_kw(fc, times, kwp):
    """PV output per slot = kWp x irradiance / 1000 W/m² x performance ratio.
    Hour j of the response is the mean over j-1..j, so it sits at j - 0.5."""
    ghi = np.interp(times + SLOT_H / 2, np.arange(len(fc["ghi"])) - 0.5, fc["ghi"])
    return kwp * np.clip(ghi, 0, None) / 1000 * PR


def morning_cloud(fc):
    """Mean cloud cover 07:00-12:00 tomorrow."""
    return float(np.mean(fc["cloud"][31:37]))


def sun_factor(sun, times, kwp):
    """Tomorrow morning's sun (07:00-12:00) against the clear-day model."""
    m = times >= SUN_H
    clear = solar_kw(times, kwp, 1.0)[m].sum()
    return float(sun[m].sum() / clear) if clear else 0.0


@dataclass
class Surprises:
    no_show: str = None
    late: str = None
    late_h: float = 1.5
    early: str = None
    early_h: float = 2.0
    sun: float = 1.0     # tomorrow morning's real sun as a share of the forecast


def actual_fleet(fleet, sp):
    """What really happens tonight. Every vehicle keeps its usual departure as due_h."""
    out = []
    for r in fleet:
        a, b = r.arrive_h, r.leave_h
        if r.name == sp.no_show:
            a = b = END_H
        else:
            if r.name == sp.late:
                a = min(a + sp.late_h, b - SLOT_H)
            if r.name == sp.early:
                b = max(b - sp.early_h, a + SLOT_H)
        out.append(replace(r, arrive_h=a, leave_h=b, due_h=r.leave_h))
    return out


def belief(fleet, actual, t):
    """The fleet as the controller knows it at time t."""
    out = []
    for r, x in zip(fleet, actual):
        if x.arrive_h <= t:                       # plugged in, or been and gone
            out.append(replace(r, arrive_h=x.arrive_h, leave_h=x.leave_h if x.leave_h <= t else r.leave_h,
                               due_h=r.leave_h))
        elif t < r.arrive_h + GRACE_H:            # not here yet, still expected
            out.append(replace(r, arrive_h=max(r.arrive_h, t + SLOT_H), due_h=r.leave_h))
        else:                                     # too late: planned without
            out.append(replace(r, arrive_h=END_H, leave_h=END_H, due_h=r.leave_h))
    return out


def sun_belief(fc_kw, act_kw, times, k):
    """Measured sun so far, then the forecast scaled by how the last hour compared with it."""
    sun = fc_kw.copy()
    sun[:k] = act_kw[:k]
    f, a = fc_kw[max(0, k - 4):k].sum(), act_kw[max(0, k - 4):k].sum()
    ratio = float(np.clip(a / f, 0.2, 1.5)) if f * SLOT_H > 0.2 else None
    if ratio is not None:
        later = (np.arange(len(times)) >= k) & (times < (NIGHT_H if times[k] < NIGHT_H else END_H))
        sun[later] *= ratio
    return sun, ratio


class LiveNight:
    """One night carried out with re-planning, plus the 18:00 plan followed blindly."""

    def __init__(self, fleet, sp, batt, base_kw, limit_kw, target, fc_kw, kwp, storage, solar_first):
        self.times = times = slot_times()
        self.fleet, self.sp, self.target, self.limit = fleet, sp, target, limit_kw
        self.batt, self.base, self.storage, self.solar_first = batt, base_kw, storage, solar_first
        self.fc_kw = fc_kw
        self.act_kw = np.where(times >= 24, fc_kw * sp.sun, fc_kw)
        self.sun_factor = sun_factor(fc_kw, times, kwp)
        self.actual = actual_fleet(fleet, sp)
        # Each slot's decision depends only on what is measured then, so carrying out the
        # first step of every 15-minute re-plan is the same as one controlled run.
        self.done = self._smart(self.actual, self.act_kw)
        self.first = self.plan_at(K_NIGHT)[0]
        self.fixed = self._blind(self.first.state == CHARGING)
        came = [i for i, x in enumerate(self.actual) if x.arrive_h < END_H]
        self.came = came
        self.log = self._events()

    def _smart(self, fleet, sun, **kw):
        return simulate_smart(fleet, self.batt, self.base, self.limit, self.target, solar=sun, storage=self.storage,
                              solar_first=self.solar_first, sun_factor=self.sun_factor, **kw)

    def _blind(self, on):
        """Switch chargers exactly as the 18:00 plan said, whatever actually happens."""
        bat = [r.battery or self.batt for r in self.actual]
        n = len(self.actual)

        def decide(t, soc, present, extra_kw):
            k = int(round((t - START_H) / SLOT_H))
            draws, st = np.zeros(n), np.zeros(n, int)
            for i in present:
                st[i] = IDLE
                if on[i, k] and soc[i] < self.target - 1e-6:
                    draws[i], st[i] = bat[i].charge_kw(soc[i]), CHARGING
            return draws, st

        return _run(self.actual, self.batt, self.base, self.limit, decide, False, 30, self.act_kw, self.storage,
                    grid_cap_kw=self.limit * 0.95)

    def plan_at(self, k):
        """Re-plan the rest of the night at slot k from the measured state."""
        t = self.times[k]
        bel = belief(self.fleet, self.actual, t)
        soc0 = self.done.soc[:, k].copy()
        for i, x in enumerate(self.actual):
            if x.leave_h <= t:
                soc0[i] = self.done.soc_leave[i]
        energy0 = self.done.store_kwh[k - 1] if k else None
        sun, ratio = sun_belief(self.fc_kw, self.act_kw, self.times, k)
        plan = self._smart(bel, sun, start_k=k, soc0=soc0, energy0=energy0)
        expected = [i for i, r in enumerate(bel) if r.arrive_h < END_H]
        ready = sum(plan.soc_leave[i] >= self.target - 0.01 for i in expected)
        return plan, ready, len(expected), ratio

    def outcome(self, res):
        s = summarize(res, self.limit, self.target)
        s["ready"] = sum(res.soc_leave[i] >= self.target - 0.01 for i in self.came)
        return s

    def _events(self):
        """Slots where something the controller didn't expect became known."""
        t_of = self.times
        log, sun_seen = [], False
        _, ready, n, _ = self.plan_at(K_NIGHT)
        cloud = f"{self.sun_factor * 100:.0f}% of a clear morning forecast"
        log.append((K_NIGHT, f"First plan for tonight: {n} vehicles expected, {cloud}", ready, n,
                    float(self.first.grid_try_kw[K_NIGHT:].max())))
        for k in range(K_NIGHT + 1, len(t_of)):
            t = t_of[k]
            notes = []
            for r, x in zip(self.fleet, self.actual):
                if abs(x.arrive_h - t) < 1e-6 and x.arrive_h > r.arrive_h + 1e-6:
                    late = x.arrive_h - r.arrive_h
                    notes.append(f"{r.name} plugged in {fmt_h(late)} late" +
                                 (": back in the plan" if late >= GRACE_H else ""))
                if abs(r.arrive_h + GRACE_H - t) < 1e-6 and x.arrive_h > t:
                    notes.append(f"{r.name} not here {fmt_h(GRACE_H)} after {hhmm(r.arrive_h)}: planned without")
                if abs(x.leave_h - t) < 1e-6 and x.leave_h < r.leave_h - 1e-6:
                    i = self.fleet.index(r)
                    notes.append(f"{r.name} unplugged {fmt_h(r.leave_h - x.leave_h)} early, "
                                 f"at {self.done.soc_leave[i] * 100:.0f}%")
            if t >= SUN_H + 1 and not sun_seen:
                ratio = sun_belief(self.fc_kw, self.act_kw, t_of, k)[1]
                if ratio is not None and abs(ratio - 1) > 0.2:
                    sun_seen = True
                    notes.append(f"Sun {abs(ratio - 1) * 100:.0f}% {'below' if ratio < 1 else 'above'} forecast "
                                 "in the last hour: rest of the morning re-forecast")
            if notes:
                plan, ready, n, _ = self.plan_at(k)
                log.append((k, "; ".join(notes), ready, n, float(plan.grid_try_kw[k:].max())))
        return log


def fmt_h(h):
    m = int(round(h * 60))
    return f"{m // 60} h {m % 60:02d} min" if m % 60 and m >= 60 else (f"{m // 60} h" if m >= 60 else f"{m} min")


def hhmm(h):
    m = int(round(h * 60)) % (24 * 60)
    return f"{m // 60:02d}:{m % 60:02d}"
