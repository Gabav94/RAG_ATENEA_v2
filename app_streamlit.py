# -*- coding: utf-8 -*-
"""
Created on Mon Nov  3 16:23:21 2025

@author: geam9
"""

from __future__ import annotations
import os
import re
import json
import time
import streamlit as st
import pandas as pd
from typing import List, Dict, Any

from config import APP_TITLE_ES, APP_TITLE_EN, DEFAULT_ENV_XLS_PATH, DEFAULT_ENV_TXT_PATH, TOPK_CANDIDATES, TOPK_FINAL
from rag_build import load_catalog, RAGIndex
from ranker import rerank
from chat_orchestrator import ProfileState, ChatOpenAI, update_state_from_text, build_query_from_state, llm_intro_coach, llm_explain_track
from pdf_utils import build_path_pdf


# ---------------------------
# Helpers
# ---------------------------
def tokenize_kw(s: str) -> List[str]:
    toks = [t.strip().lower()
            for t in re.split(r"[,\;/]| y | and ", s or "") if t.strip()]
    out = []
    for t in toks:
        out.extend([w for w in re.split(r"\s+", t) if w])
    return list(dict.fromkeys(out))


# ---------------------------
# UI Config
# ---------------------------
st.set_page_config(page_title="Coach Vocacional · Rutas", layout="wide")
LANG = st.session_state.get("lang", "es")

title = APP_TITLE_ES if LANG == "es" else APP_TITLE_EN
st.title(title)

# Sidebar: idioma + carga
with st.sidebar:
    LANG = st.selectbox("Language / Idioma", ["es", "en"], index=0, key="lang")
    st.markdown("**1) Sube el Excel del catálogo**")
    xls_file = st.file_uploader("Excel (.xlsx)", type=["xlsx"], key="xls")
    st.caption("o usa el archivo por defecto del entorno")
    use_env = st.checkbox("Usar archivo del entorno", value=False)
    st.markdown("---")
    st.markdown("**Opcional:** Subir TXT de ejemplo")
    txt_file = st.file_uploader("TXT (.txt)", type=["txt"], key="txt")

# Cargar catálogo
catalog = pd.DataFrame()
if xls_file is not None:
    catalog = load_catalog(xls_file)
elif use_env and os.path.exists(DEFAULT_ENV_XLS_PATH):
    catalog = load_catalog(DEFAULT_ENV_XLS_PATH)

if catalog.empty:
    st.info("Sube el Excel para comenzar.")
    st.stop()

# Campos dependientes: valores únicos dinámicos
sheets = sorted(catalog["_sheet"].dropna().unique().tolist())
areas = sorted(list(dict.fromkeys(
    list(catalog["Grupo de Competencias"].dropna().unique()) + sheets)))
levels = [x for x in ["Básico", "Intermedio", "Avanzado"]
          if x in catalog["Nivel de complejidad"].astype(str).unique()]
access_opts = ["REA", "Redireccionamiento", "Moodle"]

# Construir índice RAG


@st.cache_resource(show_spinner=False)
def _build_index(df: pd.DataFrame):
    return RAGIndex(df)


rag_index = _build_index(catalog)

# Estado de perfil/conversación
if "profile" not in st.session_state:
    st.session_state.profile = ProfileState(language=LANG)

state: ProfileState = st.session_state.profile
state.language = LANG  # sync

# Panel izquierdo: Campos dependientes (filtros explícitos)
with st.sidebar:
    st.markdown("---")
    st.header("Filtros (opcionales)")
    area_sel = st.selectbox("Área / Hoja", [""] + areas, index=0)
    level_sel = st.selectbox("Nivel objetivo", [""] + levels, index=0)
    max_hours = st.number_input("Máx. horas disponibles", min_value=0.0,
                                max_value=1000.0, value=float(state.max_hours or 40.0), step=1.0)
    access_sel = st.selectbox("Tipo de acceso", [""] + access_opts, index=0)
    population = st.text_input(
        "Población objetivo (texto)", value=state.population or "")
    kw_text = st.text_input("Intereses / palabras clave",
                            value=state.keywords_text or "inteligencia artificial, datos, marketing")

    # Persistir al state
    state.area = area_sel or ""
    state.level = level_sel or ""
    state.max_hours = float(max_hours)
    state.access = access_sel or ""
    state.population = population.strip()
    state.keywords_text = kw_text.strip()

    st.markdown("---")
    st.caption("Consejo: si no sabes qué elegir, ¡usa el chat evocador! 😊")


# Columna principal: Chat evocador + resultados
col_chat, col_results = st.columns([1.1, 1.4])

