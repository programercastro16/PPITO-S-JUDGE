"""
Notificaciones por cambios en procesos: correo (SMTP) y Telegram.

Configuración recomendada por variables de entorno (sin commitear secretos):
  NOTIFICACION_EMAILS     correos destino, separados por coma
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD
  TELEGRAM_BOT_TOKEN      token del bot (@BotFather)
  TELEGRAM_CHAT_IDS       uno o varios chat_id separados por coma
  (alias) TELEGRAM_CHAT_ID  un solo chat

Si no defines SMTP_PASSWORD, el correo se omite (no falla el monitor).
"""
from __future__ import annotations

import json
import os
import smtplib
import urllib.error
import urllib.request
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

# Valores por defecto (sobrescritos por env)
SMTP_HOST_DEFAULT = "smtp.gmail.com"
SMTP_PORT_DEFAULT = 587
SMTP_USER_DEFAULT = ""
SMTP_PASSWORD_DEFAULT = ""

EMAIL_DESTINOS_LEGACY: List[str] = []


def _smtp_host() -> str:
    return os.environ.get("SMTP_HOST", SMTP_HOST_DEFAULT).strip() or SMTP_HOST_DEFAULT


def _smtp_port() -> int:
    raw = os.environ.get("SMTP_PORT", str(SMTP_PORT_DEFAULT)).strip()
    try:
        return int(raw)
    except ValueError:
        return SMTP_PORT_DEFAULT


def _smtp_user() -> str:
    return os.environ.get("SMTP_USER", SMTP_USER_DEFAULT).strip()


def _smtp_password() -> str:
    return os.environ.get("SMTP_PASSWORD", SMTP_PASSWORD_DEFAULT).strip()


def _emails_por_defecto() -> List[str]:
    raw = os.environ.get("NOTIFICACION_EMAILS", "").strip()
    if raw:
        return [x.strip().lower() for x in raw.split(",") if x.strip()]
    return [e.strip().lower() for e in EMAIL_DESTINOS_LEGACY if e and str(e).strip()]


def _smtp_configurado() -> bool:
    pwd = _smtp_password()
    if not pwd or pwd == "PON_AQUI_TU_APP_PASSWORD_DE_GMAIL":
        return False
    return bool(_smtp_user())


def _construir_resumen_cambio(res_monitor: Dict[str, Any]) -> str:
    radicado = res_monitor.get("radicado", "")
    lineas: List[str] = []
    lineas.append(f"Actualización en radicado {radicado}")
    lineas.append("")

    nuevas_act = res_monitor.get("nuevas_actuaciones", []) or []
    nuevas_prov = res_monitor.get("nuevas_providencias", []) or []

    if nuevas_act:
        lineas.append("NUEVAS ACTUACIONES:")
        for a in nuevas_act:
            linea = f"- {a.get('fecha','')} | {a.get('tipo','')} | {(a.get('descripcion') or '')[:120]}"
            lineas.append(linea)
        lineas.append("")

    if nuevas_prov:
        lineas.append("NUEVAS PROVIDENCIAS:")
        for p in nuevas_prov:
            linea = f"- {p.get('fecha','')} | {p.get('tipo','')} | {(p.get('resumen') or '')[:120]}"
            lineas.append(linea)
        lineas.append("")

    pdfs = res_monitor.get("pdfs_descargados", []) or []
    if pdfs:
        lineas.append("PDFs descargados:")
        for ruta in pdfs:
            lineas.append(f"- {ruta}")
        lineas.append("")

    if not nuevas_act and not nuevas_prov:
        lineas.append("No se detectaron cambios nuevos en este monitoreo.")

    return "\n".join(lineas)


def _enviar_email_interno(destinatarios: List[str], asunto: str, cuerpo: str) -> None:
    if not destinatarios or not _smtp_configurado():
        return
    user = _smtp_user()
    msg = MIMEText(cuerpo, "plain", "utf-8")
    msg["Subject"] = asunto
    msg["From"] = user
    msg["To"] = ", ".join(destinatarios)
    with smtplib.SMTP(_smtp_host(), _smtp_port()) as server:
        server.starttls()
        server.login(user, _smtp_password())
        server.send_message(msg)


def _telegram_chat_ids() -> List[str]:
    raw = os.environ.get("TELEGRAM_CHAT_IDS", "").strip()
    if not raw:
        raw = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not raw:
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]


def enviar_telegram_texto(texto: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chats = _telegram_chat_ids()
    if not token or not chats:
        return
    url_base = f"https://api.telegram.org/bot{token}/sendMessage"
    payload_text = texto[:4090] if len(texto) > 4090 else texto
    for chat_id in chats:
        try:
            data = json.dumps({"chat_id": chat_id, "text": payload_text}).encode("utf-8")
            req = urllib.request.Request(
                url_base,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status != 200:
                    print(f"[notificaciones] Telegram HTTP {resp.status} para chat {chat_id}")
        except urllib.error.URLError as e:
            print(f"[notificaciones] Error Telegram (chat {chat_id}): {e}")
        except Exception as e:
            print(f"[notificaciones] Error Telegram: {e}")


def notificar_cambio(
    res_monitor: Dict[str, Any],
    destinatarios_email: Optional[List[str]] = None,
) -> None:
    """
    Envía resumen por correo (si hay SMTP y destinatarios) y por Telegram (si está configurado).

    :param destinatarios_email: Si es None, usa NOTIFICACION_EMAILS / lista legacy.
        Lista vacía: no envía correo (solo Telegram si aplica).
    """
    cuerpo = _construir_resumen_cambio(res_monitor)
    radicado = res_monitor.get("radicado", "")
    asunto = f"[Monitor judicial] Actualización en radicado {radicado}"

    if destinatarios_email is None:
        emails = _emails_por_defecto()
    else:
        emails = [e.strip().lower() for e in destinatarios_email if e and str(e).strip()]

    try:
        if emails:
            _enviar_email_interno(emails, asunto, cuerpo)
    except Exception as e:
        print(f"[notificaciones] Error enviando correo: {e}")

    try:
        enviar_telegram_texto(f"{asunto}\n\n{cuerpo}")
    except Exception as e:
        print(f"[notificaciones] Error en notificación Telegram: {e}")


def enviar_email_cambio(res_monitor: Dict[str, Any]) -> None:
    """Compatibilidad: mismo comportamiento que notificar_cambio sin destinatarios explícitos."""
    notificar_cambio(res_monitor, destinatarios_email=None)
