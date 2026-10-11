"""Overnight charging simulation for a cluster of e-rickshaws.

Strategies compared on the same fleet and the same building supply:

- uncontrolled: every charger switches on the moment its rickshaw is plugged in
  and stays on (floating) after the battery is full.
- smart: each charger sits behind an on/off switch (a smart plug or relay).
  Every 15-minute slot, Least Laxity First decides which chargers run so the
  building never exceeds its sanctioned load, and a charger is switched off
  once its battery reaches the target.
- smart + solar storage: the same controller, with rooftop solar charging a
  second-life EV battery during the day that discharges at night. The stored
  energy adds to what the grid connection can supply, so more charging fits
  under the same sanctioned load.

The clock runs from 06:00 on day one (so the storage can fill from the day's
sun) to 12:00 the next day (drivers told us they leave between 8 and 11 am).
Hours past midnight are written as 24+.
"""
from dataclasses import dataclass

import numpy as np

SLOT_H = 0.25      # 15-minute slots
START_H = 6.0      # 06:00 day one
NIGHT_H = 18.0     # 18:00, when drivers start coming back
SUN_H = 31.0       # 07:00 next day, when rooftop solar becomes useful for charging
END_H = 36.0       # 12:00 next day

AWAY, IDLE, CHARGING, FLOAT = 0, 1, 2, 3
STATE_NAMES = {AWAY: "away", IDLE: "plugged in, waiting", CHARGING: "charging", FLOAT: "full, still drawing"}

WEATHER = {"Clear sky": 1.0, "Hazy": 0.7, "Monsoon cloud": 0.35}
SUN_SHAPE_H = 24 / np.pi   # area under one day's sine curve, in hours


def slot_times():
    return START_H + np.arange(int((END_H - START_H) / SLOT_H)) * SLOT_H


@dataclass
class Battery:
    """Lead-acid pack and its charger: constant current, then a taper near full."""
    capacity_kwh: float = 5.8   # 48 V x ~120 Ah
    charger_kw: float = 0.9     # grid-side draw at full current
    efficiency: float = 0.80    # grid energy -> stored energy (charger + battery)
    taper_start: float = 0.80   # state of charge where the charger starts tapering
    taper_floor: float = 0.15   # smallest draw near full, as a fraction of charger_kw
    float_frac: float = 0.05    # draw of a charger left on a full battery

    def charge_kw(self, soc):
        """Grid-side draw while charging at this state of charge."""
        if soc < self.taper_start:
            return self.charger_kw
        frac = (1.0 - soc) / (1.0 - self.taper_start)
        return self.charger_kw * max(self.taper_floor, frac)

    def float_kw(self):
        return self.charger_kw * self.float_frac

    def step(self, soc, kw, hours=SLOT_H):
        return min(1.0, soc + kw * self.efficiency * hours / self.capacity_kwh)

    @classmethod
    def lithium(cls, capacity_kwh=5.1, charger_kw=1.5):
        """LFP pack: efficient, tapers only near full, and its BMS stops at full (no float)."""
        return cls(capacity_kwh, charger_kw, efficiency=0.92, taper_start=0.90, taper_floor=0.30, float_frac=0.0)

    def hours_to(self, soc, target):
        """Charging time from soc to target with the charger left on."""
        hours = 0.0
        while soc < target - 1e-6 and hours < 24:
            soc = self.step(soc, self.charge_kw(soc))
            hours += SLOT_H
        return hours


@dataclass
class Storage:
    """Stationary pack built from second-life EV cells, charged only from solar."""
    nominal_kwh: float = 15.0
    health: float = 0.75        # second-life state of health: usable share of nominal
    power_kw: float = 3.0       # inverter limit, charge and discharge
    efficiency: float = 0.95    # each way
    min_frac: float = 0.10      # never drained below this share of usable capacity

    @property
    def usable_kwh(self):
        return self.nominal_kwh * self.health


@dataclass
class Rickshaw:
    name: str
    arrive_h: float     # hours on the simulation clock (START_H .. END_H)
    leave_h: float
    soc_arrive: float   # 0..1
    battery: object = None   # this vehicle's Battery; None = the shared default
    due_h: float = None      # departure the controller plans for; None = leave_h. Differs when a driver leaves early.

    @property
    def due(self):
        return self.leave_h if self.due_h is None else self.due_h


@dataclass
class Result:
    times: np.ndarray
    base_kw: np.ndarray      # household load (lights, fans) per slot
    ev_kw: np.ndarray        # total charger draw per slot
    demand_kw: np.ndarray    # household + chargers
    grid_try_kw: np.ndarray  # grid import the building asked for, before any cut-out
    load_kw: np.ndarray      # grid import the meter sees; 0 while the supply is cut
    solar_kw: np.ndarray     # solar generation
    store_kw: np.ndarray     # storage power: + discharging, - charging
    store_kwh: np.ndarray    # storage energy at the end of each slot
    export_kw: np.ndarray    # solar the building could neither use nor store
    state: np.ndarray        # [rickshaw, slot] -> AWAY / IDLE / CHARGING / FLOAT
    soc: np.ndarray          # [rickshaw, slot] state of charge at slot start, nan when away
    soc_leave: np.ndarray    # state of charge at departure
    trips: list              # slot indices where the supply cut out


