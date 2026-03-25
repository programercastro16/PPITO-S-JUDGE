"""
Monitor: obtiene actuaciones y providencias (documento del juez) desde Consulta de Procesos.
Solo usa consultaprocesos.ramajudicial.gov.co - las providencias salen del icono verde en ACTUACIONES.
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional

from . import storage
from .storage import init_db, registrar_radicado, guardar_actuaciones, guardar_providencias
from .scraper_consulta import obtener_actuaciones_y_providencias


def ejecutar_monitor(
    numero_radicado: str,
    headless: bool = True,
    descargar_pdf: bool = True,
) -> Dict[str, Any]:
    """
    Consulta Consulta de Procesos: actuaciones + providencias (icono verde) + descarga PDFs.
    """
    init_db()
    radicado = numero_radicado.strip()
    registrar_radicado(radicado)

    resultado: Dict[str, Any] = {
        "radicado": radicado,
        "actuaciones": [],
        "providencias": [],
        "actuaciones_guardadas": 0,
        "providencias_guardadas": 0,
        "nuevas_actuaciones": [],
        "nuevas_providencias": [],
        "hubo_actualizacion": False,
        "pdfs_descargados": [],
        "errores": [],
    }

    try:
        actuaciones, providencias, pdfs = obtener_actuaciones_y_providencias(
            radicado, headless=headless, descargar_pdf=descargar_pdf
        )
        resultado["actuaciones"] = actuaciones
        resultado["providencias"] = providencias
        resultado["pdfs_descargados"] = pdfs

        total_act, nuevas_act = storage.guardar_actuaciones(radicado, actuaciones)
        resultado["actuaciones_guardadas"] = total_act
        resultado["nuevas_actuaciones"] = nuevas_act

        total_prov, nuevas_prov = storage.guardar_providencias(radicado, providencias)
        resultado["providencias_guardadas"] = total_prov
        resultado["nuevas_providencias"] = nuevas_prov

        resultado["hubo_actualizacion"] = len(nuevas_act) > 0 or len(nuevas_prov) > 0

    except Exception as e:
        resultado["errores"].append(str(e))

    return resultado


def monitorear_radicados(
    radicados: Optional[List[str]] = None,
    headless: bool = True,
    descargar_pdf: bool = True,
) -> List[Dict[str, Any]]:
    """Ejecuta el monitor para una lista de radicados."""
    init_db()
    lista = radicados or storage.listar_radicados()
    if not lista:
        return []
    return [ejecutar_monitor(r, headless=headless, descargar_pdf=descargar_pdf) for r in lista]


def monitorear_radicados_usuario(
    user_id: int,
    headless: bool = True,
    descargar_pdf: bool = True,
) -> List[Dict[str, Any]]:
    """Solo los radicados vinculados al usuario (panel web)."""
    init_db()
    lista = storage.listar_radicados_usuario(user_id)
    if not lista:
        return []
    return [ejecutar_monitor(r, headless=headless, descargar_pdf=descargar_pdf) for r in lista]
