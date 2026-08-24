"""
week_review.py — Seguimiento de la semana en curso.

Responde a tres preguntas que un entrenador mira cada día:
  1. ¿Qué tocaba y qué he hecho realmente?
  2. ¿Cuánta carga llevo vs la planeada?
  3. ¿Cómo va quedando mi forma (CTL/ATL/TSB) y cómo terminará la semana?
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
import math

from training_engine import Activity, build_pmc

DIAS_OFFSET = {"Mar": 1, "Mié": 2, "Jue": 3, "Vie": 4, "Sáb": 5}


@dataclass
class DayStatus:
    dia: str
    fecha: date
    planeado: str          # nombre de la sesión, o "Descanso"
    tss_plan: int
    hecho: bool
    tss_real: float
    estado: str            # "hecho" | "pendiente" | "saltado" | "descanso" | "extra"


def _tss_del_dia(acts: list[Activity], d: date) -> float:
    return round(sum(a.tss for a in acts if a.day == d), 1)


def week_status(plan_week: dict, inicio: date, activities: list[Activity],
                sessions: dict, names: dict, tss_fn) -> list[DayStatus]:
    """Compara el plan de la semana con lo que realmente entrenaste.
    `inicio` es el lunes de ESA semana (ya desplazado por nº de semana)."""
    hoy = date.today()
    filas: list[DayStatus] = []

    # Lunes y domingo del plan = descanso, pero pueden tener actividad "extra"
    todos = [("Lun", 0)] + [(d, o) for d, o in DIAS_OFFSET.items()] + [("Dom", 6)]

    for dia, off in todos:
        fecha = inicio + timedelta(days=off)
        key = plan_week["dias"].get(dia)
        tss_real = _tss_del_dia(activities, fecha)
        hecho = tss_real > 0

        if key is None:
            nombre, tss_plan = "Descanso", 0
            estado = "extra" if hecho else "descanso"
        else:
            nombre, tss_plan = names[key], tss_fn(sessions[key])
            if hecho:
                estado = "hecho"
            elif fecha < hoy:
                estado = "saltado"
            else:
                estado = "pendiente"

        filas.append(DayStatus(dia, fecha, nombre, tss_plan, hecho,
                               tss_real, estado))
    return filas


def week_totals(filas: list[DayStatus]) -> dict:
    """Resumen de la semana: carga planeada, hecha, pendiente y adherencia."""
    tss_plan = sum(f.tss_plan for f in filas)
    tss_real = sum(f.tss_real for f in filas)
    pendiente = sum(f.tss_plan for f in filas if f.estado == "pendiente")
    con_sesion = [f for f in filas if f.tss_plan > 0]
    ya_paso = [f for f in con_sesion if f.estado in ("hecho", "saltado")]
    cumplidos = [f for f in ya_paso if f.estado == "hecho"]
    pct = round(100 * len(cumplidos) / len(ya_paso)) if ya_paso else None
    return {
        "tss_plan": tss_plan,
        "tss_real": round(tss_real),
        "tss_pendiente": pendiente,
        "sesiones_plan": len(con_sesion),
        "sesiones_hechas": len([f for f in filas if f.estado in ("hecho", "extra")]),
        "adherencia_pct": pct,          # None si aún no ha pasado ningún día
        "saltadas": len([f for f in ya_paso if f.estado == "saltado"]),
    }


# --------------------------------------------------------------------------- #
# Impacto en la forma: dónde estabas, dónde estás y dónde acabarás
# --------------------------------------------------------------------------- #
def _simular(activities: list[Activity], futuros: dict[date, float],
             hasta: date, ctl_days=42, atl_days=7):
    """Recorre el PMC real y luego proyecta los días futuros con el TSS previsto."""
    por_dia: dict[date, float] = {}
    for a in activities:
        por_dia[a.day] = por_dia.get(a.day, 0.0) + a.tss
    for d, t in futuros.items():
        por_dia[d] = por_dia.get(d, 0.0) + t
    if not por_dia:
        return None

    ctl_k = 1 - math.exp(-1 / ctl_days)
    atl_k = 1 - math.exp(-1 / atl_days)
    ctl = atl = 0.0
    d = min(por_dia)
    while d <= hasta:
        tss = por_dia.get(d, 0.0)
        ctl += ctl_k * (tss - ctl)
        atl += atl_k * (tss - atl)
        d += timedelta(days=1)
    return round(ctl, 1), round(atl, 1), round(ctl - atl, 1)


def form_impact(activities: list[Activity], filas: list[DayStatus]) -> dict:
    """Forma al inicio de la semana, hoy, y proyectada al cierre si completas
    lo que queda. Muestra el efecto real de entrenar (o saltarte sesiones)."""
    lunes = filas[0].fecha
    domingo = filas[-1].fecha
    pmc = build_pmc(activities)
    if not pmc:
        return {}

    def punto(dia: date):
        prev = [p for p in pmc if p.day <= dia]
        return prev[-1] if prev else None

    ini = punto(lunes - timedelta(days=1))
    hoy_p = pmc[-1]

    futuros = {f.fecha: float(f.tss_plan) for f in filas
               if f.estado == "pendiente"}
    proy = _simular(activities, futuros, domingo)

    return {
        "inicio_semana": (ini.ctl, ini.atl, ini.tsb) if ini else None,
        "hoy": (hoy_p.ctl, hoy_p.atl, hoy_p.tsb),
        "fin_semana_proyectado": proy,
        "delta_ctl": round(proy[0] - ini.ctl, 1) if (proy and ini) else None,
    }
