# -*- coding: utf-8 -*-
"""
Created on Mon Nov  3 16:03:16 2025

@author: geam9
"""

from __future__ import annotations
import re
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# -----------------------------
# Limpieza / Normalización
# -----------------------------
def _norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [re.sub(r"\s+", " ", c).strip() for c in df.columns]
    return df


def _safe(s) -> str:
    return "" if pd.isna(s) else str(s)


def parse_hours(x) -> float:
    if pd.isna(x):
        return np.nan
    s = str(x).lower()
    m = re.search(r"(\d+(\.\d+)?)", s)
    if not m:
        return np.nan
    val = float(m.group(1))
    return val if "min" not in s else round(val/60.0, 2)


# -----------------------------
# Carga del catálogo
# -----------------------------
KEY_COLS = [
    "Portal o Aliado",
    "Tipo de Acceso (REA o Redireccionamiento)",
    "Grupo de Competencias",
    "Curso",
    "Descripción del Curso",
    "URL del Curso",
    "URL del curso Moodle",
    "Cualificación asociada (Marco Nacional de Cualificaciones de Colombia)",
    "Nivel de complejidad",
    "Competencia que se fomenta con el curso",
    "Habilidad",
    "Palabras Clave",
    "Población objetivo",
    "Duración del Curso",
]


def load_catalog(xls_file) -> pd.DataFrame:
    xl = pd.ExcelFile(xls_file)
    frames = []
    for sheet in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=sheet)
        df = _norm_cols(df)
        if df.empty:
            continue
        for c in KEY_COLS:
            if c not in df.columns:
                df[c] = np.nan
        df["_sheet"] = sheet
        df["_horas"] = df["Duración del Curso"].apply(parse_hours)
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    return out


# -----------------------------
# RAG híbrido (BM25 + TF-IDF)
# -----------------------------
def doc_text(row: pd.Series) -> str:
    return " | ".join([
        _safe(row.get("Curso")),
        _safe(row.get("Descripción del Curso")),
        _safe(row.get("Competencia que se fomenta con el curso")),
        _safe(row.get("Habilidad")),
        _safe(row.get("Palabras Clave")),
        _safe(row.get("Grupo de Competencias")),
        _safe(row.get("Población objetivo")),
        _safe(row.get("_sheet")),
        _safe(row.get("Portal o Aliado")),
    ])


def tokenize(s: str) -> List[str]:
    s = (s or "").lower()
    parts = re.split(r"[^a-záéíóúñ0-9]+", s, flags=re.IGNORECASE)
    return [p for p in parts if p]


class RAGIndex:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.corpus = [doc_text(r) for _, r in self.df.iterrows()]
        # BM25
        self._bm25_tokens = [tokenize(t) for t in self.corpus]
        self.bm25 = BM25Okapi(self._bm25_tokens)
        # TF-IDF
        self.tfidf = TfidfVectorizer(min_df=1, ngram_range=(1, 2))
        self.tfidf_mat = self.tfidf.fit_transform(self.corpus)

    def _bm25_search(self, q: str, topk: int) -> Tuple[List[int], np.ndarray]:
        qtok = tokenize(q)
        scores = np.array(self.bm25.get_scores(qtok))
        idx = np.argsort(-scores)[:topk]
        return idx.tolist(), scores[idx]

    def _tfidf_search(self, q: str, topk: int) -> Tuple[List[int], np.ndarray]:
        qv = self.tfidf.transform([q])
        sims = cosine_similarity(qv, self.tfidf_mat).ravel()
        idx = np.argsort(-sims)[:topk]
        return idx.tolist(), sims[idx]

    def hybrid_search(self, q: str, topk: int = 80) -> List[Dict[str, Any]]:
        idx_b, s_b = self._bm25_search(q, topk)
        idx_t, s_t = self._tfidf_search(q, topk)
        # fusión por rank y suma normalizada
        items = {}
        for rank, (i, sc) in enumerate(zip(idx_b, s_b), start=1):
            items.setdefault(i, {"bm25": 0.0, "tfidf": 0.0})
            items[i]["bm25"] = float(sc) / max(s_b.max(), 1e-9) * (1.0 / rank)
        for rank, (i, sc) in enumerate(zip(idx_t, s_t), start=1):
            items.setdefault(i, {"bm25": 0.0, "tfidf": 0.0})
            items[i]["tfidf"] = float(sc) / max(s_t.max(), 1e-9) * (1.0 / rank)

        fused = []
        for i, scs in items.items():
            row = self.df.iloc[i]
            fused.append({
                "idx": i,
                "row": row,
                "bm25_norm": scs["bm25"],
                "tfidf_norm": scs["tfidf"],
            })
        fused.sort(key=lambda x: (
            x["bm25_norm"] + x["tfidf_norm"]), reverse=True)
        return fused[:topk]
