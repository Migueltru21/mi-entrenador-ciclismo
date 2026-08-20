"""
adaptive.py — Motor de plan adaptativo con reglas TRANSPARENTES.

Arranca en una fecha de inicio (hoy) y reparte las semanas disponibles hasta
la carrera en tres fases, asegurando que la descarga aterrice antes de la
carrera. Cada semana, decide entre PROGRESAR / CONSOLIDAR / DESCARGAR según
reglas claras y predecibles (no una caja negra):

  - CUMPLIÓ (>=80% de la carga planeada) y forma sana  -> PROGRESA
  - NO CUMPLIÓ (<80%)                                  -> CONSOLIDA (repite nivel)
  - Forma muy negativa (TSB <= umbral)                 -> DESCARGA (aunque no tocara)
  - Cada 3-4 semanas de carga                          -> DESCARGA programada

Todo el razonamiento se expone al usuario para que entienda POR QUÉ.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
import math

FTP_DEFAULT = 190

# Umbrales de las reglas (ajustables y visibles)
UMBRAL_CUMPLIMIENTO = 0.80      # >=80% de carga = cumplió
TSB_DESCARGA = -25              # forma más negativa que esto = forzar descarga
SEMANAS_CARGA_ANTES_DESCARGA = 3  # cada 3 de carga, 1 de descarga


@dataclass
class DecisionSemana:
    sem: int
    lunes: date
    fase: int
    tipo: str            # "progresa" | "consolida" | "descarga" | "carrera"
    nivel: int           # nivel de carga (1..N); consolida repite, progresa sube
    horas_largo: float | None
    foco: str
    razon: str           # explicación transparente de por qué esta decisión
    horas_domingo: float | None = None   # back-to-back (2º largo), solo fase 2


# --------------------------------------------------------------------------- #
# Reparto de fases entre hoy y la carrera
# --------------------------------------------------------------------------- #
def repartir_fases(inicio: date, carrera: date) -> list[int]:
    """Devuelve una lista con el nº de fase (1,2,3) para cada semana disponible
    entre inicio y carrera. Reparte proporcionalmente asegurando que la última
    fase (descarga) tenga 1-2 semanas antes de la carrera."""
    lunes_ini = inicio - timedelta(days=inicio.weekday())
    lunes_carrera = carrera - timedelta(days=carrera.weekday())
    n = max(1, (lunes_carrera - lunes_ini).days // 7)  # semanas completas

    if n <= 2:
        # Muy poco tiempo: casi todo descarga
        return [3] * n
    if n <= 4:
        # base corta + descarga
        return [1] * (n - 1) + [3]

    # Reparto estándar: descarga = 1-2 sem, resto entre base (60%) y específica (40%)
    descarga = 2 if n >= 9 else 1
    restantes = n - descarga
    base = math.ceil(restantes * 0.6)
    especifica = restantes - base
    return [1] * base + [2] * especifica + [3] * descarga


# --------------------------------------------------------------------------- #
# Perfil de largo por semana (progresión de horas)
# --------------------------------------------------------------------------- #
def horas_largo_base(nivel: int, fase: int) -> float:
    """Horas objetivo del largo según nivel de carga y fase."""
    if fase == 3:
        return 3.0  # descarga: largo suave
    # base empieza en 3h, sube ~0.4h por nivel; específica un poco más
    base = 3.0 + 0.4 * (nivel - 1)
    if fase == 2:
        base += 0.5
    return round(min(base, 5.5), 2)  # tope 5.5h


# --------------------------------------------------------------------------- #
# Decisión semana a semana según cumplimiento y forma
# --------------------------------------------------------------------------- #
def decidir_plan(inicio: date, carrera: date,
                 cumplimiento_por_sem: dict[int, float] | None = None,
                 tsb_por_sem: dict[int, float] | None = None) -> list[DecisionSemana]:
    """Genera el plan completo adaptativo.

    cumplimiento_por_sem: {n_sem: fraccion_carga_hecha} de semanas pasadas.
    tsb_por_sem: {n_sem: tsb_al_cierre} de semanas pasadas.
    Para semanas futuras, asume cumplimiento y progresa normalmente.
    """
    cumplimiento_por_sem = cumplimiento_por_sem or {}
    tsb_por_sem = tsb_por_sem or {}

    fases = repartir_fases(inicio, carrera)
    lunes_ini = inicio - timedelta(days=inicio.weekday())

    decisiones: list[DecisionSemana] = []
    nivel = 1
    semanas_desde_descarga = 0
    ultima_fue_descarga = False

    for i, fase in enumerate(fases):
        n = i + 1
        lunes = lunes_ini + timedelta(weeks=i)
        # Refrescar flag según la última decisión tomada
        ultima_fue_descarga = bool(decisiones) and decisiones[-1].tipo == "descarga"

        # Semana de carrera (última): incluye viaje, aclimatación y activación
        if i == len(fases) - 1 and fase == 3 and n == len(fases):
            decisiones.append(DecisionSemana(
                n, lunes, 3, "carrera", nivel, None,
                "SEMANA DE CARRERA",
                "Semana del evento. Lun-Mar: piernas sueltas con aperturas "
                "cortas. Viaje y aclimatación a la altitud (llega 2-3 días "
                "antes). Activación suave en destino. Llega fresco, no cansado."))
            continue

        # Regla 1: descarga forzada por fase de descarga
        if fase == 3:
            decisiones.append(DecisionSemana(
                n, lunes, 3, "descarga", nivel, horas_largo_base(nivel, 3),
                "Taper / descarga",
                "Fase de descarga: bajamos volumen para llegar frescos."))
            semanas_desde_descarga = 0
            continue

        # Datos de la semana ANTERIOR (si existen) para decidir esta
        cumpl_prev = cumplimiento_por_sem.get(n - 1)
        tsb_prev = tsb_por_sem.get(n - 1)

        # Regla 2: forma muy negativa -> descarga aunque no tocara
        if tsb_prev is not None and tsb_prev <= TSB_DESCARGA:
            decisiones.append(DecisionSemana(
                n, lunes, fase, "descarga", nivel, horas_largo_base(nivel, 3),
                "Descarga por fatiga",
                f"Tu forma cerró en {tsb_prev:.0f} (≤{TSB_DESCARGA}): estás muy "
                f"cargado. Insertamos descarga para no arriesgar sobrecarga."))
            semanas_desde_descarga = 0
            continue

        # Regla 3: descarga programada cada N semanas de carga
        # (no si la semana previa ya fue descarga — evita descargas seguidas)
        if semanas_desde_descarga >= SEMANAS_CARGA_ANTES_DESCARGA and not ultima_fue_descarga:
            decisiones.append(DecisionSemana(
                n, lunes, fase, "descarga", nivel, horas_largo_base(nivel, 3),
                "Descarga programada",
                f"Llevas {semanas_desde_descarga} semanas de carga seguidas. "
                f"Toca asimilar (regla 3:1)."))
            semanas_desde_descarga = 0
            continue

        # Regla 4: cumplimiento de la semana anterior
        if cumpl_prev is None:
            # Sin datos (semana futura o primera): progresa normal
            tipo = "progresa"
            razon = "Progresión normal del plan."
            nivel += 1
        elif cumpl_prev >= UMBRAL_CUMPLIMIENTO:
            tipo = "progresa"
            razon = (f"Cumpliste la semana pasada ({cumpl_prev*100:.0f}% de la "
                     f"carga). Subimos un escalón.")
            nivel += 1
        else:
            tipo = "consolida"
            razon = (f"La semana pasada quedó al {cumpl_prev*100:.0f}% "
                     f"(<{int(UMBRAL_CUMPLIMIENTO*100)}%). Repetimos el nivel "
                     f"para asentar la base antes de subir.")
            # nivel NO sube

        # Back-to-back (domingo largo) solo en fase específica MTB (fase 2).
        # Es el último mes: aquí sí hay sábado Y domingo.
        h_domingo = None
        if fase == 2:
            # domingo ~60% del sábado, tope 3.5h
            h_domingo = round(min(horas_largo_base(nivel, fase) * 0.6, 3.5), 2)
            razon += (f" Fin de semana con BACK-TO-BACK: sábado largo + domingo "
                      f"{h_domingo}h para simular etapas seguidas.")

        decisiones.append(DecisionSemana(
            n, lunes, fase, tipo, nivel, horas_largo_base(nivel, fase),
            _foco(fase, tipo), razon, horas_domingo=h_domingo))
        semanas_desde_descarga += 1

    return decisiones


def _foco(fase: int, tipo: str) -> str:
    if tipo == "consolida":
        return "Consolidar (repetir nivel)"
    if fase == 1:
        return "Base de resistencia"
    if fase == 2:
        return "Específica MTB + back-to-back"
    return "Descarga"


def explicar_reglas() -> list[str]:
    """Las reglas, en lenguaje claro, para mostrar al usuario."""
    return [
        f"✅ Si cumples ≥{int(UMBRAL_CUMPLIMIENTO*100)}% de la carga de la semana "
        f"y tu forma está sana → PROGRESA (sube un escalón).",
        f"🔁 Si cumples <{int(UMBRAL_CUMPLIMIENTO*100)}% → CONSOLIDA (repite el "
        f"nivel, no sube, hasta que asientes la base).",
        f"😴 Si tu forma (TSB) cae por debajo de {TSB_DESCARGA} → DESCARGA "
        f"automática (aunque no tocara), para no sobrecargarte.",
        f"📅 Cada {SEMANAS_CARGA_ANTES_DESCARGA} semanas de carga → 1 de descarga "
        f"programada (regla 3:1 clásica).",
        "🏁 La descarga final siempre aterriza antes de la carrera.",
    ]
