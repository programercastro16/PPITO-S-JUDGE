"""
Descarga masiva de PDFs de providencias ya guardadas en BD (enlaces sin archivo local).
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from .descargar_pdf import descargar_pdfs_providencias
from .storage import actualizar_ruta_pdf_por_enlace, obtener_providencias


def _providencias_sin_archivo_local(radicado: str) -> List[Dict]:
    pendientes: List[Dict] = []
    for p in obtener_providencias(radicado):
        enlace = (p.get("enlace") or "").strip()
        if not enlace:
            continue
        ruta = (p.get("ruta_pdf") or "").strip()
        if ruta and Path(ruta).is_file():
            continue
        pendientes.append(p)
    return pendientes


def descargar_pdfs_faltantes_radicado(radicado: str, headless: bool = True) -> List[str]:
    """
    Descarga PDFs para providencias con enlace pero sin ruta_pdf válida en disco.
    Actualiza datos_json en SQLite con ruta_pdf.
    """
    pendientes = _providencias_sin_archivo_local(radicado)
    if not pendientes:
        return []
    items = descargar_pdfs_providencias(pendientes, radicado, headless=headless)
    rutas: List[str] = []
    for item in items:
        enlace = item.get("enlace") or ""
        ruta = item.get("ruta") or ""
        if enlace and ruta:
            actualizar_ruta_pdf_por_enlace(radicado, enlace, ruta)
            rutas.append(ruta)
    return rutas


def descargar_pdfs_faltantes_lista(radicados: List[str], headless: bool = True) -> Dict[str, List[str]]:
    """Por cada radicado, descarga faltantes. Devuelve mapa radicado -> lista de rutas nuevas."""
    out: Dict[str, List[str]] = {}
    for rad in radicados:
        guardados = descargar_pdfs_faltantes_radicado(rad.strip(), headless=headless)
        if guardados:
            out[rad.strip()] = guardados
    return out
