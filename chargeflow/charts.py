"""Plotly figures for the ChargeFlow dashboard, styled to the ui.py design system."""
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from scheduler import END_H, NIGHT_H, SLOT_H, START_H
from ui import (AMBER, AMBER_TEXT, COBALT, GRAPHITE, GRID, INK, INK_2, INK_3, MONO, RULE, SANS, SOLAR, STORAGE,
                VERMILION)

DAY0 = datetime(2026, 10, 10)
CONFIG = {"displayModeBar": False, "responsive": True}


def to_dt(h):
    return DAY0 + timedelta(hours=float(h))


def hhmm(h):
    return to_dt(h).strftime("%H:%M")


def _rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{alpha})"


def _axis_x(full_day=False):
    start = START_H if full_day else NIGHT_H
    return dict(type="date", range=[to_dt(start), to_dt(END_H)], tickformat="%H:%M", hoverformat="%H:%M",
                dtick=3600000 * 3, tickangle=0, showgrid=False, showline=True, linecolor=INK, linewidth=1,
                ticks="outside", tickcolor=INK, ticklen=4, tickfont=dict(family=MONO, size=11, color=INK_2),
                fixedrange=True, automargin=True)


def _axis_y(suffix="", rng=None, dtick=None):
    return dict(gridcolor=GRID, gridwidth=1, zeroline=False, showline=False, ticksuffix=suffix,
                tickfont=dict(family=MONO, size=11, color=INK_3), rangemode="tozero", fixedrange=True, range=rng,
                dtick=dtick, nticks=7, automargin=True, ticklabelstandoff=10)


def _base(fig, height, transition_ms, legend=True, top=40):
    fig.update_layout(
        height=height, margin=dict(l=4, r=8, t=top if legend else 12, b=4),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=SANS, size=12.5, color=INK_2), hovermode="x unified",
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=RULE, font=dict(family=MONO, size=12, color=INK)),
        showlegend=legend,
        legend=dict(orientation="h", x=0, xanchor="left", y=1.0, yanchor="bottom", traceorder="normal",
                    font=dict(family=SANS, size=12.5, color=INK_2), bgcolor="rgba(0,0,0,0)",
                    itemclick="toggle", itemdoubleclick="toggleothers"),
        transition=dict(duration=transition_ms, easing="cubic-in-out"),
    )
    return fig


def _with_crossings(x_h, y, level):
    """Insert points where y crosses level, so an over-limit fill meets the line exactly."""
    xs, ys = [x_h[0]], [y[0]]
    for i in range(1, len(y)):
        a, b = y[i - 1] - level, y[i] - level
        if a * b < 0:
            t = a / (a - b)
            xs.append(x_h[i - 1] + t * (x_h[i] - x_h[i - 1]))
            ys.append(level)
        xs.append(x_h[i])
        ys.append(y[i])
    return np.array(xs), np.array(ys)


def _panel_label(fig, text, yref):
    fig.add_annotation(xref="paper", yref=yref, x=0, y=1, xanchor="left", yanchor="bottom", showarrow=False,
                       text=text, font=dict(family=MONO, size=10.5, color=INK_3), yshift=4)


