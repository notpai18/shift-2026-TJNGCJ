# Pragna SolarYard — Complete Build Spec for Claude Code

> **Read this whole file before writing any code.** It is the single source of truth for the project.
> You (Claude Code) are a teammate on a 2–3 person team at a 24-hour hackathon. Build exactly what is described here, in the order given in §12, and keep every number honest.

---

## 0. Instructions for Claude Code (non-negotiable rules)

1. **Software only.** No hardware. All telemetry (battery SOC, cell temperatures, internal resistance) is **simulated**, and must be **labelled "SIMULATED"** in the UI, data files and README.
2. **All code must be written fresh during the hackathon.** The organisers' rule is *"Research and data, yes; project code, no."* Do not import, copy or reference any pre-existing Pragna code. Public open-source libraries are fine.
3. **Never invent facts.** Every number in the app comes from one of three places, and the UI must show which:
   - `SOURCE` — a verified public fact (listed in §3, with URL),
   - `FIELD` — data the team collected in Varanasi today (`data/field/*.csv`),
   - `ASSUMPTION` — an engineering assumption in `config/assumptions.yaml`, clearly tagged so the team can replace it.
4. **Honesty beats hype.** The judging guide says *"Saying honestly what didn't work counts in your favour"* and the brochure says *"One honest sentence beats a confident guess."* If the optimiser shows a site does not pay back, **show it**. Never hard-code a payback figure.
5. **Must run on a laptop with no internet** (patchy campus wifi). Every online data source has a cached offline fallback in `data/`.
6. **One command to run:** `streamlit run app/Home.py`. Python 3.11. Pin versions in `requirements.txt`.
7. Keep it simple and working. A finished, correct, clear prototype beats an ambitious broken one. Commit to git after every milestone (§12) with clear messages — the mentors score *Progress* by what changed between check-ins.
8. Do not call the system a "VPP" (virtual power plant). A single non-exporting yard is not a VPP. Call it a **"fleet energy manager"**; multi-yard aggregation is "future work".

---

## 1. The hackathon (context you need)

- **Event:** SHIFT — Sustainable e-Micromobility Hackathon, IIT (BHU) Varanasi, 10–11 Oct 2026. Hosted by IIT (BHU); with WMG (University of Warwick), IIT Kharagpur, SimLionics; funded by the British Council.
- **Format:** 24 hours, teams of 2–3, **no hardware**, software built at the event. Bring-your-own problem, with evidence that it is real.
- **Tracks (illustrative):** Batteries · Charging & swapping · Fleet & operations · Rider safety · Vehicle & retrofit · **Second life** · Models & policy · Sensing & AI. Our project spans **Charging, Batteries, Second life, Fleet ops**.
- **Judging (100 pts):**

| Criterion | Pts | What judges want (from official judging guide) |
|---|---|---|
| Problem | 25 | Real problem; **a named rider, fleet or workshop**, and **evidence you gathered** |
| Solution | 25 | **A working demo** that tackles the problem you named |
| Practicality | 20 | Would it work in India? **Costed in ₹. Runs on a cheap phone, a patchy network or weak power** |
| Progress | 15 | Real steps between mentor check-ins, **against your own plan** |
| Presentation | 15 | Clear pitch, **live demo inside 3 minutes**, straight answers |

- **Schedule (two documents disagree — team must confirm with organisers):**
  - Judging guide: Check-in 1 Sat 17:00 · Check-in 2 Sun 10:00 · Check-in 3 Sun 12:00 · **Submission Sun 14:00 (jury reads the repo)** · Pitch Sun 16:00 (3 min).
  - Brochure: Mentors Sat 17:30 · Check-in 1 Sat 20:00 · Check-in 2 Sun 08:00 · Check-in 3 Sun 12:00 · Build stops Sun 14:00 · Pitches 14:30 (5 min).
  - **Plan for the earliest times.** Build started Sat 14:00.
- **Jury/mentor profile:** WMG are battery and energy-storage specialists. Expect hard questions on battery degradation, second-life safety and thermal behaviour.

---

## 2. The product in one paragraph

**Pragna SolarYard** is a solar-powered charging node for e-rickshaw yards. A yard installs rooftop solar and a **second-life EV battery** (retired EV pack, repurposed as stationary storage). By day, solar charges the second-life battery (and any rickshaw that happens to be parked). At night, when the fleet returns, rickshaws charge **from stored solar first and the grid second**. Our software is the **brain**: a battery-wear-aware, heat-aware **charging scheduler** that guarantees every rickshaw is charged by its departure time, a **battery health & safety monitor** for the second-life pack, and a **sizing & payback tool** that tells a yard owner honestly what system to install and whether it pays back. It is the extension of the startup **Pragna Energies** (second-life EV battery storage + AI demand management for rooftop-solar homes) into e-micromobility.

### Problem statement (use this wording in README and pitch)

> India's e-rickshaws are electric but not clean. Most charge overnight — exactly when India's grid runs mostly on fossil fuel — while midday solar is curtailed for lack of storage. In Varanasi this charging also happens at informal, often unsafe yards. **Pragna SolarYard** runs e-rickshaws on sunshine: rooftop solar charges a second-life EV battery by day, and a battery-wear-aware AI scheduler charges every rickshaw by morning — giving retired EV batteries a second life and moving yards onto legal, safe connections.

