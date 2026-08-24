"""
app.py — Mi Entrenador · Plan ADAPTATIVO para carrera por etapas.
Concilia el plan con lo REALMENTE hecho (por semana, no por día exacto).
"""
from datetime import date, timedelta
import pandas as pd
import streamlit as st

from training_engine import build_pmc, interpret_form
from intervals_connector import IntervalsClient
import adaptive as A
import race_plan as rp
import workouts_rodillo as WK
import weekly_match as WM

st.set_page_config(page_title="Mi Entrenador · Adaptativo", page_icon="🚵", layout="wide")

BADGE = {"progresa": "📈", "consolida": "🔁", "descarga": "😴", "carrera": "🏁"}
FASE_ICON = {1: "🟢", 2: "🟠", 3: "🔵"}

st.sidebar.header("⚙️ Configuración")
_sec_id = _sec_key = ""
try:
    _sec_id = st.secrets.get("ATHLETE_ID", "")
    _sec_key = st.secrets.get("API_KEY", "")
except Exception:
    pass
athlete_id = st.sidebar.text_input("Athlete ID", value=_sec_id or "i627551")
api_key = st.sidebar.text_input("API key", value=_sec_key, type="password")
if _sec_key:
    st.sidebar.caption("🔒 API key cargada de forma segura.")

st.sidebar.divider()
st.sidebar.subheader("📅 Fechas")
inicio = st.sidebar.date_input("Inicio del plan", date(2026, 8, 17))
carrera = st.sidebar.date_input("Fecha de la carrera (1ª etapa)", date(2026, 11, 1))
st.sidebar.caption("El plan arranca en el inicio y reparte las fases hasta la "
                   "carrera. La descarga siempre aterriza antes del evento.")

hoy = date.today()

if not (athlete_id and api_key):
    st.title("🚵 Mi Entrenador · Adaptativo")
    st.info("Ingresa tu Athlete ID y API key en la barra lateral para empezar.")
    st.stop()

@st.cache_data(show_spinner="Trayendo tu historial…", ttl=600)
def cargar(athlete_id, api_key, desde, hasta):
    return IntervalsClient(athlete_id, api_key).get_activities(str(desde), str(hasta))

@st.cache_data(show_spinner=False, ttl=600)
def ftp_perfil(athlete_id, api_key):
    try:
        return IntervalsClient(athlete_id, api_key).get_athlete_ftp()
    except Exception:
        return None

lunes_ini = inicio - timedelta(days=inicio.weekday())
desde = min(lunes_ini, hoy) - timedelta(days=150)
try:
    acts = cargar(athlete_id, api_key, desde, hoy)
except Exception as e:
    st.title("🚵 Mi Entrenador · Adaptativo")
    st.error(f"No pude traer los datos: {e}")
    st.stop()

ftp = ftp_perfil(athlete_id, api_key) or rp.FTP

# Índice de semanas y objetivos del plan
def semana_indices():
    fases = A.repartir_fases(inicio, carrera)
    return {i + 1: (lunes_ini + timedelta(weeks=i),
                    lunes_ini + timedelta(weeks=i) + timedelta(days=6))
            for i in range(len(fases))}

idx = semana_indices()
plan_base = A.decidir_plan(inicio, carrera)

# Objetivos de rodillos/largos por semana (según fase y descarga)
def objetivos(dsem):
    if dsem.tipo == "carrera":
        return 0, 0
    if dsem.tipo == "descarga":
        return 3, 1  # rodillos suaves + largo suave
    rod = 3  # mar, mié, jue
    largos = 2 if dsem.horas_domingo else 1
    return rod, largos

# Conciliación REAL por semana (lo hecho, sin importar el día)
concil = {}
for d in plan_base:
    l, fin = idx[d.sem]
    rod_plan, larg_plan = objetivos(d)
    concil[d.sem] = WM.conciliar_semana(
        d.sem, l, acts, rod_plan, larg_plan, d.horas_largo, hoy)

# Alimentar el motor con el cumplimiento REAL
cumplimiento = {n: c.cumplimiento for n, c in concil.items()
                if c.completada}
pmc = build_pmc(acts)
def tsb_en(dd):
    prev = [p for p in pmc if p.day <= dd]
    return prev[-1].tsb if prev else None
tsb_cierre = {n: tsb_en(c.domingo) for n, c in concil.items() if c.completada}