def load_chart(times, series, focus, limit_kw, active, household=None, transition_ms=260):
    """Two panels on one time axis.
    series: (key, name, colour, dash, grid kW per slot); active: (key, name, colour, chargers on per slot)."""
    night = times >= NIGHT_H
    t = times[night] + SLOT_H / 2
    x = [to_dt(h) for h in t]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.74, 0.26], vertical_spacing=0.09)
    peak_val = max(float(s[4][night].max()) for s in series)

    if household is not None:
        fig.add_trace(go.Scatter(x=x, y=household[night], name="Household (lights, fans)", mode="lines",
                                 line=dict(color=INK_3, width=1.2, dash="dot"), hovertemplate="%{y:.2f} kW"), 1, 1)
    over_legend = False
    for key, name, color, dash, load in sorted(series, key=lambda s: s[0] == focus):
        y = load[night]
        is_focus = key == focus
        if y.max() > limit_kw + 1e-9:
            cx, cy = _with_crossings(t, y, limit_kw)
            cxd = [to_dt(h) for h in cx]
            fig.add_trace(go.Scatter(x=cxd, y=np.full(len(cx), limit_kw), mode="lines", line=dict(width=0),
                                     hoverinfo="skip", showlegend=False), 1, 1)
            fig.add_trace(go.Scatter(x=cxd, y=np.maximum(cy, limit_kw), mode="lines", line=dict(width=0),
                                     fill="tonexty", fillcolor=_rgba(VERMILION, .16), hoverinfo="skip",
                                     name="Above sanctioned load", showlegend=not over_legend, legendrank=900), 1, 1)
            over_legend = True
        fig.add_trace(go.Scatter(
            x=x, y=y, name=name, mode="lines", legendrank=1 if is_focus else 10,
            line=dict(color=color, width=2.4 if is_focus else 1.5, dash=dash),
            fill="tozeroy" if is_focus else None, fillcolor=_rgba(color, .10) if is_focus else None,
            hovertemplate="%{y:.1f} kW"), 1, 1)
        if is_focus or key == "uncontrolled":
            k = int(np.argmax(y))
            near = 0 <= limit_kw - y[k] < 0.18 * limit_kw
            fig.add_trace(go.Scatter(x=[x[k]], y=[y[k]], mode="markers", showlegend=False, hoverinfo="skip",
                                     marker=dict(size=7, color="#FFFFFF", line=dict(color=color, width=2))), 1, 1)
            fig.add_annotation(x=x[k], y=y[k], xref="x", yref="y", showarrow=False, xanchor="left", xshift=9,
                               yshift=-14 if near else 12, text=f"peak {y[k]:.1f} kW · {hhmm(t[k] - SLOT_H / 2)}",
                               font=dict(family=MONO, size=11, color=INK), bgcolor="rgba(255,255,255,.9)", borderpad=2)

    fig.add_hline(y=limit_kw, line=dict(color=AMBER, width=1.6), row=1, col=1)
    fig.add_annotation(xref="paper", yref="y", x=1, y=limit_kw, xanchor="right", yanchor="bottom", showarrow=False,
                       text=f"SANCTIONED {limit_kw:.1f} kW", font=dict(family=MONO, size=10.5, color=AMBER_TEXT),
                       bgcolor="rgba(255,255,255,.9)", borderpad=2, yshift=2)

    n_max = 1
    for key, name, color, on in sorted(active, key=lambda s: s[0] == focus):
        y = on[night]
        n_max = max(n_max, int(y.max()))
        if key == focus:
            fig.add_trace(go.Bar(x=x, y=y, name=f"{name}: chargers on", marker_color=_rgba(color, .85),
                                 marker_line_width=0, width=SLOT_H * 3600000 * 0.78, showlegend=False,
                                 hovertemplate="%{y} on"), 2, 1)
        else:
            fig.add_trace(go.Scatter(x=x, y=y, name=f"{name}: chargers on", mode="lines", line_shape="hvh",
                                     line=dict(color=color, width=1.2), showlegend=False,
                                     hovertemplate="%{y} on"), 2, 1)

    _base(fig, 520, transition_ms, top=44)
    fig.update_layout(bargap=0, uirevision="load")
    fig.update_xaxes(_axis_x())
    fig.update_xaxes(showticklabels=False, ticks="", row=1, col=1)
    fig.update_yaxes(_axis_y(" kW", [0, max(peak_val, limit_kw) * 1.2]), row=1, col=1)
    fig.update_yaxes(_axis_y("", [0, n_max * 1.15 + 0.5], dtick=max(1, round(n_max / 3))), row=2, col=1)
    _panel_label(fig, "CHARGERS DRAWING POWER", "y2 domain")
    return fig


def departure_chart(names, soc_arrive, scenarios, focus, target_pct, transition_ms=260):
    """Range from arrival to departure charge for the plan; marks for the alternatives."""
    fig = go.Figure()
    plan = next(s for s in scenarios if s[0] == focus)
    dep = plan[3] * 100
    arr = np.asarray(soc_arrive) * 100
    fig.add_trace(go.Bar(x=names, y=dep - arr, base=arr, name="Charge added overnight",
                         marker_color=_rgba(plan[2], .18), marker_line_width=0, width=0.42, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=names, y=arr, mode="markers", name="On arrival",
                             marker=dict(size=8, color="#FFFFFF", line=dict(color=INK_3, width=1.5)),
                             hovertemplate="arrives %{y:.0f}%"))
    for key, name, color, soc in scenarios:
        if key != focus:
            fig.add_trace(go.Scatter(x=names, y=soc * 100, mode="markers", name=name,
                                     marker=dict(size=14, color=color, symbol="line-ew", line=dict(color=color, width=2)),
                                     hovertemplate=f"{name}: %{{y:.0f}}%<extra></extra>"))
    fig.add_trace(go.Scatter(x=names, y=dep, mode="markers", name=f"{plan[1]}, at departure",
                             marker=dict(size=10, color=plan[2], line=dict(color="#FFFFFF", width=1.5)),
                             hovertemplate="leaves %{y:.0f}%"))
    fig.add_hline(y=target_pct, line=dict(color=INK_3, width=1, dash="dash"))
    fig.add_annotation(xref="paper", yref="y", x=0, y=target_pct, xanchor="left", yanchor="bottom", showarrow=False,
                       text=f"READY AT {target_pct}%", font=dict(family=MONO, size=10.5, color=INK_2),
                       bgcolor="rgba(255,255,255,.9)", borderpad=2, yshift=2)
    _base(fig, 380, transition_ms)
    fig.update_layout(barmode="overlay", uirevision="departure",
                      xaxis=dict(showgrid=False, showline=True, linecolor=INK, fixedrange=True, automargin=True,
                                 tickfont=dict(family=MONO, size=11, color=INK_2)),
                      yaxis=_axis_y("%", [0, 106], dtick=20))
    return fig


