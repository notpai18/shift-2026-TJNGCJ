"""Wear-aware LP dispatch for one 08:00→08:00 night (spec §7). M1: no thermal iteration yet."""
import numpy as np
import pulp

from core.config import dt_hours, n_steps
from core.fleet import availability
from core.tariff import tariff_vector

UNMET_PENALTY = 1000.0   # ₹/kWh for energy a rickshaw does not get
EARLY_EPS = 1e-4         # tiny tie-breaker: charge rickshaws and drain the battery earlier


def solve_dispatch(cfg, rickshaws, pv, battery_kwh=None, battery_price=None,
                   grid_kw=None, soc0_frac=None):
    """Solve the dispatch LP and return a dict of schedules and KPIs.

    battery_kwh  — usable-capacity basis "now" (default original × SOH). 0 disables the battery.
    soc0_frac    — battery SOC at 08:00 as a fraction of capacity (default = soc_min_frac).
    """
    b = cfg["battery"]
    T, I, dt = n_steps(cfg), range(len(rickshaws)), dt_hours(cfg)
    price = tariff_vector(cfg)
    avail = availability(rickshaws, cfg)

    cap = b["original_capacity_kwh"] * b["soh_start"] if battery_kwh is None else battery_kwh
    soc_min, soc_max = b["soc_min_frac"] * cap, b["soc_max_frac"] * cap
    soc0 = (b["soc_min_frac"] if soc0_frac is None else soc0_frac) * cap
    eta_c, eta_d = b["eta_charge"], b["eta_discharge"]
    p_bat = b["inverter_kw"] if cap > 0 else 0.0
    g_max = cfg["grid"]["sanctioned_load_kw"] if grid_kw is None else grid_kw
    c_wear = (b["price_inr_per_kwh"] if battery_price is None else battery_price) / b["remaining_cycle_life_efc"]

    m = pulp.LpProblem("solaryard_dispatch", pulp.LpMinimize)
    x = {(i, t): m.add_variable(f"x_{i}_{t}", 0, rickshaws[i]["charger_max_kw"] * avail[i, t])
         for i in I for t in range(T)}
    pv_bat = [m.add_variable(f"pvbat_{t}", 0, p_bat) for t in range(T)]
    pv_load = [m.add_variable(f"pvload_{t}", 0) for t in range(T)]
    curt = [m.add_variable(f"curt_{t}", 0) for t in range(T)]
    dis = [m.add_variable(f"dis_{t}", 0, p_bat) for t in range(T)]
    g = [m.add_variable(f"g_{t}", 0, g_max) for t in range(T)]
    soc = [m.add_variable(f"soc_{t}", soc_min, soc_max) for t in range(T + 1)]
    u = [m.add_variable(f"u_{i}", 0) for i in I]

    m += (pulp.lpSum(price[t] * g[t] * dt for t in range(T))
          + c_wear * pulp.lpSum(dis[t] * dt for t in range(T))
          + UNMET_PENALTY * pulp.lpSum(u)
          + EARLY_EPS * pulp.lpSum(t * x[i, t] for i in I for t in range(T))
          + EARLY_EPS * pulp.lpSum(t * dis[t] for t in range(T)))

    for t in range(T):
        m += pv_bat[t] + pv_load[t] + curt[t] == pv[t]                          # PV split
        m += pulp.lpSum(x[i, t] for i in I) == pv_load[t] + dis[t] + g[t]       # charger balance
        m += soc[t + 1] == soc[t] + eta_c * pv_bat[t] * dt - dis[t] * dt / eta_d  # battery dynamics
    m += soc[0] == soc0
    m += soc[T] >= soc_min
    for i in I:
        delivered = pulp.lpSum(x[i, t] * dt for t in range(T))
        m += delivered + u[i] >= rickshaws[i]["energy_needed_kwh"]
        m += delivered <= rickshaws[i]["energy_needed_kwh"]

    m.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[m.status] != "Optimal":
        raise RuntimeError(f"LP status: {pulp.LpStatus[m.status]}")

    val = lambda vs: np.array([v.value() or 0.0 for v in vs])
    X = np.array([[x[i, t].value() or 0.0 for t in range(T)] for i in I])
    g_v, dis_v, pvl_v = val(g), val(dis), val(pv_load)
    unmet = val(u)
    to_rickshaws = X.sum() * dt
    solar_direct, solar_batt, grid_kwh = pvl_v.sum() * dt, dis_v.sum() * dt, g_v.sum() * dt
    return {
        "x": X, "pv": np.asarray(pv), "pv_load": pvl_v, "pv_bat": val(pv_bat), "dis": dis_v,
        "g": g_v, "curt": val(curt), "soc": val(soc), "price": price, "capacity_kwh": cap,
        "energy_to_rickshaws_kwh": to_rickshaws,
        "solar_direct_kwh": solar_direct,
        "solar_via_battery_kwh": solar_batt,
        "grid_kwh": grid_kwh,
        "curtailed_kwh": val(curt).sum() * dt,
        "solar_share": (solar_direct + solar_batt) / to_rickshaws if to_rickshaws else 0.0,
        "grid_cost_inr": float((price * g_v).sum() * dt),
        "wear_cost_inr": c_wear * solar_batt,
        "wear_cost_per_kwh": c_wear,
        "peak_grid_kw": float(g_v.max()),
        "unmet_kwh": {rickshaws[i]["id"]: float(unmet[i]) for i in I if unmet[i] > 1e-6},
    }


def solve_with_baseline(cfg, rickshaws, pv, **kw):
    """Optimised plan plus the grid-only baseline (no PV, no battery) it is compared against.

    The baseline grid is never the binding limit, so it always charges every rickshaw in full.
    """
    plan = solve_dispatch(cfg, rickshaws, pv, **kw)
    base = solve_dispatch(cfg, rickshaws, np.zeros_like(pv), battery_kwh=0,
                          grid_kw=sum(r["charger_max_kw"] for r in rickshaws))
    plan["baseline_cost_inr"] = base["grid_cost_inr"]
    plan["baseline_grid_kwh"] = base["grid_kwh"]
    plan["net_saving_inr"] = base["grid_cost_inr"] - plan["grid_cost_inr"] - plan["wear_cost_inr"]
    return plan