def random_fleet(n, seed=7):
    """A plausible night: drivers return 19:30-23:30, leave 05:30-08:00."""
    rng = np.random.default_rng(seed)
    quarter = lambda h: round(h * 4) / 4
    fleet = []
    for i in range(n):
        arrive = quarter(np.clip(rng.normal(21.5, 0.75), 19.5, 23.5))
        leave = quarter(np.clip(rng.normal(30.5, 0.5), 29.5, 32.0))
        soc = round(float(rng.uniform(0.15, 0.45)), 2)
        fleet.append(Rickshaw(f"R{i + 1}", arrive, leave, soc))
    return fleet


def base_load(times, rooms, kw_per_room):
    """Household load: evening peak, low overnight (fans), little while drivers are out."""
    clock = times % 24
    shape = np.select(
        [(clock >= 18) & (clock < 23), (clock >= 23) | (clock < 5), (clock >= 5) & (clock < 9)],
        [1.0, 0.4, 0.6], default=0.3)
    return rooms * kw_per_room * shape


def solar_kw(times, kwp, weather=1.0, yield_kwh_per_kwp=4.0):
    """Rooftop generation: a sine from 06:00 to 18:00 giving yield_kwh_per_kwp a day."""
    clock = (times + SLOT_H / 2) % 24
    shape = np.where((clock > 6) & (clock < 18), np.sin(np.pi * (clock - 6) / 12), 0.0)
    return kwp * yield_kwh_per_kwp * weather / SUN_SHAPE_H * shape


def _run(fleet, batt, base_kw, limit_kw, decide, trips, reset_min, solar=None, storage=None,
         grid_cap_kw=None, start_k=0, soc0=None, energy0=None):
    """Step through the day slot by slot.

    Storage dispatch: first cover whatever the grid can't (import above
    grid_cap_kw), then spread the remaining stored energy evenly over what is
    left of the night, so the pack is still there when most rickshaws are
    plugged in and is empty again by morning for the next day's sun.

    start_k, soc0 and energy0 start the run mid-way from a measured state (a re-plan):
    soc0 holds each vehicle's charge now (nan = use soc_arrive), energy0 the pack's energy.
    Slots before start_k are left at zero.
    """
    times = slot_times()
    bat = [r.battery or batt for r in fleet]
    grid_cap_kw = limit_kw if grid_cap_kw is None else grid_cap_kw
    n, T = len(fleet), len(times)
    solar = np.zeros(T) if solar is None else solar
    state = np.zeros((n, T), int)
    soc_hist = np.full((n, T), np.nan)
    soc = np.array([r.soc_arrive for r in fleet], float)
    if soc0 is not None:
        soc0 = np.asarray(soc0, float)
        soc = np.where(np.isnan(soc0), soc, soc0)
    ev, demand, grid_try, load = (np.zeros(T) for _ in range(4))
    store_kw, store_kwh, export = (np.zeros(T) for _ in range(3))
    trip_slots, off_until = [], -1
    reset_slots = max(1, round(reset_min / (SLOT_H * 60)))
    if storage:
        e_min, e_max = storage.usable_kwh * storage.min_frac, storage.usable_kwh
        energy = e_min if energy0 is None else min(max(energy0, e_min), e_max)   # empty after last night
    else:
        e_min = e_max = energy = 0.0

    for k, t in enumerate(times):
        if k < start_k:
            continue
        present = [i for i, r in enumerate(fleet) if r.arrive_h <= t < r.leave_h]
        soc_hist[present, k] = soc[present]
        can_discharge = 0.0
        if storage:
            can_discharge = min(storage.power_kw, (energy - e_min) * storage.efficiency / SLOT_H)
        draws, st = decide(t, soc, present, solar[k] + can_discharge)
        demand[k] = base_kw[k] + draws.sum()
        net = demand[k] - solar[k]
        discharge = 0.0
        if storage and net > 0:
            shave = net - grid_cap_kw
            spread = ((energy - e_min) * storage.efficiency / max(END_H - t, SLOT_H)
                      if t >= NIGHT_H else 0.0)
            discharge = max(0.0, min(net, can_discharge, max(shave, spread)))
        grid_try[k] = max(net, 0.0) - discharge

        tripped = k < off_until
        if not tripped and trips and grid_try[k] > limit_kw + 1e-9:
            trip_slots.append(k)
            off_until = k + reset_slots
            tripped = True
        if tripped:
            draws[:] = 0
            st[st != AWAY] = IDLE
        elif net >= 0:
            energy -= discharge / storage.efficiency * SLOT_H if storage else 0.0
            store_kw[k] = discharge
            load[k] = grid_try[k]
        else:
            surplus = -net
            charge = 0.0
            if storage:
                charge = min(surplus, storage.power_kw,
                             (e_max - energy) / (storage.efficiency * SLOT_H))
                energy += charge * storage.efficiency * SLOT_H
            store_kw[k] = -charge
            export[k] = surplus - charge

        store_kwh[k] = energy
        ev[k] = draws.sum()
        state[:, k] = st
        for i in present:
            if st[i] == CHARGING:
                soc[i] = bat[i].step(soc[i], draws[i])

    return Result(times, base_kw, ev, demand, grid_try, load, solar, store_kw, store_kwh,
                  export, state, soc_hist, soc.copy(), trip_slots)


