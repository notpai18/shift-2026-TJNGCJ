"""Smart-plug logs: read a CSV of power readings per charger, summarise it, and make a
clearly simulated sample log for demos."""
import numpy as np
import pandas as pd

from scheduler import SLOT_H

ALIASES = {
    "timestamp": ["timestamp", "time", "datetime", "date_time"],
    "vehicle": ["vehicle", "charger", "id", "device", "rickshaw"],
    "power": ["power_kw", "kw", "power", "power_w", "watts"],
}


def parse(file):
    """Returns (per-slot kW per vehicle, building total kW, per-vehicle summary).
    Raises ValueError with a readable message on a bad file."""
    try:
        df = pd.read_csv(file)
    except Exception as e:  # noqa: BLE001 - surface any CSV problem to the user
        raise ValueError(f"Could not read the CSV: {e}")
    cols = {str(c).lower().strip(): c for c in df.columns}
    pick = {}
    for key, names in ALIASES.items():
        found = next((cols[n] for n in names if n in cols), None)
        if found is None:
            raise ValueError(f"Missing a {key} column. Accepted names: {', '.join(names)}.")
        pick[key] = found
    out = pd.DataFrame({"t": pd.to_datetime(df[pick["timestamp"]], errors="coerce"),
                        "v": df[pick["vehicle"]].astype(str),
                        "kw": pd.to_numeric(df[pick["power"]], errors="coerce")}).dropna()
    if str(pick["power"]).lower().strip() in ("power_w", "watts"):
        out["kw"] = out["kw"] / 1000
    if out.empty:
        raise ValueError("No readable rows (check the timestamp and power columns).")
    out["slot"] = out["t"].dt.floor("15min")
    grid = out.groupby(["slot", "v"])["kw"].mean().unstack(fill_value=0).sort_index()
    grid = grid.reindex(pd.date_range(grid.index.min(), grid.index.max(), freq="15min"), fill_value=0)
    rows = []
    for v in grid.columns:
        on = grid.index[grid[v] > 0.05]
        if len(on) == 0:
            continue
        rows.append(dict(vehicle=v, start=on.min(), end=on.max() + pd.Timedelta(minutes=15),
                         kwh=float(grid[v].sum() * SLOT_H), kw=float(grid[v][grid[v] > 0.05].quantile(0.9))))
    if not rows:
        raise ValueError("No charger drew more than 50 W in this log.")
    return grid, grid.sum(axis=1), pd.DataFrame(rows)


def sample_csv(vehicles, day="2026-10-10"):
    """SIMULATED log: each vehicle charging uncontrolled (on at plug-in, floating when full),
    one reading every 5 minutes. vehicles: (name, arrive_h, leave_h, Battery, charge on arrival)."""
    base, recs = pd.Timestamp(day), []
    for name, a, b, bat, soc in vehicles:
        t = a
        while t < b - 1e-9:
            if soc >= 0.999:
                kw = bat.float_kw()
            else:
                kw = bat.charge_kw(soc)
                soc = bat.step(soc, kw)
            for m in (0, 5, 10):
                recs.append((base + pd.Timedelta(hours=t, minutes=m), name, round(kw, 3)))
            t += SLOT_H
    df = pd.DataFrame(recs, columns=["timestamp", "vehicle", "power_kw"]).sort_values(["timestamp", "vehicle"])
    return df.to_csv(index=False).encode("utf-8")
