# -*- coding: utf-8 -*-
"""
Created on Mon Nov  3 16:02:36 2025

@author: geam9
"""

from __future__ import annotations

APP_TITLE_ES = "Recomendador de Rutas · Coach Vocacional"
APP_TITLE_EN = "Training Paths Recommender · Vocational Coach"

DEFAULT_ENV_XLS_PATH = "/mnt/data/CONTENIDOS ATENEA PARA RAG.xlsx"
DEFAULT_ENV_TXT_PATH = "/mnt/data/record_0.txt"

LANGS = ["es", "en"]

# Pesos de ranking (puedes ajustar en caliente desde la UI admin más adelante)
RANK_WEIGHTS = {
    "area_exact": 3.0,
    "sheet_match": 2.0,
    "level": 2.0,
    "duration_fit": 1.0,
    "access": 1.0,
    "population": 1.0,
    "kw_overlap": 1.0,   # por hit (acotado por MAX_KW)
    "sim_tfidf": 2.0,    # similitud coseno tf-idf
    "sim_bm25": 1.5
}
MAX_KW = 4
TOPK_CANDIDATES = 80
TOPK_FINAL = 12