plan = A.decidir_plan(inicio, carrera, cumplimiento, tsb_cierre)

# ---- Cabecera ----
st.title("🚵 Mi Entrenador · Plan Adaptativo")
dias = (carrera - hoy).days
sem_actual = None
for n, (l, fin) in idx.items():
    if l <= hoy <= fin:
        sem_actual = n; break

estado = pmc[-1] if pmc else None
c1, c2, c3, c4 = st.columns(4)
c1.metric("⏳ Faltan", f"{dias} días", f"{dias//7} sem")
c2.metric("Semana", f"{sem_actual or '—'}/{len(plan)}")
if estado:
    c3.metric("Forma (TSB)", estado.tsb, interpret_form(estado.tsb).split(":")[0])
    c4.metric("Fitness · FTP", estado.ctl, f"{int(ftp)}w")
st.caption("ℹ️ Los números de forma/fitness son aproximados; intervals.icu es "
           "la fuente exacta. Aquí lo útil es la tendencia y el plan.")

# ---- Selector de semana ----
st.header("🗓️ Semana")
opciones = [d.sem for d in plan]
sem_ver = st.selectbox("Elige la semana", opciones,
                       index=(sem_actual or 1) - 1,
                       format_func=lambda n: f"Semana {n}"
                       + (" (en curso)" if n == sem_actual else ""))
dsem = [d for d in plan if d.sem == sem_ver][0]
c = concil[sem_ver]

st.subheader(f"{BADGE[dsem.tipo]} Semana {sem_ver}: {dsem.tipo.upper()}")
st.markdown(f"**{FASE_ICON[dsem.fase]} {dsem.foco}** · nivel {dsem.nivel}"
            + (f" · largo objetivo {dsem.horas_largo}h" if dsem.horas_largo else ""))
st.info(f"**Por qué:** {dsem.razon}")

# Cómo va / cómo fue esta semana (conciliado real)
if c.completada or c.en_curso:
    estado_c = "Cómo vas" if c.en_curso else "Cómo fue"
    pct = c.cumplimiento * 100
    color = "🟢" if pct >= 80 else ("🟡" if pct >= 50 else "🔴")
    st.markdown(f"**{estado_c}:** {color} {pct:.0f}% — {WM.resumen_texto(c)}")

# ---- Entrenos de la semana ----
st.subheader("🚴 Entrenos de la semana")
st.caption("Rodillo estructurado entre semana (enviable a Garmin). Largo libre "
           "el fin de semana. Cuenta lo hecho AUNQUE cambies el día.")

descarga = dsem.tipo in ("descarga", "carrera")
l_sem, fin_sem = idx[sem_ver]
offset = {"Lun":0,"Mar":1,"Mié":2,"Jue":3,"Vie":4,"Sáb":5,"Dom":6}
dias_rodillo = ["Mar", "Mié", "Jue"]
envio = []
filas = []
for dia in ["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"]:
    fecha = l_sem + timedelta(days=offset[dia])
    if dia == "Sáb":
        if dsem.tipo == "carrera":
            nombre, det = "CARRERA / viaje", "según etapa"
        else:
            nombre = f"Largo MTB {dsem.horas_largo}h" if dsem.horas_largo else "Largo"
            det = "🏔️ montaña · sostenible · comer cada 40-45'"
    elif dia == "Dom" and dsem.horas_domingo:
        nombre = f"Largo MTB {dsem.horas_domingo}h"
        det = "🔥 BACK-TO-BACK · rodar cansado"
    elif dia in dias_rodillo:
        key = WK.sesion_rodillo(dsem.fase, dia, descarga, dsem.nivel)
        if key:
            pasos = WK.SESIONES[key]
            nombre = WK.NOMBRES[key]
            det = f"🏠 rodillo · {WK.duracion_min(pasos)}min · ~{WK.tss_estimado(pasos)}TSS"
            envio.append((fecha, nombre, WK.descripcion_garmin(pasos, int(ftp))))
        else:
            nombre, det = "Descanso", "—"
    else:
        nombre, det = "Descanso", "—"
    tss_real = round(sum(a.tss for a in acts if a.day == fecha))
    marca = "✅" if tss_real else ("😴" if nombre == "Descanso" else
                                   ("⬜️" if fecha >= hoy else "·"))
    filas.append({"": marca, "Día": f"{dia} {fecha.strftime('%d/%m')}",
                  "Sesión": nombre, "Detalle": det,
                  "Hecho": f"{int(tss_real)}TSS" if tss_real else "—"})
