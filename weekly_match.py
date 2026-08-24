"""
weekly_match.py — Concilia el PLAN con lo REALMENTE hecho, por SEMANA.

El problema que resuelve: la app antigua comparaba día-planeado vs actividad-en-
ese-día-exacto. Si entrenabas el mismo trabajo otro día, no lo contaba. Aquí
contamos por semana y por TIPO de sesión (rodillo corto vs largo), que es como
de verdad funciona el entrenamiento: importa que hiciste el trabajo en la
semana, no el día exacto.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta


# Umbrales para clasificar una actividad
LARGO_MIN_HORAS = 1.5   # >= 1.5h cuenta como "largo"
INDOOR_TYPES = {"VirtualRide"}  # rodillo suele venir como VirtualRide


def _horas(a) -> float:
    return (getattr(a, "duration_s", None) or 0) / 3600.0


@dataclass
class ConciliacionSemana:
    sem: int
    lunes: date
    domingo: date
    # objetivos del plan
    rodillos_plan: int
    largos_plan: int
    horas_largo_obj: float | None
    # lo realmente hecho (por tipo, en toda la semana)
    rodillos_hechos: int
    largos_hechos: int
    horas_largo_may: float     # el largo más grande de la semana
    tss_total: float
    horas_total: float
    desnivel_total: float
    # veredicto
    cumplimiento: float        # 0..1 combinando rodillos y largo
    completada: bool
    en_curso: bool


def conciliar_semana(sem: int, lunes: date, acts: list,
                     rodillos_plan: int, largos_plan: int,
                     horas_largo_obj: float | None, hoy: date) -> ConciliacionSemana:
    domingo = lunes + timedelta(days=6)
    a_sem = [a for a in acts if lunes <= a.day <= domingo]

    # Clasificar cada actividad
    largos = [a for a in a_sem if _horas(a) >= LARGO_MIN_HORAS]
    cortas = [a for a in a_sem if _horas(a) < LARGO_MIN_HORAS and a.tss > 0]

    rodillos_hechos = len(cortas)
    largos_hechos = len(largos)
    horas_largo_may = round(max((_horas(a) for a in a_sem), default=0.0), 1)
    tss_total = round(sum(a.tss for a in a_sem))
    horas_total = round(sum(_horas(a) for a in a_sem), 1)
    desnivel_total = round(sum(getattr(a, "elev_gain_m", 0) or 0 for a in a_sem))

    # Cumplimiento: 70% peso al largo (lo más importante), 30% a los rodillos
    cumpl_rodillo = min(1.0, rodillos_hechos / rodillos_plan) if rodillos_plan else 1.0
    cumpl_largo = min(1.0, largos_hechos / largos_plan) if largos_plan else 1.0
    cumplimiento = round(0.3 * cumpl_rodillo + 0.7 * cumpl_largo, 2)

    return ConciliacionSemana(
        sem=sem, lunes=lunes, domingo=domingo,
        rodillos_plan=rodillos_plan, largos_plan=largos_plan,
        horas_largo_obj=horas_largo_obj,
        rodillos_hechos=rodillos_hechos, largos_hechos=largos_hechos,
        horas_largo_may=horas_largo_may, tss_total=tss_total,
        horas_total=horas_total, desnivel_total=desnivel_total,
        cumplimiento=cumplimiento,
        completada=(domingo < hoy), en_curso=(lunes <= hoy <= domingo),
    )


def resumen_texto(c: ConciliacionSemana) -> str:
    """Frase corta de cómo va la semana."""
    partes = []
    partes.append(f"{c.rodillos_hechos}/{c.rodillos_plan} rodillos")
    if c.largos_plan:
        partes.append(f"{c.largos_hechos}/{c.largos_plan} largo"
                      + (f" ({c.horas_largo_may}h)" if c.horas_largo_may else ""))
    if c.tss_total:
        partes.append(f"{int(c.tss_total)} TSS")
    return " · ".join(partes)
