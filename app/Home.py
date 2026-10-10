"""Pragna SolarYard — Tonight's Plan (Check-in 1 prototype).

Run:  streamlit run app/Home.py
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path
from textwrap import dedent

import numpy as np
import plotly.graph_objects as go
import streamlit as st
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.config import ROOT, clock_labels, dt_hours, load_config  # noqa: E402
from core.dispatch import solve_with_baseline  # noqa: E402
from core.fleet import load_fleet  # noqa: E402
from core.solar import synthetic_pv  # noqa: E402

st.set_page_config(page_title="Pragna SolarYard", page_icon="☀️", layout="wide",
                   initial_sidebar_state="collapsed")

# Source colours: sun = amber, stored sun = teal, grid = slate. Identity is never colour-only:
# every chart has a legend and the tiles name each source in text.
C_SUN, C_BATT, C_GRID = "#E39B1B", "#1F7A6B", "#8A8F98"
INK, INK_2, INK_3, LINE = "#1D1D1F", "#6E6E73", "#86868B", "#E3E3E8"
SEASONS = {"autumn": "Autumn · Sep–Nov", "winter": "Winter · Dec–Feb",
           "spring": "Spring · Mar–May", "summer": "Monsoon · Jun–Aug"}


def html(s):
    st.markdown(dedent(s).strip(), unsafe_allow_html=True)


html("""
<style>
:root { --ink:#1D1D1F; --ink2:#6E6E73; --ink3:#86868B; --line:#E3E3E8; --card:#FFFFFF;
        --sun:#E39B1B; --batt:#1F7A6B; --grid:#8A8F98; --warn:#B4231C; }
html, body, [class*="css"], .stApp, .stMarkdown, button, input, select, label {
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Inter, Roboto,
               "Helvetica Neue", Arial, sans-serif !important; }
.stApp { background:#F5F5F7; }
header[data-testid="stHeader"], #MainMenu, footer, [data-testid="stSidebarCollapsedControl"] { display:none !important; }
.block-container { max-width:1180px; padding:2.2rem 1.5rem 4rem; }
h1,h2,h3 { letter-spacing:-0.022em; color:var(--ink); }

.strip { display:flex; flex-wrap:wrap; gap:8px; align-items:center; font-size:12.5px; color:var(--ink2); }
.pill { display:inline-flex; align-items:center; gap:6px; padding:4px 10px; border-radius:999px;
        background:#fff; border:1px solid var(--line); font-weight:500; white-space:nowrap; }
.pill.sim { color:#8A5A00; background:#FFF6E5; border-color:#F3DDB0; }
.pill.src { color:#1F5F55; background:#E9F4F1; border-color:#C7E2DB; }
.pill.ass { color:#4B4B55; background:#F2F2F5; }
.dot { width:7px; height:7px; border-radius:50%; display:inline-block; }

.eyebrow { font-size:13px; font-weight:600; letter-spacing:.08em; text-transform:uppercase; color:var(--batt); margin:34px 0 10px; }
.hero { font-size:clamp(38px, 6vw, 64px) !important; line-height:1.04 !important; font-weight:700 !important; letter-spacing:-0.035em; color:var(--ink) !important; margin:0 !important; padding:0 !important; }
.hero .soft { color:var(--ink3) !important; }
.lede { font-size:clamp(17px, 2vw, 21px); line-height:1.5; color:var(--ink2); max-width:780px; margin:22px 0 0 !important; }

.flow { display:grid; grid-template-columns:repeat(3, 1fr); gap:14px; margin:34px 0 8px; }
.step { background:var(--card); border:1px solid var(--line); border-radius:18px; padding:20px 22px; }
.step .n { font-size:12px; font-weight:600; color:var(--ink3); letter-spacing:.06em; }
.step .t { font-size:18px; font-weight:600; color:var(--ink); margin:6px 0 4px; letter-spacing:-0.01em; }
.step .d { font-size:14.5px; color:var(--ink2); line-height:1.45; }

.section { font-size:clamp(26px, 3.2vw, 34px); font-weight:700; letter-spacing:-0.028em; color:var(--ink); margin:56px 0 4px; }
.sub { font-size:16px; color:var(--ink2); margin:0 0 18px; max-width:760px; line-height:1.5; }

div[data-testid="stVerticalBlockBorderWrapper"] { background:var(--card); border:1px solid var(--line) !important;
  border-radius:18px !important; }

.kpis { display:grid; grid-template-columns:repeat(5, 1fr); gap:12px; margin:6px 0 14px; }
.kpi { background:var(--card); border:1px solid var(--line); border-radius:18px; padding:18px 18px 16px; min-width:0; }
.kpi .l { font-size:13px; color:var(--ink2); font-weight:500; display:flex; align-items:center; gap:6px; }
.kpi .v { font-size:clamp(28px, 3.4vw, 40px); font-weight:700; letter-spacing:-0.03em; color:var(--ink); margin:6px 0 2px; line-height:1.05; }
.kpi .v small { font-size:.5em; font-weight:600; color:var(--ink3); letter-spacing:-0.01em; }
.kpi .s { font-size:12.5px; color:var(--ink3); line-height:1.35; }
.kpi.muted .v { color:var(--ink3); }

.story { background:var(--card); border:1px solid var(--line); border-radius:18px; padding:20px 24px; margin:0 0 14px; }
.story ol { margin:0; padding-left:20px; color:var(--ink); font-size:15.5px; line-height:1.65; }
.story li::marker { color:var(--ink3); font-weight:600; }
.story b { font-weight:600; }
.warn { border-color:#F1C5C2; background:#FDF3F2; color:var(--warn); }

.card-h { font-size:17px; font-weight:600; color:var(--ink); letter-spacing:-0.01em; margin:2px 0 0; }
.card-s { font-size:13px; color:var(--ink3); margin:2px 0 0; }

.rk { display:grid; grid-template-columns:repeat(4, 1fr); gap:10px; margin:8px 0 6px; }
.rk div { background:#F7F7F9; border-radius:12px; padding:12px 14px; }
.rk .l { font-size:12px; color:var(--ink3); }
.rk .v { font-size:19px; font-weight:600; color:var(--ink); letter-spacing:-0.01em; margin-top:2px; }
.sms { font-size:15px; line-height:1.6; background:#F7F7F9; border-radius:14px; padding:14px 16px; color:var(--ink); }

.plan { display:grid; grid-template-columns:repeat(3, 1fr); gap:14px; }
.plan > div { background:var(--card); border:1px solid var(--line); border-radius:18px; padding:20px 22px; }
.plan h4 { font-size:13px; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:var(--ink3); margin:0 0 10px; }
.plan ul { margin:0; padding-left:18px; font-size:14.5px; line-height:1.6; color:var(--ink); }
.plan li { margin-bottom:4px; }
.plan .done li::marker { content:"✓  "; color:var(--batt); font-weight:700; }
.plan .owner { font-size:14.5px; color:var(--ink); margin-bottom:12px; line-height:1.4; }
.plan .owner b { font-weight:600; display:block; }
.plan .owner span { color:var(--ink3); font-size:13px; }
.plan .owner i { color:var(--ink3); font-style:normal; }

.foot { font-size:12.5px; color:var(--ink3); line-height:1.6; margin-top:44px; border-top:1px solid var(--line); padding-top:18px; }
.foot a { color:var(--ink2); }

@media (max-width: 900px) {
  .kpis { grid-template-columns:repeat(2, 1fr); }
  .flow, .plan { grid-template-columns:1fr; }
  .rk { grid-template-columns:repeat(2, 1fr); }
}
</style>
""")

cfg = load_config()
fleet_doc = load_fleet()
fleet = fleet_doc["rickshaws"]
labels = clock_labels(cfg)
DT = dt_hours(cfg)
t0 = datetime(2026, 10, 10, 8, 0)
times = [t0 + timedelta(minutes=cfg["time"]["step_minutes"] * k) for k in range(len(labels))]


@st.cache_data(show_spinner=False)
def run_plan(season, cloud, battery_price, grid_kw):
    pv = synthetic_pv(cfg, season, cloud)
    return solve_with_baseline(cfg, fleet, pv, battery_price=battery_price, grid_kw=grid_kw)


def hhmm(k):
    return labels[k % len(labels)]


def window(mask):
    idx = np.flatnonzero(mask)
    return (hhmm(idx[0]), hhmm(idx[-1] + 1)) if idx.size else None


# ---------------------------------------------------------------- header
html("""
<div class="strip">
  <span class="pill" style="font-weight:600;color:#1D1D1F">SHIFT Hackathon · Check-in 1 prototype</span>
  <span class="pill sim"><span class="dot" style="background:#E39B1B"></span>Fleet &amp; battery SIMULATED</span>
  <span class="pill src"><span class="dot" style="background:#1F7A6B"></span>Tariff SOURCE · UPERC FY27</span>
  <span class="pill ass">Solar · SYNTHETIC from Varanasi seasonal yield (F10)</span>
</div>
<div class="eyebrow">Pragna SolarYard</div>
<h1 class="hero">Run e-rickshaws on sunshine.<br><span class="soft">Charged by dawn, from stored sun first.</span></h1>
<p class="lede">India's e-rickshaws are electric but not clean: most charge overnight, when the grid runs mostly
on fossil fuel (168&nbsp;GW at night vs 125&nbsp;GW at 1&nbsp;pm), while midday solar is curtailed.
SolarYard banks a yard's rooftop sun in a <b style="color:#1D1D1F;font-weight:600">second-life EV battery</b> and
schedules every rickshaw to be full by its departure time.</p>
<div class="flow">
  <div class="step"><div class="n">BY DAY</div><div class="t">Rooftop solar</div>
    <div class="d">Charges the second-life battery on an off-grid circuit. No export, so it is legal on an EV connection.</div></div>
  <div class="step"><div class="n">AT NIGHT</div><div class="t">Stored sun first</div>
    <div class="d">Rickshaws charge from the battery, but only when the grid cost it saves is more than the wear on the old pack.</div></div>
  <div class="step"><div class="n">BY DEPARTURE</div><div class="t">Grid tops up</div>
    <div class="d">The LMV-11 grid connection fills any gap, so every rickshaw is full by its own departure time.</div></div>
</div>
""")

# ---------------------------------------------------------------- controls
html("""<div class="section">Tonight's plan</div>
<p class="sub">A wear-aware optimiser (linear program, PuLP/CBC) schedules a 10-rickshaw demo yard from 08:00 today to
08:00 tomorrow in 15-minute steps. Change the conditions and it re-plans.</p>""")

with st.container(border=True):
    c1, c2, c3, c4 = st.columns(4, gap="large")
    season = c1.selectbox("Season", list(SEASONS), format_func=SEASONS.get,
                          help="Daily solar yield per kWp for Varanasi, profilesolar.com (SOURCE F10).")
    cloud = c2.slider("Sunshine vs. average", 0.3, 1.0, 1.0, 0.05, format="%.2f",
                      help="1.00 = average day for the season; 0.40 = heavy cloud.")
    batt_price = c3.slider("Second-life battery price (₹/kWh)", 1000, 20000,
                           int(cfg["battery"]["price_inr_per_kwh"]), 500,
                           help="ASSUMPTION until a refurbisher quote. Sets the wear cost per kWh discharged.")
    grid_kw = c4.slider("Sanctioned grid load (kW)", 1, 15, int(cfg["grid"]["sanctioned_load_kw"]), 1,
                        help="ASSUMPTION until field data. Lower it to see the optimiser run out of power.")

with st.spinner("Optimising tonight's schedule…"):
    r = run_plan(season, cloud, batt_price, grid_kw)

n = len(fleet)
ready = n - len(r["unmet_kwh"])
wear = r["wear_cost_per_kwh"]
ef = cfg["impact"]["grid_emission_factor_kg_per_kwh"]
co2 = (f'<div class="kpi"><div class="l">CO₂ avoided</div><div class="v">'
       f'{(r["baseline_grid_kwh"] - r["grid_kwh"]) * ef:.0f}<small> kg</small></div>'
       f'<div class="s">CEA grid factor</div></div>') if ef else (
       '<div class="kpi muted"><div class="l">CO₂ avoided</div><div class="v">—</div>'
       '<div class="s">Waiting for the CEA grid emission factor. We won\'t guess it.</div></div>')

html(f"""
<div class="kpis">
  <div class="kpi"><div class="l"><span class="dot" style="background:{C_SUN}"></span>Solar share</div>
    <div class="v">{r["solar_share"] * 100:.0f}<small>%</small></div>
    <div class="s">of tonight's {r["energy_to_rickshaws_kwh"]:.0f} kWh came from the sun</div></div>
  <div class="kpi"><div class="l">Ready by departure</div>
    <div class="v" style="color:{'#1D1D1F' if ready == n else '#B4231C'}">{ready}<small> / {n}</small></div>
    <div class="s">{'every rickshaw full on time' if ready == n else 'not enough power. See below.'}</div></div>
  <div class="kpi"><div class="l"><span class="dot" style="background:{C_GRID}"></span>Grid energy</div>
    <div class="v">{r["grid_kwh"]:.0f}<small> kWh</small></div>
    <div class="s">vs {r["baseline_grid_kwh"]:.0f} kWh if charged from grid only</div></div>
  <div class="kpi"><div class="l">Net saving tonight</div>
    <div class="v">₹{r["net_saving_inr"]:.0f}</div>
    <div class="s">vs grid-only ₹{r["baseline_cost_inr"]:.0f}, after ₹{r["wear_cost_inr"]:.0f} battery wear</div></div>
  {co2}
</div>
""")

# ---------------------------------------------------------------- what the optimiser decided
chg, dis_w = window(r["pv_bat"] > 0.05), window(r["dis"] > 0.05)
items = []
if chg:
    items.append(f"<b>Stores midday sun:</b> the battery charges from solar {chg[0]}–{chg[1]} and holds "
                 f"{r['solar_via_battery_kwh']:.1f} kWh for the night.")
if dis_w:
    items.append(f"<b>Night from stored sun:</b> the battery feeds rickshaws {dis_w[0]}–{dis_w[1]}, because the "
                 f"₹{wear:.2f}/kWh wear cost is below the ₹{cfg['tariff']['lmv11_energy_inr_per_kwh']:.2f} night tariff it avoids.")
else:
    items.append(f"<b>Battery left idle:</b> at this price the wear cost (₹{wear:.2f}/kWh) is more than the grid "
                 f"tariff it would avoid, so the optimiser does not cycle the old pack.")
if r["solar_direct_kwh"] > 0.05:
    items.append(f"<b>Midday top-ups:</b> {r['solar_direct_kwh']:.1f} kWh goes straight from the panels to rickshaws "
                 f"parked at lunch.")
items.append(f"<b>Grid fills the gap:</b> {r['grid_kwh']:.1f} kWh, peaking at {r['peak_grid_kw']:.1f} kW "
             f"(limit {grid_kw} kW).")
if r["curtailed_kwh"] > 0.5:
    items.append(f"<b>Honest note:</b> {r['curtailed_kwh']:.0f} kWh of sun goes unused because the battery is full and "
                 f"most rickshaws are out on the road. Right-sizing the panels and battery is our next milestone.")
html('<div class="story"><ol>' + "".join(f"<li>{s}</li>" for s in items) + "</ol></div>")

if r["unmet_kwh"]:
    short = ", ".join(f"{k} ({v:.1f} kWh short)" for k, v in r["unmet_kwh"].items())
    html(f'<div class="story warn"><b>Not every rickshaw can be charged by departure:</b> {short}. '
         f'Raise the sanctioned load or add storage.</div>')

# ---------------------------------------------------------------- charts
AX = dict(showgrid=False, zeroline=False, linecolor=LINE, tickfont=dict(color=INK_3, size=12),
          title_font=dict(color=INK_2, size=12))
LAYOUT = dict(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
              font=dict(family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif", color=INK),
              margin=dict(l=8, r=8, t=8, b=8), hovermode="x unified",
              hoverlabel=dict(bgcolor="white", bordercolor=LINE, font=dict(color=INK, size=13)),
              legend=dict(orientation="h", y=1.12, x=0, traceorder="normal", font=dict(size=13, color=INK_2), bgcolor="rgba(0,0,0,0)"))
XAX = dict(AX, type="date", tickformat="%H:%M", dtick=2 * 3600 * 1000)


def solar_band(fig):
    lo, hi = (labels.index(h) for h in cfg["tariff"]["solar_hours"])
    fig.add_vrect(x0=times[lo], x1=times[hi], fillcolor="#FFF4DC", opacity=0.6, line_width=0, layer="below",
                  annotation_text="Solar-hour tariff ₹6.16", annotation_position="top left",
                  annotation_font=dict(size=11, color="#8A5A00"))


with st.container(border=True):
    html('<div class="card-h">Where the rickshaws\' power comes from</div>'
         '<div class="card-s">kW delivered to chargers, by source. Shaded: 20% cheaper solar-hour tariff (SOURCE F3).</div>')
    fig = go.Figure()
    for name, y, c in [("Solar, direct", r["pv_load"], C_SUN), ("Stored sun (battery)", r["dis"], C_BATT),
                       ("Grid", r["g"], C_GRID)]:
        fig.add_trace(go.Scatter(x=times, y=y, name=name, stackgroup="src", mode="lines", line=dict(width=0, color=c, shape="hv"),
                                 fillcolor=c, hovertemplate="%{y:.2f} kW"))
    fig.add_trace(go.Scatter(x=times, y=r["pv"], name="Solar available", mode="lines",
                             line=dict(color=C_SUN, width=2, dash="dot"), hovertemplate="%{y:.2f} kW"))
    solar_band(fig)
    fig.update_layout(**LAYOUT, height=330, xaxis=XAX,
                      yaxis=dict(AX, title="kW", showgrid=True, gridcolor="#F0F0F3"))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

a, b = st.columns([1, 1.35], gap="medium")
with a, st.container(border=True):
    html(f'<div class="card-h">Second-life battery</div>'
         f'<div class="card-s">Stored energy, kWh · {r["capacity_kwh"]:.0f} kWh pack (37.5 kWh new at 80% health) · SIMULATED</div>')
    f2 = go.Figure(go.Scatter(x=times + [times[-1] + timedelta(minutes=15)], y=r["soc"], mode="lines",
                              line=dict(color=C_BATT, width=2.5, shape="hv"), fill="tozeroy", fillcolor="rgba(31,122,107,0.10)",
                              name="Stored energy", hovertemplate="%{y:.1f} kWh"))
    f2.update_layout(**LAYOUT, height=290, showlegend=False, xaxis=dict(XAX, dtick=4 * 3600 * 1000),
                     yaxis=dict(AX, title="kWh", showgrid=True, gridcolor="#F0F0F3", rangemode="tozero"))
    st.plotly_chart(f2, width="stretch", config={"displayModeBar": False})

with b, st.container(border=True):
    html('<div class="card-h">Charging schedule per rickshaw</div>'
         '<div class="card-s">Darker = more kW · ◆ marks departure · each row is one charger</div>')
    ids = [x["id"] for x in fleet]
    f3 = go.Figure(go.Heatmap(z=r["x"], x=times, y=ids, colorscale=[[0, "#F4F5F7"], [0.001, "#D6ECE7"], [1, C_BATT]],
                              showscale=False, xgap=0, ygap=3,
                              hovertemplate="%{y} · %{x|%H:%M}<br>%{z:.2f} kW<extra></extra>"))
    dep = [times[labels.index(x["depart"])] for x in fleet]
    f3.add_trace(go.Scatter(x=dep, y=ids, mode="markers", marker=dict(symbol="diamond", size=9, color=INK),
                            hovertemplate="%{y} departs %{x|%H:%M}<extra></extra>", showlegend=False))
    f3.update_layout(**{**LAYOUT, "hovermode": "closest"}, height=290, xaxis=dict(XAX, dtick=4 * 3600 * 1000),
                     yaxis=dict(AX, autorange="reversed", tickfont=dict(color=INK_2, size=12)))
    st.plotly_chart(f3, width="stretch", config={"displayModeBar": False})

# ---------------------------------------------------------------- one rickshaw
html("""<div class="section">For the driver</div>
<p class="sub">Pick a rickshaw to see its slot and the plain message its driver would get on a basic phone.
Drivers and batteries here are SIMULATED placeholders until our Varanasi interviews are entered.</p>""")

with st.container(border=True):
    pick = st.selectbox("Rickshaw", [x["id"] for x in fleet],
                        format_func=lambda i: f"{i} · " + next(x for x in fleet if x["id"] == i)["driver"])
    i = [x["id"] for x in fleet].index(pick)
    rk, xi = fleet[i], r["x"][i]
    total = r["pv_load"] + r["dis"] + r["g"]
    solar_frac = np.divide(r["pv_load"] + r["dis"], total, out=np.zeros_like(total), where=total > 1e-9)
    got = xi.sum() * DT
    sun_pct = (xi * solar_frac).sum() * DT / got * 100 if got else 0
    on = np.flatnonzero(xi > 1e-4)
    night = on[on >= labels.index(rk["arrive"])] if on.size else on
    slot = f"{hhmm(night[0])}–{hhmm(night[-1] + 1)}" if night.size else "—"
    done = hhmm(on[-1] + 1) if on.size else "—"
    ok = pick not in r["unmet_kwh"]
    html(f"""
<div class="rk">
  <div><div class="l">Plugged in</div><div class="v">{rk['arrive']} → {rk['depart']}</div></div>
  <div><div class="l">Needs</div><div class="v">{rk['energy_needed_kwh']:.1f} kWh</div></div>
  <div><div class="l">Full by</div><div class="v" style="color:{'#1D1D1F' if ok else '#B4231C'}">{done if ok else 'Short'}</div></div>
  <div><div class="l">From the sun</div><div class="v">{sun_pct:.0f}%</div></div>
</div>
<div class="card-s" style="margin:4px 0 10px">{rk['battery']} · charger {rk['charger_max_kw']} kW
{(' · lunch top-up ' + '–'.join(rk['midday_window'])) if rk.get('midday_window') else ''}</div>
<div class="sms">📱 <b>{pick}</b> — आज रात चार्जिंग: {slot} · प्रस्थान {rk['depart']} तक पूरा चार्ज ·
आज की बिजली: {sun_pct:.0f}% धूप से ☀️ · शुल्क: ₹___</div>
<div class="card-s" style="margin-top:8px">Fee left blank until field data. A static Hindi page under 50 KB is planned for M3.</div>
""")

# ---------------------------------------------------------------- plan
team = yaml.safe_load((ROOT / "config" / "team.yaml").read_text(encoding="utf-8"))["workstreams"]
owners = "".join(
    f'<div class="owner"><b>{w["name"]}</b>{w["owner"] or "<i>Owner to be confirmed</i>"}<br>'
    f'<span>{w["scope"]}</span></div>' for w in team)
html(f"""
<div class="section">Where we are</div>
<p class="sub">Measured against our own build plan (docs/SPEC.md §12).</p>
<div class="plan">
  <div class="done"><h4>Built so far · M1</h4><ul>
    <li>Wear-aware LP scheduler, plus a grid-only baseline</li>
    <li>UP time-of-day EV tariff and Varanasi seasonal solar (sourced)</li>
    <li>10-rickshaw simulated yard with departure guarantees</li>
    <li>Automated tests: energy balance, battery limits, every rickshaw charged, cost ≤ baseline</li>
    <li>Field-interview templates ready for tonight</li></ul></div>
  <div><h4>Building next · M2, by Check-in 2</h4><ul>
    <li>Heat-aware battery derating (40→55 °C)</li>
    <li>Second-life battery health (SOH) projection</li>
    <li>Real solar: PVGIS hourly data and Open-Meteo forecast, cached offline</li>
    <li>Battery health page: module anomaly alerts</li>
    <li>Field Evidence page from Varanasi interviews</li></ul>
    <h4 style="margin-top:16px">Then · M3</h4><ul>
    <li>Sizing &amp; honest payback heatmaps</li><li>Hindi driver page</li></ul></div>
  <div><h4>Team</h4>{owners}</div>
</div>
<div class="foot">
<b>Data provenance.</b> SOURCE: UPERC FY2026-27 LMV-11 tariff ₹7.70/kWh with 20% off 09:00–16:00 (F3);
Varanasi solar yield 3.66–6.31 kWh/kWp/day (F10); fossil generation 125 GW at 1 pm vs 168 GW at night, Ember via Down To Earth (F2).
ASSUMPTION: battery size, efficiency, ₹5,000/kWh price and 2,000-cycle life; 10 kW sanctioned load; charger power.
SIMULATED: all rickshaws, drivers and battery telemetry. Charger CC-CV taper is not modelled. Every parameter is in
config/assumptions.yaml.
</div>
""")
