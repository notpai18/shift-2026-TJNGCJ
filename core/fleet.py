"""Fleet of rickshaws: load/generate the SIMULATED demo yard and build availability."""
import json
import random

import numpy as np

from core.config import ROOT, n_steps, step_index

FLEET_PATH = ROOT / "data" / "fleet" / "rickshaws.json"

SEED_RICKSHAWS = [
    {"id": "R01", "driver": "Driver A", "battery": "lead-acid 48V 120Ah", "energy_needed_kwh": 6.0,
     "charger_max_kw": 1.0, "arrive": "19:30", "depart": "06:30", "midday_window": None},
    {"id": "R02", "driver": "Driver B", "battery": "lead-acid 48V 100Ah", "energy_needed_kwh": 5.0,
     "charger_max_kw": 0.9, "arrive": "20:00", "depart": "06:00", "midday_window": ["13:00", "14:30"]},
    {"id": "R03", "driver": "Driver C", "battery": "lithium 51V 105Ah", "energy_needed_kwh": 5.2,
     "charger_max_kw": 1.5, "arrive": "21:00", "depart": "07:00", "midday_window": None},
]


def _hhmm(minutes):
    return f"{minutes // 60 % 24:02d}:{minutes % 60:02d}"


def generate_fleet(n=10, seed=42):
    """3 spec rickshaws + (n-3) seeded random ones. All values ASSUMPTION / SIMULATED."""
    rng = random.Random(seed)
    fleet = [dict(r) for r in SEED_RICKSHAWS]
    for k in range(len(fleet) + 1, n + 1):
        ah = rng.choice([100, 110, 120])
        midday = None
        if rng.random() < 0.3:
            start = rng.randrange(12 * 60, 14 * 60 + 1, 15)
            midday = [_hhmm(start), _hhmm(start + rng.choice([60, 75, 90]))]
        fleet.append({
            "id": f"R{k:02d}",
            "driver": f"Driver {chr(64 + k)}",
            "battery": f"lead-acid 48V {ah}Ah",
            "energy_needed_kwh": round(rng.uniform(4.5, 6.5), 1),
            "charger_max_kw": rng.choice([0.9, 1.0, 1.2]),
            "arrive": _hhmm(rng.randrange(19 * 60, 22 * 60 + 31, 15)),
            "depart": _hhmm(rng.randrange(5 * 60 + 30, 7 * 60 + 31, 15)),
            "midday_window": midday,
        })
    return {"label": "SIMULATED — 10-rickshaw demo yard; replace with FIELD data", "rickshaws": fleet}


def load_fleet(path=FLEET_PATH):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(generate_fleet(), indent=2, ensure_ascii=False), encoding="utf-8")
    return json.loads(path.read_text(encoding="utf-8"))


def _window(avail_row, start, end, cfg):
    a, b = step_index(start, cfg), step_index(end, cfg)
    if a <= b:
        avail_row[a:b] = 1
    else:  # wraps the end of the horizon
        avail_row[a:] = 1
        avail_row[:b] = 1


def availability(rickshaws, cfg):
    """avail[i, t] = 1 when rickshaw i is plugged in (night window + optional midday window)."""
    avail = np.zeros((len(rickshaws), n_steps(cfg)), dtype=int)
    for i, r in enumerate(rickshaws):
        _window(avail[i], r["arrive"], r["depart"], cfg)
        if r.get("midday_window"):
            _window(avail[i], *r["midday_window"], cfg)
    return avail
