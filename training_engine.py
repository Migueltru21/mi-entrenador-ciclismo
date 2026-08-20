"""training_engine.py — Núcleo: TSS y PMC (CTL/ATL/TSB)."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
import math


@dataclass
class Activity:
    day: date
    tss: float
    np_watts: float | None = None
    ftp_at_time: float | None = None
    duration_s: float | None = None
    best_5min_w: float | None = None
    elev_gain_m: float | None = None
    name: str | None = None


@dataclass
class PmcPoint:
    day: date
    tss: float
    ctl: float
    atl: float
    tsb: float


def build_pmc(activities, ctl_days=42, atl_days=7):
    if not activities:
        return []
    by_day = {}
    for a in activities:
        by_day[a.day] = by_day.get(a.day, 0.0) + a.tss
    start, end = min(by_day), max(max(by_day), date.today())
    ctl_k = 1 - math.exp(-1 / ctl_days)
    atl_k = 1 - math.exp(-1 / atl_days)
    ctl = atl = 0.0
    out, d = [], start
    while d <= end:
        tss = by_day.get(d, 0.0)
        ctl += ctl_k * (tss - ctl)
        atl += atl_k * (tss - atl)
        out.append(PmcPoint(d, round(tss, 1), round(ctl, 1), round(atl, 1),
                            round(ctl - atl, 1)))
        d += timedelta(days=1)
    return out


def interpret_form(tsb):
    if tsb > 15:   return "Muy fresco / desentrenando"
    if tsb > 5:    return "Fresco: ideal para objetivo"
    if tsb >= -10: return "Equilibrado: zona productiva"
    if tsb >= -30: return "Cargado: vigila la recuperación"
    return "Muy cargado: alto riesgo, mete descanso"


def ramp_rate(pmc, days=7):
    if len(pmc) <= days:
        return 0.0
    return round(pmc[-1].ctl - pmc[-1 - days].ctl, 1)
