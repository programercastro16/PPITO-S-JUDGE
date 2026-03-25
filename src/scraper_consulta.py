"""
Scraper de Consulta de Procesos Nacional Unificada (Rama Judicial).
Obtiene actuaciones y providencias (documento del juez) por número de radicación.
https://consultaprocesos.ramajudicial.gov.co/Procesos/Index

Flujo: radicado → Datos del proceso → pestaña ACTUACIONES → tabla con icono verde
       → clic en icono = providencia (PDF con decisión del juez).
"""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urljoin
from typing import List, Dict, Any, Tuple

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from .config import (
    URL_CONSULTA_PROCESOS,
    TIMEOUT_NAVEGACION,
    TIMEOUT_SELECTOR,
    CARPETA_PDF_PROVIDENCIAS,
)


def normalizar_radicado(numero: str) -> str:
    """Deja solo dígitos (23 para radicado estándar)."""
    return re.sub(r"\D", "", numero).strip()


def _nombre_archivo_seguro(fecha: str, tipo: str, indice: int) -> str:
    s = f"{fecha}_{tipo}_{indice}".strip()
    s = re.sub(r'[<>:"/\\|?*]', "_", s)
    return (s[:80].strip() or f"providencia_{indice}") + ".pdf"


def obtener_actuaciones_y_providencias(
    numero_radicado: str,
    headless: bool = True,
    descargar_pdf: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    """
    Abre Consulta de Procesos, busca por radicado, va a ACTUACIONES,
    extrae la tabla y descarga las providencias (icono verde) asociadas.

    :return: (actuaciones, providencias, rutas_pdf_descargados)
    """
    radicado = normalizar_radicado(numero_radicado)
    if not radicado:
        return [], [], []

    carpeta_pdf = Path(CARPETA_PDF_PROVIDENCIAS) / radicado
    carpeta_pdf.mkdir(parents=True, exist_ok=True)

    actuaciones: List[Dict[str, Any]] = []
    providencias: List[Dict[str, Any]] = []
    pdfs_descargados: List[str] = []

    with sync_playwright() as p:
        launch_opts = {"headless": headless}
        if not headless:
            launch_opts["slow_mo"] = 300
            launch_opts["args"] = ["--start-maximized"]
        browser = p.chromium.launch(**launch_opts)
        context = browser.new_context(
            locale="es-CO",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = context.new_page()
        page.set_default_timeout(TIMEOUT_NAVEGACION)

        try:
            page.goto(URL_CONSULTA_PROCESOS, wait_until="domcontentloaded", timeout=TIMEOUT_NAVEGACION)
            page.wait_for_load_state("load", timeout=10000)
            if not headless:
                page.wait_for_timeout(3000)

            # Clic en "Número de Radicación"
            page.wait_for_timeout(1000)
            opcion = page.get_by_role("link", name=re.compile(r"número de radicación", re.I))
            if opcion.count() == 0:
                opcion = page.locator("a:has-text('Radicación'), a:has-text('Radicado')").first
            if opcion.count() == 0:
                opcion = page.locator("a[href*='Radicacion'], .card a").first
            opcion.click(timeout=TIMEOUT_SELECTOR)
            page.wait_for_load_state("load", timeout=10000)

            # Seleccionar "Todos los Procesos" - force=True evita overlay que bloquea el clic
            try:
                label_todos = page.locator("label:has-text('Todos los Procesos'), .v-label:has-text('Todos los Procesos')").first
                if label_todos.count() > 0:
                    label_todos.click(force=True, timeout=5000)
                else:
                    page.get_by_label(re.compile(r"todos los procesos", re.I)).first.click(force=True, timeout=5000)
            except Exception:
                page.evaluate("""() => {
                    const all = document.querySelectorAll('label, .v-label, .v-input--selection-controls__input, [role="radio"]');
                    for (const el of all) {
                        if (el.textContent && el.textContent.toLowerCase().includes('todos los procesos')) {
                            el.click();
                            return;
                        }
                    }
                    const radios = document.querySelectorAll('input[type="radio"]');
                    if (radios.length >= 2) radios[1].click();
                }""")
            page.wait_for_timeout(800)

            # Campo de radicado: input text/tel (no checkbox)
            input_radicado = page.get_by_placeholder(re.compile(r"23|Ingrese|Radicación|dígitos", re.I))
            if input_radicado.count() == 0:
                input_radicado = page.locator("input[type='text'], input[type='tel'], input[type='number']").first
            if input_radicado.count() == 0:
                input_radicado = page.locator("input:not([type='checkbox']):not([role='switch'])").first
            input_radicado.first.fill(radicado, timeout=TIMEOUT_SELECTOR)

            # Botón CONSULTAR
            btn = page.get_by_role("button", name=re.compile(r"consultar", re.I))
            if btn.count() == 0:
                btn = page.locator("button:has-text('CONSULTAR'), input[value='CONSULTAR']").first
            btn.click(timeout=TIMEOUT_SELECTOR)
            page.wait_for_load_state("load", timeout=15000)
            page.wait_for_timeout(2000)

            # Si hay lista de resultados, clic en el proceso para ir al detalle
            enlace = page.locator("a[href*='Detalle'], a[href*='detalle'], table tbody a").first
            if enlace.count() > 0:
                try:
                    enlace.click(timeout=TIMEOUT_SELECTOR)
                    page.wait_for_load_state("load", timeout=15000)
                    page.wait_for_timeout(1500)
                except PlaywrightTimeout:
                    pass

            # Clic en pestaña ACTUACIONES
            tab_actuaciones = page.get_by_role("tab", name=re.compile(r"actuaciones", re.I))
            if tab_actuaciones.count() == 0:
                tab_actuaciones = page.locator("a:has-text('ACTUACIONES'), button:has-text('ACTUACIONES'), [role='tab']:has-text('ACTUACIONES')").first
            if tab_actuaciones.count() > 0:
                tab_actuaciones.first.click(timeout=TIMEOUT_SELECTOR)
                page.wait_for_load_state("load", timeout=10000)
                page.wait_for_timeout(1500)

            # Extraer actuaciones y descargar providencias (clic directo en icono)
            rows = page.locator("table tbody tr").all()
            indice_prov = 0

            for i, row in enumerate(rows):
                celdas = row.locator("td").all_text_contents()
                if len(celdas) < 2:
                    continue
                fecha = celdas[0].strip() if len(celdas) > 0 else ""
                tipo = celdas[1].strip() if len(celdas) > 1 else ""
                descripcion = celdas[2].strip() if len(celdas) > 2 else " ".join(c.strip() for c in celdas[2:])

                act = {"fecha": fecha, "tipo": tipo, "descripcion": descripcion, "enlace_providencia": ""}
                actuaciones.append(act)

                # Buscar clickable para providencia: última celda o último enlace en la fila
                icono = row.locator("td:last-child a, td:last-child button").first
                if icono.count() == 0:
                    icono = row.locator("a[href]").last
                if icono.count() > 0:
                    href = icono.get_attribute("href")
                    if href and not href.startswith("#") and "regresar" not in (href or "").lower():
                        act["enlace_providencia"] = urljoin(page.url, href)

                prov = {"fecha": fecha, "tipo": tipo, "resumen": descripcion[:200], "enlace": act.get("enlace_providencia", ""), "ruta_pdf": ""}
                providencias.append(prov)

                if not descargar_pdf or icono.count() == 0:
                    continue

                indice_prov += 1
                ruta_pdf_path = carpeta_pdf / _nombre_archivo_seguro(fecha, tipo, indice_prov)

                try:
                    # 1) Clic puede disparar descarga
                    with page.expect_download(timeout=6000) as dl_info:
                        icono.click(timeout=3000)
                    download = dl_info.value
                    download.save_as(ruta_pdf_path)
                    pdfs_descargados.append(str(ruta_pdf_path))
                    prov["ruta_pdf"] = str(ruta_pdf_path)
                except Exception:
                    try:
                        page.wait_for_timeout(2000)
                        # 2) Quizá se abrió nueva pestaña con el clic
                        pages = context.pages
                        if len(pages) > 1:
                            popup = pages[-1]
                            popup.wait_for_load_state("domcontentloaded", timeout=8000)
                            popup.wait_for_timeout(1500)
                            url_pdf = popup.url
                            resp = popup.request.fetch(url_pdf)
                            if resp and resp.ok:
                                body = resp.body()
                                if body and (body[:4] == b"%PDF" or len(body) > 500):
                                    ruta_pdf_path.write_bytes(body)
                                    pdfs_descargados.append(str(ruta_pdf_path))
                                    prov["ruta_pdf"] = str(ruta_pdf_path)
                            popup.close()
                        else:
                            # 3) Navegó en misma pestaña al PDF
                            page.wait_for_load_state("domcontentloaded", timeout=8000)
                            page.wait_for_timeout(1500)
                            url_actual = page.url
                            if url_actual:
                                resp_obj = page.request.fetch(url_actual)
                                if resp_obj and resp_obj.ok:
                                    body = resp_obj.body()
                                    if body and (body[:4] == b"%PDF" or len(body) > 500):
                                        ruta_pdf_path.write_bytes(body)
                                        pdfs_descargados.append(str(ruta_pdf_path))
                                        prov["ruta_pdf"] = str(ruta_pdf_path)
                            page.go_back(timeout=TIMEOUT_SELECTOR)
                            page.wait_for_load_state("load", timeout=6000)
                            page.wait_for_timeout(500)
                    except Exception:
                        try:
                            page.go_back(timeout=5000)
                        except Exception:
                            pass

        except PlaywrightTimeout as e:
            raise TimeoutError(f"Tiempo de espera agotado en Consulta Procesos: {e}")
        finally:
            browser.close()

    return actuaciones, providencias, pdfs_descargados


def obtener_actuaciones(numero_radicado: str, headless: bool = True) -> List[Dict[str, Any]]:
    """Compatibilidad: devuelve solo actuaciones (sin descargar PDFs)."""
    act, _, _ = obtener_actuaciones_y_providencias(
        numero_radicado, headless=headless, descargar_pdf=False
    )
    return act