### Who has the problem (named stakeholders — fill from field work)

- **Yard / garage owners** in Varanasi (e.g. near Lanka, BHU gate) — name(s) in `data/field/yards.csv`.
- **E-rickshaw drivers** who charge there — names (with consent) in `data/field/drivers.csv`.
- **PuVVNL** (Purvanchal Vidyut Vitran Nigam Ltd., the DISCOM for Varanasi) — night peak load and unauthorised use.

---

## 3. Verified facts (SOURCE) — use these and only these as "facts"

| # | Fact | Source |
|---|---|---|
| F1 | UP has **8,60,054** registered e-rickshaws (Vahan, Rajya Sabha answer 12 Mar 2025, with an RTO-wise annexure incl. Varanasi). | https://rsdebate.nic.in/bitstream/123456789/757555/1/PQ_267_12032025_U1536_p379_p383.pdf |
| F2 | India's fossil generation averaged ~**125 GW at 1 pm** vs **168 GW from 5 pm–7 am** (H1 2026, Ember); evening/night fossil up 22 GW vs 2023; on sunny days solar/wind is curtailed so coal units stay on; Ember says batteries storing midday solar could help. | https://www.downtoearth.org.in/energy/indias-solar-power-cuts-coal-use-in-the-day-but-evening-demand-keeps-fossil-fuel-running |
| F3 | **UPERC FY2026-27 tariff order:** EV charging category **LMV-11** energy charge **₹7.70/kWh (LT)**, ₹7.30/kWh (HT); LMV-11 explicitly covers battery charging stations, battery swapping stations and Battery-as-a-Service; **20% ToD discount 09:00–16:00** for solar-hour charging. | https://powerpeakdigest.com/uperc-retains-fy27-power-tariffs-raises-subsidy-and-expands-ev-benefits/ |
| F4 | MoP EV Charging Guidelines 2024: setting up a charging station is a **de-licensed activity**; each station needs separate metering. | https://www.mercomindia.com/ministry-of-power-releases-ev-charging-infrastructure-guidelines |
| F5 | Bihar e-rickshaw survey (ADRI): **70%** of drivers charge **overnight at private unauthorised stations**; full charge **8–12 h**; drivers travel **80–100 km/day**; lead-acid dominant; new lead-acid set ~₹40,000/yr; charging cost ~₹100/day. | https://www.adriindia.org/images/brochures/1691124443a.pdf |
| F6 | Delhi: official says **>60%** of e-rickshaws involved in power theft via illegal charging; garages charge **₹120–150/day**; electrocution deaths at illegal charging points (2024). | https://www.newslaundry.com/2024/09/14/power-theft-illegal-charging-no-safety-inside-delhis-e-rickshaw-chaos |
| F7 | WRI India (Jul 2025): EV batteries retire at **70–80%** capacity; second life extends total life from **4–8 to 10–15 years**; new pack prices fell 20% to **$115/kWh** in 2024 (narrowing second-life cost advantage); **India lacks specific second-life battery standards**; testing/certification capacity is limited. | https://wri-india.org/perspectives/second-charge-unlocking-second-life-potential-ev-batteries |
| F8 | Battery Waste Management Rules 2022 define **refurbishers** (repurposing used batteries for second life); they must **register** and report on CPCB's portal. | https://lexplosion.in/battery-waste-management-rules-2022-changes-in-the-regime/ |
| F9 | UP rooftop-solar net metering eligibility (2019 regs, 2023 amendment) covers domestic, agricultural and institutional categories — **EV charging (LMV-11) is not listed** → our design uses an **off-grid solar circuit** (no export). | https://solarquarter.com/2023/11/29/uperc-empowers-solar-energy-adoption-with-landmark-amendment-to-rooftop-solar-regulations-2019/ |
| F10 | Varanasi solar output per kW installed (kWh/day): Spring **6.31**, Summer **4.82**, Autumn **4.70**, Winter **3.66** (seasonal averages). | https://profilesolar.com/locations/India/Varanasi/ |
| F11 | Using electricity for a purpose other than the sanctioned one is "unauthorised use" under Section 126, Electricity Act (Bombay HC, 6 Feb 2024, reasoning by analogy for domestic→commercial). | https://www.livelaw.in/pdf_upload/electricity-525280.pdf |

**Unknowns the team must NOT fake** (show as "not yet known / to be confirmed"):
- Current CEA grid emission factor (kg CO₂/kWh) — the team will look it up from the CEA CO₂ Baseline Database and enter it in `config/assumptions.yaml`. If empty, the UI asks for it and hides CO₂ numbers.
- Second-life battery price in ₹/kWh — default is an ASSUMPTION; replace with a refurbisher quote.
- What Varanasi yards pay today and their connection type — FIELD data.

---

## 4. Legal design (why the architecture looks the way it does)

