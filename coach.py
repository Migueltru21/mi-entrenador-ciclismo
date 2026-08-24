"""coach.py — Cerebro adaptativo: veredicto del día y ajuste de la sesión."""
from __future__ import annotations
from dataclasses import dataclass
from training_engine import Activity


@dataclass
class Readiness:
    nivel: str
    puntos: int
    razones: list[str]
    mensaje: str


def readiness(tsb: float, ramp: float = 0.0,
              hrv: float | None = None, hrv_base: float | None = None,
              rhr: float | None = None, rhr_base: float | None = None,
              sleep_score: float | None = None) -> Readiness:
    pts, razones = 0, []
    if tsb < -30:
        pts += 2; razones.append("Forma muy negativa (TSB<-30): cargado")
    elif tsb < -20:
        pts += 1; razones.append("Forma negativa: fatiga acumulada")
    elif tsb > 10:
        razones.append("Fresco (TSB+): buen día para calidad")
    if ramp > 8:
        pts += 1; razones.append(f"Rampa de carga alta ({ramp}/sem)")
    if hrv is not None and hrv_base:
        ratio = hrv / hrv_base
        if ratio < 0.90:
            pts += 2; razones.append("HRV bastante por debajo de tu base")
        elif ratio < 0.95:
            pts += 1; razones.append("HRV algo por debajo de tu base")
    if rhr is not None and rhr_base is not None and rhr - rhr_base > 7:
        pts += 1; razones.append("FC en reposo elevada (poca recuperación)")
    if sleep_score is not None and sleep_score < 55:
        pts += 1; razones.append("Sueño pobre anoche")

    if pts >= 3:
        nivel, msg = "rojo", "Tu cuerpo pide bajar: cambia la calidad por Z2 suave o descansa."
    elif pts >= 1:
        nivel, msg = "ambar", "Recuperación parcial: reduce el volumen/intensidad de hoy."
    else:
        nivel, msg = "verde", "Buen estado: haz la sesión como está planeada."
    return Readiness(nivel, pts, razones or ["Todo en rango normal"], msg)


def _total_min(steps: list) -> int:
    total = 0
    for s in steps:
        if "repeat" in s:
            total += s["repeat"] * _total_min(s["steps"])
        else:
            total += s["min"]
    return total


def adjust_workout(steps: list, nivel: str) -> tuple[list, str]:
    if nivel == "verde":
        return steps, "Sin cambios: hazla completa."
    if nivel == "rojo":
        dur = min(_total_min(steps), 60)
        return ([{"min": dur, "zone": "Z2"}],
                f"Sustituida por {dur}' en Z2 suave (o descansa si vienes muy cargado).")
    nuevo, recortado = [], False
    for s in steps:
        if "repeat" in s and s["repeat"] > 2 and not recortado:
            s = {"repeat": s["repeat"] - 1, "steps": s["steps"]}
            recortado = True
        nuevo.append(s)
    nota = ("Quitada una serie del bloque principal." if recortado
            else "Baja un 5-10% la intensidad objetivo.")
    return nuevo, nota


def detect_ftp_change(activities: list[Activity]) -> dict | None:
    ftps = [(a.day, a.ftp_at_time) for a in activities if a.ftp_at_time]
    if len(ftps) < 2:
        return None
    ftps.sort()
    inicio, fin = ftps[0][1], ftps[-1][1]
    if abs(fin - inicio) >= 3:
        return {"antes": int(inicio), "ahora": int(fin), "delta": int(fin - inicio)}
    return None