def soc_chart(times, series, focus, target_pct, transition_ms=260):
    """series: (key, name, colour, dash, state of charge per slot) for one rickshaw."""
    fig = go.Figure()
    x = [to_dt(h) for h in times]
    for key, name, color, dash, soc in sorted(series, key=lambda s: s[0] == focus):
        fig.add_trace(go.Scatter(x=x, y=soc * 100, name=name, mode="lines", hovertemplate="%{y:.0f}%",
                                 line=dict(color=color, width=2.4 if key == focus else 1.5, dash=dash)))
    fig.add_hline(y=target_pct, line=dict(color=INK_3, width=1, dash="dash"))
    _base(fig, 300, transition_ms)
    fig.update_layout(uirevision="soc", xaxis=_axis_x(), yaxis=_axis_y("%", [0, 106], dtick=20))
    return fig


def supply_chart(times, direct, from_store, grid, solar, limit_kw, transition_ms=260):
    """Stacked supply by source; grid at the bottom so its top edge is the import the
    sanctioned-load line applies to."""
    fig = go.Figure()
    x = [to_dt(h + SLOT_H / 2) for h in times]
    for name, y, color in (("From the grid", grid, COBALT), ("From second-life pack", from_store, STORAGE),
                           ("Solar, used directly", direct, SOLAR)):
        fig.add_trace(go.Scatter(x=x, y=y, name=name, mode="lines", stackgroup="supply",
                                 line=dict(width=0.8, color="#FFFFFF"), fillcolor=_rgba(color, .82),
                                 hovertemplate="%{y:.1f} kW"))
    fig.add_trace(go.Scatter(x=x, y=solar, name="Solar generated", mode="lines",
                             line=dict(color="#9A7400", width=1.5, dash="dot"), hovertemplate="%{y:.1f} kW"))
    fig.add_hline(y=limit_kw, line=dict(color=AMBER, width=1.6))
    fig.add_annotation(xref="paper", yref="y", x=1, y=limit_kw, xanchor="right", yanchor="bottom", showarrow=False,
                       text=f"SANCTIONED {limit_kw:.1f} kW", font=dict(family=MONO, size=10.5, color=AMBER_TEXT),
                       bgcolor="rgba(255,255,255,.9)", borderpad=2, yshift=2)
    fig.add_vline(x=to_dt(NIGHT_H), line=dict(color=INK_3, width=1, dash="dot"))
    fig.add_annotation(x=to_dt(NIGHT_H), yref="paper", y=1, xanchor="left", yanchor="top", showarrow=False, xshift=6,
                       text="DRIVERS RETURN", font=dict(family=MONO, size=10.5, color=INK_3))
    peak = max(float((direct + from_store + grid).max()), float(solar.max()), limit_kw)
    _base(fig, 380, transition_ms)
    fig.update_layout(uirevision="supply", xaxis=_axis_x(True), yaxis=_axis_y(" kW", [0, peak * 1.2]))
    return fig


