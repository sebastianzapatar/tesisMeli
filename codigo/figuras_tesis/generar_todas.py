"""Genera todas las figuras de la tesis (todos los capítulos).

    ./.venv/Scripts/python figuras_tesis/generar_todas.py      (Windows)
    ./.venv/bin/python     figuras_tesis/generar_todas.py      (Linux/Mac)

Corre, en orden, cada script fig_*.py de cada carpeta capitulo_*/.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

fallos = []
for capitulo in sorted(AQUI.glob("capitulo_*")):
    print(f"\n{capitulo.name}")
    for script in sorted(capitulo.glob("fig_*.py")):
        print(f"  {script.name}")
        try:
            runpy.run_path(str(script), run_name="__main__")
        except Exception as e:                        # sigue con las demás
            print(f"  !! falló: {e}")
            fallos.append(script.name)

if fallos:
    print(f"\nFiguras con error: {', '.join(fallos)}")
    sys.exit(1)
print("\nListo.")
