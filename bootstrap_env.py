"""
Carga variables desde el archivo .env en la raíz del proyecto.
Importar este módulo antes que el resto de la aplicación local.
"""
from __future__ import annotations

from pathlib import Path


def load_env_file() -> None:
    root = Path(__file__).resolve().parent
    env_path = root / ".env"
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(env_path)


load_env_file()
