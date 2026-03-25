"""
Scraper de Publicaciones Procesales (Rama Judicial).
Obtiene las providencias (decisiones del juez) asociadas a un proceso por número de radicado.
https://publicacionesprocesales.ramajudicial.gov.co/
"""
from __future__ import annotations

import re
from typing import List, Dict, Any

from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeout

from .config import URL_PUBLICACIONES, TIMEOUT_NAVEGACION, TIMEOUT_SELECTOR


def normalizar_radicado(numero: str) -> str:
    return re.sub(r"\D", "", numero).strip()


def extraer_providencias_desde_pagina(page: Page) -> List[Dict[str, Any]]:
    """
    Extrae la lista de publicaciones/providencias de la página actual.
    Ajustar selectores según la estructura real del portal.
    """
    providencias: List[Dict[str, Any]] = []
    try:
        # Tabla de resultados
        rows = page.locator("table tbody tr").all()
        for row in rows:
            celdas = row.locator("td").all_text_contents()
            enlaces = row.locator("a[href]").all()
            enlace = enlaces[0].get_attribute("href") if enlaces else ""
            if enlace and not enlace.startswith("http"):
                enlace = URL_PUBLICACIONES.rstrip("/") + ("/" if not enlace.startswith("/") else "") + enlace
            if len(celdas) >= 1:
                providencias.append({
                    "fecha": celdas[0].strip() if len(celdas) > 0 else "",
                    "tipo": celdas[1].strip() if len(celdas) > 1 else "",
                    "resumen": " ".join(c.strip() for c in celdas[2:]) if len(celdas) > 2 else "",
                    "enlace": enlace,
                })

        if providencias:
            return providencias

        # Cards o listas de publicaciones
        items = page.locator("[data-publicacion], .publicacion, .resultado-item, article, .card").all()
        for item in items:
            link = item.locator("a[href]").first
            href = link.get_attribute("href") if link.count() else ""
            if href and not href.startswith("http"):
                href = URL_PUBLICACIONES.rstrip("/") + ("/" if not href.startswith("/") else "") + href
            texto = item.inner_text()
            lineas = [l.strip() for l in texto.split("\n") if l.strip()]
            providencias.append({
                "fecha": lineas[0] if len(lineas) > 0 else "",
                "tipo": lineas[1] if len(lineas) > 1 else "",
                "resumen": " ".join(lineas[2:]) if len(lineas) > 2 else texto.strip(),
                "enlace": href or "",
            })
    except Exception:
        pass
    return providencias


def obtener_providencias(numero_radicado: str, headless: bool = True) -> List[Dict[str, Any]]:
    """
    Abre Publicaciones Procesales, busca por número de radicado y devuelve las providencias.

    :param numero_radicado: Número de radicación.
    :param headless: Si True, el navegador no se muestra.
    :return: Lista de dicts con keys: fecha, tipo, resumen, enlace.
    """
    radicado = normalizar_radicado(numero_radicado)
    if not radicado:
        return []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            locale="es-CO",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = context.new_page()
        page.set_default_timeout(TIMEOUT_NAVEGACION)

        try:
            page.goto(URL_PUBLICACIONES, wait_until="domcontentloaded")
            page.wait_for_load_state("networkidle", timeout=TIMEOUT_NAVEGACION)

            # Campo de búsqueda (placeholder "Búsqueda...")
            search = page.get_by_placeholder(re.compile(r"búsqueda|busqueda|search", re.I))
            if search.count() == 0:
                search = page.locator("input[type='search'], input[type='text']").first
            search.fill(radicado, timeout=TIMEOUT_SELECTOR)

            # Botón BUSCAR
            btn = page.get_by_role("button", name=re.compile(r"buscar", re.I))
            if btn.count() == 0:
                btn = page.locator("button:has-text('BUSCAR'), button:has-text('Buscar'), .btn-buscar").first
            btn.click(timeout=TIMEOUT_SELECTOR)
            page.wait_for_load_state("networkidle", timeout=TIMEOUT_NAVEGACION)

            providencias = extraer_providencias_desde_pagina(page)
            return providencias

        except PlaywrightTimeout as e:
            raise TimeoutError(f"Tiempo de espera agotado en Publicaciones Procesales: {e}")
        finally:
            browser.close()

    return []
