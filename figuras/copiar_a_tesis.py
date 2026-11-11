"""Copia los PDF de las figuras de los capítulos 1 a 3 a la carpeta Figuras/ de la tesis en LaTeX.

Uso (desde la raíz del repositorio):
    python figuras/generar_todas.py                     # 1. regenera las figuras
    python figuras/copiar_a_tesis.py                    # 2. copia los PDF
    python figuras/copiar_a_tesis.py "C:/ruta/TESIS/Figuras"   # o a otra carpeta

Sin argumento, busca la carpeta TESIS/Figuras subiendo desde el repositorio
(la tesis en LaTeX NO está en el repositorio).
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent          # figuras/


def buscar_destino() -> Path | None:
    for padre in AQUI.parents:
        candidata = padre / "TESIS" / "Figuras"
        if candidata.is_dir():
            return candidata
    return None


def main() -> None:
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else buscar_destino()
    if destino is None:
        print("No encontré TESIS/Figuras. Pasa la carpeta como argumento.")
        return
    pdfs = sorted(AQUI.glob("capitulo_*/*.pdf"))
    if not pdfs:
        print("No hay PDF. Corre primero figuras/generar_todas.py")
        return
    destino.mkdir(parents=True, exist_ok=True)
    for pdf in pdfs:
        shutil.copy2(pdf, destino / pdf.name)
        print(f"  {pdf.parent.name}/{pdf.name}")
    print(f"{len(pdfs)} figuras copiadas a {destino}")


if __name__ == "__main__":
    main()
