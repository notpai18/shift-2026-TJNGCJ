"""Load config/assumptions.yaml and expose time-grid helpers."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "assumptions.yaml"


def load_config(path=CONFIG_PATH):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def to_minutes(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def step_index(hhmm, cfg):
    """Index of the 15-min step a clock time falls in, on the 08:00→08:00 horizon."""
    start = to_minutes(cfg["time"]["horizon_start"])
    step = cfg["time"]["step_minutes"]
    return ((to_minutes(hhmm) - start) % (24 * 60)) // step


def n_steps(cfg):
    return 24 * 60 // cfg["time"]["step_minutes"]


def dt_hours(cfg):
    return cfg["time"]["step_minutes"] / 60


def clock_labels(cfg):
    start = to_minutes(cfg["time"]["horizon_start"])
    step = cfg["time"]["step_minutes"]
    return [f"{((start + k * step) // 60) % 24:02d}:{(start + k * step) % 60:02d}"
            for k in range(n_steps(cfg))]
