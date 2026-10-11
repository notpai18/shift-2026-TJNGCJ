"""ChargeFlow: smart overnight charging for an e-rickshaw cluster.

Run with:  streamlit run app.py
"""
import copy
import random
from datetime import datetime, time

import numpy as np
import pandas as pd
import streamlit as st

import charts
import health
import import_log
import live
import ui
from charts import CONFIG, hhmm
from scheduler import (CHARGING, END_H, FLOAT, NIGHT_H, SLOT_H, START_H, WEATHER, Battery,
                       Rickshaw, Storage, base_load, random_fleet, simulate_smart,
                       simulate_uncontrolled, slot_times, solar_kw, summarize)

st.set_page_config(page_title="ChargeFlow", page_icon="⚡", layout="wide", initial_sidebar_state="auto")

DEFAULTS = {
    "n": 10, "kw_room": 0.15, "seed": 7, "limit": 7.0, "capacity": 5.8, "charger": 0.9,
    "target": 95, "kwp": 5.0, "weather": "Clear sky", "nominal": 15.0, "health": 75,
    "inverter": 3.0, "trips": False, "reset_min": 30, "scenario": "solar",
    "compare": ["cmp1"], "flow_period": "cycle", "tariff": 6.5, "preset": "random", "solar_first": False,
    "lv_src": "live", "lv_noshow": "None", "lv_late": "None", "lv_late_h": 1.5, "lv_early": "None",
    "lv_early_h": 2.0, "lv_sun": 1.0, "lv_k": live.K_NIGHT, "lv_playing": False, "stress": False,
}
SUN_OPTS = {0.5: "Cloudier (−50%)", 1.0: "As forecast", 1.25: "Sunnier (+25%)"}
NAMES = {"solar": "ChargeFlow + solar storage", "grid": "ChargeFlow, grid only",
         "uncontrolled": "Uncontrolled plug-in"}
SHORT = {"solar": "ChargeFlow + solar", "grid": "Grid only", "uncontrolled": "Uncontrolled"}
OTHERS = {"solar": ["uncontrolled", "grid"], "grid": ["uncontrolled", "solar"],
          "uncontrolled": ["solar", "grid"]}

# Re-assigning keeps each setting alive across runs where its widget isn't drawn
# (controls inside a closed view), instead of Streamlit resetting it.
for k, v in DEFAULTS.items():
    st.session_state[k] = st.session_state[k] if k in st.session_state else copy.copy(v)


def reset():
    for k, v in DEFAULTS.items():
        st.session_state[k] = copy.copy(v)
    for k in [k for k in st.session_state if str(k).startswith("fleet_")]:
        del st.session_state[k]


def shuffle():
    st.session_state.update(preset="random", stress=False)
    st.session_state.seed = random.choice([s for s in range(1000) if s != st.session_state.seed])


def load_field():
    st.session_state.update(preset="field", stress=False)


def use_random():
    st.session_state.update(preset="random", stress=False)


def stress_test():
    """A tight night: 12 rickshaws on a 7 kW supply whose meter cuts out on overload."""
    reset()
    st.session_state.update(n=12, limit=7.0, trips=True, stress=True)


def messy_night(names):
    pick = lambda i: names[i % len(names)]
    st.session_state.update(lv_noshow=pick(1), lv_late=pick(3), lv_early=pick(0), lv_sun=0.5,
                            lv_k=live.K_NIGHT, lv_playing=True)


def calm_night():
    st.session_state.update(lv_noshow="None", lv_late="None", lv_early="None", lv_sun=1.0, lv_playing=False)


def toggle_play():
    ss_ = st.session_state
    ss_.lv_playing = not ss_.lv_playing
    if ss_.lv_playing and ss_.lv_k >= len(slot_times()):
        ss_.lv_k = live.K_NIGHT


@st.cache_data(ttl=1800, show_spinner="Fetching the solar forecast…")
def forecast():
    return live.fetch_forecast(), datetime.now().strftime("%H:%M")


def use_import(records):
    st.session_state.imported = records
    st.session_state.preset = "import"
    st.session_state.pop("fleet_import", None)


# The seven drivers from our Varanasi visit who rent and charge at a garage (E and H own their
# vehicles and charge at home). Times and chemistry are as reported; charger power is derived
# from each driver's reported full-charge time and an assumed pack size; arrival charge was not
# collected, so 20% is assumed.
FIELD = [("A", "20:00", "10:00", "Lead-acid", 10), ("B", "00:00", "11:00", "Lithium", 3.5),
         ("C", "00:00", "10:00", "Lithium", 3.5), ("D", "00:00", "10:00", "Lead-acid", 8),
         ("F", "00:00", "11:00", "Lithium", 5.5), ("G", "23:00", "08:00", "Lead-acid", 8),
         ("I", "22:00", "10:00", "Lithium", 5)]
PACK = {"Lead-acid": (6.5, 0.80), "Lithium": (5.1, 0.92)}   # assumed kWh, charging efficiency


def roles(focus):
    """Colour and dash per scenario: cobalt is the ChargeFlow plan being viewed,
    graphite is always uncontrolled, the other ChargeFlow variant is dashed gray."""
    plan = "grid" if focus == "grid" else "solar"
    color = {"uncontrolled": ui.GRAPHITE, plan: ui.COBALT, ({"grid", "solar"} - {plan}).pop(): ui.GRAY}
    dash = {k: (None if k in (focus, "uncontrolled") or color[k] == ui.COBALT else "dash") for k in NAMES}
    return color, dash


