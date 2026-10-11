# ChargeFlow

Smart overnight charging for an e-rickshaw cluster: every rickshaw charged by morning,
without going over the building's sanctioned load.

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\streamlit run app.py
```

## Files

- `scheduler.py`: battery/charger model and the strategies (uncontrolled, Least Laxity First smart schedule, smart + solar storage). No UI code, so it can be tested and extended on its own.
- `live.py`: live re-planning: the Open-Meteo solar forecast, the rolling 15-minute re-plan from the measured state, and the surprise scenarios. `tests/test_live.py` checks it.
- `app.py`: state, layout and wiring of the Streamlit dashboard.
- `ui.py`: design system (tokens, type, spacing, motion) and the custom HTML parts: headline figures with the readiness bars and the sanctioned-load gauge, the data strip, the schedule timeline and the energy-flow schematic, plus a small motion runtime that tweens numbers and bars from their previous values and records the reduced-motion preference.
- `charts.py`: Plotly figures styled to the design system, including the two-panel load chart (grid draw over chargers drawing power).
- `.streamlit/config.toml`: warm paper theme; Inter, Inter Tight and IBM Plex Mono.

Layout: 01 Outcome (readiness, peak demand vs sanctioned load), 02 Analysis (load profile, charging schedule, live re-plan), 03 Supporting analysis (solar and storage, battery behaviour, fleet data). Parameters live in the sidebar.

Colour roles: cobalt is the ChargeFlow plan being viewed and grid power; graphite is always uncontrolled charging; amber is only the sanctioned-load threshold; vermilion only marks a violation; yellow is solar; teal is the second-life pack.

Note for development: Streamlit sometimes reruns `app.py` before reloading an edited `ui.py` or `charts.py`; restart the server after editing those.

## How the smart schedule works

Each charger sits behind an on/off switch (smart plug or relay). Every 15 minutes:

1. Free power = sanctioned load × 95% − household load.
2. Rank plugged-in rickshaws by laxity = time until departure − charging time still needed.
3. Switch on the least-slack rickshaws until the free power runs out. A rickshaw that can no longer make its target goes to the back of the queue, so overloaded nights still get as many rickshaws ready as possible.
4. Switch a charger off when its pack reaches the target.

## Solar + second-life storage

Rooftop panels charge a stationary pack built from retired EV cells while the drivers are out
(the simulation runs from 06:00 to 12:00 the next day). At night the pack first covers
anything the grid can't supply within the sanctioned load, then spreads its remaining energy
across the night so it is empty again for the next day's sun. The smart schedule adds the power
the pack can supply to its headroom, so the same grid connection charges more rickshaws.

## Live re-plan

Real nights don't follow the plan: a driver doesn't come, arrives late or leaves early, and
tomorrow's sun differs from the forecast. ChargeFlow therefore never commits to one plan for the
whole night. Every 15 minutes it re-plans the rest of the night from what it can measure now
(who is plugged in, each pack's charge, the storage level, the sun so far), carries out only the
next 15 minutes, then measures and re-plans again (a receding horizon, as in model predictive control).

- **Solar forecast**: hourly irradiance for Varanasi from [Open-Meteo](https://open-meteo.com) (free, no key),
  converted to panel output as kWp × irradiance ÷ 1000 W/m² × 0.78 performance ratio. Falls back
  to the sidebar weather when offline. Solar-first charging waits less as the forecast gets cloudier.
- **Nowcast**: from 08:00, the last hour of measured sun against the forecast scales the rest of the morning.
- **Late drivers**: a driver more than 1 h late is planned without, and comes back into the plan on plugging in.
- **Departures**: the controller plans for each driver's stated departure; an early leave is known only when they unplug.

The **Live re-plan** view plays the night on a clock. Add surprises (no-show, late, early,
cloudier or sunnier morning, or "Messy night" for all four) and watch the plan change. The
re-plan log lists what changed and what the new plan expects. At the end, re-planning is compared
with the 18:00 plan followed blindly. On the default random night with all four surprises,
re-planning gets 9 of 9 ready against 8 of 9, with neither going over the sanctioned load.

This is a rolling planner driven by a forecast and live state, shown here with a simulator. It
reacts to changes; it doesn't learn or predict them from history. In a real garage the state
would come from metered smart plugs (for example ESP32 relays, Tasmota or Shelly, over MQTT).

## Field data features

- **Field garage preset**: the seven renting drivers from our Varanasi visit (times and battery type as reported; charger power derived from reported full-charge time; arrival charge assumed 20%).
- **Per-vehicle batteries**: lead-acid or lithium (LFP) with pack size and charger power per row; blanks use the sidebar.
- **Battery health** (`health.py`): health = km per full charge now ÷ when new; good ≥ 80%, watch 60–80% (lithium can go to second-life storage), replace < 60%.
- **Smart-plug log import** (`import_log.py`): CSV with `timestamp, vehicle, power_kw` (or `power_w`); shows the measured peak and overload, then plans the same vehicles. "Download a sample log" gives a simulated example.
- **Solar-first charging**: vehicles that can still finish after 07:00 with a 25% margin wait for the morning sun.
- **₹ view**: electricity tariff input and grid electricity cost per night.

## Roadmap

1. ~~Daytime solar with a second-life storage battery~~ (done)
2. Time-of-day tariff and cost-optimal schedule (linear programming)
3. ~~Per-pack battery-health tracking~~ (done)
4. ~~Live re-planning with a solar forecast~~ (done, simulated); next: real smart-plug data over MQTT