| Element | Status | Design consequence |
|---|---|---|
| Charging yard | Legal, de-licensed (F4) | Yard must have its own **LMV-11** EV connection, not a domestic one (F11). |
| Solar-hour tariff discount | Legal (F3) | Grid tariff is **time-of-day**: ₹6.16 (09:00–16:00), ₹7.70 otherwise. |
| Rooftop solar | No net metering for EV connections (F9) | **Off-grid solar circuit**: PV → battery/rickshaw chargers only. **No export to grid. PV surplus is curtailed** (and reported honestly). |
| Second-life battery | Legal via registered refurbisher (F8) | Battery is **charged only from solar** (config flag `allow_grid_charging_battery: false`). Procure from CPCB-registered refurbisher with grading report. |
| Battery charging from grid | Technically possible, legally fine, but adds no sustainability value and complicates the circuit | Disabled by default; keep as a config flag for "what-if". |

---

## 5. Physical system model

```
             ┌──────────── Rooftop PV (kWp) ────────────┐
             │                                           │
             ▼                                           ▼
   [Battery inverter/charger] ◄──► Second-life battery   (direct PV → chargers)
             │                                           │
             └────────► AC bus to rickshaw chargers ◄────┘
                                  ▲
                                  │  (changeover per charger circuit)
                      PuVVNL grid, LMV-11 meter (import only)
```

Each rickshaw has its own charger (lead-acid 48 V sets in most Varanasi e-rickshaws; some lithium). Per time step the chargers' total power is supplied by: direct PV + battery discharge + grid.

**Simplification (state in README):** chargers are modelled as controllable power sinks with a maximum power; real lead-acid chargers follow a CC-CV profile with tapering in the absorption stage. We do not model the taper.

---

## 6. Data model & input files

### 6.1 `config/assumptions.yaml` (every value tagged)

```yaml
site:
  name: "Demo Yard, Lanka (SIMULATED until FIELD data entered)"
  latitude: 25.26
  longitude: 82.99
  timezone: "Asia/Kolkata"

time:
  step_minutes: 15            # Δt = 0.25 h
  horizon_start: "08:00"      # day D 08:00 → day D+1 08:00 (96 steps)

tariff:                        # SOURCE F3
  lmv11_energy_inr_per_kwh: 7.70
  solar_hour_discount: 0.20
  solar_hours: ["09:00", "16:00"]
  source: "UPERC FY27 order via Power Peak Digest (F3)"

grid:
  sanctioned_load_kw: 10       # ASSUMPTION — replace with FIELD
  allow_grid_charging_battery: false   # legal/design choice, §4

pv:
  kwp: 10                      # team's proposed design
  performance_ratio: 0.78      # ASSUMPTION (used only for GHI→kW conversion from Open-Meteo)
  seasonal_kwh_per_kw_day:     # SOURCE F10 (fallback profile)
    winter: 3.66               # Dec–Feb
    spring: 6.31               # Mar–May
    summer: 4.82               # Jun–Aug
    autumn: 4.70               # Sep–Nov

battery:                       # second-life pack
  original_capacity_kwh: 37.5  # ASSUMPTION: pack was 37.5 kWh new
  soh_start: 0.80              # SOURCE-consistent: EV packs retire at 70–80% (F7) → 30 kWh now
  soh_end_of_life: 0.60        # ASSUMPTION: retire from second life at 60%
  soc_min_frac: 0.10           # ASSUMPTION
  soc_max_frac: 0.95           # ASSUMPTION
  eta_charge: 0.95             # ASSUMPTION (LFP-class)
  eta_discharge: 0.95          # ASSUMPTION → ~90% round trip
  inverter_kw: 6               # ASSUMPTION
  chemistry: "LFP"             # recommended for thermal safety
  price_inr_per_kwh: 5000      # ASSUMPTION — replace with refurbisher quote
  remaining_cycle_life_efc: 2000   # ASSUMPTION — equivalent full cycles to soh_end_of_life
  thermal:
    enclosure_rise_c: 5        # ASSUMPTION: enclosure is 5 °C above ambient
    derate_start_c: 40         # ASSUMPTION
    derate_zero_c: 55          # ASSUMPTION
    full_power_rise_c: 8       # ASSUMPTION: cell temp rise at full inverter power
  ageing:
    k_cycle_per_efc: 0.0001    # ASSUMPTION: SOH loss per equivalent full cycle at 25 °C
    k_calendar_per_year: 0.02  # ASSUMPTION
    arrhenius_doubling_c: 10   # ASSUMPTION: ageing doubles per +10 °C above 25 °C

capex_inr:                     # calibrated so 10 kWp + 30 kWh ≈ team estimate ₹6.8–8.3 lakh
  pv_per_kwp: 45000            # ASSUMPTION — replace with installer quote
  battery_per_kwh: 5000        # = battery.price_inr_per_kwh
  inverter_bos_safety_fixed: 120000   # ASSUMPTION (hybrid inverter, BOS, fire safety, enclosure)
  om_per_year: 10000           # ASSUMPTION

impact:
  grid_emission_factor_kg_per_kwh: null   # TEAM MUST FILL from CEA CO2 Baseline Database
```