def pack_chart(times, store_kwh, usable_kwh, label, transition_ms=260):
    fig = go.Figure()
    x = [to_dt(h + SLOT_H) for h in times]
    fig.add_trace(go.Scatter(x=x, y=store_kwh, name="Energy in the pack", mode="lines",
                             line=dict(color=STORAGE, width=2), fill="tozeroy", fillcolor=_rgba(STORAGE, .12),
                             hovertemplate="%{y:.1f} kWh"))
    fig.add_hline(y=usable_kwh, line=dict(color=INK_3, width=1, dash="dash"))
    fig.add_annotation(xref="paper", yref="y", x=0, y=usable_kwh, xanchor="left", yanchor="bottom", showarrow=False,
                       text=label.upper(), font=dict(family=MONO, size=10.5, color=INK_2),
                       bgcolor="rgba(255,255,255,.9)", borderpad=2, yshift=2)
    _base(fig, 250, transition_ms, legend=False)
    fig.update_layout(uirevision="pack", xaxis=_axis_x(True), yaxis=_axis_y(" kWh", [0, usable_kwh * 1.3]))
    return fig


def health_chart(names, h, status, transition_ms=260):
    """Estimated health per pack with the 80% (watch) and 60% (replace) lines."""
    col = {"Good": COBALT, "Watch": AMBER, "Replace": VERMILION}
    fig = go.Figure(go.Bar(x=names, y=[v * 100 for v in h], marker_color=[col[s] for s in status],
                           marker_line_width=0, width=0.5, text=[f"{v * 100:.0f}% · {s}" for v, s in zip(h, status)],
                           textposition="outside", textfont=dict(family=MONO, size=12, color=INK),
                           hovertemplate="%{x}: %{y:.0f}%<extra></extra>"))
    for y, lab in ((80, "WATCH BELOW 80%"), (60, "REPLACE BELOW 60%")):
        fig.add_hline(y=y, line=dict(color=INK_3, width=1, dash="dash"))
        fig.add_annotation(xref="paper", yref="y", x=1, y=y, xanchor="right", yanchor="bottom", showarrow=False,
                           text=lab, font=dict(family=MONO, size=10.5, color=INK_2), bgcolor="rgba(255,255,255,.9)")
    _base(fig, 300, transition_ms, legend=False)
    fig.update_layout(uirevision="health",
                      xaxis=dict(showgrid=False, showline=True, linecolor=INK, fixedrange=True, automargin=True,
                                 tickfont=dict(family=MONO, size=12, color=INK_2), type="category",
                                 range=[-0.5, max(len(names), 8) - 0.5]),
                      yaxis=_axis_y("%", [0, 115], dtick=20))
    return fig


def measured_chart(index, total, limit_kw, transition_ms=260):
    """Measured charger load from a smart-plug log against the sanctioned load."""
    fig = go.Figure()
    x = list(index + pd.Timedelta(minutes=7.5))
    if max(total) > limit_kw:
        fig.add_trace(go.Scatter(x=x, y=[limit_kw] * len(x), mode="lines", line=dict(width=0), hoverinfo="skip",
                                 showlegend=False))
        fig.add_trace(go.Scatter(x=x, y=np.maximum(total, limit_kw), mode="lines", line=dict(width=0), fill="tonexty",
                                 fillcolor=_rgba(VERMILION, .16), hoverinfo="skip", name="Above sanctioned load"))
    fig.add_trace(go.Scatter(x=x, y=total, mode="lines", name="Measured charger load", line=dict(color=GRAPHITE, width=2),
                             hovertemplate="%{y:.2f} kW"))
    fig.add_hline(y=limit_kw, line=dict(color=AMBER, width=1.6))
    fig.add_annotation(xref="paper", yref="y", x=1, y=limit_kw, xanchor="right", yanchor="bottom", showarrow=False,
                       text=f"SANCTIONED {limit_kw:.1f} kW", font=dict(family=MONO, size=10.5, color=AMBER_TEXT),
                       bgcolor="rgba(255,255,255,.9)", borderpad=2, yshift=2)
    _base(fig, 320, transition_ms)
    fig.update_layout(uirevision="measured",
                      xaxis=dict(type="date", tickformat="%H:%M", hoverformat="%H:%M", showgrid=False, showline=True,
                                 linecolor=INK, ticks="outside", tickcolor=INK, fixedrange=True, automargin=True,
                                 tickfont=dict(family=MONO, size=11, color=INK_2)),
                      yaxis=_axis_y(" kW", [0, max(max(total), limit_kw) * 1.2]))
    return fig


