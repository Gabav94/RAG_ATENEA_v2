# -*- coding: utf-8 - *-
"""
Created on Mon Nov  3 16:04:10 2025

@author: geam9
"""

from __future__ import annotations
import os
import re
import json
from typing import Dict, Any, List
from pydantic import BaseModel, Field
import streamlit as st
from dotenv import dotenv_values


config = dotenv_values()


# --------------------------
# ChatOpenAI wrapper (light)
# --------------------------
class ChatOpenAI:
    """
    Wrapper minimalista. Si no hay OPENAI_API_KEY, responde con heurística local.
    Reemplaza por tu cliente real (langchain/openai) si lo deseas.
    """

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.4):
        self.model = model
        self.temperature = temperature
        # self.enabled = bool(os.environ.get("OPENAI_API_KEY"))
        self.enabled = bool(st.secrets["OPENAI_API_KEY"])
        # self.enabled = bool(config["OPENAI_API_KEY"])

    def chat(self, messages: List[Dict[str, str]]) -> str:
        if not self.enabled:
            # Fallback simple: eco con tips
            last = messages[-1]["content"] if messages else ""
            return ("(demo sin LLM) Entiendo. A partir de lo que me cuentas, "
                    "priorizaré cursos intro y prácticos; si te gusta la creatividad "
                    "y análisis, mezclaré IA básica + marketing digital + proyectos cortos. "
                    f"Mensaje recibido: {last[:200]}...")
        # ↓ Si integras el cliente real, haz la llamada aquí y retorna el texto
        # Ej. con openai: client.chat.completions.create(model=..., messages=messages)
        # Devuelve `response_text`
        return "(demo) LLM activo — agrega tu cliente aquí."


# --------------------------
# Estado de entrevista
# --------------------------
class ProfileState(BaseModel):
    language: str = "es"
    # Campos del catálogo
    area: str = ""
    level: str = ""
    max_hours: float | None = 40.0
    access: str = ""         # REA/Redireccionamiento/Moodle
    population: str = ""
    keywords_text: str = ""
    # Campos evocadores (psico/vocacionales)
    age: int | None = None
    short_bio: str = ""      # “cuéntame sobre ti”
    self_style: str = ""     # “¿cómo te describirías?”
    interests: List[str] = Field(default_factory=list)  # hobbies, curiosidades
    # “impacto social”, “creatividad”, “seguridad”, etc.
    values: List[str] = Field(default_factory=list)
    learning_style: str = ""  # “práctico”, “teórico”, “proyectos”, “micro-lecciones”
    goals: str = ""          # “quiero emprender”, “busco empleo rápido”, etc.
    constraints: str = ""    # horarios, conectividad, dispositivos
    # Control de conversación
    step: int = 0
    confirmed: bool = False


EVOCATIVE_QUESTIONS_ES = [
    "¡Hola! 😊 ¿Cómo estás hoy? ¿Qué edad tienes?",
    "Cuéntame un poco sobre ti: ¿qué te entusiasma últimamente?",
    "¿Cómo te describirías en pocas palabras (p. ej., creativo, analítico, práctico, social)?",
    "¿Qué intereses o hobbies tienes (ej.: tecnología, diseño, negocios, ciencia, arte, servicio social)?",
    "¿Qué valoras más al aprender: resultados rápidos, profundidad teórica, proyectos, comunidad?",
    "¿Cómo te gusta aprender: cursos cortos, retos prácticos, lecturas, videos, mentores?",
    "En esta plataforma: ¿qué esperas lograr en 1–3 meses?",
    "¿Cuántas horas a la semana podrías dedicar? (número aproximado)",
]

FOLLOWUP_ES = [
    "Con lo que me cuentas, ¿te gustaría empezar por fundamentos o prefieres saltar directo a cosas aplicadas?",
    "¿Te interesan rutas con certificación/constancia o te basta con aprender práctico?",
    "¿Hay alguna restricción o preferencia técnica? (acceso REA/Moodle, conexión, dispositivo)",
    "¿Te gusta este path inicial? ¿Qué le cambiarías o agregarías?",
]


def extract_number(s: str) -> int | None:
    m = re.search(r"(\d+)", s or "")
    return int(m.group(1)) if m else None


def update_state_from_text(state: ProfileState, user_msg: str) -> ProfileState:
    # Heurística simple para llenar slots durante la charla
    if state.age is None:
        age = extract_number(user_msg)
        if age:
            state.age = age
    # keywords
    kws = [w.strip().lower() for w in re.split(
        r"[,\;/]| y | and ", user_msg) if 2 <= len(w.strip()) <= 32]
    # si el usuario menciona cosas tipo "marketing", "datos", etc. súmalas a interests
    interest_hits = [w for w in kws if w in {"datos", "data", "marketing", "diseño", "programación", "ia", "inteligencia", "excel", "python",
                                             "finanzas", "proyectos", "emprendimiento", "servicio", "social", "salud", "docencia", "seguridad", "ciberseguridad", "cloud"}]
    if interest_hits:
        merged = list(dict.fromkeys((state.interests or []) + interest_hits))
        state.interests = merged[:10]
    # estilo/aprendizaje
    if any(t in user_msg.lower() for t in ["proyecto", "proyectos", "hands-on", "práctic"]):
        state.learning_style = state.learning_style or "proyectos"
    return state


def build_query_from_state(state: ProfileState) -> str:
    # Query semántica híbrida
    parts = []
    if state.area:
        parts.append(f"area:{state.area}")
    if state.level:
        parts.append(f"level:{state.level}")
    if state.access:
        parts.append(f"access:{state.access}")
    if state.population:
        parts.append(f"population:{state.population}")
    if state.keywords_text:
        parts.append(state.keywords_text)
    # intereses/valores
    if state.interests:
        parts.append("intereses: " + ", ".join(state.interests))
    if state.values:
        parts.append("valores: " + ", ".join(state.values))
    if state.learning_style:
        parts.append("aprendizaje:" + state.learning_style)
    if state.goals:
        parts.append("meta:" + state.goals)
    if state.constraints:
        parts.append("restricciones:" + state.constraints)
    return " | ".join(parts) or "fundamentos para principiantes"


def llm_intro_coach(llm: ChatOpenAI, state: ProfileState, user_msg: str) -> str:
    messages = [
        {"role": "system", "content": "Eres un coach vocacional amable y práctico. Haces preguntas cortas, conectas intereses con cursos y justificas sugerencias con claridad. No inventes datos del catálogo."},
        {"role": "user", "content": f"Idioma: {
            state.language}. Usuario dice: {user_msg}."}
    ]
    return llm.chat(messages)


def llm_explain_track(llm: ChatOpenAI, state: ProfileState, courses: List[dict]) -> str:
    # Genera explicación amigable de por qué ese orden y cómo encaja con la persona
    bullets = []
    for c in courses[:6]:
        r = c["row"]
        bullets.append(f"- {r.get('Curso', '(sin nombre)')} · {r.get(
            'Nivel de complejidad', '')} · {r.get('Duración del Curso', '')}")
    plan = "\n".join(bullets)
    messages = [
        {"role": "system", "content": "Eres un asesor que explica rutas de aprendizaje en lenguaje claro, de básico a avanzado, conectando intereses/valores del usuario con los cursos."},
        {"role": "user", "content": f"Perfil: {state.model_dump()}. Propón un orden (starter→aplicado→proyecto), 4–8 cursos. Lista breve:\n{
            plan}\nExplica cómo encaja con sus intereses/estilo. Cierra preguntando si desea cambios."}
    ]
    return llm.chat(messages)
