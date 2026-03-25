   |# Cómo probar el monitor de radicados — Paso a paso

## Paso 1: Abrir la terminal en la carpeta del proyecto

1. Abre **PowerShell** o **Símbolo del sistema** (cmd).
2. Ve a la carpeta del proyecto:
   ```bash
   cd "c:\Users\Thomas Castro\Desktop\JudgeScrapper_Pipito"
   ```
3. Comprueba que estás en la carpeta correcta (debe aparecer el archivo `main.py`):
   ```bash
   dir main.py
   ```

---

## Paso 2: Crear un entorno virtual (recomendado)

1. Crea el entorno:
   ```bash
   python -m venv venv
   ```
2. Actívalo:
   - En **PowerShell**: `.\venv\Scripts\Activate.ps1`
   - En **cmd**: `venv\Scripts\activate.bat`
3. Verás algo como `(venv)` al inicio de la línea.

---

## Paso 3: Instalar dependencias

1. Instala los paquetes de Python:
   ```bash
   pip install -r requirements.txt
   ```
2. Instala el navegador que usa el programa (Chromium):
   ```bash
   playwright install chromium
   ```
3. Si todo va bien, no debería salir ningún error.

---

## Paso 4: Registrar tu número de radicado

1. Sustituye `TU_NUMERO_DE_23_DIGITOS` por tu radicado real.
2. Ejecuta:
   ```bash
   python main.py agregar TU_NUMERO_DE_23_DIGITOS
   ```
   Ejemplo:
   ```bash
   python main.py agregar 25001234567890123456789
   ```
3. Debe aparecer: `Radicado registrado: ...`

---

## Paso 5: Ejecutar el monitor (primera vez, con navegador visible)

1. Ejecuta (con tu número de radicado):
   ```bash
   python main.py monitor TU_NUMERO_DE_23_DIGITOS --visible
   ```
2. Se abrirá una ventana de Chromium:
   - Entrará a **Consulta de Procesos** y buscará por radicado.
   - Luego entrará a **Publicaciones Procesales** y buscará por radicado.
3. Al terminar, en la terminal verás:
   - Cuántas actuaciones se obtuvieron y guardaron.
   - Cuántas providencias se obtuvieron y guardadas.
   - Si hubo actualizaciones nuevas (y cuáles).

---

## Paso 6: Ver lo que se guardó

1. Ejecuta:
   ```bash
   python main.py ver TU_NUMERO_DE_23_DIGITOS
   ```
2. Verás la lista de actuaciones y providencias guardadas en la base de datos.

---

## Paso 7 (opcional): Descargar los PDF de las providencias

1. **Opción A** — Al hacer el monitor y descargar en el mismo paso:
   ```bash
   python main.py monitor TU_NUMERO_DE_23_DIGITOS --descargar-pdf
   ```
2. **Opción B** — Si ya hiciste el monitor antes, solo descargar PDFs:
   ```bash
   python main.py descargar-pdf TU_NUMERO_DE_23_DIGITOS
   ```
3. Los PDFs se guardan en la carpeta:
   `JudgeScrapper_Pipito\providencias_pdf\TU_NUMERO_DE_23_DIGITOS\`

---

## Resumen de comandos (en orden)

| Orden | Comando |
|-------|--------|
| 1 | `cd "c:\Users\Thomas Castro\Desktop\JudgeScrapper_Pipito"` |
| 2 | `python -m venv venv` |
| 3 | `.\venv\Scripts\Activate.ps1` (PowerShell) o `venv\Scripts\activate.bat` (cmd) |
| 4 | `pip install -r requirements.txt` |
| 5 | `playwright install chromium` |
| 6 | `python main.py agregar TU_RADICADO` |
| 7 | `python main.py monitor TU_RADICADO --visible` |
| 8 | `python main.py ver TU_RADICADO` |

Cuando quieras repetir solo la consulta (sin ver el navegador), usa:
```bash
python main.py monitor TU_RADICADO
```
(sin `--visible`).
