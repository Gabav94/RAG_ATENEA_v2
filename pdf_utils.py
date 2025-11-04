# -*- coding: utf-8 -*-
"""
Created on Mon Nov  3 16:20:41 2025

@author: geam9
"""

from __future__ import annotations
from io import BytesIO
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch


def build_path_pdf(title: str, profile_text: str, courses: list[dict]) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    width, height = LETTER
    x, y = 0.8*inch, height - 1*inch

    def line(txt, size=10, leading=14):
        nonlocal y
        c.setFont("Helvetica", size)
        for part in wrap_text(txt, 90):
            c.drawString(x, y, part)
            y -= leading
            if y < 1*inch:
                c.showPage()
                y = height - 1*inch

    c.setTitle(title)
    line(title, size=14, leading=18)
    y -= 6
    line("Perfil resumido:", size=11, leading=15)
    line(profile_text, size=9, leading=13)
    y -= 8
    line("Ruta recomendada:", size=11, leading=15)

    for i, cobj in enumerate(courses, start=1):
        r = cobj["row"]
        line(f"{i}. {r.get('Curso', '(sin nombre)')}", size=11, leading=15)
        line(f"   Nivel: {r.get('Nivel de complejidad', '')}  ·  Duración: {
             r.get('Duración del Curso', '')}", size=9)
        line(f"   Portal: {r.get('Portal o Aliado', '')
                           }  ·  Categoría: {r.get('_sheet', '')}", size=9)
        url = str(r.get('URL del Curso', '') or '')
        if url.strip():
            line(f"   URL: {url}", size=9)
        desc = str(r.get('Descripción del Curso', '') or '')
        if desc.strip():
            line(f"   Desc: {desc[:400]}{
                 '...' if len(desc) > 400 else ''}", size=9)
        line("")

    c.showPage()
    c.save()
    return buf.getvalue()


def wrap_text(text: str, width: int) -> list[str]:
    words = (text or "").split()
    lines, current = [], []
    for w in words:
        tentative = " ".join(current + [w])
        if len(tentative) > width:
            lines.append(" ".join(current))
            current = [w]
        else:
            current.append(w)
    if current:
        lines.append(" ".join(current))
    return lines