def simulate_uncontrolled(fleet, batt, base_kw, limit_kw, trips=False, reset_min=30):
    n = len(fleet)
    bat = [r.battery or batt for r in fleet]

    def decide(t, soc, present, extra_kw):
        draws, st = np.zeros(n), np.zeros(n, int)
        for i in present:
            if soc[i] >= 0.999:
                draws[i], st[i] = bat[i].float_kw(), FLOAT
            else:
                draws[i], st[i] = bat[i].charge_kw(soc[i]), CHARGING
        return draws, st

    return _run(fleet, batt, base_kw, limit_kw, decide, trips, reset_min)


def simulate_smart(fleet, batt, base_kw, limit_kw, target=1.0, headroom=0.95,
                   trips=False, reset_min=30, solar=None, storage=None, solar_first=False,
                   sun_factor=1.0, start_k=0, soc0=None, energy0=None):
    """Least Laxity First with on/off chargers under the sanctioned load.

    laxity = time left before departure - charging time still needed.
    The rickshaw with the least slack is switched on first; chargers that do
    not fit in the remaining headroom wait for a later slot. A rickshaw whose
    laxity has gone negative can no longer be ready in time, so it moves to the
    back of the queue: on an overloaded night that gets as many rickshaws ready
    as possible instead of leaving all of them half charged.

    With solar and storage, the power they can supply this slot is added to the
    headroom, so the grid import still stays under the sanctioned load.

    sun_factor is tomorrow morning's forecast sun against a clear day: solar-first
    waits less as the forecast gets cloudier, and not at all below 0.4.
    Laxity uses each vehicle's planned departure (due), which is all the
    controller knows until the driver actually unplugs.
    """
    n = len(fleet)
    bat = [r.battery or batt for r in fleet]

    def decide(t, soc, present, extra_kw):
        draws, st = np.zeros(n), np.zeros(n, int)
        k = int(round((t - START_H) / SLOT_H))
        avail = limit_kw * headroom - base_kw[k] + extra_kw
        queue = []
        for i in present:
            st[i] = IDLE
            if soc[i] < target - 1e-6:
                need = bat[i].hours_to(soc[i], target)
                # Solar-first: before the morning sun, a vehicle that can still finish with a
                # 25% margin between 07:00 and departure waits, so its energy comes from solar.
                if (solar_first and sun_factor >= 0.4 and t < SUN_H
                        and need <= 0.75 * min(sun_factor, 1.0) * (fleet[i].due - SUN_H)):
                    continue
                laxity = (fleet[i].due - t) - need
                queue.append((laxity, i))
        for _, i in sorted(queue, key=lambda q: (q[0] < 0, q[0])):
            kw = bat[i].charge_kw(soc[i])
            if kw <= avail + 1e-9:
                draws[i], st[i] = kw, CHARGING
                avail -= kw
        return draws, st

    return _run(fleet, batt, base_kw, limit_kw, decide, trips, reset_min, solar, storage,
                grid_cap_kw=limit_kw * headroom, start_k=start_k, soc0=soc0, energy0=energy0)


def summarize(res, limit_kw, target):
    over = res.load_kw > limit_kw + 1e-9
    night = res.times >= NIGHT_H
    direct_solar = np.minimum(res.solar_kw, res.demand_kw)
    discharge = np.clip(res.store_kw, 0, None)
    night_demand = res.demand_kw[night].sum()
    return {
        "peak_kw": float(res.grid_try_kw.max()),
        "over_min": int(over.sum() * SLOT_H * 60),
        "trips": len(res.trips),
        "ready": int((res.soc_leave >= target - 0.01).sum()),
        "float_h": float((res.state == FLOAT).sum() * SLOT_H),
        "energy_kwh": float(res.ev_kw.sum() * SLOT_H),
        "avg_soc_leave": float(res.soc_leave.mean()),
        "grid_night_kwh": float(res.load_kw[night].sum() * SLOT_H),
        "solar_kwh": float(res.solar_kw.sum() * SLOT_H),
        "export_kwh": float(res.export_kw.sum() * SLOT_H),
        "discharged_kwh": float(discharge.sum() * SLOT_H),
        "solar_night_share": float((direct_solar + discharge)[night].sum() / night_demand)
                             if night_demand else 0.0,
    }
