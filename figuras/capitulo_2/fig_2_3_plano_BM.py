"""Figura 2.3 — Qué miden la burstiness B y la memoria M.

(a) Cuatro secuencias de eventos con el MISMO tiempo medio entre eventos
    (10 unidades): regular, Poisson, en ráfagas sin memoria y en ráfagas
    con memoria. Cada raya es un evento.
(b) Las cuatro secuencias en el plano B–M de Goh y Barabási (2008).

B y M se calculan con las fórmulas del capítulo 2 sobre secuencias largas
(N_LARGO intervalos) para que los valores sean estables; en (a) se muestra
solo una ventana. Datos SINTÉTICOS.

Salida: capitulo_2/Plano_BM_conceptual.pdf
Para cambiar los procesos, editar las funciones de PROCESOS.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import estilo  # noqa: E402
from comun_tesis import AZUL, GRIS, NARANJA, TINTA, VERDE, guardar  # noqa: E402
from estilo import etiqueta_panel  # noqa: E402

SEMILLA = 7
N_LARGO = 4000          # intervalos para calcular B y M
VENTANA = 300           # unidades de tiempo mostradas en (a)
MEDIA = 10.0


def regular(rng, n):
    return MEDIA + rng.uniform(-1.0, 1.0, n)


def poisson(rng, n):
    return rng.exponential(MEDIA, n)


def _corto_largo(rng, estados):
    corto = rng.exponential(2.0, estados.size)
    largo = rng.exponential(42.0, estados.size)
    return np.where(estados, largo, corto)          # media = 0.8*2 + 0.2*42 = 10


def rafagas(rng, n):
    return _corto_largo(rng, rng.random(n) < 0.2)


def rafagas_memoria(rng, n):
    # Cadena de Markov de dos estados con la misma proporción estacionaria (20 % largos)
    estados = np.empty(n, dtype=bool)
    estados[0] = False
    u = rng.random(n)
    for k in range(1, n):
        estados[k] = (u[k] < 0.80) if estados[k - 1] else (u[k] < 0.05)
    return _corto_largo(rng, estados)


PROCESOS = [
    ("Regular", regular, VERDE),
    ("Poisson", poisson, GRIS),
    ("Bursty, no memory", rafagas, AZUL),
    ("Bursty with memory", rafagas_memoria, NARANJA),
]


def burstiness(tau):
    s, m = tau.std(), tau.mean()
    return (s - m) / (s + m)


def memoria(tau):
    a, b = tau[:-1], tau[1:]
    return float(np.mean((a - a.mean()) * (b - b.mean())) / (a.std() * b.std()))


def main() -> None:
    estilo.aplicar_estilo()
    rng = np.random.default_rng(SEMILLA)
    alto = 2.55
    fig = plt.figure(figsize=(estilo.ANCHO, alto))
    ax_a = fig.add_axes([0.20 / estilo.ANCHO + 1.25 / estilo.ANCHO, 0.62 / alto,
                         2.45 / estilo.ANCHO, 1.75 / alto])
    ax_b = fig.add_axes([4.55 / estilo.ANCHO, 0.62 / alto, 1.55 / estilo.ANCHO, 1.75 / alto])

    puntos = []
    for i, (nombre, gen, color) in enumerate(PROCESOS):
        tau = gen(rng, N_LARGO)
        b, m = burstiness(tau), memoria(tau)
        puntos.append((nombre, b, m, color))
        t = np.cumsum(tau)
        t = t[t < VENTANA]
        y = len(PROCESOS) - 1 - i
        ax_a.vlines(t, y - 0.32, y + 0.32, color=color, lw=1.0)
        print(f"  {nombre:20s} B = {b:+.2f}  M = {m:+.2f}")

    ax_a.set_yticks(range(len(PROCESOS)), [p[0] for p in PROCESOS][::-1], fontsize=8)
    ax_a.set_xlim(0, VENTANA)
    ax_a.set_ylim(-0.6, len(PROCESOS) - 0.4)
    ax_a.set_xlabel("Time", fontsize=9)
    ax_a.grid(False)
    ax_a.tick_params(axis="y", length=0, right=False)
    ax_a.tick_params(axis="x", labelsize=8, top=False)
    etiqueta_panel(ax_a, "(a)", debajo=0.48)

    ax_b.axhline(0, color=GRIS, lw=0.7)
    ax_b.axvline(0, color=GRIS, lw=0.7)
    for nombre, b, m, color in puntos:
        ax_b.scatter(b, m, s=34, color=color, zorder=3, edgecolor="white", linewidth=0.6)
    ax_b.set_xlim(-1, 1)
    ax_b.set_ylim(-0.5, 1)
    ax_b.set_xticks([-1, 0, 1])
    ax_b.set_yticks([-0.5, 0, 0.5, 1])
    ax_b.set_xlabel("Burstiness $B$", fontsize=9)
    ax_b.set_ylabel("Memory $M$", fontsize=9, labelpad=2)
    ax_b.tick_params(labelsize=8)
    ax_b.grid(False)
    for x, y, txt in ((-0.97, 0.90, "periodic"), (0.08, 0.90, "clustered,\npersistent")):
        ax_b.text(x, y, txt, fontsize=7, color=TINTA, va="top")
    etiqueta_panel(ax_b, "(b)", debajo=0.48)
    guardar(fig, "capitulo_2", "Plano_BM_conceptual")


if __name__ == "__main__":
    main()
