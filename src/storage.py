"""
Almacenamiento local para monitoreo de radicados.
Guarda actuaciones, providencias y permite detectar actualizaciones.
"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from .config import DB_PATH


def get_connection():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Crea las tablas si no existen."""
    conn = get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                creado_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS radicados (
                numero TEXT PRIMARY KEY,
                creado_at TEXT NOT NULL,
                ultima_consulta_at TEXT
            );
            CREATE TABLE IF NOT EXISTS user_radicados (
                user_id INTEGER NOT NULL,
                radicado TEXT NOT NULL,
                creado_at TEXT NOT NULL,
                PRIMARY KEY (user_id, radicado),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (radicado) REFERENCES radicados(numero)
            );
            CREATE TABLE IF NOT EXISTS actuaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                radicado TEXT NOT NULL,
                fecha TEXT,
                tipo TEXT,
                descripcion TEXT,
                datos_json TEXT,
                registrado_at TEXT NOT NULL,
                FOREIGN KEY (radicado) REFERENCES radicados(numero)
            );
            CREATE TABLE IF NOT EXISTS providencias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                radicado TEXT NOT NULL,
                fecha TEXT,
                tipo TEXT,
                resumen TEXT,
                enlace TEXT,
                datos_json TEXT,
                registrado_at TEXT NOT NULL,
                FOREIGN KEY (radicado) REFERENCES radicados(numero)
            );
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
            CREATE INDEX IF NOT EXISTS idx_user_radicados_user ON user_radicados(user_id);
            CREATE INDEX IF NOT EXISTS idx_actuaciones_radicado ON actuaciones(radicado);
            CREATE INDEX IF NOT EXISTS idx_providencias_radicado ON providencias(radicado);
        """)
        conn.commit()
    finally:
        conn.close()


def crear_usuario(nombre: str, email: str, password_hash: str) -> int:
    """Crea un usuario y devuelve su id."""
    conn = get_connection()
    try:
        now = datetime.utcnow().isoformat()
        cur = conn.execute(
            "INSERT INTO users (nombre, email, password_hash, creado_at) VALUES (?, ?, ?, ?)",
            (nombre.strip(), email.strip().lower(), password_hash, now),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def obtener_usuario_por_email(email: str) -> Optional[dict]:
    """Busca un usuario por correo."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, nombre, email, password_hash, creado_at FROM users WHERE email = ? LIMIT 1",
            (email.strip().lower(),),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def obtener_usuario_por_id(user_id: int) -> Optional[dict]:
    """Busca un usuario por id."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, nombre, email, password_hash, creado_at FROM users WHERE id = ? LIMIT 1",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def registrar_radicado(numero: str) -> None:
    """Registra un número de radicado para monitoreo."""
    conn = get_connection()
    try:
        now = datetime.utcnow().isoformat()
        conn.execute(
            "INSERT OR IGNORE INTO radicados (numero, creado_at) VALUES (?, ?)",
            (numero.strip(), now),
        )
        conn.commit()
    finally:
        conn.close()


def vincular_radicado_a_usuario(user_id: int, radicado: str) -> None:
    """Asocia un radicado a un usuario sin duplicarlo."""
    conn = get_connection()
    try:
        now = datetime.utcnow().isoformat()
        conn.execute(
            "INSERT OR IGNORE INTO user_radicados (user_id, radicado, creado_at) VALUES (?, ?, ?)",
            (user_id, radicado.strip(), now),
        )
        conn.commit()
    finally:
        conn.close()


def _existe_actuacion(conn, radicado: str, fecha: str, tipo: str, descripcion: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM actuaciones WHERE radicado=? AND fecha=? AND tipo=? AND descripcion=? LIMIT 1",
        (radicado, fecha, tipo, descripcion),
    ).fetchone()
    return row is not None


def guardar_actuaciones(radicado: str, actuaciones: list[dict]) -> tuple[int, list[dict]]:
    """Guarda actuaciones (sin duplicar). Devuelve (total_guardadas, lista_de_nuevas)."""
    conn = get_connection()
    nuevas = []
    try:
        now = datetime.utcnow().isoformat()
        conn.execute(
            "UPDATE radicados SET ultima_consulta_at = ? WHERE numero = ?",
            (now, radicado),
        )
        for a in actuaciones:
            fecha = a.get("fecha") or ""
            tipo = a.get("tipo") or ""
            desc = a.get("descripcion") or ""
            if _existe_actuacion(conn, radicado, fecha, tipo, desc):
                continue
            conn.execute(
                """INSERT INTO actuaciones (radicado, fecha, tipo, descripcion, datos_json, registrado_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (radicado, fecha, tipo, desc, json.dumps(a, ensure_ascii=False), now),
            )
            nuevas.append(a)
        conn.commit()
        return len(actuaciones), nuevas
    finally:
        conn.close()


def _existe_providencia(conn, radicado: str, fecha: str, tipo: str, enlace: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM providencias WHERE radicado=? AND fecha=? AND tipo=? AND enlace=? LIMIT 1",
        (radicado, fecha, tipo, enlace),
    ).fetchone()
    return row is not None


