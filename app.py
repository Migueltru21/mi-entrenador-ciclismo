"""
app.py — Mi Entrenador · Plan ADAPTATIVO para carrera por etapas.
Corre con:  python3 -m streamlit run app.py
"""
from datetime import date, timedelta
import pandas as pd
import streamlit as st

from training_engine import build_pmc, interpret_form
from intervals_connector import IntervalsClient
import adaptive as A
import history as H
import race_plan as rp
import workouts_rodillo as WK

st.set_page_config(page_title="Mi Entrenador · Adaptativo", page_icon="🚵", layout="wide")

BADGE = {"progresa": "📈", "consolida": "🔁", "descarga": "😴", "carrera": "🏁"}
FASE_ICON = {1: "🟢", 2: "🟠", 3: "🔵"}

st.sidebar.header("⚙️ Configuración")

# En Streamlit Cloud, las credenciales pueden venir de "secrets" (seguro).
# Si no, se piden a mano como siempre.
_sec_id = ""
_sec_key = ""
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
inicio = st.sidebar.date_input("Inicio del plan (hoy)", date.today())
carrera = st.sidebar.date_input("Fecha de la carrera (1ª etapa)", date(2026, 11, 1))
st.sidebar.caption("El plan arranca en el inicio y reparte las fases hasta la "
                   "carrera. La descarga siempre aterriza antes del evento.")

hoy = date.today()

if not (athlete_id and api_key):
    st.title("🚵 Mi Entrenador · Adaptativo")
    st.info("Ingresa tu Athlete ID y API key en la barra lateral para empezar.")
    st.stop()

@st.cache_data(show_spinner="Trayendo tu historial…")
def cargar(athlete_id, api_key, desde, hasta):
    return IntervalsClient(athlete_id, api_key).get_activities(str(desde), str(hasta))

@st.cache_data(show_spinner=False)
def ftp_perfil(athlete_id, api_key):
    try:
        return IntervalsClient(athlete_id, api_key).get_athlete_ftp()
    except Exception:
        return None

lunes_ini = inicio - timedelta(days=inicio.weekday())
# Cargar ~4 meses de historial para calcular bien el CTL (Fitness),
# no solo desde el inicio del plan.
desde = min(lunes_ini, hoy) - timedelta(days=120)
try:
    acts = cargar(athlete_id, api_key, desde, hoy)
except Exception as e:
    st.title("🚵 Mi Entrenador · Adaptativo")
    st.error(f"No pude traer los datos: {e}")
    st.info("Si es error de red, en la Terminal:\n\n"
            "`pip3 install --force-reinstall \"urllib3==1.26.18\" --timeout 120`")
    st.stop()

ftp = ftp_perfil(athlete_id, api_key) or rp.FTP

def semana_indices():
    fases = A.repartir_fases(inicio, carrera)
    out = {}
    for i in range(len(fases)):
        l = lunes_ini + timedelta(weeks=i)
        out[i + 1] = (l, l + timedelta(days=6))
    return out

pmc = build_pmc(acts)

def tsb_en(d):
    prev = [p for p in pmc if p.day <= d]
    return prev[-1].tsb if prev else None

idx = semana_indices()
plan_base = A.decidir_plan(inicio, carrera)
carga_obj = {d.sem: 120 + d.nivel * 45 for d in plan_base if d.horas_largo}

cumplimiento, tsb_cierre = {}, {}
for n, (l, fin) in idx.items():
    if fin >= hoy:
        continue
    tss_hecho = sum(a.tss for a in acts if l <= a.day <= fin)
    obj = carga_obj.get(n, 300)
    cumplimiento[n] = round(tss_hecho / obj, 2) if obj else 1.0
    tsb_cierre[n] = tsb_en(fin)

plan = A.decidir_plan(inicio, carrera, cumplimiento, tsb_cierre)

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