### 6.2 `data/fleet/rickshaws.json` (SIMULATED demo, replace with FIELD)

```json
{
  "label": "SIMULATED — 10-rickshaw demo yard; replace with FIELD data",
  "rickshaws": [
    {"id": "R01", "driver": "Driver A", "battery": "lead-acid 48V 120Ah", "energy_needed_kwh": 6.0, "charger_max_kw": 1.0, "arrive": "19:30", "depart": "06:30", "midday_window": null},
    {"id": "R02", "driver": "Driver B", "battery": "lead-acid 48V 100Ah", "energy_needed_kwh": 5.0, "charger_max_kw": 0.9, "arrive": "20:00", "depart": "06:00", "midday_window": ["13:00", "14:30"]},
    {"id": "R03", "driver": "Driver C", "battery": "lithium 51V 105Ah", "energy_needed_kwh": 5.2, "charger_max_kw": 1.5, "arrive": "21:00", "depart": "07:00", "midday_window": null}
  ]
}
```
Generate the remaining 7 with a seeded random generator: `energy_needed_kwh` ∈ [4.5, 6.5] (ASSUMPTION: 48 V, 100–120 Ah lead-acid ≈ 4.8–5.8 kWh nominal, plus charger losses), `arrive` ∈ [19:00, 22:30], `depart` ∈ [05:30, 07:30], 30% of them get a midday window of 60–90 min between 12:00 and 15:30 (ASSUMPTION — to be verified with drivers).

### 6.3 Solar input (three sources, in priority order)

1. **PVGIS hourly CSV (preferred, real data).** Team downloads from https://re.jrc.ec.europa.eu/pvg_tools/en/ → "Hourly data", lat 25.26, lon 82.99, PV power output for 1 kWp, save as `data/solar/pvgis_varanasi_hourly.csv`. Loader: skip metadata lines until the header containing `time`; parse `time` as `%Y%m%d:%H%M` in **UTC**, convert to IST (+05:30); column `P` is in **W for the configured kWp** → convert to kW per kWp. Build a **monthly average day** (24 h profile per month) and resample to 15 min.
2. **Open-Meteo forecast (live "tomorrow" plan, optional).**
   `https://api.open-meteo.com/v1/forecast?latitude=25.26&longitude=82.99&hourly=shortwave_radiation,temperature_2m&timezone=Asia%2FKolkata&forecast_days=2`
   PV kW ≈ `kwp × GHI/1000 × performance_ratio` (state: horizontal GHI approximation). Use `temperature_2m` as ambient for the thermal model. Cache the last response to `data/solar/openmeteo_cache.json`; fall back to it offline.
3. **Synthetic fallback (always available offline).** Half-sine between sunrise and sunset (use 06:00–18:00 if no table), scaled so the daily energy equals `kwp × seasonal_kwh_per_kw_day[season]` (F10). Ambient temperature profile: sinusoid, monthly mean/amplitude ASSUMPTION table (e.g. May mean 34 °C ±7, Jan mean 16 °C ±6). Label "SYNTHETIC".

### 6.4 Field data templates (`data/field/`) — the team fills these in Saturday evening

`yards.csv`: `yard_id, owner_name_or_initials, consent(Y/N), area, rickshaws_per_night, connection_type(domestic/commercial/LMV-11/unknown), monthly_bill_inr, fee_per_driver_per_night_inr, plug_in_time_typical, leave_time_typical, roof_area_m2, notes, quote`

`drivers.csv`: `driver_id, name_or_initials, consent, battery_type, battery_age_months, km_per_full_charge, charge_location, charge_fee_inr, plug_in_time, leave_time, midday_break(Y/N, when), would_charge_daytime_if_cheaper(Y/N), quote`

The **Field Evidence** page (§9) reads these and shows summary stats + quotes. If files are empty, show "Field data pending" — never fill with fake people.

---

## 7. The core algorithm — wear- and heat-aware LP dispatch

This is the centrepiece for the **Solution** score. Implement in `core/dispatch.py` with **PuLP** (bundled CBC solver). One horizon = 96 steps of Δt = 0.25 h, from 08:00 day D to 08:00 day D+1.

### 7.1 Sets & parameters
- `T` = time steps 0..95; `I` = rickshaws.
- `PV[t]` (kW) solar available; `c[t]` (₹/kWh) grid tariff (₹6.16 in 09:00–16:00, else ₹7.70).
- `avail[i,t]` ∈ {0,1}: rickshaw i plugged in (night window arrive→depart, plus optional midday window).
- `E[i]` kWh needed; `Pmax[i]` kW charger limit.
- `Cap = original_capacity × SOH` (kWh); `SOCmin = soc_min_frac × Cap`; `SOCmax = soc_max_frac × Cap`.
- `ηc, ηd`; `Pinv` inverter kW; `Gmax` sanctioned load kW.
- `derate[t]` ∈ [0,1] from the thermal model (§7.4); `Pbat[t] = Pinv × derate[t]`.
- **Wear cost** `c_wear = (price_inr_per_kwh × Cap) / (Cap × remaining_cycle_life_efc) = price_inr_per_kwh / remaining_cycle_life_efc` ₹ per kWh discharged (defaults: 5000 / 2000 = ₹2.50/kWh). Interpretation: the pack can deliver roughly Cap × EFC kWh over its second life, so each kWh discharged uses up that fraction of its purchase cost. Expose battery price as a slider in the UI.
- `M` = 1000 ₹/kWh penalty for unmet rickshaw energy.

