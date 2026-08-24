"""workouts.py — Biblioteca de sesiones y plan de 8 semanas para subir FTP."""
import re

def WU(m=12): return {"min": m, "zone": "Z2"}
def CD(m=8):  return {"min": m, "zone": "Z1"}
def REC(m):   return {"min": m, "zone": "Z1"}

def over_under(blocks=3, under="90-95%", over="105-110%", under_min=2, over_min=1):
    steps = []
    for _ in range(blocks):
        steps.append({"min": under_min, "power": under})
        steps.append({"min": over_min, "power": over})
    return steps

SESSIONS: dict[str, list] = {
    "SS_2x10":  [WU(12), {"repeat": 2, "steps": [{"min": 10, "power": "88-92%"}, REC(5)]}, CD(8)],
    "SS_2x12":  [WU(12), {"repeat": 2, "steps": [{"min": 12, "power": "88-92%"}, REC(5)]}, CD(8)],
    "SS_3x10":  [WU(12), {"repeat": 3, "steps": [{"min": 10, "power": "88-92%"}, REC(4)]}, CD(8)],
    "SS_2x15":  [WU(12), {"repeat": 2, "steps": [{"min": 15, "power": "89-93%"}, REC(6)]}, CD(8)],
    "SS_3x12":  [WU(10), {"repeat": 3, "steps": [{"min": 12, "power": "90-93%"}, REC(4)]}, CD(8)],
    "OU_3x9":   [WU(12), {"repeat": 3, "steps": over_under(3) + [REC(5)]}, CD(8)],
    "OU_4x9":   [WU(12), {"repeat": 4, "steps": over_under(3) + [REC(5)]}, CD(8)],
    "THR_2x12": [WU(12), {"repeat": 2, "steps": [{"min": 12, "power": "98-102%"}, REC(6)]}, CD(8)],
    "THR_2x15": [WU(12), {"repeat": 2, "steps": [{"min": 15, "power": "98-100%"}, REC(7)]}, CD(8)],
    "THR_3x12": [WU(10), {"repeat": 3, "steps": [{"min": 12, "power": "98-100%"}, REC(4)]}, CD(8)],
    "VO2_5x3":  [WU(15), {"repeat": 5, "steps": [{"min": 3, "power": "112-118%"}, REC(3)]}, CD(10)],
    "OPENERS":  [WU(15), {"repeat": 3, "steps": [{"min": 1, "power": "108-115%"}, REC(4)]},
                 {"min": 20, "zone": "Z2"}, CD(8)],
    "Z2_45":    [{"min": 45, "zone": "Z2"}],
    "Z2_60":    [{"min": 60, "zone": "Z2"}],
    "LONG_75":  [{"min": 75, "zone": "Z2"}],
    "LONG_90":  [{"min": 90, "zone": "Z2"}],
    "LONG_100": [{"min": 100, "zone": "Z2"}],
    "LONG_105": [{"min": 105, "zone": "Z2"}],
    "LONG_110": [{"min": 110, "zone": "Z2"}],
    "LONG_120": [{"min": 120, "zone": "Z2"}],
    "TEST_20":  [WU(15), {"min": 3, "power": "110%"}, REC(5),
                 {"min": 20, "power": "TEST máximo"}, CD(10)],
}

NAMES = {
    "SS_2x10": "Sweet Spot 2×10'", "SS_2x12": "Sweet Spot 2×12'",
    "SS_3x10": "Sweet Spot 3×10'", "SS_2x15": "Sweet Spot 2×15'",
    "SS_3x12": "Sweet Spot 3×12'", "OU_3x9": "Over-unders 3×9'",
    "OU_4x9": "Over-unders 4×9'", "THR_2x12": "Umbral 2×12'",
    "THR_2x15": "Umbral 2×15'", "THR_3x12": "Umbral 3×12'",
    "VO2_5x3": "VO2max 5×3'", "OPENERS": "Aperturas (activación)",
    "Z2_45": "Z2 suave 45'", "Z2_60": "Z2 suave 60'",
    "LONG_75": "Largo Z2 75'", "LONG_90": "Largo Z2 90'",
    "LONG_100": "Largo Z2 100'", "LONG_105": "Largo Z2 105'",
    "LONG_110": "Largo Z2 110'", "LONG_120": "Largo Z2 120'",
    "TEST_20": "Test FTP 20'",
}

PLAN_8W = [
    {"semana": 1, "foco": "Reintroducción + sweet spot",
     "dias": {"Mar": "SS_2x10", "Mié": "Z2_45", "Jue": "SS_2x12", "Vie": "Z2_45", "Sáb": "LONG_75"}},
    {"semana": 2, "foco": "Sweet spot progresivo",
     "dias": {"Mar": "SS_2x12", "Mié": "Z2_60", "Jue": "SS_3x10", "Vie": "Z2_45", "Sáb": "LONG_90"}},
    {"semana": 3, "foco": "Sweet spot + over-unders",
     "dias": {"Mar": "SS_2x15", "Mié": "Z2_60", "Jue": "OU_3x9", "Vie": "Z2_45", "Sáb": "LONG_100"}},
    {"semana": 4, "foco": "RECUPERACIÓN (descarga 3:1)",
     "dias": {"Mar": "OPENERS", "Mié": "Z2_45", "Jue": "Z2_45", "Vie": None, "Sáb": "LONG_75"}},
    {"semana": 5, "foco": "Entrada al umbral",
     "dias": {"Mar": "SS_3x12", "Mié": "Z2_60", "Jue": "THR_2x12", "Vie": "Z2_45", "Sáb": "LONG_105"}},
    {"semana": 6, "foco": "Umbral + over-unders",
     "dias": {"Mar": "OU_4x9", "Mié": "Z2_60", "Jue": "THR_2x15", "Vie": "Z2_45", "Sáb": "LONG_110"}},
    {"semana": 7, "foco": "Carga pico + VO2max",
     "dias": {"Mar": "THR_3x12", "Mié": "Z2_60", "Jue": "VO2_5x3", "Vie": "Z2_45", "Sáb": "LONG_120"}},
    {"semana": 8, "foco": "Descarga + test de FTP",
     "dias": {"Mar": "OPENERS", "Mié": "Z2_45", "Jue": "TEST_20", "Vie": None, "Sáb": "LONG_75"}},
]

ZONE_IF = {"Z1": 0.50, "Z2": 0.65, "Z3": 0.80, "Z4": 0.98, "Z5": 1.12}

def _step_if(step: dict) -> float:
    if "zone" in step:
        return ZONE_IF.get(step["zone"], 0.65)
    nums = re.findall(r"\d+", step.get("power", ""))
    if nums:
        return sum(int(n) for n in nums) / len(nums) / 100
    return 1.0

def tss(steps: list) -> int:
    total = 0.0
    for s in steps:
        if "repeat" in s:
            total += s["repeat"] * tss(s["steps"])
        else:
            total += (s["min"] / 60) * _step_if(s) ** 2 * 100
    return round(total)

def pretty(steps: list) -> list[str]:
    out = []
    for s in steps:
        if "repeat" in s:
            out.append(f"{s['repeat']}× bloque:")
            out += ["    " + ln for ln in pretty(s["steps"])]
        else:
            out.append(f"{s['min']} min · {s.get('power') or s.get('zone')}")
    return out
