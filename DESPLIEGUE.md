# 🚀 Cómo publicar tu app en Streamlit Cloud (URL propia, sin Terminal)

Sigue estos pasos UNA vez. Después, tu app vivirá en una URL que abres desde
cualquier navegador (computador o celular), sin Terminal ni instalaciones.

---

## Paso 1 — Crear el repositorio en GitHub

1. Entra a https://github.com y crea un **repositorio nuevo** (New repository).
2. Nómbralo, por ejemplo, `mi-entrenador-ciclismo`.
3. **Hazlo privado** (Private) — así nadie ve tu configuración.
4. NO marques "Add README" (ya tenemos archivos).
5. Créalo.

## Paso 2 — Subir los archivos

Descomprime el ZIP que te pasé. Sube TODOS estos archivos al repo
(arrastrándolos en la web de GitHub, botón "Add file > Upload files", o con git):

```
app.py
adaptive.py
race_plan.py
workouts_rodillo.py
history.py
training_engine.py
intervals_connector.py
requirements.txt
.streamlit/config.toml
.gitignore
```

⚠️ IMPORTANTE: NO subas ningún archivo `secrets.toml` con tu API key real.
El `.gitignore` ya lo evita, pero por si acaso: tu API key NUNCA va en el repo.

## Paso 3 — Conectar Streamlit Cloud

1. Entra a https://share.streamlit.io e inicia sesión **con tu cuenta de GitHub**.
2. Click en **"New app"** (o "Create app").
3. Elige:
   - **Repository:** el que acabas de crear (`mi-entrenador-ciclismo`)
   - **Branch:** `main`
   - **Main file path:** `app.py`
4. Click en **"Deploy"**.

En 1-2 minutos tu app estará viva en una URL como:
`https://mi-entrenador-ciclismo.streamlit.app`

## Paso 4 (opcional) — Guardar tu API key de forma segura

Para no meter la API key cada vez:

1. En share.streamlit.io, abre tu app > **Settings** (⚙️) > **Secrets**.
2. Pega esto (con tus datos reales):

```toml
ATHLETE_ID = "i627551"
API_KEY = "tu_api_key_real_de_intervals"
```

3. Guarda. La app se reinicia sola y ya cargará tus datos sin pedirte nada.

Esto es SEGURO: los secrets viven cifrados en Streamlit, no en el repo público.
Si prefieres no hacerlo, simplemente sigue metiendo la API key a mano en la app.

---

## Ventajas de tener esto en la nube
- ✅ La abres desde cualquier navegador, también el celular.
- ✅ Se acabaron los "Failed to resolve" y los líos de urllib3.
- ✅ No necesitas Terminal nunca más.
- ✅ Puedes revisar tu plan durante la carrera desde el móvil.

## Cómo actualizar la app en el futuro
Cuando cambiemos algo del código, actualizas los archivos en el repo de GitHub
y Streamlit Cloud lo detecta y re-despliega solo. Sin pasos extra.