### 7.2 Decision variables (all ≥ 0, continuous)
- `x[i,t]` kW to rickshaw i
- `pv_bat[t]` PV → battery (kW, DC-side input)
- `pv_load[t]` PV → chargers directly (kW)
- `curt[t]` PV curtailed (kW)
- `dis[t]` battery → chargers (kW, AC-side output)
- `g[t]` grid → chargers (kW)
- `soc[t]` for t = 0..96 (kWh)
- `u[i]` unmet energy for rickshaw i (kWh)

### 7.3 Constraints
1. PV split: `pv_bat[t] + pv_load[t] + curt[t] = PV[t]`
2. Charger balance: `Σ_i x[i,t] = pv_load[t] + dis[t] + g[t]`
3. Battery dynamics: `soc[t+1] = soc[t] + ηc·pv_bat[t]·Δt − dis[t]·Δt/ηd`
4. SOC bounds: `SOCmin ≤ soc[t] ≤ SOCmax`
5. Battery power (heat-aware): `pv_bat[t] ≤ Pbat[t]`, `dis[t] ≤ Pbat[t]`
6. Grid limit: `g[t] ≤ Gmax`
7. Charger limit & availability: `x[i,t] ≤ Pmax[i]·avail[i,t]`
8. Energy delivery: `Σ_t x[i,t]·Δt + u[i] ≥ E[i]` and `Σ_t x[i,t]·Δt ≤ E[i]`
9. Initial / terminal SOC:
   - *Operational mode:* `soc[0] = SOC from telemetry`; `soc[96] ≥ SOCmin`.
   - *Sizing mode (representative days):* cyclic `soc[96] ≥ soc[0]`, `soc[0]` free within bounds.
10. No grid → battery path exists (design, §4). If `allow_grid_charging_battery` is true, add `g_bat[t]` with tariff cost and include it in (3) and in the grid limit.

No binary variables are needed: simultaneous charge/discharge is never optimal because of round-trip losses and wear cost.

### 7.4 Objective
```
minimise   Σ_t c[t]·g[t]·Δt   +   c_wear·Σ_t dis[t]·Δt   +   M·Σ_i u[i]
```
Behaviour judges should see: the old battery is cycled **only when grid cost avoided > wear cost**. Demo this with the wear-cost slider (raise battery price → battery sits idle, grid use rises).

### 7.5 Thermal model & derating (sequential linearisation, 2–3 iterations)
- Enclosure temperature: `T_enc[t] = T_amb[t] + enclosure_rise_c`.
- Iteration 0: `T_cell[t] = T_enc[t]` → `derate[t] = f(T_cell[t])` where `f(T) = 1` if T ≤ 40; `(55 − T)/15` if 40 < T < 55; `0` if T ≥ 55.
- Solve LP. Then post-simulate: `T_cell[t] = T_enc[t] + full_power_rise_c × (pv_bat[t] + dis[t]) / Pinv`.
- Recompute `derate[t]` from new `T_cell`, re-solve. Stop when max change in derate < 0.01 or after 3 iterations. Report iterations and final peak cell temperature.
- UI: show `T_cell[t]` line with shaded derate zone; show "Thermal limit active at hh:mm" if derate < 1.
- **Label: SIMULATED, first-order steady-state approximation, not a validated thermal model.**

### 7.6 Battery health (SOH) update — daily
```
EFC_day   = Σ_t dis[t]·Δt / Cap                      # equivalent full cycles
A(T)      = 2 ** ((T_cell_avg_day − 25) / arrhenius_doubling_c)
ΔSOH_day  = k_cycle_per_efc · EFC_day · A(T) + (k_calendar_per_year / 365) · A(T)
SOH_next  = SOH − ΔSOH_day
```
Project years to `soh_end_of_life`. Label: "simplified empirical model; parameters are assumptions; real second-life packs need measured capacity tests".

### 7.7 Baseline (for comparison) — same LP with `PV = 0` and no battery
Gives baseline grid kWh and ₹ (all rickshaws charged from grid). Everything we report is **relative to this baseline**, never to an invented number.

### 7.8 Outputs per day (dict → JSON → UI)
- per-rickshaw schedule `x[i,t]`, source stack (pv_load, dis, g), `soc[t]`, `T_cell[t]`, `derate[t]`
- `energy_to_rickshaws_kwh`, `solar_direct_kwh`, `solar_via_battery_kwh` (= Σ dis·Δt), `grid_kwh`, `curtailed_kwh`
- `solar_share = (solar_direct + solar_via_battery) / energy_to_rickshaws`
- `grid_cost_inr`, `baseline_cost_inr`, `wear_cost_inr`, `net_saving_inr = baseline − grid_cost − wear_cost`
- `co2_avoided_kg = (baseline_grid_kwh − grid_kwh) × EF` (only if EF set)
- `peak_grid_kw`, `unmet_kwh` per rickshaw (must be 0 when feasible; otherwise show red warning naming the rickshaw)
- `EFC_day`, `SOH_next`, thermal iterations, peak `T_cell`