st.dataframe(pd.DataFrame(filas).astype(str), width="stretch", hide_index=True)
st.caption("Nota: el ✅ marca los días con actividad. El cumplimiento real de "
           "arriba cuenta por semana, así que aunque muevas un entreno de día, "
           "igual cuenta.")

# ---- Ver intervalos + enviar a Garmin ----
if envio:
    with st.expander("👁️ Ver los intervalos de las sesiones de rodillo"):
        for fecha, nombre, desc in envio:
            st.markdown(f"**{fecha.strftime('%a %d/%m')} · {nombre}**")
            st.code(desc)
    st.markdown("**📤 Enviar el rodillo de esta semana a Garmin**")
    preview = st.checkbox("Solo previsualizar (no enviar)", True, key=f"prev{sem_ver}")
    if st.button(f"Enviar rodillo semana {sem_ver} a Garmin", type="primary"):
        if preview:
            st.info(f"👀 Previsualización: {len(envio)} entrenos (NO enviados). "
                    "Desmarca la casilla para enviar de verdad.")
        else:
            cli = IntervalsClient(athlete_id, api_key)
            ok, errores = 0, []
            for fecha, nombre, desc in envio:
                try:
                    cli.push_planned_workout(str(fecha), nombre, desc); ok += 1
                except Exception as e:
                    errores.append(f"{fecha} {nombre}: {e}")
            st.success(f"✅ {ok} entrenos enviados a intervals.icu → Garmin.")
            if errores:
                st.error("Fallaron:\n" + "\n".join(errores))

# ---- Historia acumulada (real) ----
st.header("📚 Tu historia en este plan")
vividas = [c for c in concil.values() if c.completada or c.en_curso]
tot_h = round(sum(c.horas_total for c in vividas), 1)
tot_tss = round(sum(c.tss_total for c in vividas))
tot_desn = round(sum(c.desnivel_total for c in vividas))
hechas = len([c for c in concil.values() if c.completada])
h1, h2, h3, h4 = st.columns(4)
h1.metric("Horas acumuladas", f"{tot_h} h")
h2.metric("Desnivel acumulado", f"{tot_desn:,} m".replace(",", "."))
h3.metric("Carga total (TSS)", f"{tot_tss:,}".replace(",", "."))
h4.metric("Semanas hechas", f"{hechas}/{len(plan)}")

# Tabla completa del plan con cumplimiento real
filas_p = []
for d in plan:
    cc = concil[d.sem]
    estado_txt = ("✅" if cc.completada else "▶️" if cc.en_curso else "⬜️")
    cumpl_txt = (f"{cc.cumplimiento*100:.0f}%" if (cc.completada or cc.en_curso) else "—")
    filas_p.append({"": estado_txt, "Sem": str(d.sem),
                    "Desde": cc.lunes.strftime("%d/%m"),
                    "Decisión": f"{BADGE[d.tipo]} {d.tipo}",
                    "Foco": d.foco,
                    "Largo obj": f"{d.horas_largo}h" if d.horas_largo else "—",
                    "Cumplido": cumpl_txt})
st.dataframe(pd.DataFrame(filas_p).astype(str), width="stretch", hide_index=True)

# ---- Reglas + gráficas ----
with st.expander("📏 Las reglas del plan (cómo se ajusta solo)"):
    for r in A.explicar_reglas():
        st.markdown(f"- {r}")

st.subheader("📈 Progresión de largos")
prog = pd.DataFrame([{"Semana": d.sem, "Objetivo (h)": d.horas_largo or 0,
    "Hecho (h)": concil[d.sem].horas_largo_may} for d in plan
    if d.horas_largo]).set_index("Semana")
st.line_chart(prog)

if pmc:
    st.subheader("Fitness / Fatiga / Forma")
    st.line_chart(pd.DataFrame([{"Fecha": p.day, "Fitness": p.ctl,
        "Fatiga": p.atl, "Forma": p.tsb} for p in pmc]).set_index("Fecha"))

st.divider()
st.caption("💡 El plan se adapta a tu cumplimiento real (cuenta por semana). "
           "Tu sensación siempre manda: si el cuerpo dice basta, descansa.")