def replan_chart(times, k_now, done_kw, plan_kw, fixed_kw, sun_fc, sun_now, limit_kw, transition_ms=0):
    """Grid import carried out so far and the plan from now on, against the 18:00 plan followed
    blindly; solar measured so far and forecast."""
    fig = go.Figure()
    night = times >= NIGHT_H
    idx = np.arange(len(times))
    x = np.array([to_dt(h + SLOT_H / 2) for h in times])
    past = night & (idx < k_now)
    ahead = night & (idx >= k_now)
    fig.add_trace(go.Scatter(x=x[night], y=sun_fc[night], name="Solar forecast", mode="lines",
                             line=dict(color="#9A7400", width=1.2, dash="dot"), hovertemplate="%{y:.1f} kW"))
    if past.any():
        fig.add_trace(go.Scatter(x=x[past], y=sun_now[past], name="Solar measured", mode="lines",
                                 line=dict(color=SOLAR, width=1.8), hovertemplate="%{y:.1f} kW"))
        fig.add_trace(go.Scatter(x=x[past], y=fixed_kw[past], name="18:00 plan followed blindly", mode="lines",
                                 line=dict(color=GRAPHITE, width=1.4), hovertemplate="%{y:.1f} kW"))
        fig.add_trace(go.Scatter(x=x[past], y=done_kw[past], name="Grid import with re-planning", mode="lines",
                                 line=dict(color=COBALT, width=2.4), fill="tozeroy", fillcolor=_rgba(COBALT, .10),
                                 hovertemplate="%{y:.1f} kW"))
    if ahead.any() and plan_kw is not None:
        join = ahead | (idx == k_now - 1) & night
        y = np.where(idx == k_now - 1, done_kw, plan_kw)
        fig.add_trace(go.Scatter(x=x[join], y=y[join], name="Plan from now", mode="lines",
                                 line=dict(color=COBALT, width=1.8, dash="dash"), hovertemplate="%{y:.1f} kW"))
    fig.add_hline(y=limit_kw, line=dict(color=AMBER, width=1.6))
    fig.add_annotation(xref="paper", yref="y", x=1, y=limit_kw, xanchor="right", yanchor="bottom", showarrow=False,
                       text=f"SANCTIONED {limit_kw:.1f} kW", font=dict(family=MONO, size=10.5, color=AMBER_TEXT),
                       bgcolor="rgba(255,255,255,.9)", borderpad=2, yshift=2)
    if k_now < len(times):
        fig.add_vline(x=to_dt(times[k_now]), line=dict(color=INK, width=1))
        fig.add_annotation(x=to_dt(times[k_now]), yref="paper", y=1, xanchor="left", yanchor="top", showarrow=False,
                           xshift=6, text=f"NOW {hhmm(times[k_now])}", font=dict(family=MONO, size=10.5, color=INK))
    top = max(float(np.nanmax(np.r_[done_kw[night], fixed_kw[night], sun_fc[night]])), limit_kw)
    _base(fig, 420, transition_ms, top=44)
    fig.update_layout(uirevision="replan", xaxis=_axis_x(), yaxis=_axis_y(" kW", [0, top * 1.2]))
    return fig


def month_chart(dates, series, sun, transition_ms=0):
    """Two panels on one date axis: grid electricity per night for each strategy, and each day's sun.
    series: (name, colour, dash, rupees per night)."""
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.1)
    for name, color, dash, y in series:
        fig.add_trace(go.Scatter(x=dates, y=y, name=name, mode="lines+markers", line=dict(color=color, width=2, dash=dash),
                                 marker=dict(size=5, color=color), hovertemplate="₹%{y:,.0f}"), 1, 1)
    fig.add_trace(go.Bar(x=dates, y=sun, name="Sun that day", marker_color=_rgba(SOLAR, .85), marker_line_width=0,
                         showlegend=False, hovertemplate="%{y:.1f} kWh per kW of panels"), 2, 1)
    top = max(max(s[3]) for s in series)
    _base(fig, 440, transition_ms, top=44)
    fig.update_layout(bargap=0.25, uirevision="month", hovermode="x unified")
    xa = dict(type="date", tickformat="%d %b", hoverformat="%a %d %b", showgrid=False, showline=True, linecolor=INK,
              ticks="outside", tickcolor=INK, ticklen=4, tickfont=dict(family=MONO, size=11, color=INK_2),
              fixedrange=True, automargin=True)
    fig.update_xaxes(xa)
    fig.update_xaxes(showticklabels=False, ticks="", row=1, col=1)
    fig.update_yaxes(_axis_y("", [0, top * 1.15]), tickprefix="₹", row=1, col=1)
    fig.update_yaxes(_axis_y("", [0, max(5.0, max(sun) * 1.1)], dtick=2), row=2, col=1)
    _panel_label(fig, "SUN THAT DAY · kWh PER kW OF PANELS", "y2 domain")
    return fig
