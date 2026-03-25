# PPITO'S JUDGE

## Demo en vivo
[https://ppito-s-judge.onrender.com](https://ppito-s-judge.onrender.com)

Este es mi sistema privado para seguimiento judicial por número de radicado.  
El objetivo es centralizar en un solo panel:

- actuaciones;
- providencias;
- descarga de PDFs;
- alertas por correo (y opcionalmente Telegram).

La información se consulta desde fuentes oficiales de la Rama Judicial y se guarda en SQLite para detectar novedades entre consultas.

## Funcionalidades

- Registro de usuarios y login en panel web.
- Asociación de radicados por usuario.
- Consulta de actuaciones y providencias.
- Descarga de PDFs de providencias.
- Actualización masiva de radicados.
- Notificaciones automáticas por cambios.

## Requisitos

- Python 3.10 o superior
- Playwright + Chromium

## Instalación

```bash
cd JudgeScrapper_Pipito
pip install -r requirements.txt
playwright install chromium
copy .env.example .env
```

Luego se debe editar `.env` con la configuración local (correo, sesión web, etc.).

## Uso rápido

### 1) CLI

```bash
python main.py agregar 25001234567890123456789
python main.py monitor
python main.py ver 25001234567890123456789
python main.py descargar-pdfs
```

### 2) Panel web

```bash
python web_app.py
```

Abrir en navegador:

`http://127.0.0.1:5000`

## Variables de entorno principales

| Variable | Descripción |
|---|---|
| `WEB_APP_SECRET_KEY` | Clave de sesión de Flask |
| `WEB_APP_HOST` | Host de arranque (`127.0.0.1` local, `0.0.0.0` para exponer) |
| `WEB_APP_PORT` | Puerto local de la app |
| `WEB_APP_DEBUG` | Modo debug |
| `NOTIFICACION_EMAILS` | Correos destino para alertas |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` | Configuración SMTP |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_IDS` | Alertas por Telegram (opcional) |
| `MONITOR_INTERVAL_HOURS` | Intervalo del monitoreo automático |
| `ENABLE_BACKGROUND_MONITOR` | Activa/desactiva monitor embebido en web |
| `DB_PATH` | Ruta del archivo SQLite |
| `CARPETA_PDF_PROVIDENCIAS` | Carpeta de PDFs descargados |

## Despliegue web

El repositorio ya incluye:

- `Dockerfile`
- `render.yaml`

Con eso se puede desplegar en Render y obtener URL pública.

## Estructura

```text
main.py
web_app.py
auto_monitor.py
src/
templates/
static/
```

## Nota de uso

Este proyecto está pensado para uso privado y controlado.  
Si se publica en internet, se recomienda mantener el registro/login activo, proteger secretos en variables de entorno y no exponer el archivo `.env`.