---

## 8. Sizing & payback (the honesty engine — Practicality score)

`core/sizing.py`:
- Grid search: `kwp ∈ {4, 6, 8, 10, 12}` × `battery_kwh_now ∈ {0, 15, 30, 45, 60}` (25 combos).
- For each combo, solve the LP in **sizing mode** for **12 representative days** (one average day per month, from PVGIS monthly profile or seasonal fallback). Annual savings = Σ_m days_in_month × net_saving_m.
- `capex = pv_per_kwp × kwp + battery_per_kwh × battery_kwh + inverter_bos_safety_fixed` (fixed cost only if battery or PV > 0).
- `simple_payback_years = capex / (annual_net_saving − om_per_year)` (show "never" if ≤ 0).
- `years_to_battery_EOL` from the SOH model with that combo's annual EFC → **flag combos where the battery dies before payback** ("battery replacement needed before payback").
- Also report `annual_solar_share`, `annual_curtailed_kwh`, `annual_co2_avoided_kg`.
- Show a **heatmap of payback** and a **heatmap of solar share**, and mark the team's proposed design (10 kWp + 30 kWh). Recommend the combo with best payback **subject to** solar share ≥ target (slider, default 50%).
- Use `@st.cache_data` so the sweep runs once (~300 small LPs; should finish in well under a minute).

**Known result to expect (sanity check, do not hard-code):** a 30 kWh pack can deliver at most ~24 kWh/night (30 × 0.85 usable × ~0.9 round trip ≈ 23 kWh), so with 10 kWp (~40–45 kWh/day) roughly 15–20 kWh/day is curtailed unless rickshaws charge midday. At ₹7.70 that is ≈ ₹185/day ≈ ₹67,500/yr gross, i.e. **payback of ~10–12 years on ₹6.8–8.3 lakh — NOT 3–5 years.** Even if all 45 kWh/day were used, 45 × 7.70 × 365 ≈ ₹1.26 lakh/yr → 5.4–6.6 years. The tool must surface this and show which right-sized combos do better. This honesty is a feature, not a bug.

---

## 9. App (Streamlit multipage + a static driver page)

Run: `streamlit run app/Home.py`. Use Plotly for charts. Clean, high-contrast, large fonts (projector-friendly). A persistent banner on every page: **"Telemetry SIMULATED · Tariff SOURCE: UPERC FY27 · Solar: PVGIS / Open-Meteo / synthetic"** (show whichever is active).

1. **Home / Tonight's Plan** (the live demo screen)
   - KPI tiles: Solar share % · Grid kWh tonight · ₹ net saving vs baseline · Rickshaws ready by departure (x/10) · CO₂ avoided (or "enter CEA factor").
   - Stacked area: power to chargers by source (PV direct / battery / grid) over 08:00→08:00, tariff shaded (solar hours).
   - SOC line of the second-life battery.
   - Gantt / heat strip: each rickshaw's charging power over time, departure markers.
   - Controls: solar source (PVGIS month / Open-Meteo tomorrow / synthetic season), cloudy-day factor slider (0.3–1.0), battery price (wear cost) slider, sanctioned load slider, "add a rickshaw" form.
2. **Battery Health & Safety**
   - SIMULATED module telemetry for 8 modules: temperature and internal resistance (IR) time series; generator drifts one module's IR upward over days.
   - Anomaly rules: module IR > 1.3 × median of modules → "Inspect module"; T_cell > 50 °C → "Over-temperature"; z-score > 3 on any module temp → "Outlier". Show alert list with timestamps.
   - Thermal derating chart (T_cell vs derate) and SOH projection to end-of-life (years).
3. **Sizing & Payback** — heatmaps (§8), recommended combo, proposed design highlighted, honest flags.
4. **Impact** — daily/annual solar share, kWh shifted from night grid to stored sun, kWh curtailed, CO₂ avoided (if EF set), second-life kWh in service, and the F2 day-vs-night fossil context chart (two bars: 125 GW at 1 pm vs 168 GW 5 pm–7 am, cite Ember/DTE).
5. **Field Evidence** — reads `data/field/*.csv`; shows counts, medians (fee/night, rickshaws/yard, plug-in/leave times), connection-type breakdown, and quotes. "Field data pending" if empty.
6. **Assumptions & Sources** — table of every parameter with value and tag (SOURCE/FIELD/ASSUMPTION + URL). Editable in UI for what-if (session only).

**Driver page (Practicality: cheap phone, patchy network):** `driver/index.html` generated by `core/export_driver.py` — a single static Hindi page < 50 KB, no JS framework, listing each rickshaw's slot, e.g.
`R02 — आज रात चार्जिंग: 20:00–02:15 · प्रस्थान 06:00 तक पूरा चार्ज · आज की बिजली: 68% धूप से ☀️ · शुल्क: ₹___` (fee from FIELD data or blank). Also generate a plain-text SMS/WhatsApp-style summary per driver (`driver/messages.txt`). Link both from the Home page.

