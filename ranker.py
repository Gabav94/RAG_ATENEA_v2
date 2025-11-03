# -*- coding: utf-8 -*-
"""
Created on Mon Nov  3 16:03:42 2025

@author: geam9
"""

from __future__ import annotations
from typing import Dict, Any, List
import numpy as np
import pandas as pd
from config import RANK_WEIGHTS, MAX_KW


def _safe(x): return "" if pd.isna(x) else str(x)


def kw_overlap(user_tokens: List[str], text: str) -> int:
    if not user_tokens:
        return 0
    s = (text or "").lower()
    hits = sum(1 for t in user_tokens if t in s)
    return min(hits, MAX_KW)


def build_text_blob(r: pd.Series) -> str:
    return " | ".join([
        _safe(r.get("Palabras Clave")),
        _safe(r.get("Descripción del Curso")),
        _safe(r.get("Curso")),
        _safe(r.get("Competencia que se fomenta con el curso")),
        _safe(r.get("Habilidad")),
    ])


def featureize(candidate: Dict[str, Any], profile: Dict[str, Any], user_tokens: List[str]) -> Dict[str, float]:
    r = candidate["row"]

    f = dict.fromkeys([
        "area_exact", "sheet_match", "level",
        "duration_fit", "access", "population",
        "kw_overlap", "sim_tfidf", "sim_bm25"
    ], 0.0)

    # Área / hoja
    area = profile.get("area", "").lower().strip()
    if area:
        if _safe(r.get("Grupo de Competencias")).lower().strip() == area:
            f["area_exact"] = 1.0
        elif _safe(r.get("_sheet")).lower().strip() == area:
            f["sheet_match"] = 1.0

    # Nivel
    level = profile.get("level", "").lower().strip()
    if level and _safe(r.get("Nivel de complejidad")).lower().strip() == level:
        f["level"] = 1.0

    # Duración fit
    max_hours = profile.get("max_hours", None)
    if max_hours is not None:
        horas = r.get("_horas", None)
        try:
            if horas is not None and not pd.isna(horas) and float(horas) <= float(max_hours):
                f["duration_fit"] = 1.0
        except Exception:
            pass

    # Acceso
    access = profile.get("access", "").lower().strip()
    if access and access in _safe(r.get("Tipo de Acceso (REA o Redireccionamiento)")).lower():
        f["access"] = 1.0

    # Población
    pop = profile.get("population", "").lower().strip()
    if pop and pop in _safe(r.get("Población objetivo")).lower():
        f["population"] = 1.0

    # KW overlap
    f["kw_overlap"] = float(kw_overlap(user_tokens, build_text_blob(r)))

    # Similitudes del retriever
    f["sim_tfidf"] = float(candidate.get("tfidf_norm", 0.0))
    f["sim_bm25"] = float(candidate.get("bm25_norm",  0.0))

    return f


def score_features(feats: Dict[str, float], weights: Dict[str, float]) -> float:
    return sum(feats[k]*weights.get(k, 0.0) for k in feats.keys())


def rerank(candidates: List[Dict[str, Any]], profile: Dict[str, Any], user_tokens: List[str], weights=RANK_WEIGHTS):
    scored = []
    for c in candidates:
        feats = featureize(c, profile, user_tokens)
        c["feats"] = feats
        c["score"] = score_features(feats, weights)
        scored.append(c)
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored
