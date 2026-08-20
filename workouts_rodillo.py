"""
workouts_rodillo.py — Sesiones ESTRUCTURADAS de rodillo (≤1h) para entre semana.

Estas sí se envían a Garmin (estructura exacta watts/minutos). El largo del
sábado NO está aquí: es libre por terreno (solo objetivo de horas).

Todas las sesiones caben en ~45-60 min. Watts en % de FTP; se resuelven a
vatios reales al construir la descripción.
"""

from __future__ import annotations

# Cada sesión: lista de pasos. Paso = {"min":x, "pct":(lo,hi)} o {"min":x,"z":"Z2"}
# "rep": {"veces":n, "pasos":[...]} se expande explícitamente (intervals.icu
# interpreta mal el marcador de repetición).

Z1, Z2 = (0.50, 0.60), (0.60, 0.70)

def _wu(m=10): return {"min": m, "z": "Z2", "pct": (0.55, 0.65)}
def _cd(m=6):  return {"min": m, "z": "Z1", "pct": (0.45, 0.55)}
def _rec(m):   return {"min": m, "z": "Z1", "pct": (0.45, 0.55)}

SESIONES = {
    # Sweet Spot (88-92%)
    "SS_2x10": [_wu(10), {"min": 10, "pct": (0.88, 0.92)}, _rec(5),
                {"min": 10, "pct": (0.88, 0.92)}, _cd(6)],
    "SS_2x12": [_wu(10), {"min": 12, "pct": (0.88, 0.92)}, _rec(5),
                {"min": 12, "pct": (0.88, 0.92)}, _cd(6)],
    "SS_3x8":  [_wu(9), {"min": 8, "pct": (0.88, 0.92)}, _rec(4),
                {"min": 8, "pct": (0.88, 0.92)}, _rec(4),
                {"min": 8, "pct": (0.88, 0.92)}, _cd(5)],
    # Umbral (98-102%)
    "THR_2x10": [_wu(10), {"min": 10, "pct": (0.98, 1.02)}, _rec(6),
                 {"min": 10, "pct": (0.98, 1.02)}, _cd(6)],
    "THR_3x8":  [_wu(9), {"min": 8, "pct": (0.98, 1.00)}, _rec(4),
                 {"min": 8, "pct": (0.98, 1.00)}, _rec(4),
                 {"min": 8, "pct": (0.98, 1.00)}, _cd(5)],
    # Over-unders (fuerza en subida, útil para MTB)
    "OU_3x9": [_wu(10),
               *([{"min": 2, "pct": (0.90, 0.95)}, {"min": 1, "pct": (1.05, 1.10)}] * 3), _rec(5),
               *([{"min": 2, "pct": (0.90, 0.95)}, {"min": 1, "pct": (1.05, 1.10)}] * 3), _rec(5),
               *([{"min": 2, "pct": (0.90, 0.95)}, {"min": 1, "pct": (1.05, 1.10)}] * 3), _cd(6)],
    # VO2 corto (chispa)
    "VO2_4x3": [_wu(12), {"min": 3, "pct": (1.10, 1.16)}, _rec(3),
                {"min": 3, "pct": (1.10, 1.16)}, _rec(3),
                {"min": 3, "pct": (1.10, 1.16)}, _rec(3),
                {"min": 3, "pct": (1.10, 1.16)}, _cd(8)],
    # Z2 estructurado (recuperación / base indoor)
    "Z2_45": [{"min": 45, "z": "Z2", "pct": (0.60, 0.68)}],
    "Z2_60": [{"min": 60, "z": "Z2", "pct": (0.60, 0.68)}],
    # Aperturas (pre-evento)
    "OPENERS": [_wu(12),
                {"min": 1, "pct": (1.08, 1.15)}, _rec(3),
                {"min": 1, "pct": (1.08, 1.15)}, _rec(3),
                {"min": 1, "pct": (1.08, 1.15)}, {"min": 15, "z": "Z2", "pct": (0.6, 0.68)}, _cd(6)],
}

NOMBRES = {
    "SS_2x10": "Sweet Spot 2×10'", "SS_2x12": "Sweet Spot 2×12'",
    "SS_3x8": "Sweet Spot 3×8'", "THR_2x10": "Umbral 2×10'",
    "THR_3x8": "Umbral 3×8'", "OU_3x9": "Over-unders 3×9'",
    "VO2_4x3": "VO2max 4×3'", "Z2_45": "Z2 rodillo 45'",
    "Z2_60": "Z2 rodillo 60'", "OPENERS": "Aperturas (activación)",
}


def duracion_min(pasos: list) -> int:
    return sum(p["min"] for p in pasos)


def tss_estimado(pasos: list) -> int:
    total = 0.0
    for p in pasos:
        lo, hi = p.get("pct", (0.6, 0.68))
        inten = (lo + hi) / 2
        total += (p["min"] / 60) * inten ** 2 * 100
    return round(total)


def watts(pasos: list, ftp: int) -> list:
    """Devuelve los pasos con vatios reales calculados."""
    out = []
    for p in pasos:
        lo, hi = p.get("pct", (0.6, 0.68))
        out.append({**p, "w": (round(ftp * lo), round(ftp * hi))})
    return out


def descripcion_garmin(pasos: list, ftp: int) -> str:
    """Texto para enviar a intervals.icu → Garmin. Repeticiones ya expandidas."""
    lines = []
    for p in watts(pasos, ftp):
        w = p["w"]
        etiqueta = p.get("z", "")
        lines.append(f"- {p['min']}m {w[0]}-{w[1]}w {etiqueta}".rstrip())
    return "\n".join(lines)


# Qué sesión de rodillo corresponde según fase, nivel y día
def sesion_rodillo(fase: int, dia: str, descarga: bool, nivel: int) -> str | None:
    """Devuelve la clave de sesión para un día de rodillo, o None si descanso."""
    if descarga:
        return {"Mar": "Z2_45", "Mié": "OPENERS", "Jue": "Z2_45"}.get(dia)
    if fase == 1:  # base: sweet spot dominante
        return {"Mar": "SS_2x10" if nivel < 3 else "SS_2x12",
                "Mié": "Z2_60",
                "Jue": "SS_2x12" if nivel < 3 else "SS_3x8"}.get(dia)
    if fase == 2:  # específica: umbral + over-unders (fuerza para MTB)
        return {"Mar": "THR_2x10" if nivel < 5 else "THR_3x8",
                "Mié": "Z2_60",
                "Jue": "OU_3x9"}.get(dia)
    # fase 3 (descarga/carrera)
    return {"Mar": "OPENERS", "Mié": "Z2_45"}.get(dia)