if sem_actual:
    dsem = [d for d in plan if d.sem == sem_actual][0]
    st.header(f"{BADGE[dsem.tipo]} Esta semana: {dsem.tipo.upper()}")
    st.markdown(f"**{FASE_ICON[dsem.fase]} {dsem.foco}**  ·  nivel {dsem.nivel}"
                + (f"  ·  largo objetivo {dsem.horas_largo}h" if dsem.horas_largo else ""))
    st.info(f"**Por qué:** {dsem.razon}")

    # --- Entrenos de la semana: rodillo estructurado (Lun-Vie) + largo (Sáb) ---
    st.subheader("🚴 Tus entrenos de esta semana")
    st.caption("Entre semana: rodillo estructurado (≤1h). Sábado: largo libre "
               "por terreno. Los de rodillo se pueden enviar a Garmin.")

    descarga = dsem.tipo in ("descarga", "carrera")
    l_sem, fin_sem = idx[sem_actual]
    dias_rodillo = ["Mar", "Mié", "Jue"]
    offset = {"Lun": 0, "Mar": 1, "Mié": 2, "Jue": 3, "Vie": 4, "Sáb": 5, "Dom": 6}

    filas_ent = []
    envio = []  # (fecha, nombre, descripcion) de sesiones estructuradas
    for dia in ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]:
        fecha = l_sem + timedelta(days=offset[dia])
        if dia == "Sáb":
            if dsem.tipo == "carrera":
                nombre, det = "CARRERA / viaje", "según etapa"
            else:
                nombre = f"Largo MTB {dsem.horas_largo}h" if dsem.horas_largo else "Largo libre"
                det = "🏔️ montaña · ritmo sostenible · comer cada 40-45'"
        elif dia == "Dom" and dsem.horas_domingo:
            nombre = f"Largo MTB {dsem.horas_domingo}h"
            det = "🔥 BACK-TO-BACK · rodar cansado · simula día 2 de etapas"
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
        # ¿hecho?
        tss_real = round(sum(a.tss for a in acts if a.day == fecha))
        marca = "✅" if tss_real else ("😴" if nombre == "Descanso" else
                                       ("⬜️" if fecha >= hoy else "❌"))
        filas_ent.append({"": marca, "Día": f"{dia} {fecha.strftime('%d/%m')}",
                          "Sesión": nombre, "Detalle": det,
                          "Hecho": f"{int(tss_real)}TSS" if tss_real else "—"})

    st.dataframe(pd.DataFrame(filas_ent).astype(str), width="stretch", hide_index=True)

    # Ver los intervalos de las sesiones de rodillo
    with st.expander("👁️ Ver los intervalos de las sesiones de rodillo"):
        for fecha, nombre, desc in envio:
            st.markdown(f"**{fecha.strftime('%a %d/%m')} · {nombre}**")
            st.code(desc)

    # Enviar a Garmin
    st.markdown("**📤 Enviar los entrenos de rodillo a Garmin**")
    preview = st.checkbox("Solo previsualizar (no enviar)", True)
    if preview:
        st.caption("👀 Modo previsualización: desmarca para enviar de verdad.")
    if st.button(f"Enviar rodillo de la semana {sem_actual} a Garmin", type="primary"):
        if preview:
            st.success(f"Previsualización: {len(envio)} entrenos (NO enviados).")
        else:
            cli = IntervalsClient(athlete_id, api_key)
            ok, errores = 0, []
            for fecha, nombre, desc in envio:
                try:
                    cli.push_planned_workout(str(fecha), nombre, desc)
                    ok += 1
                except Exception as e:
                    errores.append(f"{fecha} {nombre}: {e}")
            st.success(f"✅ {ok} entrenos enviados a tu calendario de intervals.icu.")
            if errores:
                st.error("Fallaron:\n" + "\n".join(errores))
        st.caption("El sábado es largo libre, no se envía. Sincroniza el Edge "
                   "cada mañana para bajar el entreno del día.")

st.header("📚 Tu historia en este plan")
resumenes = []
for n, (l, fin) in idx.items():
    a_sem = [a for a in acts if l <= a.day <= fin]
    horas = round(sum((x.duration_s or 0) for x in a_sem) / 3600, 1)
    tss = round(sum(x.tss for x in a_sem))
    desn = round(sum((x.elev_gain_m or 0) for x in a_sem))
    resumenes.append((n, l, fin, horas, tss, desn, len(a_sem)))

vividas = [r for r in resumenes if r[2] <= hoy or (r[1] <= hoy <= r[2])]
tot_h = round(sum(r[3] for r in vividas), 1)
tot_tss = round(sum(r[4] for r in vividas))
tot_desn = round(sum(r[5] for r in vividas))
hechas = len([r for r in resumenes if r[2] < hoy])

h1, h2, h3, h4 = st.columns(4)
h1.metric("Horas acumuladas", f"{tot_h} h")
h2.metric("Desnivel acumulado", f"{tot_desn:,} m".replace(",", "."))
h3.metric("Carga total (TSS)", f"{tot_tss:,}".replace(",", "."))
h4.metric("Semanas hechas", f"{hechas}/{len(plan)}")
st.caption("Memoria de todo el plan: no se reinicia al cambiar de semana ni al mover las fechas.")

st.header("🗓️ Plan adaptativo completo")
filas = []
for d in plan:
    l, fin = idx[d.sem]
    r = next((x for x in resumenes if x[0] == d.sem), None)
    hecho = ""
    if r and (fin < hoy or (l <= hoy <= fin)):
        hecho = f"{r[3]}h · {int(r[4])}TSS" if r[3] else "—"
    estado_txt = ("✅" if fin < hoy else "▶️" if l <= hoy <= fin else "⬜️")
    filas.append({"": estado_txt, "Sem": str(d.sem), "Desde": l.strftime("%d/%m"),
                  "Decisión": f"{BADGE[d.tipo]} {d.tipo}", "Foco": d.foco,
                  "Largo": f"{d.horas_largo}h" if d.horas_largo else "—",
                  "Hecho": hecho or "—"})
st.dataframe(pd.DataFrame(filas).astype(str), width="stretch", hide_index=True)

with st.expander("🔎 Ver por qué de cada semana"):
    for d in plan:
        st.markdown(f"**Sem {d.sem} · {BADGE[d.tipo]} {d.tipo}** — {d.razon}")

st.header("📏 Las reglas del plan")
st.caption("El plan se ajusta solo, pero con reglas claras que puedes predecir:")
for regla in A.explicar_reglas():
    st.markdown(f"- {regla}")

st.header("📈 Progresión de largos y forma")
prog_df = pd.DataFrame([{"Semana": d.sem, "Objetivo (h)": d.horas_largo or 0,
    "Hecho (h)": next((r[3] for r in resumenes if r[0] == d.sem), 0)}
    for d in plan if d.horas_largo]).set_index("Semana")
st.line_chart(prog_df)

if pmc:
    st.subheader("Fitness / Fatiga / Forma")
    st.line_chart(pd.DataFrame([{"Fecha": p.day, "Fitness": p.ctl, "Fatiga": p.atl,
        "Forma": p.tsb} for p in pmc]).set_index("Fecha"))

st.divider()
st.caption("💡 El plan se adapta a tu cumplimiento con reglas transparentes, "
           "pero tu sensación siempre manda: si el cuerpo dice basta, descansa.")
