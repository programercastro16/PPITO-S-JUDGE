from __future__ import annotations

import bootstrap_env  # noqa: F401 — carga .env antes del resto

"""
Auto-monitor de PPITO'S JUDGE.

Revisa periódicamente todos los radicados registrados, actualiza actuaciones/
providencias y dispara notificaciones por correo cuando hay cambios.

Uso:
    cd "c:\\Users\\Thomas Castro\\Desktop\\JudgeScrapper_Pipito"
    .\\venv\\Scripts\\python.exe auto_monitor.py
"""

import time
from typing import List, Dict, Any

from src.monitor import monitorear_radicados
from src.notificaciones import notificar_cambio
from src.storage import emails_usuarios_para_radicado, init_db


# Intervalo entre ejecuciones (en minutos)
INTERVALO_MINUTOS = 30  # puedes subirlo o bajarlo a tu gusto


def ejecutar_ciclo() -> List[Dict[str, Any]]:
    """
    Ejecuta un ciclo de monitoreo sobre todos los radicados registrados.
    Devuelve la lista de resultados.
    """
    init_db()
    resultados = monitorear_radicados(
        radicados=None,        # None = todos los radicados de la base
        headless=True,         # navegador oculto
        descargar_pdf=True,    # descargar PDFs de providencias
    )

    for res in resultados:
        rad = res.get("radicado", "")
        if res.get("errores"):
            print(f"[{rad}] Errores durante el monitoreo:")
            for err in res["errores"]:
                print("   -", err)
        if res.get("hubo_actualizacion"):
            print(
                f"[{rad}] Actualizado. "
                f"Actuaciones nuevas: {len(res.get('nuevas_actuaciones', []))}, "
                f"Providencias nuevas: {len(res.get('nuevas_providencias', []))}, "
                f"PDFs descargados: {len(res.get('pdfs_descargados', []))}"
            )
            dest = emails_usuarios_para_radicado(rad) or None
            notificar_cambio(res, destinatarios_email=dest)
        else:
            print(f"[{rad}] Sin cambios nuevos.")

    return resultados


def main() -> None:
    print("=== PPITO'S JUDGE · Auto-monitor ===")
    print(f"Intervalo configurado: {INTERVALO_MINUTOS} minutos")
    print("Presiona Ctrl+C para detener.\n")

    try:
        while True:
            print("\n[Ejecución] Iniciando ciclo de monitoreo...")
            try:
                ejecutar_ciclo()
            except Exception as e:
                print("Error en el ciclo de monitoreo:", e)
            print(f"[Ejecución] Ciclo completado. Esperando {INTERVALO_MINUTOS} minutos...")
            time.sleep(INTERVALO_MINUTOS * 60)
    except KeyboardInterrupt:
        print("\nAuto-monitor detenido por el usuario.")


if __name__ == "__main__":
    main()

