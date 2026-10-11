# ChargeFlow: smart overnight charging for e-rickshaw garages

**Every rickshaw charged by morning, without overloading the building's supply.**

SHIFT Sustainable e-Micromobility Hackathon · IIT (BHU) Varanasi · 10–11 October 2026

ChargeFlow decides when each e-rickshaw charger switches on overnight. It keeps the garage within its sanctioned electricity load, makes sure every rickshaw is charged before its driver leaves, and uses rooftop solar with a second-life battery to cover part of the night's power.

> **Submission status:** a working prototype. The planner, dashboard and simulations run; the hardware pilot has not started. All fleet results are **simulated** and labelled as such in the app.

## The problem

- About ten drivers in one owner's quarters plug in at the same time. Together their chargers can exceed the building's sanctioned load. Breakers trip, wiring overheats, and chargers keep running on full batteries all night where people sleep.
- In our Varanasi field visit, seven of nine drivers rent their rickshaw by the day with charging included, so the garage owner pays the electricity bill.
- India's e-rickshaws mostly charge overnight, when the grid runs mostly on fossil fuel (about 168 GW of evening demand against 125 GW at 1 pm, per Ember via [Down To Earth](https://www.downtoearth.org.in/energy/indias-solar-power-cuts-coal-use-in-the-day-but-evening-demand-keeps-fossil-fuel-running)). Uttar Pradesh alone has **8,60,054** registered e-rickshaws ([Rajya Sabha, March 2025](https://rsdebate.nic.in/bitstream/123456789/757555/1/PQ_267_12032025_U1536_p379_p383.pdf)).

## Our solution

- **Smart plug per charger.** A smart plug or relay switches each charger. The charger itself is unchanged.
- **Least Laxity First scheduling.** Every 15 minutes, ChargeFlow calculates the free power within the sanctioned load and switches on the rickshaws with the least time to spare. A rickshaw that can no longer make its departure moves to the back of the queue, so an overloaded night still gets as many rickshaws ready as possible.
- **Solar and second-life storage.** Rooftop panels charge a stationary battery built from retired EV cells during the day. At night the battery covers whatever the grid cannot supply within the sanctioned load.
- **Live re-planning.** Real nights differ from the plan. Every 15 minutes ChargeFlow re-plans the rest of the night from what it can measure: who is plugged in, each battery's charge, the storage level, and the sun so far. It uses a live solar forecast when online.
- **Battery health.** A simple check from range: km per full charge now against when new. It tells the owner which packs are good, which can move to second-life storage, and which to replace.

## What the prototype does

| Feature | Where |
|---|---|
| Overnight plan for a garage: readiness, peak demand against the sanctioned load, grid cost | 01 Outcome |
| Grid load through the night, and the charging schedule per rickshaw | 02 Analysis |
| Live re-plan: play the night, add surprises, see the plan change | 02 · Live re-plan |
| Solar generation, power by source, second-life pack, and battery behaviour | 03 Supporting analysis |
| Battery health from range, with replacement and second-life advice | 03 · Battery health |
| Fleet editor, including the seven renting drivers from our field visit (field preset) | 03 · Fleet data |
| Smart-plug CSV import: measured peak and overload, then plan the same vehicles | 03 · Fleet data |
| 30 nights in a row with real Varanasi sunshine | 04 · 30 nights |
| Stress test: a tight night with supply cut-outs | Masthead button |
| Method dialog and CSV export of the schedule | Masthead |

## Results (simulated, from our field data)

| Scenario | Result |
|---|---|
| Field garage (7 renting drivers), 7 kW supply | Peak **8.5 kW** uncontrolled, **6.6 kW** with ChargeFlow. All 7 ready by departure. |
| Field garage, one night's grid cost | ₹318 uncontrolled, **₹233** with ChargeFlow + solar at ₹6.5/kWh |
| Stress test: 12 rickshaws, 7 kW, supply cuts out on overload | Ready by departure: uncontrolled **0 of 12** (19 cut-outs), ChargeFlow on the grid **6 of 12** (no cut-outs), ChargeFlow + solar **12 of 12** |
| Live re-plan, one "messy" night (a no-show, a late arrival, an early departure, a cloudier morning) | Re-planning **9 of 9** ready, against **8 of 9** for the 18:00 plan followed blindly |
| 30 nights, last 30 days of Varanasi sunshine, 10 rickshaws | Uncontrolled charging exceeds the sanctioned load on **all 30 nights**. ChargeFlow on the grid alone: grid cost ₹11,469 for the month. With solar and storage: **₹9,214**, saving ₹2,255. Every rickshaw ready on 29 of 30 nights. |