---

## 10. Repository structure

```
pragna-solaryard/
├── README.md                    # §11
├── requirements.txt
├── config/assumptions.yaml
├── data/
│   ├── fleet/rickshaws.json            # SIMULATED (+ generator)
│   ├── solar/pvgis_varanasi_hourly.csv # team downloads (optional)
│   ├── solar/openmeteo_cache.json      # auto-cached
│   └── field/yards.csv, drivers.csv    # FIELD (templates with headers only)
├── core/
│   ├── config.py        # load yaml, tagging helpers
│   ├── solar.py         # PVGIS loader, Open-Meteo client+cache, synthetic profile
│   ├── fleet.py         # load/generate rickshaws, availability matrix
│   ├── tariff.py        # ToD tariff vector
│   ├── thermal.py       # derate f(T), post-sim T_cell
│   ├── dispatch.py      # LP (§7) + iteration loop + baseline
│   ├── health.py        # SOH model, simulated module telemetry, anomaly rules
│   ├── sizing.py        # grid search, payback (§8)
│   ├── metrics.py       # KPI calculations
│   └── export_driver.py # Hindi static page + messages
├── app/
│   ├── Home.py
│   └── pages/ 2_Battery_Health.py 3_Sizing_Payback.py 4_Impact.py 5_Field_Evidence.py 6_Assumptions.py
├── driver/              # generated
└── tests/
    ├── test_dispatch.py
    └── test_sizing.py
```

`requirements.txt` (pin exact versions you install): `streamlit`, `pulp`, `pandas`, `numpy`, `plotly`, `pyyaml`, `requests`, `pytest`.

### Tests (must pass before each commit)
- Energy balance: for every t, `Σx = pv_load + dis + g` within 1e-6; PV split holds.
- SOC within bounds; `soc[t+1]` recursion holds.
- All rickshaws fully charged when feasible (`u = 0`); infeasible case (Gmax = 1 kW) produces `u > 0` and a named warning, not a crash.
- No grid-to-battery flow when flag is false.
- `derate = 0` at ≥ 55 °C ⇒ `dis = pv_bat = 0` at those steps.
- Optimised cost ≤ baseline cost.
- Raising wear cost above max tariff ⇒ battery discharge ≈ 0.
- Sizing: PV = 0 & battery = 0 ⇒ saving 0 ⇒ payback "never".

---

## 11. README.md (the jury reads the repo at submission — make it excellent)

Sections, in this order:
1. **One-line pitch** + problem statement (§2).
2. **Who has the problem** — named yard(s)/drivers from FIELD data (with consent), plus F1, F5, F6.
3. **Evidence** — table of FIELD findings + SOURCE facts with links (§3).
4. **What we built** — screenshots/GIF of each page; how to run (`pip install -r requirements.txt && streamlit run app/Home.py`).
5. **How it works** — the LP (§7) in plain words + equations; thermal derating; SOH model; sizing.
6. **Legal design** — table from §4.
7. **Practicality** — ₹ capex/payback from the sizing tool (actual output), offline-capable, driver page < 50 KB for cheap phones.
8. **Data provenance** — SIMULATED vs FIELD vs SOURCE vs ASSUMPTION.
9. **What didn't work / limitations** (honest): e.g. lead-acid CC-CV taper not modelled; thermal & SOH models are simplified; second-life price is an assumption; payback of the original 10 kWp + 30 kWh design is ~10–12 years, not 3–5; PV surplus curtailed because EV connections can't net-meter; no real BMS data.
10. **Next steps** — pilot at one Varanasi yard with real BMS logs; refurbisher partnership (CPCB-registered); PuVVNL confirmation of off-grid solar on LMV-11; multi-yard aggregation later.
11. **Team** — who did what. **Progress log** — what changed at each check-in (timestamps).

---

## 12. Build order & milestones (map to check-ins)

Commit after each milestone. Keep the app runnable at every commit.

**M1 — before Check-in 1 (Sat evening):**
- Repo scaffold, `assumptions.yaml`, fleet generator, tariff, synthetic solar.
- `dispatch.py` LP working (without thermal iteration) + baseline + tests 1–3, 6.
- Home page: KPI tiles + source stack chart + SOC line from one simulated night.
- Field templates created; README skeleton with problem statement and plan.
- *Show mentors:* the written plan (this milestone list) + first working dispatch.

**M2 — overnight → Check-in 2 (Sun morning):**
- Thermal derating iteration, wear cost slider, SOH model.
- PVGIS loader (if CSV available) + Open-Meteo with cache.
- Battery Health page with simulated module telemetry + anomaly alerts.
- Field Evidence page wired to real CSVs (team enters interviews).
- Remaining tests.

**M3 — Check-in 3 (Sun ~12:00):**
- Sizing & Payback page (heatmaps, honest flags).
- Impact page, Assumptions page, driver Hindi page + messages export.
- README complete with screenshots, limitations, progress log.
- 3-minute demo rehearsed on the Home page.

