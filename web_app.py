from __future__ import annotations

import bootstrap_env  # noqa: F401 — carga .env antes del resto

"""
PPITO'S JUDGE - interfaz web privada con registro de usuarios.

Ejecuta:
    cd "c:\\Users\\Thomas Castro\\Desktop\\JudgeScrapper_Pipito"
    python web_app.py

Luego abre en el navegador:
    http://127.0.0.1:5000/
"""

import os
import threading
import time
from functools import wraps
from datetime import timedelta

from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash

from src.config import FUENTES_JUDICIALES
from src.monitor import ejecutar_monitor, monitorear_radicados, monitorear_radicados_usuario
from src.notificaciones import notificar_cambio
from src.pdfs_masivos import descargar_pdfs_faltantes_lista, descargar_pdfs_faltantes_radicado
from src.storage import (
    init_db,
    crear_usuario,
    obtener_usuario_por_email,
    obtener_usuario_por_id,
    obtener_actuaciones,
    obtener_providencias,
    obtener_metricas_usuario,
    emails_usuarios_para_radicado,
    listar_radicados_usuario,
    usuario_tiene_radicado,
    vincular_radicado_a_usuario,
    desvincular_radicado_usuario,
)

app = Flask(__name__)
app.secret_key = os.environ.get("WEB_APP_SECRET_KEY", "ppitos-judge-dev-secret-change-me")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
)
init_db()


def _intervalo_monitor_horas() -> float:
    raw = os.environ.get("MONITOR_INTERVAL_HOURS", "6").strip()
    try:
        return max(0.25, float(raw))
    except ValueError:
        return 6.0


def _scraper_headless_default() -> bool:
    """
    Define si Playwright corre en headless al disparar escaneos desde la web.
    En hosting (Render) debe ser True para evitar errores de X server.
    """
    raw = os.environ.get("SCRAPER_HEADLESS", "true").strip().lower()
    return raw in ("1", "true", "yes", "on")


def background_monitor_loop() -> None:
    """Hilo en segundo plano que actualiza todos los radicados cada X horas."""
    while True:
        try:
            print("[AUTO-MONITOR] Iniciando ciclo automático...")
            resultados = monitorear_radicados(
                radicados=None,
                headless=True,
                descargar_pdf=True,
            )
            for res in resultados:
                rad = res.get("radicado", "")
                if res.get("hubo_actualizacion"):
                    print(
                        f"[AUTO-MONITOR] {rad} actualizado. "
                        f"Nuevas actuaciones: {len(res.get('nuevas_actuaciones', []))}, "
                        f"Nuevas providencias: {len(res.get('nuevas_providencias', []))}, "
                        f"PDFs descargados: {len(res.get('pdfs_descargados', []))}"
                    )
                    dest = emails_usuarios_para_radicado(rad) or None
                    notificar_cambio(res, destinatarios_email=dest)
                else:
                    print(f"[AUTO-MONITOR] {rad} sin cambios nuevos.")
        except Exception as e:
            print("[AUTO-MONITOR] Error en ciclo automático:", e)

        # Espera hasta el siguiente ciclo
        time.sleep(_intervalo_monitor_horas() * 3600)


def start_background_monitor_once() -> None:
    """Arranca el hilo de auto-monitor solo una vez por proceso."""
    enabled = os.environ.get("ENABLE_BACKGROUND_MONITOR", "false").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if not enabled:
        return
    if getattr(start_background_monitor_once, "_started", False):
        return
    # En modo debug de Flask, evita duplicado por el reloader.
    debug_mode = os.environ.get("WEB_APP_DEBUG", "true").strip().lower() in ("1", "true", "yes", "on")
    if debug_mode and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return
    thread = threading.Thread(target=background_monitor_loop, daemon=True)
    thread.start()
    start_background_monitor_once._started = True
    print(
        f"[AUTO-MONITOR] Hilo automático iniciado. Intervalo: "
        f"{_intervalo_monitor_horas()} horas."
    )


