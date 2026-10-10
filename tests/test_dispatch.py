import numpy as np
import pytest

from core.config import dt_hours, load_config
from core.dispatch import solve_dispatch, solve_with_baseline
from core.fleet import generate_fleet
from core.solar import synthetic_pv


@pytest.fixture(scope="module")
def setup():
    cfg = load_config()
    fleet = generate_fleet()["rickshaws"]
    pv = synthetic_pv(cfg, "autumn")
    return cfg, fleet, pv


@pytest.fixture(scope="module")
def plan(setup):
    cfg, fleet, pv = setup
    return solve_with_baseline(cfg, fleet, pv)


def test_energy_balance(plan):
    assert np.allclose(plan["x"].sum(axis=0), plan["pv_load"] + plan["dis"] + plan["g"], atol=1e-6)
    assert np.allclose(plan["pv_bat"] + plan["pv_load"] + plan["curt"], plan["pv"], atol=1e-6)


def test_soc_bounds_and_recursion(setup, plan):
    cfg = setup[0]
    b, cap, dt = cfg["battery"], plan["capacity_kwh"], dt_hours(cfg)
    soc = plan["soc"]
    assert soc.min() >= b["soc_min_frac"] * cap - 1e-6
    assert soc.max() <= b["soc_max_frac"] * cap + 1e-6
    expected = soc[:-1] + b["eta_charge"] * plan["pv_bat"] * dt - plan["dis"] * dt / b["eta_discharge"]
    assert np.allclose(soc[1:], expected, atol=1e-6)


def test_all_rickshaws_charged_when_feasible(setup, plan):
    fleet = setup[1]
    assert plan["unmet_kwh"] == {}
    assert plan["energy_to_rickshaws_kwh"] == pytest.approx(sum(r["energy_needed_kwh"] for r in fleet))


def test_infeasible_grid_names_rickshaws(setup):
    cfg, fleet, pv = setup
    res = solve_dispatch(cfg, fleet, pv, grid_kw=1)
    assert res["unmet_kwh"], "expected unmet energy with a 1 kW grid limit"
    assert all(k.startswith("R") for k in res["unmet_kwh"])


def test_cost_not_above_baseline(plan):
    assert plan["grid_cost_inr"] + plan["wear_cost_inr"] <= plan["baseline_cost_inr"] + 1e-6


def test_expensive_battery_sits_idle(setup):
    cfg, fleet, pv = setup
    # wear cost (₹/kWh) above the highest tariff ⇒ never worth cycling the old pack
    res = solve_dispatch(cfg, fleet, pv, battery_price=8.0 * cfg["battery"]["remaining_cycle_life_efc"])
    assert res["solar_via_battery_kwh"] < 1e-6
