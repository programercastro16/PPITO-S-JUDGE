# JudgeScrapper Pipito

Sistema unificado para **monitorear actualizaciones** de procesos judiciales por **número de radicado**, orientado a **uso privado** (panel web, alertas y PDFs). Los datos se obtienen principalmente desde [Consulta de Procesos Nacional Unificada](https://consultaprocesos.ramajudicial.gov.co/Procesos/Index) (actuaciones y providencias con descarga de PDF desde el flujo oficial).

Todo se guarda en una base SQLite local para detectar cuándo hay novedades.

## Requisitos

- Python 3.10+
- Navegador Chromium (lo instala Playwright)

## Instalación

```bash
cd JudgeScrapper_Pipito
pip install -r requirements.txt
playwright install chromium
# Windows: copy .env.example .env
# macOS/Linux: cp .env.example .env
# Luego edita .env con SMTP, Telegram, etc. (opcional)
```

Las variables de entorno también pueden definirse en un archivo **`.env`** en la raíz del proyecto; se cargan automáticamente al arrancar `web_app.py`, `main.py` y `auto_monitor.py` (vía `python-dotenv`). El archivo **`.env` no debe subirse a git** (está en `.gitignore`).

## Subir a GitHub (sin `.env`)

```bash
git init
git add .
git status
```

Verifica que **`.env` no aparezca** en `git status`.  
Si llegara a aparecer por haber sido trackeado antes:

```bash
git rm --cached .env
git status
```

Luego:

```bash
git commit -m "Inicial: app web privada de monitoreo judicial"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/TU_REPO.git
git push -u origin main
```

## Publicar con link público (Render + Docker)

Este proyecto incluye `Dockerfile` y `render.yaml` para deploy web.

1. Sube el repo a GitHub (pasos anteriores).
2. Crea cuenta en [Render](https://render.com/) y conecta GitHub.
3. En Render, crea un **Web Service** desde el repo (detectará Docker).
4. Configura variables de entorno en Render (NO usar `.env` del repo):
   - `NOTIFICACION_EMAILS`
   - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`
   - `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_IDS` (opcional)
   - `WEB_APP_SECRET_KEY` (si no la generas automática)
5. Crea un **Disk** montado en `/data` (ya definido en `render.yaml`) para que SQLite y PDFs persistan.
6. Deploy. Render te da una URL pública `https://...onrender.com`.

Notas:
- En Render se usa `gunicorn` y `PORT` dinámico automáticamente.
- `ENABLE_BACKGROUND_MONITOR=false` por defecto para evitar loops pesados dentro del web service.  
  Para monitoreo periódico, usa `auto_monitor.py` como worker aparte o un cron job.

## Uso

### Registrar radicados a monitorear

```bash
python main.py agregar 25001234567890123456789
python main.py agregar 25001234567890123456789 25000987654321098765432
```

### Ejecutar una consulta (actuaciones + providencias)

```bash
# Consultar todos los radicados registrados
python main.py monitor

# Consultar radicados concretos
python main.py monitor 25001234567890123456789
```

### Ver datos guardados

```bash
python main.py ver 25001234567890123456789
```

### Opciones del monitor

- `--visible`: abre el navegador para ver el proceso (útil para depurar).
- `--sin-pdf`: no descargar PDFs de providencias durante el escaneo.

```bash
python main.py monitor --visible
python main.py monitor --sin-pdf 25001234567890123456789
```

### Descargar PDFs faltantes (masivo por HTTP)

Si ya tienes providencias guardadas con enlace pero sin archivo en disco:

```bash
python main.py descargar-pdfs
python main.py descargar-pdfs 25001234567890123456789
```

### Listar radicados registrados

```bash
python main.py listar
```

### Interfaz web y auto-monitor

```bash
python web_app.py
```

- Panel por usuario, métricas, **actualizar todos** los radicados del usuario y **PDFs faltantes**.
- Hilo en segundo plano que ejecuta `python main.py monitor` sobre todos los radicados de la base cada **N horas** (por defecto 6). Ajusta con la variable de entorno `MONITOR_INTERVAL_HOURS`.

```bash
python auto_monitor.py
```

### Compartir el panel por internet con [ngrok](https://ngrok.com/)

1. En el `.env` deja **`WEB_APP_HOST=0.0.0.0`**, **`WEB_APP_PORT=5000`** y **`WEB_APP_DEBUG=false`** (ya suelen estar si copiaste la plantilla del proyecto).
2. Crea cuenta en ngrok, instala el programa y (una vez) configura tu authtoken: `ngrok config add-authtoken TU_TOKEN`.
3. Arranca la app: `python web_app.py` (debe escuchar en el puerto 5000).
4. En **otra** terminal: `ngrok http 5000`.
5. Ngrok muestra una URL **`https://….ngrok-free.app`** (o similar): esa es la que compartes. Cada vez que reinicies ngrok gratis, el subdominio puede cambiar.

**Importante:** el enlace es público; protege el acceso con usuarios/contraseña del panel y no lo publiques en redes abiertas. Apaga ngrok cuando no lo uses.

### Alertas (correo y Telegram)

Configura variables de entorno (recomendado en lugar de secretos en código):

| Variable | Uso |
|----------|-----|
| `NOTIFICACION_EMAILS` | Destinatarios separados por coma |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` | Envío por SMTP (p. ej. Gmail con contraseña de aplicación) |
| `TELEGRAM_BOT_TOKEN` | Token del bot |
| `TELEGRAM_CHAT_IDS` o `TELEGRAM_CHAT_ID` | Chat(s) a notificar |
| `MONITOR_INTERVAL_HOURS` | Intervalo del hilo automático en `web_app.py` |

Si un radicado está vinculado a usuarios del panel web, las alertas por correo se envían a esos correos; si no hay usuarios vinculados, se usan los de `NOTIFICACION_EMAILS`. Telegram usa siempre la configuración del bot si está definida.

## Estructura del proyecto

```
JudgeScrapper_Pipito/
  main.py                 # CLI
  web_app.py              # Panel web + hilo automático
  auto_monitor.py         # Bucle programable (Task Scheduler / servidor)
  requirements.txt
  templates/              # HTML del panel
  src/
    config.py             # URLs, timeouts, registro de fuentes judiciales
    storage.py            # SQLite: usuarios, radicados, actuaciones, providencias
    scraper_consulta.py   # Consulta Procesos → actuaciones + providencias + PDFs
    scraper_publicaciones.py
    monitor.py
    notificaciones.py     # Email + Telegram
    pdfs_masivos.py       # Descarga masiva de PDFs por enlace
    descargar_pdf.py
  monitor_radicados.db    # Creada al usar (en la raíz del proyecto)
```

## Notas

- El **número de radicación** suele ser de **23 dígitos**. Puedes ingresarlo con o sin espacios/guiones; se normaliza automáticamente.
- Las páginas de la Rama Judicial pueden cambiar estructura (HTML). Si dejan de extraerse datos, puede ser necesario ajustar los selectores en `src/scraper_consulta.py` (y `scraper_publicaciones.py` si lo usas por separado).
- Para monitoreo periódico puedes usar un programador de tareas (cron, Task Scheduler) ejecutando `python main.py monitor` cada X tiempo.
