# Figuras de la tesis

Una carpeta por capítulo, un script por figura. Todas comparten la
geometría y el estilo de `estilo.py`.

```
figuras_tesis/
├── estilo.py              # tamaño, márgenes y estilo COMUNES a todas
├── generar_todas.py       # corre todos los fig_*.py
├── capitulo_1/
│   ├── datos/             # datos propios del capítulo (p. ej. Inversiones.xlsx)
│   ├── fig_1_1_generacion_renovable.py   -> Generation.pdf
│   └── fig_1_2_tres_dias.py              -> Tres_dias_horizontal.pdf
└── salida/
    └── capitulo_1/        # PDF (para LaTeX) y PNG (para revisar)
```

## Cómo correr

Desde la raíz del proyecto, con el entorno del pipeline:

```bash
.venv\Scripts\python figuras_tesis\generar_todas.py                       # todas
.venv\Scripts\python figuras_tesis\capitulo_1\fig_1_2_tres_dias.py        # solo una
```

## Reglas comunes (definidas en `estilo.py`)

| Qué | Valor |
|---|---|
| Ancho de toda figura | 6.3 in (≈ `\textwidth`) |
| Espacio para el eje Y (borde → eje) | 0.70 in, **igual en todas** |
| Etiqueta del eje Y | centrada a 0.15 in del borde, **igual en todas** |
| Margen blanco derecho / superior | 0.25 in / 0.15 in |
| Letra | 10 pt |
| `bbox_inches="tight"` | **no se usa** (cambiaría el margen de cada figura) |

En LaTeX inserte todas con el mismo ancho para que los ejes queden
alineados:

```latex
\includegraphics[width=\textwidth]{Figuras/Tres_dias_horizontal.pdf}
```

## Agregar una figura nueva

1. Crear `capitulo_N/fig_N_M_nombre.py` (copiar uno existente).
2. Usar `crear_figura(ncols=...)`, `formatear_eje(...)` y
   `guardar(fig, "capitulo_N", "Nombre")`.
3. Si hace falta más espacio abajo (leyenda, paneles (a)(b)(c)),
   aumentar solo `margen_inf`; el margen izquierdo nunca se toca.
