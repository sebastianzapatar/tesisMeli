#!/usr/bin/env bash
# Corre el pipeline completo. Se detiene al primer error.
set -euo pipefail
cd "$(dirname "$0")"

PY=./.venv/bin/python
if [ ! -x "$PY" ]; then
  echo "No existe $PY — crea el entorno primero:"
  echo "  python3.12 -m venv .venv && ./.venv/bin/python -m pip install -e '.[dev,rapido,notebook]'"
  exit 1
fi

# Evita que Matplotlib y Fontconfig intenten escribir en $HOME. Esto hace
# reproducible el pipeline también en contenedores y carpetas restringidas.
mkdir -p .cache/matplotlib .cache/fontconfig
export MPLBACKEND=Agg
export MPLCONFIGDIR="$PWD/.cache/matplotlib"
export XDG_CACHE_HOME="$PWD/.cache"

echo ">>> Tests"
$PY -m pytest tests/ -q

for paso in 01_diagnostico 02_intermitencia 03_curvas 04_optimo 05_sustituto 06_figuras 07_informe; do
  echo
  echo ">>> pipeline/${paso}.py"
  $PY "pipeline/${paso}.py"
done

echo
echo ">>> Listo. Resultados en resultados/ y figuras en resultados/figuras/"