def guardar_providencias(radicado: str, providencias: list[dict]) -> tuple[int, list[dict]]:
    """Guarda providencias (sin duplicar). Devuelve (total_guardadas, lista_de_nuevas)."""
    conn = get_connection()
    nuevas = []
    try:
        now = datetime.utcnow().isoformat()
        for p in providencias:
            fecha = p.get("fecha") or ""
            tipo = p.get("tipo") or ""
            enlace = p.get("enlace") or p.get("ruta_pdf") or ""
            if _existe_providencia(conn, radicado, fecha, tipo, enlace):
                continue
            conn.execute(
                """INSERT INTO providencias (radicado, fecha, tipo, resumen, enlace, datos_json, registrado_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    radicado,
                    fecha,
                    tipo,
                    p.get("resumen") or "",
                    enlace,
                    json.dumps(p, ensure_ascii=False),
                    now,
                ),
            )
            nuevas.append(p)
        conn.commit()
        return len(providencias), nuevas
    finally:
        conn.close()


def obtener_actuaciones(radicado: str) -> list[dict]:
    """Devuelve todas las actuaciones guardadas para un radicado."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT fecha, tipo, descripcion, datos_json FROM actuaciones WHERE radicado = ? ORDER BY fecha DESC",
            (radicado,),
        ).fetchall()
        out = []
        for r in rows:
            d = {"fecha": r["fecha"], "tipo": r["tipo"], "descripcion": r["descripcion"]}
            if r["datos_json"]:
                try:
                    d.update(json.loads(r["datos_json"]))
                except Exception:
                    pass
            out.append(d)
        return out
    finally:
        conn.close()


def obtener_providencias(radicado: str) -> list[dict]:
    """Devuelve todas las providencias guardadas para un radicado."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT fecha, tipo, resumen, enlace, datos_json FROM providencias WHERE radicado = ? ORDER BY fecha DESC",
            (radicado,),
        ).fetchall()
        out = []
        for r in rows:
            d = {"fecha": r["fecha"], "tipo": r["tipo"], "resumen": r["resumen"], "enlace": r["enlace"]}
            if r["datos_json"]:
                try:
                    d.update(json.loads(r["datos_json"]))
                except Exception:
                    pass
            out.append(d)
        return out
    finally:
        conn.close()


def listar_radicados() -> list[str]:
    """Lista los números de radicado registrados."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT numero FROM radicados ORDER BY creado_at DESC").fetchall()
        return [r["numero"] for r in rows]
    finally:
        conn.close()


def listar_radicados_usuario(user_id: int) -> list[str]:
    """Lista solo los radicados asociados a un usuario."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT ur.radicado
            FROM user_radicados ur
            JOIN radicados r ON r.numero = ur.radicado
            WHERE ur.user_id = ?
            ORDER BY ur.creado_at DESC
            """,
            (user_id,),
        ).fetchall()
        return [r["radicado"] for r in rows]
    finally:
        conn.close()


def usuario_tiene_radicado(user_id: int, radicado: str) -> bool:
    """Indica si un radicado está asociado al usuario."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM user_radicados WHERE user_id = ? AND radicado = ? LIMIT 1",
            (user_id, radicado.strip()),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def desvincular_radicado_usuario(user_id: int, radicado: str) -> None:
    """Quita un radicado del panel de un usuario (no borra la info global)."""
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM user_radicados WHERE user_id = ? AND radicado = ?",
            (user_id, radicado.strip()),
        )
        conn.commit()
    finally:
        conn.close()


def emails_usuarios_para_radicado(radicado: str) -> list[str]:
    """Correos de usuarios que tienen el radicado en su panel (sin duplicados)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT DISTINCT u.email
            FROM users u
            JOIN user_radicados ur ON ur.user_id = u.id
            WHERE ur.radicado = ?
            ORDER BY u.email
            """,
            (radicado.strip(),),
        ).fetchall()
        return [r["email"] for r in rows]
    finally:
        conn.close()


def obtener_metricas_usuario(user_id: int) -> dict:
    """Totales de actuaciones/providencias y última consulta entre los radicados del usuario."""
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM actuaciones a
               JOIN user_radicados ur ON ur.radicado = a.radicado
               WHERE ur.user_id = ?) AS n_actuaciones,
              (SELECT COUNT(*) FROM providencias p
               JOIN user_radicados ur ON ur.radicado = p.radicado
               WHERE ur.user_id = ?) AS n_providencias,
              (SELECT MAX(r.ultima_consulta_at) FROM radicados r
               JOIN user_radicados ur ON ur.radicado = r.numero
               WHERE ur.user_id = ?) AS ultima_consulta_at
            """,
            (user_id, user_id, user_id),
        ).fetchone()
        return {
            "n_actuaciones": int(row["n_actuaciones"] or 0),
            "n_providencias": int(row["n_providencias"] or 0),
            "ultima_consulta_at": row["ultima_consulta_at"] or "",
        }
    finally:
        conn.close()


def actualizar_ruta_pdf_por_enlace(radicado: str, enlace: str, ruta_pdf: str) -> None:
    """Guarda ruta_pdf en datos_json de todas las providencias que coincidan por enlace."""
    if not enlace.strip():
        return
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, datos_json FROM providencias WHERE radicado = ? AND enlace = ?",
            (radicado.strip(), enlace.strip()),
        ).fetchall()
        for row in rows:
            try:
                d = json.loads(row["datos_json"] or "{}")
            except Exception:
                d = {}
            d["ruta_pdf"] = ruta_pdf
            conn.execute(
                "UPDATE providencias SET datos_json = ? WHERE id = ?",
                (json.dumps(d, ensure_ascii=False), row["id"]),
            )
        conn.commit()
    finally:
        conn.close()


def limpiar_base() -> None:
    """
    Elimina TODOS los radicados, actuaciones y providencias.
    Deja la base de datos vacía para empezar desde cero.
    """
    conn = get_connection()
    try:
        conn.executescript(
            """
            DELETE FROM actuaciones;
            DELETE FROM providencias;
            DELETE FROM user_radicados;
            DELETE FROM radicados;
            """
        )
        conn.commit()
    finally:
        conn.close()
