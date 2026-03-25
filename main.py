#!/usr/bin/env python3
"""
Monitor de actuaciones y providencias por radicado.
Solo Consulta de Procesos: actuaciones + providencias (icono verde) + descarga PDFs.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bootstrap_env  # noqa: E402,F401 — .env tras asegurar raíz en path

from src.monitor import ejecutar_monitor, monitorear_radicados
from src.storage import (
    init_db,
    listar_radicados,
    obtener_actuaciones,
    obtener_providencias,
    limpiar_base,
    emails_usuarios_para_radicado,
)
from src.pdfs_masivos import descargar_pdfs_faltantes_lista
from src.notificaciones import notificar_cambio


def cmd_agregar(args):
    from src.storage import registrar_radicado
    init_db()
    for num in args.numeros:
        registrar_radicado(num)
        print(f"Radicado registrado: {num}")


def cmd_listar(args):
    init_db()
    radicados = listar_radicados()
    if not radicados:
        print("No hay radicados registrados. Usa: python main.py agregar <numero>")
        return
    for r in radicados:
        print(r)


def cmd_monitor(args):
    init_db()
    radicados = args.numeros if args.numeros else listar_radicados()
    if not radicados:
        print("Indica al menos un número de radicado o registra uno con 'agregar'.")
        return
    headless = not args.visible
    descargar_pdf = not args.sin_pdf
    if args.visible:
        print("Modo visible: el navegador se abrirá en unos segundos...")
    for radicado in radicados:
        print(f"\n--- Monitoreando {radicado} ---")
        try:
            res = ejecutar_monitor(
                radicado,
                headless=headless,
                descargar_pdf=descargar_pdf,
            )
            print(f"Actuaciones obtenidas: {len(res['actuaciones'])} (guardadas: {res['actuaciones_guardadas']})")
            print(f"Providencias obtenidas: {len(res['providencias'])} (guardadas: {res['providencias_guardadas']})")
            if res.get("pdfs_descargados"):
                print(f"PDFs descargados: {len(res['pdfs_descargados'])}")
                for ruta in res["pdfs_descargados"]:
                    print(f"    -> {ruta}")
            if res["hubo_actualizacion"]:
                print("[*] Hay actualizaciones nuevas:")
                for a in res.get("nuevas_actuaciones", []):
                    print(f"    - Actuación: {a.get('fecha')} | {a.get('tipo')} | {(a.get('descripcion') or '')[:50]}...")
                for p in res.get("nuevas_providencias", []):
                    print(f"    - Providencia: {p.get('fecha')} | {p.get('tipo')} | {(p.get('resumen') or '')[:50]}...")
                dest = emails_usuarios_para_radicado(radicado) or None
                notificar_cambio(res, destinatarios_email=dest)
            for err in res["errores"]:
                print(f"Error: {err}")
        except Exception as e:
            print(f"Error: {e}")


def cmd_ver(args):
    init_db()
    radicado = args.radicado
    print(f"=== Actuaciones ({radicado}) ===")
    for a in obtener_actuaciones(radicado):
        print(a.get("fecha"), a.get("tipo"), "-", (a.get("descripcion") or "")[:80])
    print(f"\n=== Providencias ({radicado}) ===")
    for p in obtener_providencias(radicado):
        ruta = p.get("ruta_pdf") or p.get("enlace", "")
        print(p.get("fecha"), p.get("tipo"), "-", (p.get("resumen") or "")[:60])
        if ruta:
            print(f"      PDF: {ruta}")


def cmd_descargar_pdfs(args):
    init_db()
    radicados = args.numeros if args.numeros else listar_radicados()
    if not radicados:
        print("Indica radicados o registra alguno con 'agregar'.")
        return
    resumen = descargar_pdfs_faltantes_lista(radicados, headless=not args.visible)
    if not resumen:
        print("No se descargaron PDFs (sin pendientes o sin enlaces).")
        return
    for rad, rutas in resumen.items():
        print(f"\n{rad}: {len(rutas)} archivo(s)")
        for ruta in rutas:
            print(f"  -> {ruta}")


def cmd_limpiar(args):
    """Borra todos los radicados, actuaciones y providencias (reset total)."""
    init_db()
    confirmar = input(
        "Esto eliminará TODOS los radicados y sus actuaciones/providencias guardadas. "
        "Escribe 'SI' para continuar: "
    ).strip()
    if confirmar != "SI":
        print("Operación cancelada.")
        return
    limpiar_base()
    print("Base de datos limpiada. No hay radicados registrados.")


def main():
    parser = argparse.ArgumentParser(
        description="Monitor: actuaciones + providencias (Consulta Procesos) por radicado.",
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    p_agregar = sub.add_parser("agregar", help="Registrar número(s) de radicado")
    p_agregar.add_argument("numeros", nargs="+", help="Números de radicado")
    p_agregar.set_defaults(func=cmd_agregar)

    p_listar = sub.add_parser("listar", help="Listar radicados registrados")
    p_listar.set_defaults(func=cmd_listar)

    p_monitor = sub.add_parser("monitor", help="Consultar actuaciones y descargar providencias (PDFs)")
    p_monitor.add_argument("numeros", nargs="*", help="Radicados (si no se indica, todos los registrados)")
    p_monitor.add_argument("--visible", action="store_true", help="Mostrar el navegador")
    p_monitor.add_argument("--sin-pdf", action="store_true", help="No descargar PDFs de providencias")
    p_monitor.set_defaults(func=cmd_monitor)

    p_ver = sub.add_parser("ver", help="Ver actuaciones y providencias guardadas")
    p_ver.add_argument("radicado", help="Número de radicado")
    p_ver.set_defaults(func=cmd_ver)

    p_pdf = sub.add_parser(
        "descargar-pdfs",
        help="Descargar PDFs faltantes de providencias ya guardadas (por HTTP)",
    )
    p_pdf.add_argument("numeros", nargs="*", help="Radicados (omite para todos los registrados)")
    p_pdf.add_argument("--visible", action="store_true", help="Navegador visible (mismo flag que monitor)")
    p_pdf.set_defaults(func=cmd_descargar_pdfs)

    p_limpiar = sub.add_parser("limpiar", help="Eliminar todos los radicados y datos guardados")
    p_limpiar.set_defaults(func=cmd_limpiar)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
