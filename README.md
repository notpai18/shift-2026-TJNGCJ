# Pragna SolarYard

**Run e-rickshaws on sunshine.** Rooftop solar charges a second-life EV battery by day, and a battery-wear-aware scheduler charges every rickshaw by its departure time, from stored sun first and the grid second.

> SHIFT Sustainable e-Micromobility Hackathon · IIT (BHU) Varanasi · 10–11 Oct 2026
> Status: **Check-in 1 prototype (M1).** Fleet and battery data are **SIMULATED** and labelled as such in the app.

## Problem

India's e-rickshaws are electric but not clean. Most charge overnight, exactly when India's grid runs mostly on fossil fuel (~168 GW from 5 pm–7 am vs ~125 GW at 1 pm, Ember via [Down To Earth](https://www.downtoearth.org.in/energy/indias-solar-power-cuts-coal-use-in-the-day-but-evening-demand-keeps-fossil-fuel-running)), while midday solar is curtailed for lack of storage. In Varanasi this charging also happens at informal, often unsafe yards. UP alone has **8,60,054** registered e-rickshaws ([Rajya Sabha, Mar 2025](https://rsdebate.nic.in/bitstream/123456789/757555/1/PQ_267_12032025_U1536_p379_p383.pdf)).

**Who has the problem:** yard owners and drivers in Varanasi (interviews in progress; see `data/field/`) and PuVVNL, the local DISCOM.

## Run it

```bash
pip install -r requirements.txt
streamlit run app/Home.py
pytest -q
```

Works offline. M1 uses a synthetic solar profile built from sourced Varanasi seasonal yields, with no network calls.

## What works today (M1)

- **Wear-aware LP scheduler** (`core/dispatch.py`, PuLP + CBC) plans a 10-rickshaw yard from 08:00 to 08:00 in 15-minute steps. It splits power between solar direct, the second-life battery and the grid, guarantees each rickshaw's energy by departure, and only cycles the old battery when the grid cost it avoids is more than its wear cost.
- **Grid-only baseline:** every saving is reported relative to the same LP with no solar and no battery, never against an invented number.
- **Tonight's Plan screen** (`app/Home.py`): controls for season, cloud, battery price (wear cost) and sanctioned load; source-stack, battery and per-rickshaw schedule charts; a per-driver Hindi message preview.
- **Tests** (`tests/test_dispatch.py`): energy balance, battery SOC limits and dynamics, every rickshaw charged when feasible, named shortfall when not, cost ≤ baseline, expensive battery left idle.

## Plan

| Milestone | Scope | Status |
|---|---|---|
| M1 · Check-in 1 | Scaffold, config, fleet, tariff, synthetic solar, LP + baseline, tests, Home screen | ✅ done |
| M2 · Check-in 2 | Thermal derating, SOH model, PVGIS + Open-Meteo (cached), Battery Health page, Field Evidence page | next |
| M3 · Check-in 3 | Sizing & honest payback heatmaps, Impact, Assumptions page, Hindi driver page | planned |

Full build spec: [`docs/SPEC.md`](docs/SPEC.md). Team workstreams: [`config/team.yaml`](config/team.yaml).

## Data provenance

| Tag | Meaning | Examples |
|---|---|---|
| SOURCE | Verified public fact with link | UPERC FY27 LMV-11 tariff ₹7.70/kWh, 20% off 09:00–16:00; Varanasi solar 3.66–6.31 kWh/kWp/day |
| FIELD | Collected by the team in Varanasi | `data/field/*.csv` (being filled in) |
| ASSUMPTION | Engineering assumption, replaceable | battery size, efficiency, price, cycle life, sanctioned load (`config/assumptions.yaml`) |
| SIMULATED | Generated demo data | the 10 rickshaws and drivers, battery state |

## Known limitations (so far)

- Lead-acid CC-CV charging taper is not modelled. Chargers are treated as controllable loads with a maximum power.
- Solar is a synthetic half-sine profile until the PVGIS / Open-Meteo loaders land (M2).
- No thermal or battery-health model yet (M2). The battery's wear cost is a simple price ÷ cycle-life assumption.
- No real battery data. Every battery number is simulated.

## Progress log

- **Sat 10 Oct, Check-in 1:** repo scaffold, LP dispatch + baseline, tests, Tonight's Plan screen.