start_background_monitor_once()


def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return obtener_usuario_por_id(int(user_id))


@app.context_processor
def inject_current_user():
    return {"current_user": get_current_user()}


def start_user_session(user_id: int) -> None:
    """Reinicia la sesión actual y crea una nueva sesión autenticada."""
    session.clear()
    session["user_id"] = int(user_id)
    session.permanent = True


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not get_current_user():
            flash("Debes iniciar sesión para entrar al panel privado.", "error")
            return redirect(url_for("acceso"))
        return view_func(*args, **kwargs)
    return wrapped


@app.route("/")
def home():
    if get_current_user():
        return redirect(url_for("panel"))
    return redirect(url_for("acceso"))


@app.route("/acceso")
def acceso():
    if get_current_user():
        return redirect(url_for("panel"))
    return render_template("auth.html")


@app.route("/registro", methods=["POST"])
def registro():
    if get_current_user():
        session.clear()

    nombre = (request.form.get("nombre") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    password_confirm = request.form.get("password_confirm") or ""

    if len(nombre) < 3:
        flash("El nombre debe tener al menos 3 caracteres.", "error")
        return redirect(url_for("acceso"))
    if "@" not in email or "." not in email:
        flash("Ingresa un correo válido.", "error")
        return redirect(url_for("acceso"))
    if len(password) < 6:
        flash("La contraseña debe tener al menos 6 caracteres.", "error")
        return redirect(url_for("acceso"))
    if password != password_confirm:
        flash("Las contraseñas no coinciden.", "error")
        return redirect(url_for("acceso"))
    if obtener_usuario_por_email(email):
        flash("Ese correo ya está registrado.", "error")
        return redirect(url_for("acceso"))

    user_id = crear_usuario(nombre, email, generate_password_hash(password))
    start_user_session(user_id)
    flash("Cuenta creada correctamente. Bienvenido a PPITO'S JUDGE.", "success")
    return redirect(url_for("panel"))


@app.route("/login", methods=["POST"])
def login():
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    user = obtener_usuario_por_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        # Cerramos cualquier sesión previa para evitar que un usuario ya autenticado
        # parezca "entrar" con credenciales erróneas.
        session.clear()
        flash("Correo o contraseña incorrectos.", "error")
        return redirect(url_for("acceso"))

    start_user_session(user["id"])
    flash("Sesión iniciada correctamente.", "success")
    return redirect(url_for("panel"))


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Sesión cerrada.", "success")
    return redirect(url_for("acceso"))


@app.route("/panel", methods=["GET", "POST"])
@login_required
def panel():
    user = get_current_user()

    if request.method == "POST":
        radicado = (request.form.get("radicado") or "").strip()
        if radicado:
            # En servidores sin entorno gráfico (ej. Render), debe ser headless.
            res = ejecutar_monitor(
                radicado,
                headless=_scraper_headless_default(),
                descargar_pdf=True,
            )
            vincular_radicado_a_usuario(user["id"], radicado)
            msg = (
                f"Radicado procesado. Actuaciones: {len(res.get('actuaciones', []))} "
                f"(nuevas: {len(res.get('nuevas_actuaciones', []))}), "
                f"Providencias: {len(res.get('providencias', []))} "
                f"(nuevas: {len(res.get('nuevas_providencias', []))}), "
                f"PDFs descargados: {len(res.get('pdfs_descargados', []))}."
            )
            flash(msg, "success")
            for err in res.get("errores", []):
                flash(f"Error al procesar {radicado}: {err}", "error")
            return redirect(url_for("detalle_radicado", radicado=radicado))

    radicados = listar_radicados_usuario(user["id"])
    radicados_info = []
    for numero in radicados:
        acts = obtener_actuaciones(numero)
        provs = obtener_providencias(numero)
        ultima = acts[0] if acts else None
        radicados_info.append(
            {
                "numero": numero,
                "ultima_fecha": (ultima.get("fecha") if ultima else ""),
                "ultima_tipo": (ultima.get("tipo") if ultima else ""),
                "ultima_desc": (ultima.get("descripcion") if ultima else ""),
                "n_actuaciones": len(acts),
                "n_providencias": len(provs),
            }
        )
    metricas = obtener_metricas_usuario(user["id"])
    return render_template(
        "index.html",
        radicados=radicados_info,
        metricas=metricas,
        fuentes=FUENTES_JUDICIALES,
        intervalo_horas=_intervalo_monitor_horas(),
    )


@app.route("/radicado/<radicado>")
@login_required
def detalle_radicado(radicado: str):
    user = get_current_user()
    if not usuario_tiene_radicado(user["id"], radicado):
        abort(403)

    actuaciones = obtener_actuaciones(radicado)
    providencias = obtener_providencias(radicado)
    return render_template(
        "detalle.html",
        radicado=radicado,
        actuaciones=actuaciones,
        providencias=providencias,
    )


@app.route("/radicado/<radicado>/descargar-pdfs", methods=["POST"])
@login_required
def detalle_descargar_pdfs(radicado: str):
    user = get_current_user()
    if not usuario_tiene_radicado(user["id"], radicado):
        abort(403)
    rutas = descargar_pdfs_faltantes_radicado(radicado, headless=True)
    if rutas:
        flash(f"Se descargaron {len(rutas)} PDF(s) para este radicado.", "success")
    else:
        flash("No había PDFs pendientes para este radicado.", "success")
    return redirect(url_for("detalle_radicado", radicado=radicado))


@app.route("/panel/actualizar-todos", methods=["POST"])
@login_required
def panel_actualizar_todos():
    user = get_current_user()
    resultados = monitorear_radicados_usuario(
        user["id"],
        headless=True,
        descargar_pdf=True,
    )
    if not resultados:
        flash("No tienes radicados en el panel para actualizar.", "error")
        return redirect(url_for("panel"))
    n_cambios = sum(1 for r in resultados if r.get("hubo_actualizacion"))
    flash(
        f"Actualización masiva terminada: {len(resultados)} proceso(s), "
        f"{n_cambios} con novedades.",
        "success",
    )
    for res in resultados:
        rad = res.get("radicado", "")
        if res.get("hubo_actualizacion"):
            dest = emails_usuarios_para_radicado(rad) or None
            notificar_cambio(res, destinatarios_email=dest)
        for err in res.get("errores", []):
            flash(f"{rad}: {err}", "error")
    return redirect(url_for("panel"))


@app.route("/panel/descargar-pdfs", methods=["POST"])
@login_required
def panel_descargar_pdfs():
    user = get_current_user()
    rads = listar_radicados_usuario(user["id"])
    if not rads:
        flash("No hay radicados en tu panel.", "error")
        return redirect(url_for("panel"))
    resumen = descargar_pdfs_faltantes_lista(rads, headless=True)
    total = sum(len(v) for v in resumen.values())
    if total:
        flash(f"PDFs descargados (faltantes): {total} archivo(s) en {len(resumen)} radicado(s).", "success")
    else:
        flash("No había PDFs pendientes por enlace o ya estaban descargados.", "success")
    return redirect(url_for("panel"))


@app.route("/radicado/<radicado>/eliminar", methods=["POST"])
@login_required
def eliminar_radicado(radicado: str):
    user = get_current_user()
    if not usuario_tiene_radicado(user["id"], radicado):
        abort(403)
    desvincular_radicado_usuario(user["id"], radicado)
    flash(f"Radicado {radicado} eliminado de tu panel.", "success")
    return redirect(url_for("panel"))


if __name__ == "__main__":
    host = os.environ.get("WEB_APP_HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", os.environ.get("WEB_APP_PORT", "5000")))
    debug = os.environ.get("WEB_APP_DEBUG", "true").strip().lower() in ("1", "true", "yes", "on")
    app.run(debug=debug, host=host, port=port)

