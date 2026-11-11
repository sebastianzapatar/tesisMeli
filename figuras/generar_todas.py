"""Genera todas las figuras de los capítulos 1 a 3 de la tesis.

    python figuras/generar_todas.py        (desde la raíz del repositorio)

Corre, en orden, cada script fig_*.py de cada carpeta capitulo_*/ y deja
los PDF (para LaTeX) y los PNG (para revisar) junto al script, en la misma
carpeta capitulo_N/.

Cada script corre en su PROPIO proceso: así un cambio de estilo de una
figura (p. ej. la letra serif de la línea de tiempo) no se filtra a las
siguientes, y el resultado es idéntico a correr cada script por separado.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent             # figuras/
CODIGO = AQUI.parent / "codigo"                    # codigo/

# El paquete intermitencia (codigo/src/) y los módulos comunes (figuras/)
# quedan disponibles aunque el paquete no esté instalado.
ENTORNO = dict(os.environ, MPLBACKEND="Agg")
ENTORNO["PYTHONPATH"] = os.pathsep.join(
    [str(CODIGO / "src"), str(AQUI), ENTORNO.get("PYTHONPATH", "")]).rstrip(os.pathsep)


def orden_natural(ruta: Path) -> list:
    """fig_3_2 antes que fig_3_10 (orden numérico, no alfabético)."""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", ruta.name)]


fallos = []
for capitulo in sorted(AQUI.glob("capitulo_*"), key=orden_natural):
    print(f"\n{capitulo.name}")
    for script in sorted(capitulo.glob("fig_*.py"), key=orden_natural):
        print(f"  {script.name}", flush=True)
        r = subprocess.run([sys.executable, str(script)], cwd=AQUI.parent, env=ENTORNO,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        salidas = [l for l in r.stdout.splitlines() if l.strip().startswith("->")]
        for linea in salidas:
            print(f"    {linea.strip()}")
        if r.returncode != 0:                         # sigue con las demás
            ultima = (r.stderr.strip().splitlines() or ["(sin mensaje)"])[-1]
            print(f"    !! falló: {ultima}")
            fallos.append(script.name)

if fallos:
    print(f"\nFiguras con error: {', '.join(fallos)}")
    sys.exit(1)
print(f"\nListo. Figuras en {AQUI}")