with col_chat:
    st.subheader("Coach · Charlemos")
    if txt_file is not None:
        with st.expander("Ver TXT subido"):
            st.code(txt_file.read().decode("utf-8"), language="text")
    elif os.path.exists(DEFAULT_ENV_TXT_PATH):
        with open(DEFAULT_ENV_TXT_PATH, "r", encoding="utf-8") as fh:
            demo_txt = fh.read()
        with st.expander("Ver record TXT (demo)"):
            st.code(demo_txt[:1200] + ("..." if len(demo_txt)
                    > 1200 else ""), language="text")

    # Inicio de entrevista con preguntas evocadoras
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
        st.session_state.chat_history.append(
            {"role": "assistant", "content": "¡Hola! Soy tu coach. 😊 ¿Cómo estás hoy? ¿Qué edad tienes?"})

    # Render conversación
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("Escribe aquí…")
    if user_input:
        st.session_state.chat_history.append(
            {"role": "user", "content": user_input})
        # Actualiza slots
        state = update_state_from_text(state, user_input)
        # Decide siguiente pregunta / respuesta con LLM (o fallback)
        llm = ChatOpenAI()
        reply = llm_intro_coach(llm, state, user_input)

        # Avanza pasos de entrevista
        state.step += 1
        # Siguiente pregunta guiada (simple)
        from chat_orchestrator import EVOCATIVE_QUESTIONS_ES, FOLLOWUP_ES
        if state.step < len(EVOCATIVE_QUESTIONS_ES):
            reply = reply + "\n\n" + EVOCATIVE_QUESTIONS_ES[state.step]
        elif state.step == len(EVOCATIVE_QUESTIONS_ES):
            reply = reply + "\n\n" + FOLLOWUP_ES[0]
        else:
            # Cuando ya hay suficiente contexto, ofrecer generar ruta
            reply = reply + "\n\n¿Te propongo una ruta inicial y la ajustamos juntos?"

        st.session_state.chat_history.append(
            {"role": "assistant", "content": reply})

    # Botón para proponer ruta desde el chat
    propose = st.button("Proponer ruta desde la conversación")
    if propose:
        st.session_state.chat_history.append(
            {"role": "assistant", "content": "Perfecto. Construyamos una ruta inicial según lo conversado…"})


with col_results:
    st.subheader("Ruta sugerida (RAG + Ranking)")
    # Construye query híbrida desde el perfil
    query_text = build_query_from_state(state)
    user_tokens = tokenize_kw(
        (state.keywords_text or "") + " " + " ".join(state.interests or []))

    # Recuperar candidatos
    fused = rag_index.hybrid_search(query_text, topk=TOPK_CANDIDATES)

    # Filtrar por metadatos (post-retrieval) según selección explícita del usuario
    def pass_filters(row: pd.Series) -> bool:
        if state.area and (row.get("Grupo de Competencias") != state.area) and (row.get("_sheet") != state.area):
            return False
        if state.level and str(row.get("Nivel de complejidad", "")).strip() != state.level:
            return False
        if state.access and state.access.lower() not in str(row.get("Tipo de Acceso (REA o Redireccionamiento)", "")).lower():
            return False
        if state.population and state.population.lower() not in str(row.get("Población objetivo", "")).lower():
            return False
        if state.max_hours is not None:
            try:
                h = float(row.get("_horas", 1e9))
                if h > float(state.max_hours):
                    return False
            except Exception:
                pass
        return True

    filtered = [c for c in fused if pass_filters(c["row"])]

    # Ranking final
    ranked = rerank(filtered, profile=state.model_dump(),
                    user_tokens=user_tokens)
    ranked = ranked[:TOPK_FINAL]

    # Explicación por LLM y controles
    llm = ChatOpenAI()
    if ranked:
        with st.expander("Explicación del plan (coach)"):
            st.write(llm_explain_track(llm, state, ranked))

        # Render cards
        for c in ranked:
            r = c["row"]
            with st.container(border=True):
                st.markdown(f"### {r.get('Curso', '(sin nombre)')}")
                st.write(f"**Nivel:** {r.get('Nivel de complejidad', '')
                                       }  |  **Duración:** {r.get('Duración del Curso', '')}")
                st.write(
                    f"**Portal/Aliado:** {r.get('Portal o Aliado', '')}  |  **Categoría:** {r.get('_sheet', '')}")
                url = str(r.get("URL del Curso", "") or "")
                if url.strip():
                    st.markdown(f"[🔗 Ir al curso]({url})")
                st.caption(
                    f"**Por qué aparece:** tfidf/bm25 + filtros + perfil.")
                st.write(str(r.get("Descripción del Curso", "") or ""))
                st.caption(
                    f"**Competencias:** {str(r.get('Competencia que se fomenta con el curso', '') or '')}")
                st.caption(
                    f"**Habilidades:** {str(r.get('Habilidad', '') or '')}")

        # Descargar PDF
        profile_text = (
            f"Idioma: {state.language} | Edad: {
                state.age or 'N/D'} | Estilo: {state.self_style or 'N/D'} | "
            f"Intereses: {', '.join(state.interests)
                          if state.interests else 'N/D'} | "
            f"Valores: {', '.join(state.values) if state.values else 'N/D'} | "
            f"Meta: {state.goals or 'N/D'} | Tiempo/semana: {state.max_hours} h | "
            f"Área: {
                state.area or 'N/D'} | Nivel: {state.level or 'N/D'} | Acceso: {state.access or 'N/D'}"
        )
        pdf_bytes = build_path_pdf("Ruta recomendada", profile_text, ranked)
        st.download_button("⬇️ Descargar ruta en PDF", data=pdf_bytes,
                           file_name="ruta_recomendada.pdf", mime="application/pdf")
    else:
        st.warning(
            "No encontré coincidencias suficientes. Ajusta filtros o cuéntame más en el chat (intereses, metas, estilo).")