These are model results. The fleet data is from one field visit and is partly assumed (see below). We have not yet measured anything on a real garage.

## How we know which numbers are what

| Label | Meaning | Examples |
|---|---|---|
| FIELD | What drivers told us in Varanasi (approximate, one visit) | start and end times, battery type, rent, the seven-driver preset |
| DERIVED | Calculated from field data | charger power from the reported full-charge time |
| ASSUMPTION | Engineering assumption, shown in the app | pack sizes, 20% charge on arrival, household load, 7 kW supply, 0.78 solar performance ratio |
| SOURCE | Public data with a link | Open-Meteo sunshine (live forecast and last 30 days), UPERC tariffs, Rajya Sabha count |
| SIMULATED | Generated by the model | every result above, the sample smart-plug log, the stress night |
| PROJECTED | Economics that depend on assumptions | `docs/hackathon/Unit_Economics_Projected.docx` |

## Run it

ChargeFlow is the main submission.

```bash
cd chargeflow
pip install -r requirements.txt
streamlit run app.py
```

It works offline. Live solar forecast and 30-night sunshine need internet; without it the app uses the sidebar weather and says so.

## Tests

`chargeflow/tests/test_live.py` checks the re-planner: that restarting mid-night from a measured state reproduces the full plan, that the plan never exceeds the sanctioned load, that surprises are logged, and that re-planning does no worse than the fixed plan. Run with `pytest` (not in `requirements.txt`).

## Repository layout

- `chargeflow/`: the ChargeFlow app.
  - `scheduler.py`: battery and charger models, and the strategies (uncontrolled, Least Laxity First, solar and storage).
  - `live.py`: solar forecast, rolling re-plan and surprise scenarios.
  - `month.py`: 30-night runs with real sunshine.
  - `health.py`: battery health. `import_log.py`: smart-plug CSV import.
  - `app.py`, `ui.py`, `charts.py`: the Streamlit dashboard, design system and charts.
- `docs/hackathon/`: raw field notes, the field findings report and deck, and the unit economics reports (base, best case, projected).
- `core/`, `app/Home.py`, `tests/`, `config/`, `data/`: an earlier, separate prototype by the team: a linear-programming dispatch with PuLP and CBC that plans the same yard from a synthetic solar profile. It is not used by the ChargeFlow app. Its dependencies are in the top-level `requirements.txt`.

## Limitations

- The fleet, batteries and results are simulated, built from one field visit with assumed values.
- No hardware has been installed or tested. The smart-plug control is modelled, not connected.
- Lead-acid charging is simplified as a constant-current charge with a taper near full. The model does not include temperature effects.
- Solar uses a performance factor of 0.78, not a site survey. Roof area and shading are not modelled.
- Battery health comes from range estimates, which depend on load and route. A capacity test is needed to confirm them.
- The economics in the projected report rest on assumptions listed inside it.

## Future scope (beyond the hackathon)

These steps come after the hackathon and are not part of this submission.

1. **Hardware pilot:** one garage, about four weeks. Smart plugs or relays (ESP32, Tasmota or Shelly) on each charger, sending power readings over MQTT. The pilot replaces our assumptions with measured data on peak load, cost and battery wear.
2. **Time-of-day tariff:** a linear-programming schedule that also uses the time-of-day tariff.
3. **Battery health with real data:** per-pack health tracking from measured capacity, not range estimates.
4. **Arrival prediction:** from each driver's own history of plug-in and departure times.
5. **Driver interface in Hindi:** a simple view and messages for drivers.
6. **Subsidies and utility:** check eligibility for PM Surya Ghar (rooftop solar) and talk to the local distribution utility about metering and net billing.
7. **Packaging for owners:** a controller and smart plugs as a monthly service, with a pay-if-it-saves trial.

## Project documents

- Field notes: [`docs/hackathon/field_notes_raw.txt`](docs/hackathon/field_notes_raw.txt)
- Field findings report: [`docs/hackathon/Field_Findings_Varanasi.docx`](docs/hackathon/Field_Findings_Varanasi.docx)
- Pitch deck: [`docs/hackathon/ChargeFlow Field Findings, Varanasi.pptx`](docs/hackathon/ChargeFlow%20Field%20Findings,%20Varanasi.pptx)
- Unit economics: [`base`](docs/hackathon/Unit_Economics_Feasibility.docx), [`projected`](docs/hackathon/Unit_Economics_Projected.docx)

## Build history

- Feasibility study and field visit to Varanasi.
- Prototype planner with Least Laxity First scheduling, lead-acid and lithium models.
- Solar and second-life storage, battery health, smart-plug import.
- Live re-planning with a solar forecast; 30-night runs; stress test; judge-facing review.
