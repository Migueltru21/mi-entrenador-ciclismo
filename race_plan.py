"""
race_plan.py — Plan específico para la carrera por etapas de MTB (Ecuador).

Filosofía distinta al bloque genérico: el objetivo es TERMINAR una carrera
por etapas (~300km, ~7000m desnivel, altitud 2600-4000m). Prioridad:
horas > desnivel > adaptación MTB > back-to-back > FTP.

El plan se ancla a la FECHA DE LA CARRERA (no a un "inicio" movible).
Las semanas se cuentan hacia atrás desde la carrera, así nada se descuadra.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta

# Ventana de la carrera (primer día de etapas). Ajustable cuando se confirme.
RACE_DATE = date(2026, 11, 1)

# FTP de referencia para las zonas
FTP = 190


@dataclass
class Fase:
    nombre: str
    semanas: tuple[int, int]   # rango de nº de semana del plan (1-indexado)
    objetivo: str


FASES = [
    Fase("Base de resistencia", (1, 6),
         "Construir base aeróbica y horas. Largos que crecen. Grueso en ruta, "
         "MTB los sábados. Practicar comer/beber sobre la bici."),
    Fase("Específica MTB", (7, 10),
         "Largos en MTB en terreno de carrera. Back-to-back (sáb+dom). "
         "Máximo desnivel y horas."),
    Fase("Descarga y viaje", (11, 12),
         "Bajar volumen, llegar fresco. Aclimatar a la altitud llegando "
         "2-3 días antes."),
]

# Plan semana a semana. horas_sabado = objetivo del largo principal (referencia).
# tipo_sabado: "ruta" | "mtb". back_to_back: si hay domingo largo.
PLAN = [
    {"sem": 1, "foco": "Transición / arranque base", "sabado_h": 3.0, "sabado": "mtb",
     "b2b": None, "carga_obj": 300},
    {"sem": 2, "foco": "Subir volumen", "sabado_h": 3.5, "sabado": "mtb",
     "b2b": None, "carga_obj": 330},
    {"sem": 3, "foco": "Progresión", "sabado_h": 4.0, "sabado": "mtb",
     "b2b": None, "carga_obj": 360},
    {"sem": 4, "foco": "DESCARGA (asimilar)", "sabado_h": 2.75, "sabado": "mtb",
     "b2b": None, "carga_obj": 230},
    {"sem": 5, "foco": "Retomar carga", "sabado_h": 4.25, "sabado": "mtb",
     "b2b": None, "carga_obj": 380},
    {"sem": 6, "foco": "Pico de base", "sabado_h": 4.75, "sabado": "mtb",
     "b2b": None, "carga_obj": 400},
    {"sem": 7, "foco": "Inicio específico + 1er back-to-back", "sabado_h": 4.5,
     "sabado": "mtb", "b2b": 2.5, "carga_obj": 430},
    {"sem": 8, "foco": "DESCARGA", "sabado_h": 3.0, "sabado": "mtb",
     "b2b": None, "carga_obj": 250},
    {"sem": 9, "foco": "Carga máxima + back-to-back", "sabado_h": 5.0,
     "sabado": "mtb", "b2b": 3.0, "carga_obj": 460},
    {"sem": 10, "foco": "Último gran bloque + back-to-back", "sabado_h": 5.25,
     "sabado": "mtb", "b2b": 3.25, "carga_obj": 470},
    {"sem": 11, "foco": "Inicio de descarga (taper)", "sabado_h": 3.0,
     "sabado": "mtb", "b2b": None, "carga_obj": 250},
    {"sem": 12, "foco": "SEMANA DE CARRERA", "sabado_h": None, "sabado": "carrera",
     "b2b": None, "carga_obj": None},
]

# Sesiones tipo por día de la semana, según fase. Se resuelven con la sem.
def dias_de_semana(sem_info: dict) -> list[dict]:
    """Devuelve las sesiones Lun-Dom de una semana del plan."""
    n = sem_info["sem"]
    fase = fase_de_semana(n)
    sab_h = sem_info["sabado_h"]
    b2b = sem_info["b2b"]
    descarga = "DESCARGA" in sem_info["foco"]

    # Día de calidad (lunes) según fase y descarga
    if descarga:
        lun = ("Aperturas suaves", "picos cortos + Z2")
    elif fase == 1:
        lun = ("Sweet Spot 2×12", f"{int(FTP*0.88)}-{int(FTP*0.92)}w · mantener motor")
    else:
        lun = ("Umbral/SS en MTB", "fuerza en subida")

    z2 = ("Z2 suave 45'", f"<{int(FTP*0.70)}w / <140 bpm")
    z2c = ("Z2 60'", "recuperación activa")
    desc = ("Descanso", "—")

    # Miércoles: largo entre semana (crece con la fase)
    if descarga:
        mie = z2c
    elif fase == 1:
        mie = ("Largo ruta 2.5-3h", "Z2 + subidas a ritmo cómodo")
    else:
        mie = ("Largo MTB 3.5-4h", "terreno técnico + desnivel")

    # Sábado
    if sem_info["sabado"] == "carrera":
        sab = ("CARRERA (etapas)", "¡A disfrutar y terminar!")
    else:
        tipo = "MTB" if sem_info["sabado"] == "mtb" else "Ruta"
        sab = (f"Largo {tipo} {_fmt_h(sab_h)}",
               "ritmo sostenible · comer cada 40-45' · desnivel")

    dom = desc
    if b2b:
        dom = (f"Largo MTB {_fmt_h(b2b)}", "BACK-TO-BACK · rodar cansado")

    return [
        {"dia": "Lun", "sesion": lun[0], "detalle": lun[1]},
        {"dia": "Mar", "sesion": z2[0], "detalle": z2[1]},
        {"dia": "Mié", "sesion": mie[0], "detalle": mie[1]},
        {"dia": "Jue", "sesion": z2[0], "detalle": z2[1]},
        {"dia": "Vie", "sesion": desc[0], "detalle": desc[1]},
        {"dia": "Sáb", "sesion": sab[0], "detalle": sab[1]},
        {"dia": "Dom", "sesion": dom[0], "detalle": dom[1]},
    ]


def _fmt_h(h: float | None) -> str:
    if h is None:
        return ""
    horas = int(h)
    mins = int(round((h - horas) * 60))
    return f"{horas}h" + (f"{mins:02d}" if mins else "")


def fase_de_semana(n: int) -> int:
    for i, f in enumerate(FASES, 1):
        if f.semanas[0] <= n <= f.semanas[1]:
            return i
    return 1


def total_semanas() -> int:
    return len(PLAN)


def lunes_de_semana(n: int, race_date: date = RACE_DATE) -> date:
    """Lunes de la semana nº n del plan, contando hacia atrás desde la carrera.
    La semana 12 es la de la carrera."""
    total = total_semanas()
    # Lunes de la semana de carrera
    lunes_carrera = race_date - timedelta(days=race_date.weekday())
    # Retroceder (total - n) semanas
    return lunes_carrera - timedelta(weeks=(total - n))


def semana_actual(hoy: date = None, race_date: date = RACE_DATE) -> int:
    """Nº de semana del plan en la que caemos hoy."""
    if hoy is None:
        hoy = date.today()
    for info in PLAN:
        ini = lunes_de_semana(info["sem"], race_date)
        fin = ini + timedelta(days=6)
        if ini <= hoy <= fin:
            return info["sem"]
    # Antes del plan → 1; después → última
    if hoy < lunes_de_semana(1, race_date):
        return 0  # el plan aún no empieza
    return total_semanas()


def dias_hasta_carrera(hoy: date = None, race_date: date = RACE_DATE) -> int:
    if hoy is None:
        hoy = date.today()
    return (race_date - hoy).days


def zonas() -> dict:
    return {
        "Z2": (0, int(FTP * 0.70)),
        "Sweet Spot": (int(FTP * 0.88), int(FTP * 0.92)),
        "Umbral": (int(FTP * 0.98), int(FTP * 1.02)),
    }
