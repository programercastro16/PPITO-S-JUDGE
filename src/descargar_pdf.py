"""
Descarga los PDF de las providencias (enlaces guardados) a una carpeta local.
Usa Playwright para respetar la sesión/cookies del portal si hace falta.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Dict, Any

from playwright.sync_api import sync_playwright

from .config import CARPETA_PDF_PROVIDENCIAS, TIMEOUT_NAVEGACION


def _nombre_archivo_seguro(fecha: str, tipo: str, indice: int) -> str:
    """Genera un nombre de archivo seguro a partir de fecha y tipo."""
    s = f"{fecha}_{tipo}_{indice}".strip()
    s = re.sub(r'[<>:"/\\|?*]', "_", s)
    s = s[:80].strip() or f"providencia_{indice}"
    return s + ".pdf"


def descargar_pdfs_providencias(
    providencias: List[Dict[str, Any]],
    radicado: str,
    headless: bool = True,
) -> List[Dict[str, str]]:
    """
    Descarga el PDF de cada providencia que tenga 'enlace' a la carpeta
    CARPETA_PDF_PROVIDENCIAS/<radicado>/.

    Devuelve una lista de dicts {"enlace": url, "ruta": path} por cada archivo guardado.
    """
    if not providencias:
        return []

    carpeta = Path(CARPETA_PDF_PROVIDENCIAS) / radicado
    carpeta.mkdir(parents=True, exist_ok=True)
    guardados: List[Dict[str, str]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            locale="es-CO",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

        try:
            for i, prov in enumerate(providencias):
                enlace = (prov.get("enlace") or "").strip()
                if not enlace or not (enlace.startswith("http") or enlace.startswith("/")):
                    continue
                if not enlace.startswith("http"):
                    enlace = "https://publicacionesprocesales.ramajudicial.gov.co" + (
                        enlace if enlace.startswith("/") else "/" + enlace
                    )
                fecha = prov.get("fecha") or ""
                tipo = prov.get("tipo") or "providencia"
                nombre = _nombre_archivo_seguro(fecha, tipo, i + 1)
                ruta = carpeta / nombre
                try:
                    resp = context.request.get(
                        enlace,
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"},
                        timeout=TIMEOUT_NAVEGACION,
                    )
                    if resp.ok:
                        body = resp.body()
                        if body and len(body) > 100:
                            ruta.write_bytes(body)
                            guardados.append({"enlace": enlace, "ruta": str(ruta)})
                except Exception:
                    pass
        finally:
            browser.close()

    return guardados