**Freeze (Sun 14:00):** final commit, tag `v1.0-submission`. No new features after Check-in 3 — only bug fixes and README.

**If time runs short, cut in this order (last = cut first):** Open-Meteo live forecast → Impact page polish → driver messages.txt → sizing grid resolution (use 3×3). **Never cut:** working LP dispatch, Home demo, honest README, field evidence.

---

## 13. Demo script (3 minutes, Home page)

1. (20 s) "This is [yard owner], [area]. Ten rickshaws charge here every night on [connection]." (FIELD)
2. (20 s) Impact page context: 125 GW fossil at 1 pm vs 168 GW at night (F2) — "electric isn't clean yet".
3. (60 s) Home: tonight's plan — stacked chart shows sun → battery by day, battery → rickshaws first at night, grid only to top up; all 10 ready by departure; solar share X%. Move **cloudy-day slider** → plan adapts, still meets every departure.
4. (30 s) Raise **battery price slider** → wear cost exceeds savings → scheduler stops cycling the old pack. "We only use the second-life battery when it's worth the wear." Battery Health page: module anomaly alert + thermal derating.
5. (30 s) Sizing page: honest payback heatmap; "our original 10 kWp + 30 kWh pays back in ~X years; right-sized design Y does better." Legal design: off-grid solar on an LMV-11 connection.
6. (20 s) Driver Hindi page on a phone. Close with ask/next step.

### Elevator pitch (fill brackets from real outputs)
> "Uttar Pradesh has 8.6 lakh registered e-rickshaws, and most charge at night — when India's grid burns the most fossil fuel, 168 GW versus 125 GW at 1 pm — so Varanasi's 'clean' rickshaws largely run on coal. Pragna turns a yard's roof into a night-time power station: panels bank midday sun in a second-life EV battery, and our wear-aware scheduler charges every rickshaw by dawn, cycling the old battery only when the saving is worth the wear. Each node moves about [Y] kWh of sunshine into the night — [₹Z] a day at UP's ₹7.70 EV tariff and [X] kg of CO₂ — and [yard owner] told us today: '[quote]'."

---

## 14. Expected judge questions & defences

| Question | Defence (keep honest) |
|---|---|
| "Your payback is too long." | "Yes — our own tool shows the 10 kWp/30 kWh design is ~10–12 years because the battery caps night delivery; right-sizing to [combo] gives [n] years. Our priority is moving rickshaw charging off night-time fossil power; the tool makes the economics transparent." |
| "Where do second-life packs come from? Are they cheaper?" | "From CPCB-registered refurbishers with grading reports (BWMR 2022). New packs fell to $115/kWh (WRI), so second-life only wins if cheaper per stored kWh — the wear-cost slider shows exactly where it stops paying. The software works with new LFP too." |
| "Thermal runaway in a hot Varanasi summer?" | "LFP chemistry, cell-level temperature monitoring, ventilated separated enclosure; our scheduler derates power from 40 °C to zero at 55 °C and flags modules with rising internal resistance. Thresholds are assumptions to be set from the pack datasheet." |
| "Is this legal?" | "Charging stations are de-licensed (MoP 2024); yard uses an LMV-11 EV connection; solar runs on an off-grid circuit because UP net metering doesn't cover EV connections; no export; batteries via registered refurbishers. We'll confirm the off-grid arrangement with PuVVNL." |
| "Yards today pay less — they use domestic or stolen power." | "That's unauthorised use (Sec. 126). Our model assumes a legal connection; the benefit is formalisation + clean energy, and we show cost vs the legal baseline." |
| "Lead-acid can't be fast-charged / CC-CV taper?" | "Correct — we schedule within each charger's max power over 8–12 h windows; taper is not modelled (listed limitation)." |
| "Why not swap spare rickshaw batteries charged by day?" | "Valid alternative. Spare lead-acid sets are heavy, cost ~₹40k/yr each (ADRI) and wear fast; a stationary second-life pack serves the whole yard. We'd compare ₹/kWh delivered in a pilot." |
| "Is the data real?" | "Tariffs, fleet scale, grid mix and solar yield are sourced; yard data is from our interviews today; battery telemetry is simulated and labelled." |
| "Why is this a startup and not a one-off?" | "Pragna already builds second-life storage + demand management for solar homes; yards are a large, predictable night load — the same stack, a new market." |

---

## 15. Definition of done

- [ ] `streamlit run app/Home.py` works offline on a fresh laptop.
- [ ] LP schedules 10 rickshaws, all ready by departure, in < 2 s.
- [ ] Wear-cost and cloudy-day sliders visibly change the plan.
- [ ] Thermal derating and SOH projection shown, labelled SIMULATED.
- [ ] Sizing heatmap shows honest payback incl. the proposed design.
- [ ] Field Evidence page shows real interviews (names only with consent).
- [ ] Every number in the UI is tagged SOURCE / FIELD / ASSUMPTION / SIMULATED.
- [ ] Hindi driver page < 50 KB.
- [ ] All tests pass; README complete with limitations and progress log; tagged `v1.0-submission`.