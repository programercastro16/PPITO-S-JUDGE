import os
from pathlib import Path

# Directorio raíz del proyecto (para rutas absolutas)
ROOT_DIR = Path(__file__).resolve().parent.parent

# URLs de la Rama Judicial Colombia
URL_CONSULTA_PROCESOS = "https://consultaprocesos.ramajudicial.gov.co/Procesos/Index"
URL_PUBLICACIONES = "https://publicacionesprocesales.ramajudicial.gov.co/"

# Fuentes judiciales (activas + hueco para ampliar el sistema tipo “legaltech privada”)
FUENTES_JUDICIALES = [
    {
        "id": "consulta_procesos",
        "nombre": "Consulta de Procesos (Rama Judicial)",
        "url": URL_CONSULTA_PROCESOS,
        "activa": True,
    },
    {
        "id": "publicaciones_procesales",
        "nombre": "Publicaciones procesales (Rama Judicial)",
        "url": URL_PUBLICACIONES,
        "activa": False,
        "nota": "Reservado: el flujo actual unifica actuaciones y providencias desde Consulta de Procesos.",
    },
]

# Timeouts (milisegundos)
TIMEOUT_NAVEGACION = 30000
TIMEOUT_SELECTOR = 12000

# Base de datos local (puede configurarse por env, útil para hosting)
DB_PATH = os.environ.get("DB_PATH", "monitor_radicados.db")

# Carpeta donde se descargan los PDF de providencias (ruta absoluta)
CARPETA_PDF_PROVIDENCIAS = os.environ.get(
    "CARPETA_PDF_PROVIDENCIAS",
    str(ROOT_DIR / "providencias_pdf"),
)
