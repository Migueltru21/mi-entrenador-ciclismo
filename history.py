"""
history.py — Memoria del plan completo, no solo la semana actual.

Acumula lo que realmente has hecho desde el inicio del plan de carrera:
horas totales, desnivel, carga (TSS), y progreso semana a semana. Así la app
tiene "historia" y no se reinicia visualmente al cambiar de semana.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta

import race_plan as rp


@dataclass
class SemanaResumen:
    sem: int
    lunes: date
    horas: float
    tss: float
    desnivel_m: float
    n_actividades: int
    completada: bool     # True si la semana ya pasó
    en_curso: bool
    carga_obj: int | None


def _horas(act) -> float:
    s = getattr(act, "duration_s", None) or 0
    return s / 3600.0


def resumen_por_semana(activities: list, hoy: date = None,
                       race_date: date = rp.RACE_DATE) -> list[SemanaResumen]:
    """Recorre todo el plan y acumula lo hecho en cada semana."""
    if hoy is None:
        hoy = date.today()
    out = []
    for info in rp.PLAN:
        n = info["sem"]
        ini = rp.lunes_de_semana(n, race_date)
        fin = ini + timedelta(days=6)
        acts = [a for a in activities if ini <= a.day <= fin]
        horas = round(sum(_horas(a) for a in acts), 1)
        tss = round(sum(a.tss for a in acts), 0)
        desnivel = round(sum(getattr(a, "elev_gain_m", 0) or 0 for a in acts))
        out.append(SemanaResumen(
            sem=n, lunes=ini, horas=horas, tss=tss, desnivel_m=desnivel,
            n_actividades=len(acts),
            completada=(fin < hoy),
            en_curso=(ini <= hoy <= fin),
            carga_obj=info.get("carga_obj"),
        ))
    return out


def acumulado_total(resumenes: list[SemanaResumen]) -> dict:
    """Totales del bloque hasta hoy (solo semanas completadas o en curso)."""
    vividas = [r for r in resumenes if r.completada or r.en_curso]
    return {
        "horas": round(sum(r.horas for r in vividas), 1),
        "tss": round(sum(r.tss for r in vividas)),
        "desnivel_m": round(sum(r.desnivel_m for r in vividas)),
        "semanas_hechas": len([r for r in resumenes if r.completada]),
        "semanas_total": len(resumenes),
        "actividades": sum(r.n_actividades for r in vividas),
    }


def progreso_largos(activities: list, hoy: date = None,
                    race_date: date = rp.RACE_DATE) -> list[dict]:
    """El largo más grande (en horas) hecho cada semana vs el objetivo.
    Sirve para ver si la progresión de resistencia va en camino."""
    if hoy is None:
        hoy = date.today()
    out = []
    for info in rp.PLAN:
        n = info["sem"]
        ini = rp.lunes_de_semana(n, race_date)
        fin = ini + timedelta(days=6)
        acts = [a for a in activities if ini <= a.day <= fin]
        mayor = max((_horas(a) for a in acts), default=0.0)
        out.append({
            "sem": n,
            "objetivo_h": info.get("sabado_h"),
            "hecho_h": round(mayor, 1),
            "en_curso": ini <= hoy <= fin,
            "completada": fin < hoy,
        })
    return out