def h_to_time(h):
    minutes = int(round(h * 60)) % (24 * 60)
    return time(minutes // 60, minutes % 60)


def time_to_h(t):
    h = t.hour + t.minute / 60
    return h + 24 if h < 12 else h


@st.cache_data
def fleet_frame(n, seed):
    return pd.DataFrame([{
        "Rickshaw": r.name,
        "Arrives": h_to_time(r.arrive_h),
        "Leaves": h_to_time(r.leave_h),
        "Charge on arrival (%)": int(round(r.soc_arrive * 100)),
        "Battery": "Lead-acid", "Pack (kWh)": np.nan, "Charger (kW)": np.nan,
    } for r in random_fleet(n, seed)])


@st.cache_data
def field_frame():
    rows = []
    for name, a, b, chem, hours in FIELD:
        kwh, eff = PACK[chem]
        rows.append({"Rickshaw": name, "Arrives": time.fromisoformat(a), "Leaves": time.fromisoformat(b),
                     "Charge on arrival (%)": 20, "Battery": chem, "Pack (kWh)": kwh,
                     "Charger (kW)": round(kwh / eff / hours, 2)})
    return pd.DataFrame(rows)


def parse_fleet(df, capacity, charger):
    """Rows -> Rickshaws. A blank pack or charger cell falls back to the sidebar value."""
    fleet, skipped = [], []
    for row in df.itertuples(index=False):
        name, arrives, leaves, soc, chem, kwh, kw = row
        if arrives is None or leaves is None or pd.isna(soc):
            skipped.append(str(name))
            continue
        a = min(max(time_to_h(arrives), START_H), END_H)
        b = min(max(time_to_h(leaves), START_H), END_H)
        if b <= a:
            skipped.append(str(name))
            continue
        kwh = capacity if pd.isna(kwh) else float(kwh)
        kw = charger if pd.isna(kw) else float(kw)
        bat = Battery.lithium(kwh, kw) if chem == "Lithium" else Battery(capacity_kwh=kwh, charger_kw=kw)
        fleet.append(Rickshaw(str(name), a, b, min(max(float(soc), 0), 100) / 100, bat))
    return fleet, skipped


def runs(mask):
    out, start = [], None
    for k, m in enumerate(mask):
        if m and start is None:
            start = k
        elif not m and start is not None:
            out.append((start, k))
            start = None
    if start is not None:
        out.append((start, len(mask)))
    return out


@st.cache_data
def sample_log():
    """Simulated sample log from the field garage, for demos only."""
    vehicles, _ = parse_fleet(field_frame(), 5.8, 0.9)
    return import_log.sample_csv([(r.name, r.arrive_h, r.leave_h, r.battery, r.soc_arrive) for r in vehicles])


@st.dialog("Method", width="large")
def method():
    st.markdown("""
**The problem.** About ten drivers park in one owner's quarters and plug in at roughly the same time.
Ten chargers plus the rooms' lights and fans can far exceed the building's sanctioned load: breaker
trips, overheated wiring, and chargers left running on full batteries all night where people sleep.

**The controller.** Each charger sits behind an on/off switch (a smart plug or relay; the charger is
unchanged). Every 15 minutes ChargeFlow:
1. works out the free power: sanctioned load × 95% − household load, plus whatever solar and the
   storage pack can supply right now,
2. ranks plugged-in rickshaws by **laxity** = time until departure − charging time still needed,
3. switches on the least-slack rickshaws until the free power runs out (a rickshaw that can no
   longer make it goes to the back, so an overloaded night still gets as many as possible ready),
4. switches a charger off once its pack reaches the ready level.

**Solar + second-life storage.** Rooftop panels charge a stationary pack built from retired EV cells
while the drivers are out. At night the pack first covers anything the grid can't supply within the
sanctioned load, then spreads its remaining energy across the night so it is empty again by morning.
Usable capacity = nominal × pack health; 95% efficiency each way; never drained below 10%.

**Live re-plan.** Real nights don't follow the plan, so ChargeFlow re-plans every 15 minutes from what
it measures now (who is plugged in, each pack's charge, the storage level, the sun so far) and carries
out only the next 15 minutes. Tomorrow's sun comes from the Open-Meteo forecast for Varanasi
(kWp × irradiance ÷ 1000 W/m² × 0.78). From 08:00 the last hour of measured sun corrects the rest of
the morning's forecast. A driver more than 1 h late is planned without until they plug in.

**Battery model.** Constant current to 80%, then a linear taper to 15% of charger draw near full;
80% grid-to-battery efficiency; an idle charger on a full pack still draws 5%.

**Assumptions to replace with field data:** pack size, charger draw, arrival and departure times,
charge on arrival, sanctioned load, household load, roof area for panels.
""")


# ---------------------------------------------------------------- styles
first_run = not st.session_state.get("_entered", False)
st.session_state._entered = True
st.html(ui.styles(first_run))
reduced_motion = st.context.cookies.get("cf_rm") == "1"
TMS = 0 if reduced_motion else 260
st.session_state._run = st.session_state.get("_run", 0) + 1


def tms(chart):
    """Animate a chart only if it was already on screen in the previous run (a parameter
    change). A chart's first draw is never animated: Plotly can leave a fill blank when
    its opening transition is interrupted by the follow-up resize."""
    last = st.session_state.get(f"_drawn_{chart}")
    st.session_state[f"_drawn_{chart}"] = st.session_state._run
    return TMS if last == st.session_state._run - 1 else 0

# ---------------------------------------------------------------- sidebar: parameters
with st.sidebar:
    st.html(ui.side_head())
    with st.container(key="sg_1"):
        st.html(ui.group("01", "Fleet"))
        preset = st.session_state.preset if (st.session_state.preset != "import" or st.session_state.get("imported")) else "random"
        field = preset != "random"
        if field:
            st.html('<p class="cf-note">' + ('Showing the <b>field garage</b>: the seven renting drivers we met '
                                             '(A, B, C, D, F, G, I).' if preset == "field" else
                                             'Showing the vehicles from your <b>imported smart-plug log</b>.') + '</p>')
            st.button("Back to a random night", on_click=use_random, key="sb_random", width="stretch")
        else:
            st.button("Load our field garage", on_click=load_field, key="sb_field", width="stretch",
                      help="Replaces the random fleet with the drivers we interviewed in Varanasi.")
        st.number_input("Rickshaws", 1, 30, step=1, key="n", disabled=field, help="E-rickshaws charging at the quarters tonight.")
        st.slider("Evening load per room", 0.0, 0.5, step=0.05, format="%.2f kW", key="kw_room",
                  help="Lights, fans, phone charging. Lower overnight and while drivers are out.")
        st.number_input("Night", 0, 999, step=1, key="seed", disabled=field,
                        help="Each number generates a different random night of arrivals, departures and charge levels.")
    with st.container(key="sg_2"):
        st.html(ui.group("02", "Building supply"))
        st.slider("Sanctioned load", 2.0, 20.0, step=0.5, format="%.1f kW", key="limit",
                  help="The building's contracted supply limit.")
        st.slider("Electricity tariff", 3.0, 12.0, step=0.1, format="₹%.1f/kWh", key="tariff",
                  help="UPERC FY 2026-27: domestic average about ₹5.8, EV charging (LMV-11) ₹7.7, non-domestic average about ₹9.9.")
    with st.container(key="sg_3"):
        st.html(ui.group("03", "Battery and charger"))
        st.slider("Pack size", 3.0, 10.0, step=0.1, format="%.1f kWh", key="capacity", help="48 V x 120 Ah ≈ 5.8 kWh")
        st.slider("Charger draw", 0.3, 2.0, step=0.05, format="%.2f kW", key="charger")
        st.slider("Ready when charged to", 70, 100, step=5, format="%d%%", key="target")
    with st.container(key="sg_4"):
        st.html(ui.group("04", "Solar and second-life storage"))
        st.slider("Solar panels", 1.0, 20.0, step=0.5, format="%.1f kW", key="kwp",
                  help="Needs about 6.5 m² of roof per kW. About 4 kWh per kW on a clear day.")
        st.segmented_control("Weather today", list(WEATHER), key="weather", required=True,
                             format_func=lambda w: {"Clear sky": "Clear", "Hazy": "Hazy", "Monsoon cloud": "Monsoon"}[w])
        st.slider("Pack capacity, nominal", 5.0, 40.0, step=2.5, format="%.1f kWh", key="nominal")
        st.slider("Pack health", 50, 100, step=5, format="%d%%", key="health",
                  help="Packs retired from EVs typically keep 70-80% of their original capacity.")
        st.slider("Inverter power", 1.0, 10.0, step=0.5, format="%.1f kW", key="inverter")
        st.toggle("Solar-first charging", key="solar_first",
                  help="Vehicles that can still finish after 07:00 wait for the morning sun instead of charging from the "
                       "grid at night. Applies to ChargeFlow + solar storage. Suits lithium packs that leave at 10–11 am.")
    with st.container(key="sg_5"):
        st.html(ui.group("05", "Supply cut-outs"))
        st.toggle("Cut supply above sanctioned load", key="trips",
                  help="Models a meter or MCB that disconnects the building on overload.")
        st.slider("Reset after", 15, 120, step=15, format="%d min", key="reset_min", disabled=not st.session_state.trips,
                  help="How long until someone resets the supply.")

ss = st.session_state
n, seed, limit_kw, target_pct = ss.n, ss.seed, ss.limit, ss.target
target = target_pct / 100

# ---------------------------------------------------------------- page skeleton
masthead = st.container(key="masthead", horizontal=True, vertical_alignment="center", gap="small", wrap=False)
outcome = st.container(key="outcome")
sec2 = st.container(key="sec2")
sec3 = st.container(key="sec3")

with outcome:
    head = st.container(key="outhead")
    with head:
        oh_l, oh_r = st.columns([3, 2], vertical_alignment="bottom", gap="large")
    with oh_r:
        st.segmented_control("Scenario", list(NAMES), key="scenario", required=True, format_func=NAMES.get,
                             width="content")
    with st.container(key="figs"):
        figs = st.columns([1, 1.18], gap="large")
    strip_slot = st.container()
focus = ss.scenario

with sec2:
    sec2_head = st.container()
    with st.container(key="ws"):
        tab_load, tab_sched, tab_live = st.tabs(["`01` Load profile", "`02` Charging schedule", "`03` Live re-plan"],
                                                key="view_main", on_change="rerun")
with sec3:
    sec3_head = st.container()
    with st.container(key="sup"):
        # Closed views don't render their charts (so charts always measure a visible
        # container); the fleet editor always renders because the simulation needs it.
        tab_solar, tab_soc, tab_health, tab_fleet = st.tabs(
            ["`04` Solar and storage", "`05` Battery behaviour", "`06` Battery health", "`07` Fleet data"],
            key="view_sup", on_change="rerun")

with tab_fleet:
    st.html(ui.view_head("Fleet data", "Times before noon are next morning. Blank pack or charger cells use the "
                                       "sidebar values. Every edit re-plans the night."))
    if preset == "import":
        st.html('<p class="cf-note"><b>From your smart-plug log.</b> Plug-in and out times and charger power are '
                'measured. Charge on arrival is estimated from the energy each vehicle drew, assuming the sidebar '
                'pack size and lead-acid; edit the rows if you know better.</p>')
    if preset == "field":
        st.html('<p class="cf-note"><b>Field garage.</b> Times and battery type as drivers A, B, C, D, F, G and I '
                'reported. Charger power is derived from each reported full-charge time, assuming 6.5 kWh lead-acid '
                'and 5.1 kWh lithium packs. Charge on arrival was not collected: 20% is assumed.</p>')
    edited = st.data_editor(
        {"field": field_frame, "import": lambda: pd.DataFrame(ss.imported)}.get(preset, lambda: fleet_frame(n, seed))(),
        key={"field": "fleet_field", "import": "fleet_import"}.get(preset, f"fleet_{n}_{seed}"),
        hide_index=True, num_rows="fixed", width="stretch",
        column_config={
            "Rickshaw": st.column_config.TextColumn(disabled=True),
            "Arrives": st.column_config.TimeColumn(format="HH:mm", step=900),
            "Leaves": st.column_config.TimeColumn(format="HH:mm", step=900),
            "Charge on arrival (%)": st.column_config.NumberColumn(min_value=0, max_value=100, step=1),
            "Battery": st.column_config.SelectboxColumn(options=["Lead-acid", "Lithium"], required=True),
            "Pack (kWh)": st.column_config.NumberColumn(min_value=1.0, max_value=15.0, step=0.1, format="%.1f"),
            "Charger (kW)": st.column_config.NumberColumn(min_value=0.2, max_value=3.0, step=0.05, format="%.2f"),
        })

with tab_fleet:
    st.html('<div style="height:28px"></div>' + ui.view_head(
        "Import a smart-plug log", "CSV with columns timestamp, vehicle and power_kw (or power_w), one row per reading. "
        "We show the measured night, then plan the same vehicles with ChargeFlow."))
    lc, rc = st.columns([3, 1], vertical_alignment="bottom")
    with lc:
        log_file = st.file_uploader("Smart-plug log (CSV)", type="csv", key="log_file", label_visibility="collapsed")
    with rc:
        st.download_button("Download a sample log", sample_log(), "chargeflow_sample_log.csv", "text/csv",
                           on_click="ignore", width="stretch",
                           help="Simulated, not measured: the seven field-garage vehicles charging uncontrolled, "
                                "one reading every 5 minutes.")
    if log_file is not None:
        try:
            grid_kw, total_kw, veh = import_log.parse(log_file)
        except ValueError as e:
            st.warning(str(e), icon=":material/warning:")
        else:
            pk = int(total_kw.values.argmax())
            over = int((total_kw > limit_kw).sum() * 15)
            kwh = float(veh["kwh"].sum())
            st.html(ui.strip([
                ("Vehicles in the log", ui.num("lg_n", len(veh)), f"{total_kw.index.min():%d %b %H:%M} to "
                                                                    f"{total_kw.index.max() + pd.Timedelta(minutes=15):%H:%M}", False),
                ("Measured peak", f'{ui.num("lg_pk", float(total_kw.max()), 1)}<small>kW</small>',
                 f"at {total_kw.index[pk]:%H:%M} · chargers only", float(total_kw.max()) > limit_kw),
                ("Time over sanctioned load", ui.fmt_min(over), f"against {limit_kw:.1f} kW", over > 0),
                ("Most chargers on at once", ui.num("lg_mx", int((grid_kw > 0.05).sum(axis=1).max())), "15-minute slots", False),
                ("Energy and cost", f'{ui.num("lg_kwh", kwh, 1)}<small>kWh</small>', f"₹{kwh * ss.tariff:,.0f} at ₹{ss.tariff:.1f}/kWh", False),
            ]), unsafe_allow_javascript=True)
            st.plotly_chart(charts.measured_chart(total_kw.index, total_kw.values, limit_kw, tms("measured")),
                            key="measured_chart", config=CONFIG, theme=None,
                            alt=f"Measured charger load, peak {float(total_kw.max()):.1f} kW against {limit_kw:.1f} kW.")
            recs = []
            for r in veh.itertuples(index=False):
                soc0 = min(max(1 - r.kwh * 0.8 / ss.capacity, 0.0), 0.95)
                recs.append({"Rickshaw": r.vehicle, "Arrives": r.start.time(), "Leaves": r.end.time(),
                             "Charge on arrival (%)": int(round(soc0 * 100)), "Battery": "Lead-acid",
                             "Pack (kWh)": ss.capacity, "Charger (kW)": round(r.kw, 2)})
            st.dataframe(pd.DataFrame([{"Vehicle": r.vehicle, "Plugged in": f"{r.start:%H:%M}", "Out": f"{r.end:%H:%M}",
                                        "Energy (kWh)": round(r.kwh, 1), "Charger power (kW)": round(r.kw, 2)}
                                       for r in veh.itertuples(index=False)]), hide_index=True, width="stretch")
            st.button("Plan these vehicles with ChargeFlow", on_click=use_import, args=(recs,), key="lg_use",
                      type="primary", help="Replaces the fleet with the vehicles in this log. Scroll up to see the plan.")

fleet, skipped = parse_fleet(edited, ss.capacity, ss.charger)
if skipped:
    with strip_slot:
        st.warning(f"Skipped {', '.join(skipped)}: check that each row leaves after it arrives.",
                   icon=":material/warning:")
if not fleet:
    st.stop()

# ---------------------------------------------------------------- simulate (logic unchanged)
batt = Battery(capacity_kwh=ss.capacity, charger_kw=ss.charger)
times = slot_times()
base = base_load(times, len(fleet), ss.kw_room)
store = Storage(nominal_kwh=ss.nominal, health=ss.health / 100, power_kw=ss.inverter)
sun = solar_kw(times, ss.kwp, WEATHER[ss.weather])
sims = {
    "uncontrolled": simulate_uncontrolled(fleet, batt, base, limit_kw, ss.trips, ss.reset_min),
    "grid": simulate_smart(fleet, batt, base, limit_kw, target, trips=ss.trips, reset_min=ss.reset_min),
    "solar": simulate_smart(fleet, batt, base, limit_kw, target, trips=ss.trips, reset_min=ss.reset_min,
                            solar=sun, storage=store, solar_first=ss.solar_first),
}
sums = {k: summarize(r, limit_kw, target) for k, r in sims.items()}
names = [r.name for r in fleet]
N = len(fleet)
color, dash = roles(focus)
res, s = sims[focus], sums[focus]
u, sol = sums["uncontrolled"], sums["solar"]
grid_saved = sums["grid"]["grid_night_kwh"] - sol["grid_night_kwh"]
active = {k: ((r.state == CHARGING) | (r.state == FLOAT)).sum(axis=0) for k, r in sims.items()}

# ---------------------------------------------------------------- 01 outcome
with oh_l:
    who = {"field": "Field garage, drivers A–I who rent", "import": f"Imported log, {N} vehicles"}.get(
        preset, f"{N} rickshaw{'s' if N != 1 else ''}")
    st.html(ui.section("01", "Outcome", f"Tonight · {who} · {limit_kw:.1f} kW sanctioned"))
socs = [(names[i], res.soc_leave[i] * 100, res.soc_leave[i] >= target - 0.01) for i in range(N)]
short_names = [n_ for n_, _, ok in socs if not ok]
peak_k = int(np.argmax(res.grid_try_kw))
if focus != "uncontrolled":
    cmp_note = (f"Uncontrolled charging would peak at {u['peak_kw']:.1f} kW"
                + (f" and run over for {ui.fmt_min(u['over_min'])}." if u["over_min"] else "."))
else:
    cmp_note = f"ChargeFlow + solar keeps the peak at {sol['peak_kw']:.1f} kW."
with figs[0]:
    st.html(ui.readiness(s["ready"], N, target_pct, socs, short_names), unsafe_allow_javascript=True)
with figs[1]:
    st.html(ui.demand(s["peak_kw"], hhmm(times[peak_k]), limit_kw,
                      u["peak_kw"] if focus != "uncontrolled" else sol["peak_kw"],
                      s["over_min"], s["trips"], ss.trips, cmp_note), unsafe_allow_javascript=True)

ref, ref_name = (u, "uncontrolled") if focus != "uncontrolled" else (sol, "ChargeFlow + solar")
avg = s["avg_soc_leave"] * 100
dpeak = s["peak_kw"] - ref["peak_kw"]
items = [
    ("Average charge at departure", f'{ui.num("avg", avg)}<small>%</small>', f"target {target_pct}%",
     avg < target_pct - 0.5),
    ("Time over sanctioned load", ui.fmt_min(s["over_min"]), f"{ref_name}: {ui.fmt_min(ref['over_min'])}",
     s["over_min"] > 0),
    (f"Peak vs {ref_name}", f'{"−" if dpeak < 0 else "+"}{ui.num("dpeak", abs(dpeak), 1)}<small>kW</small>',
     f"{ref['peak_kw']:.1f} → {s['peak_kw']:.1f} kW", False),
    ("Charger-hours on full packs", f'{ui.num("float", s["float_h"], 1)}<small>h</small>',
     f"{ref_name}: {ref['float_h']:.1f} h", s["float_h"] > 0),
]
cost, ref_cost = s["grid_night_kwh"] * ss.tariff, ref["grid_night_kwh"] * ss.tariff
items.append(("Grid electricity tonight", f'₹{ui.num("cost", cost)}',
              f"₹{cost / N:.0f} a vehicle · {ref_name}: ₹{ref_cost:,.0f} · about ₹{cost * 30:,.0f} a month", False))
if ss.trips:
    items.append(("Supply cut-outs", ui.num("trips_n", s["trips"]), f"{ref_name}: {ref['trips']}", s["trips"] > 0))
items.append(("Night load from solar", f'{ui.num("share", sol["solar_night_share"] * 100)}<small>%</small>',
              (f"{grid_saved:.1f} kWh less from the grid" if focus == "solar"
               else "if solar + storage is added"), False))
with strip_slot:
    st.html(ui.strip(items), unsafe_allow_javascript=True)
    if ss.stress:
        g = sums["grid"]
        st.html(ui.view_head("Stress test: three ways through a tight night",
                             f"{N} rickshaws on a {limit_kw:.1f} kW supply" + (", and the meter cuts the supply on "
                             "overload until someone resets it" if ss.trips else "") + "."))
        st.html(ui.strip([
            (NAMES[k], f'{sums[k]["ready"]}<small>of {N} ready</small>',
             (f'{sums[k]["trips"]} supply cut-outs · ' if ss.trips else "")
             + f'peak {sums[k]["peak_kw"]:.1f} kW · average {sums[k]["avg_soc_leave"] * 100:.0f}%',
             sums[k]["ready"] < N) for k in ("uncontrolled", "grid", "solar")]), unsafe_allow_javascript=True)
        if ss.trips:
            st.html(f'<p class="cf-note">Plugged in uncontrolled, the chargers overload the supply '
                    f'{u["trips"]} times, and every cut-out stops all charging for {ss.reset_min} minutes. '
                    f'ChargeFlow keeps the supply on all night ({g["trips"]} cut-outs) and gets '
                    f'{g["ready"]} of {N} ready from the grid alone; with solar and second-life storage adding '
                    f'power at night, {sol["ready"]} of {N}.</p>')

# ---------------------------------------------------------------- 02 analysis
with sec2_head:
    st.html(ui.section("02", "Analysis", f"{NAMES[focus]} · 15-minute intervals", ruled=True))

if tab_load.open:
    with tab_load:
        hl, hr = st.columns([3, 2], vertical_alignment="bottom")
        with hl:
            st.html(ui.view_head("Grid load through the night",
                                 "Upper trace: kW drawn from the grid. Lower trace: chargers drawing power."))
        cmp_keys = OTHERS[focus]
        with hr:
            st.pills("Compare with", ["cmp1", "cmp2", "household"], selection_mode="multi", key="compare",
                     format_func=lambda o: {"cmp1": SHORT[cmp_keys[0]], "cmp2": SHORT[cmp_keys[1]],
                                            "household": "Household load"}[o],
                     label_visibility="collapsed", width="content")
        chosen = [cmp_keys[0]] * ("cmp1" in ss.compare) + [cmp_keys[1]] * ("cmp2" in ss.compare)
        shown = [focus] + chosen
        fig = charts.load_chart(
            times, [(k, NAMES[k], color[k], dash[k], sims[k].load_kw) for k in shown], focus, limit_kw,
            [(k, SHORT[k], color[k], active[k]) for k in shown],
            household=base if "household" in ss.compare else None, transition_ms=tms("load"))
        st.plotly_chart(fig, key="load_chart", config=CONFIG, theme=None,
                        alt=f"Grid load from 18:00 to 12:00. {NAMES[focus]} peaks at {s['peak_kw']:.1f} kW against "
                            f"a sanctioned load of {limit_kw:.1f} kW.")
        night = times >= NIGHT_H
        notes = [f"At most <b>{int(active[focus][night].max())}</b> chargers draw power at once under "
                 f"{SHORT[focus]}" + "".join(f", against <b>{int(active[k][night].max())}</b> {SHORT[k].lower()}"
                                             for k in chosen) + "."]
        over = [k for k in shown if sums[k]["over_min"] > 0]
        if over:
            notes.append("Shaded red: time above the sanctioned load, "
                         + ", ".join(f"{SHORT[k].lower()} {ui.fmt_min(sums[k]['over_min'])}" for k in over) + ".")
        st.html(f'<p class="cf-note">{" ".join(notes)}</p>')
        with st.expander("Show as table"):
            st.dataframe(pd.DataFrame(
                {"Time": [hhmm(h) for h in times[night]], "Household (kW)": base[night].round(2)}
                | {f"{SHORT[k]} (kW)": sims[k].load_kw[night].round(2) for k in NAMES}
                | {f"{SHORT[k]} chargers on": active[k][night] for k in NAMES}),
                hide_index=True, width="stretch")

night_slots = np.where(times >= NIGHT_H)[0]
span = END_H - NIGHT_H
pct = lambda h: (min(max(h, NIGHT_H), END_H) - NIGHT_H) / span * 100
schedule_rows, table_rows = [], []
for i, r in enumerate(fleet):
    segs, windows = [], []
    for kind, state in (("charge", CHARGING), ("float", FLOAT)):
        for a0, b0 in runs(res.state[i, night_slots] == state):
            h0, h1 = times[night_slots[a0]], times[night_slots[b0 - 1]] + SLOT_H
            label = "Charger on" if kind == "charge" else "Full, charger still drawing"
            segs.append((pct(h0), pct(h1) - pct(h0), kind, f"{label} {hhmm(h0)}–{hhmm(h1)}"))
            if kind == "charge":
                windows.append(f"{hhmm(h0)}–{hhmm(h1)}")
    leave_pct = res.soc_leave[i] * 100
    ready = res.soc_leave[i] >= target - 0.01
    schedule_rows.append({
        "name": r.name, "sub": f"{hhmm(r.arrive_h)}–{hhmm(r.leave_h)} · {r.soc_arrive * 100:.0f}% in",
        "window": (pct(r.arrive_h), pct(r.leave_h) - pct(r.arrive_h)),
        "window_title": f"Plugged in {hhmm(r.arrive_h)}–{hhmm(r.leave_h)}",
        "segments": segs, "soc_leave": leave_pct, "ready": ready,
        "aria": f"{r.name}: arrives {hhmm(r.arrive_h)} at {r.soc_arrive * 100:.0f}%, leaves {hhmm(r.leave_h)} "
                f"at {leave_pct:.0f}%, {'ready' if ready else 'below target'}",
    })
    table_rows.append({"Rickshaw": r.name, "Arrives": hhmm(r.arrive_h), "Leaves": hhmm(r.leave_h),
                       "Charge on arrival (%)": round(r.soc_arrive * 100),
                       "Charge at departure (%)": round(leave_pct, 1), "Ready": "yes" if ready else "no",
                       "Charging hours": float((res.state[i] == CHARGING).sum() * SLOT_H),
                       "Charging windows": "; ".join(windows)})
schedule_df = pd.DataFrame(table_rows)

if tab_sched.open:
    with tab_sched:
        st.html(ui.view_head("Charging schedule", f"When each charger is switched on overnight under {NAMES[focus]}."))
        st.html(ui.timeline(schedule_rows, color[focus], target_pct,
                            ["18:00", "21:00", "00:00", "03:00", "06:00", "09:00", "12:00"]), unsafe_allow_javascript=True)
        with st.expander("Show as table"):
            st.dataframe(schedule_df, hide_index=True, width="stretch")

# ---------------------------------------------------------------- live re-plan
T = len(times)


@st.fragment(run_every=0.7 if ss.lv_playing else None)
def live_clock(night):
    if ss.lv_playing:
        if ss.lv_k >= T:
            ss.lv_playing = False
            st.rerun(scope="app")
        ss.lv_k = min(ss.lv_k + 2, T)
    st.select_slider("Clock", list(range(live.K_NIGHT, T + 1)), key="lv_k", label_visibility="collapsed",
                     format_func=lambda k: hhmm(times[k]) if k < T else "12:00 · night over")
    k = ss.lv_k
    t = times[k] if k < T else END_H
    if k < T:
        plan, ready, n_exp, ratio = night.plan_at(k)
    else:
        plan, ratio = None, live.sun_belief(night.fc_kw, night.act_kw, times, T - 1)[1]
        ready, n_exp = night.outcome(night.done)["ready"], len(night.came)
    here = sum(x.arrive_h <= t < x.leave_h for x in night.actual)
    peak = float(night.done.grid_try_kw[live.K_NIGHT:k].max()) if k > live.K_NIGHT else 0.0
    triggered = sum(1 for e in night.log[1:] if e[0] <= k)
    st.html(ui.strip([
        ("Clock", hhmm(t), f"{k - live.K_NIGHT} re-plans since 18:00 · {triggered} after a surprise", False),
        ("Plugged in now", ui.num("lv_here", here), f"{n_exp} expected tonight", False),
        ("Ready at departure" + (", current plan" if k < T else ""), f"{ready}<small>of {n_exp}</small>",
         "if nothing else changes" if k < T else "final", ready < n_exp),
        ("Peak so far", f'{ui.num("lv_peak", peak, 1)}<small>kW</small>', f"sanctioned {limit_kw:.1f} kW",
         peak > limit_kw),
        ("Sun vs forecast", f"{ratio * 100:.0f}<small>%</small>" if ratio is not None else "–",
         "measured ÷ forecast, last hour" if ratio is not None else "no sun to measure yet", False),
    ]), unsafe_allow_javascript=True)
    st.plotly_chart(charts.replan_chart(times, k, night.done.load_kw, plan.load_kw if plan else None,
                                        night.fixed.load_kw, night.fc_kw, night.act_kw, limit_kw),
                    key="replan_chart", config=CONFIG, theme=None,
                    alt=f"Grid import up to {hhmm(t)} and the plan from then on, against the sanctioned load.")
    st.html(ui.view_head("Re-plan log", "Changes the controller has seen by now. It re-plans every 15 minutes "
                                        "regardless; these are the re-plans a surprise triggered."))
    st.dataframe(pd.DataFrame([{"Time": hhmm(times[e[0]]), "What changed": e[1],
                                "Plan after re-planning": f"{e[2]} of {e[3]} ready · peak ahead {e[4]:.1f} kW"}
                               for e in night.log if e[0] <= k]), hide_index=True, width="stretch")


if tab_live.open:
    with tab_live:
        st.html(ui.view_head("Live re-plan", "Tonight as it really happens. Every 15 minutes ChargeFlow re-plans the "
                                             "rest of the night from what it measures: who is plugged in, each pack's "
                                             "charge, the storage level and the sun so far. Add surprises, then play "
                                             "the night."))
        opts = ["None"] + names
        for key in ("lv_noshow", "lv_late", "lv_early"):
            if ss[key] not in opts:
                ss[key] = "None"
        c1, c2, c3, c4 = st.columns([1.2, 1.5, 0.8, 0.8], vertical_alignment="bottom")
        with c1:
            st.segmented_control("Solar forecast", ["live", "sidebar"], key="lv_src", required=True,
                                 format_func={"live": "Open-Meteo, live", "sidebar": "Sidebar weather"}.get)
        with c2:
            st.segmented_control("Tomorrow morning's real sun", list(SUN_OPTS), key="lv_sun", required=True,
                                 format_func=SUN_OPTS.get)
        with c3:
            st.button("Pause" if ss.lv_playing else "Play the night", on_click=toggle_play, key="lv_play",
                      type="primary", width="stretch", icon=":material/pause:" if ss.lv_playing else ":material/play_arrow:")
        with c4:
            st.button("Messy night", on_click=messy_night, args=(names,), key="lv_messy", width="stretch",
                      help="One no-show, one driver late, one leaving early and a cloudier morning than forecast.")
        c1, c2, c3, c4, c5 = st.columns(5, vertical_alignment="bottom")
        with c1:
            st.selectbox("Doesn't come", opts, key="lv_noshow")
        with c2:
            st.selectbox("Arrives late", opts, key="lv_late")
        with c3:
            st.select_slider("Late by", [0.5, 1.0, 1.5, 2.0, 3.0], key="lv_late_h", format_func=live.fmt_h,
                             disabled=ss.lv_late == "None")
        with c4:
            st.selectbox("Leaves early", opts, key="lv_early")
        with c5:
            st.select_slider("Early by", [0.5, 1.0, 2.0, 3.0, 4.0], key="lv_early_h", format_func=live.fmt_h,
                             disabled=ss.lv_early == "None")

        fc, fetched = forecast() if ss.lv_src == "live" else (None, None)
        if fc:
            fc_kw = live.forecast_kw(fc, times, ss.kwp)
            src_note = (f"<b>Forecast:</b> Open-Meteo for Varanasi (25.32° N, 82.99° E), fetched {fetched}. Tomorrow "
                        f"07:00–12:00 is {live.sun_factor(fc_kw, times, ss.kwp) * 100:.0f}% of a clear morning, "
                        f"{live.morning_cloud(fc):.0f}% cloud. PV = kWp × irradiance ÷ 1000 W/m² × 0.78.")
        else:
            fc_kw = sun
            src_note = ("<b>Forecast:</b> " + ("Open-Meteo could not be reached, so the " if ss.lv_src == "live"
                                               else "The ") + f"sidebar weather ({ss.weather.lower()}) is used.")
        who = lambda v: None if v == "None" else v
        sp = live.Surprises(who(ss.lv_noshow), who(ss.lv_late), ss.lv_late_h, who(ss.lv_early), ss.lv_early_h,
                            ss.lv_sun)
        night = live.LiveNight(fleet, sp, batt, base, limit_kw, target, fc_kw, ss.kwp, store, ss.solar_first)
        st.html(f'<p class="cf-note">{src_note} A driver more than 1 h late is planned without until they plug in. '
                'From 08:00 the last hour of measured sun corrects the rest of the morning\'s forecast. Only the first '
                '15 minutes of each plan are carried out, then ChargeFlow measures again and re-plans.</p>')
        live_clock(night)
        d, f = night.outcome(night.done), night.outcome(night.fixed)
        nc = len(night.came)
        st.html(ui.view_head("How the night ends", "Re-planning every 15 minutes against the 18:00 plan "
                                                   "followed blindly, with the same surprises."))
        st.html(ui.strip([
            ("Ready at departure", f'{d["ready"]}<small>of {nc}</small>', f"18:00 plan blindly: {f['ready']} of {nc}",
             d["ready"] < nc),
            ("Time over sanctioned load", ui.fmt_min(d["over_min"]), f"18:00 plan blindly: {ui.fmt_min(f['over_min'])}",
             d["over_min"] > 0),
            ("Peak grid import", f'{ui.num("lv_dpk", d["peak_kw"], 1)}<small>kW</small>',
             f"18:00 plan blindly: {f['peak_kw']:.1f} kW", d["peak_kw"] > limit_kw),
            ("Grid electricity", f'₹{ui.num("lv_cost", d["grid_night_kwh"] * ss.tariff)}',
             f"18:00 plan blindly: ₹{f['grid_night_kwh'] * ss.tariff:,.0f}", False),
        ]), unsafe_allow_javascript=True)

# ---------------------------------------------------------------- 03 supporting analysis
with sec3_head:
    st.html(ui.section("03", "Supporting analysis", "Solar, storage, battery behaviour and the fleet inputs",
                       ruled=True))

PERIODS = {"cycle": ("Full cycle", times >= 0), "day": ("Day 06–18", times < NIGHT_H),
           "night": ("Night 18–12", times >= NIGHT_H)}
if tab_solar.open:
    with tab_solar:
        sl, sr = st.columns([3, 2], vertical_alignment="bottom")
        with sl:
            note = "" if focus == "solar" else " Shown for the ChargeFlow + solar storage scenario."
            st.html(ui.view_head("Energy flows", "Simulated kWh from 06:00 to 12:00 the next day; line width is "
                                                 f"proportional to energy.{note}"))
        with sr:
            st.segmented_control("Period", list(PERIODS), key="flow_period", required=True,
                                 format_func=lambda p: PERIODS[p][0], label_visibility="collapsed", width="content")
        rs = sims["solar"]
        period_label, mask = PERIODS[ss.flow_period]
        direct = np.minimum(rs.solar_kw, rs.demand_kw)
        to_pack = np.clip(-rs.store_kw, 0, None)
        from_pack = np.clip(rs.store_kw, 0, None)
        kwh = lambda arr: float(arr[mask].sum() * SLOT_H)
        flows = {
            "solar": kwh(rs.solar_kw), "direct": kwh(direct), "to_pack": kwh(to_pack), "unused": kwh(rs.export_kw),
            "from_pack": kwh(from_pack), "grid": kwh(rs.load_kw), "demand": kwh(rs.demand_kw), "ev": kwh(rs.ev_kw),
            "rooms": kwh(rs.demand_kw - rs.ev_kw),
            "solar_sub": f"{ss.kwp:g} kW · {ss.weather.lower()}",
            "grid_sub": f"sanctioned {limit_kw:.1f} kW", "fleet_sub": f"{N} rickshaws",
        }
        fc, ff = st.columns([1.75, 1], gap="large")
        with fc:
            st.html(ui.flow(flows, period_label), unsafe_allow_javascript=True)
        ready_diff = sol["ready"] - sums["grid"]["ready"]
        with ff:
            st.html(ui.facts([
                ("Solar generated", f"{sol['solar_kwh']:.1f} kWh", ui.SOLAR),
                ("Night load met by solar", f"{sol['solar_night_share'] * 100:.0f}%", ui.SOLAR),
                ("Grid energy saved vs grid only", f"{grid_saved:.1f} kWh", ui.COBALT),
                ("Ready at departure", f"{sol['ready']}/{N}" + (f" <em>({ready_diff:+d} vs grid only)</em>"
                                                                 if ready_diff else ""), None),
                ("Unused solar, pack full", f"{sol['export_kwh']:.1f} kWh", ui.RULE),
                ("Second-life pack, usable", f"{store.usable_kwh:.1f} kWh <em>of {ss.nominal:g}</em>", ui.STORAGE),
                ("Pack cycled tonight", f"{sol['discharged_kwh'] / store.usable_kwh * 100:.0f}%", ui.STORAGE),
            ]), unsafe_allow_javascript=True)
        st.html(ui.view_head("Power by source", "What supplied the building in each 15-minute interval."))
        st.plotly_chart(charts.supply_chart(times, direct, from_pack, rs.load_kw, rs.solar_kw, limit_kw, tms("supply")),
                        key="supply_chart", config=CONFIG, theme=None,
                        alt="Building power by source from 06:00 to 12:00: grid, second-life pack, solar used directly.")
        st.html(ui.view_head("Second-life pack", "Energy stored through the day and night."))
        st.plotly_chart(charts.pack_chart(times, rs.store_kwh, store.usable_kwh,
                                          f"Usable {store.usable_kwh:.1f} kWh ({ss.nominal:g} kWh at {ss.health}% health)",
                                          tms("pack")),
                        key="pack_chart", config=CONFIG, theme=None, alt="Energy in the second-life pack over the day.")
        with st.expander("Show as table"):
            st.dataframe(pd.DataFrame({
                "Time": [hhmm(h) for h in times], "Solar generated (kW)": rs.solar_kw.round(2),
                "Solar used directly (kW)": direct.round(2), "From storage (kW)": from_pack.round(2),
                "Into storage (kW)": to_pack.round(2), "From grid (kW)": rs.load_kw.round(2),
                "Pack energy (kWh)": rs.store_kwh.round(2)}), hide_index=True, width="stretch")

if tab_soc.open:
    with tab_soc:
        st.html(ui.view_head("Charge at departure", f"Bars run from charge on arrival to charge at departure under "
                                                    f"{NAMES[focus]}; short marks show the alternatives."))
        dep = [(k, SHORT[k], color[k], sims[k].soc_leave) for k in [focus] + OTHERS[focus]]
        st.plotly_chart(charts.departure_chart(names, [r.soc_arrive for r in fleet], dep, focus, target_pct, tms("departure")),
                        key="departure_chart", config=CONFIG, theme=None,
                        alt=f"Charge on arrival and at departure per rickshaw; {s['ready']} of {N} reach {target_pct}%.")
        fl, fr = st.columns([1, 3], vertical_alignment="bottom")
        with fl:
            pick = st.selectbox("Follow one rickshaw through the night", names, key="follow")
        with fr:
            st.html('<p class="cf-note">Lead-acid packs charge at full current up to about 80%, then the charger '
                    'tapers. That slow last 20% is why a deeply drained pack needs most of the night.</p>')
        i = names.index(pick)
        st.plotly_chart(charts.soc_chart(times, [(k, SHORT[k], color[k], dash[k], sims[k].soc[i]) for k in NAMES],
                                         focus, target_pct, tms("soc")),
                        key="soc_chart", config=CONFIG, theme=None, alt=f"State of charge of {pick} through the night.")

# ---------------------------------------------------------------- battery health
# Seeded with what our nine drivers reported; blanks were not collected.
HEALTH_ROWS = [
    ("A", "Lead-acid", None, 90, None, 48000, 2), ("B", "Lithium", None, 100, None, 70000, 2),
    ("C", "Lithium", None, 100, None, None, 1.5), ("D", "Lead-acid", None, 100, None, None, None),
    ("E", "Lead-acid", 150, 60, None, 50000, 2), ("F", "Lithium", None, 100, 3, 50000, None),
    ("G", "Lead-acid", None, 120, None, 48000, None), ("H", "Lead-acid", None, 100, None, None, 1.5),
    ("I", "Lithium", None, 100, None, None, None)]
HEALTH_COLS = ["Vehicle", "Battery", "Range when new (km)", "Range now (km)", "Pack age (years)",
               "Replacement cost (₹)", "Replaced every (years)"]

if tab_health.open:
    with tab_health:
        st.html(ui.view_head("Battery health", "Estimated from range: km on a full charge now against when the pack "
                                               "was new. Fill in the blanks to see each pack's health."))
        hdf = st.data_editor(
            pd.DataFrame([[np.nan if v is None else v for v in r] for r in HEALTH_ROWS], columns=HEALTH_COLS),
            key="health_table", hide_index=True, num_rows="dynamic", width="stretch",
            column_config={
                "Battery": st.column_config.SelectboxColumn(options=["Lead-acid", "Lithium"], required=True),
                "Range when new (km)": st.column_config.NumberColumn(min_value=1, max_value=400, step=1),
                "Range now (km)": st.column_config.NumberColumn(min_value=0, max_value=400, step=1),
                "Pack age (years)": st.column_config.NumberColumn(min_value=0.0, max_value=15.0, step=0.5),
                "Replacement cost (₹)": st.column_config.NumberColumn(min_value=0, step=1000, format="₹%d"),
                "Replaced every (years)": st.column_config.NumberColumn(min_value=0.5, max_value=10.0, step=0.5),
            })
        out = []
        for r in hdf.itertuples(index=False):
            if not isinstance(r[0], str) or not r[0]:
                continue
            h, status, action, left, per_day = health.assess(r[1], r[2], r[3], r[4], r[5], r[6])
            out.append(dict(name=r[0], chem=r[1], h=h, status=status, action=action, left=left, per_day=per_day))
        known = [o for o in out if o["h"] is not None]
        spend = sum(o["per_day"] for o in out if o["per_day"]) * 365
        n_cost = sum(1 for o in out if o["per_day"])
        st.html(ui.strip([
            ("Packs with a health estimate", f"{len(known)}<small>of {len(out)}</small>",
             "the rest need range when new", False),
            ("Average health", (f'{ui.num("h_avg", 100 * sum(o["h"] for o in known) / len(known))}<small>%</small>'
                                if known else "–"), "km now ÷ km when new", bool(known) and
             sum(o["h"] for o in known) / len(known) < health.WATCH),
            ("Packs to replace now", ui.num("h_rep", sum(o["status"] == "Replace" for o in out)),
             "below 60% of range when new", any(o["status"] == "Replace" for o in out)),
            ("Second-life candidates", ui.num("h_sl", sum(o["status"] == "Watch" and o["chem"] == "Lithium" for o in out)),
             "lithium packs at 60–80%", False),
            ("Battery spend a year", f"₹{ui.num('h_spend', spend)}",
             f"from {n_cost} vehicles with cost and interval", False),
        ]), unsafe_allow_javascript=True)
        if known:
            st.plotly_chart(charts.health_chart([o["name"] for o in known], [o["h"] for o in known],
                                                [o["status"] for o in known], tms("health")),
                            key="health_chart", config=CONFIG, theme=None,
                            alt="Estimated battery health per vehicle against 80% and 60% thresholds.")
        st.dataframe(pd.DataFrame([{
            "Vehicle": o["name"], "Battery": o["chem"],
            "Health": f"{o['h'] * 100:.0f}%" if o["h"] is not None else "–", "Status": o["status"],
            "Years to 60%": (f"{o['left']:.1f}" if o["left"] is not None else "–"),
            "Battery cost a day": (f"₹{o['per_day']:.0f}" if o["per_day"] else "–"), "Next step": o["action"]}
            for o in out]), hide_index=True, width="stretch")
        st.html('<p class="cf-note">Thresholds: 80% and above good, 60–80% watch (lithium packs can then go to '
                'second-life storage), below 60% replace. Range also depends on load, route and driving, so this is '
                'a rough estimate to confirm with a capacity test. E\'s 150 km is from when the vehicle was bought '
                'in 2023; the pack may have been replaced since, so the pack age is left blank.</p>')

# ---------------------------------------------------------------- masthead
with masthead:
    st.html(ui.masthead("Overnight charging planner · e-rickshaw cluster"), width="stretch")
    st.button("New night", help="Generate a different random night", on_click=shuffle,
              key="mh_new", type="tertiary")
    st.button("Field garage", help="Load the seven renting drivers we interviewed", on_click=load_field,
              key="mh_field", type="tertiary")
    st.button("Stress test", help="A tight night: 12 rickshaws on a 7 kW supply that cuts out on overload",
              on_click=stress_test, key="mh_stress", type="tertiary")
    st.button("Reset", help="Reset every parameter to its default", on_click=reset,
              key="mh_reset", type="tertiary")
    st.download_button("Export CSV", schedule_df.to_csv(index=False).encode("utf-8"),
                       file_name=f"chargeflow_{focus}_schedule.csv", mime="text/csv", help="Download tonight's charging schedule", key="mh_csv", type="tertiary", on_click="ignore")
    if st.button("Method", help="How ChargeFlow plans the night", key="mh_method",
                 type="tertiary"):
        method()
