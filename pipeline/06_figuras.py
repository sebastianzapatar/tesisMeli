"""Paso 6 — Figuras.

Genera las figuras nuevas y las correcciones de las anteriores. Todas se
construyen a partir de los resultados en disco: ninguna tiene
coeficientes quemados (el mapa de calor anterior sí los tenía, y no
correspondían al modelo ajustado).

Salidas: resultados/figuras/*.png y *.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from _comun import guardar as guardar_excel  # noqa: F401
from _comun import preparar, subtitulo, titulo
from intermitencia import viz
from intermitencia.viz import AZUL, GRIS, NARANJA, VERDE


def fig_comparacion_metodos(cfg, comp: pd.DataFrame) -> None:
    """F1 — B y M: método antiguo vs corregido."""
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.6))

    for ax, var, color in zip(axes, ["B", "M"], [AZUL, NARANJA]):
        x = comp[f"{var}_legacy"]
        y = comp[var]
        ax.scatter(x, y, s=28, color=color, edgecolor="white", linewidth=0.8, zorder=3)

        lim = [min(x.min(), y.min()) - 0.08, max(x.max(), y.max()) + 0.08]
        ax.plot(lim, lim, color=GRIS, lw=1.2, ls=":", zorder=1, label="identidad")
        ax.axhline(0, color=GRIS, lw=0.8, zorder=1)
        ax.axvline(0, color=GRIS, lw=0.8, zorder=1)
        ax.set_xlim(lim)
        ax.set_ylim(lim)

        r = np.corrcoef(x, y)[0, 1]
        viz.eje(ax, f"${var}$ — método de cruces (anterior)",
                f"${var}$ — eventos de déficit (corregido)")
        ax.set_title(f"$r = {r:+.2f}$", loc="right", fontsize=9, color=GRIS)
        ax.legend(loc="upper left")

    fig.suptitle(
        "Las métricas anteriores no son un proxy de las corregidas",
        x=0.02, ha="left", fontsize=10,
    )
    fig.tight_layout()
    viz.guardar(fig, cfg.rutas.figuras, "F1_comparacion_metodos_BM")


def fig_curvas_confiabilidad(cfg, curvas: pd.DataFrame) -> None:
    """F2 — Curvas capacidad-confiabilidad, con LPSP en eje logarítmico."""
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.6))

    for ax, col, etq in [
        (axes[0], "cobertura_deficit", "Cobertura de déficit"),
        (axes[1], "lpsp", "LPSP  (ENS / demanda total)"),
    ]:
        for _, g in curvas.groupby("Serie"):
            g = g.sort_values("pct_energia_diaria")
            ax.plot(g["pct_energia_diaria"], g[col], color=GRIS, alpha=0.30, lw=1.0)

        mediana = curvas.groupby("pct_energia_diaria")[col].median()
        ax.plot(mediana.index, mediana.values, color=AZUL, lw=2.4,
                label="mediana de las 51 series", zorder=5)
        viz.eje(ax, "Capacidad BESS [% de la energía diaria generada]", etq)
        ax.legend(loc="best")

    axes[1].set_yscale("log")
    axes[1].axhline(0.05, color=NARANJA, lw=1.4, ls="--", label="LPSP = 5 %")
    axes[1].legend(loc="best")

    fig.suptitle(
        "Con la planta fija en 100 MW la LPSP nunca baja de ~20 %",
        x=0.02, ha="left", fontsize=10,
    )
    fig.tight_layout()
    viz.guardar(fig, cfg.rutas.figuras, "F2_curvas_confiabilidad")


def fig_mapa_lcoe(cfg, grilla: pd.DataFrame, optimos: pd.DataFrame,
                  diag: pd.DataFrame) -> None:
    """F3 — Mapa LCOE(P_pv, E_bess) con isolíneas de LPSP y el óptimo.

    Responde literalmente a "cuadrar los tamaños de planta y baterías":
    el modelo anterior solo dimensionaba la batería.
    """
    series = list(grilla["Serie"].unique()[:3])
    fig, axes = plt.subplots(1, len(series), figsize=(3.5 * len(series) + 1.1, 3.5),
                             squeeze=False, sharey=True)

    # Escala común de color: si cada panel tuviera la suya, los colores no
    # serían comparables entre sitios, que es justo lo que se quiere ver.
    zmin = grilla["lcoe_usd_mwh"].min()
    zmax = np.percentile(grilla["lcoe_usd_mwh"], 92)
    niveles = np.linspace(zmin, zmax, 19)
    y_max = 3.0 * optimos.loc[series, "e_bess_mwh"].max()

    for j, (ax, s) in enumerate(zip(axes[0], series)):
        g = grilla[grilla["Serie"] == s]
        pv_u = np.sort(g["p_pv_mw"].unique())
        be_u = np.sort(g["e_bess_mwh"].unique())
        Z = g.pivot(index="e_bess_mwh", columns="p_pv_mw",
                    values="lcoe_usd_mwh").loc[be_u, pv_u].to_numpy()
        L = g.pivot(index="e_bess_mwh", columns="p_pv_mw",
                    values="lpsp").loc[be_u, pv_u].to_numpy()
        X, Y = np.meshgrid(pv_u, be_u)

        cf = ax.contourf(X, Y, np.clip(Z, zmin, zmax), levels=niveles,
                         cmap=viz.SECUENCIAL, extend="max")
        # Pocas isolíneas y bien separadas: con cinco niveles las etiquetas
        # colisionaban en la esquina inferior izquierda.
        cs = ax.contour(X, Y, L, levels=[0.02, 0.05, 0.20],
                        colors="white", linewidths=1.1)
        ax.clabel(cs, inline=True, inline_spacing=2, fontsize=7,
                  fmt=lambda v: f"{v:.0%}")

        o = optimos.loc[s]
        ax.scatter([o["p_pv_mw"]], [o["e_bess_mwh"]], s=150, marker="*",
                   color="white", edgecolor="black", linewidth=1.0, zorder=6,
                   label="óptimo económico")
        # Diseño anterior: 100 MW fijos y 25 % de la energía diaria.
        ax.scatter([cfg.planta.potencia_mw],
                   [0.25 * float(diag.loc[s, "energia_planta_MWh_dia"])],
                   s=55, marker="s", color=NARANJA, edgecolor="black",
                   linewidth=0.8, zorder=6, label="diseño anterior")

        ax.set_ylim(0, y_max)
        ax.grid(False)
        viz.eje(ax, "Potencia de planta [MW]",
                "Capacidad BESS [MWh]" if j == 0 else "", s)
        if j == 0:
            ax.legend(loc="upper right", fontsize=8, labelcolor="white")

    cb = fig.colorbar(cf, ax=axes[0].tolist(), pad=0.02, aspect=28)
    cb.set_label("LCOE [USD/MWh]")
    cb.add_lines(cs)
    viz.guardar(fig, cfg.rutas.figuras, "F3_mapa_lcoe_planta_bateria")


def fig_ley_exponencial(cfg, kappa: pd.DataFrame) -> None:
    """F4 — κ frente a B, M y PSH: el vínculo intermitencia -> almacenamiento."""
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.4))
    lk = np.log(kappa["kappa_mwh"])

    for ax, var, etq, color in zip(
        axes, ["B", "M", "PSH"],
        ["Burstiness $B$", "Memory $M$", "PSH [h/día]"],
        [AZUL, NARANJA, VERDE],
    ):
        ax.scatter(kappa[var], lk, s=26, color=color,
                   edgecolor="white", linewidth=0.7, zorder=3)
        viz.anotar_ajuste(ax, kappa[var], lk, color=GRIS)
        viz.eje(ax, etq, r"$\ln \kappa$  [$\kappa$ en MWh]" if var == "B" else "")
        ax.legend(loc="best", fontsize=8)

    fig.suptitle(
        r"$\kappa$: almacenamiento que divide la LPSP por $e$  "
        r"(planta común de referencia)",
        x=0.02, ha="left", fontsize=10,
    )
    fig.tight_layout()
    viz.guardar(fig, cfg.rutas.figuras, "F4_kappa_vs_intermitencia")


def fig_validacion_loo(cfg, res) -> None:
    """F5 — Predicho vs observado FUERA DE MUESTRA.

    Reemplaza al "antes vs después" del modelo anterior, que se evaluaba
    sobre los mismos datos con que se había ajustado.
    """
    fig, ax = plt.subplots(figsize=(4.4, 4.0))
    y, p = res.y, res.predicciones_loo

    ax.scatter(y, p, s=34, color=AZUL, edgecolor="white", linewidth=0.8, zorder=3)
    lim = [min(y.min(), p.min()) - 0.15, max(y.max(), p.max()) + 0.15]
    ax.plot(lim, lim, color=GRIS, lw=1.4, ls=":", label="1:1", zorder=1)
    ax.fill_between(lim, np.array(lim) - res.rmse_loo, np.array(lim) + res.rmse_loo,
                    color=AZUL, alpha=0.10, lw=0, label=f"±RMSE = {res.rmse_loo:.3f}")
    ax.set_xlim(lim)
    ax.set_ylim(lim)

    viz.eje(ax, r"$\ln \kappa$ observado", r"$\ln \kappa$ predicho (LOO)")
    ax.set_title(
        f"$R^2_{{LOO}} = {res.r2_loo:.3f}$   "
        f"({res.mejora_sobre_baseline:+.0%} vs. media)",
        loc="right", fontsize=9, color=GRIS,
    )
    ax.legend(loc="upper left")
    fig.tight_layout()
    viz.guardar(fig, cfg.rutas.figuras, "F5_validacion_loo")


def fig_optimos(cfg, optimos: pd.DataFrame) -> None:
    """F6 — Dimensionamiento óptimo por serie vs. el rango buscado antes."""
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.8))
    d = optimos.sort_values("p_pv_mw")
    y = np.arange(len(d))

    ax = axes[0]
    ax.barh(y, d["p_pv_mw"], color=AZUL, height=0.75, zorder=3)
    ax.axvline(cfg.planta.potencia_mw, color=NARANJA, lw=1.8, ls="--",
               label=f"diseño anterior ({cfg.planta.potencia_mw:.0f} MW, fijo)")
    ax.set_yticks([])
    viz.eje(ax, "Potencia de planta óptima [MW]", "Series (51)")
    ax.legend(loc="lower right", fontsize=8)

    ax = axes[1]
    ax.barh(y, d["bess_pct_energia_diaria"], color=VERDE, height=0.75, zorder=3)
    ax.axvspan(5, 30, color=NARANJA, alpha=0.18, zorder=1,
               label="rango buscado antes (5–30 %)")
    ax.set_yticks([])
    viz.eje(ax, "BESS óptimo [% de la energía diaria]", "")
    ax.legend(loc="lower right", fontsize=8)

    fig.suptitle(
        "El óptimo económico cae fuera del rango que se barría antes",
        x=0.02, ha="left", fontsize=10,
    )
    fig.tight_layout()
    viz.guardar(fig, cfg.rutas.figuras, "F6_optimos_por_serie")


def fig_pareto(cfg, pareto: pd.DataFrame) -> None:
    """F7 — Frente costo-confiabilidad."""
    fig, ax = plt.subplots(figsize=(5.2, 3.8))
    p = pareto[pareto["alcanzable"]]

    for color, (s, g) in zip(viz.CATEGORICA, p.groupby("Serie")):
        g = g.sort_values("lpsp")
        ax.plot(g["lpsp"] * 100, g["lcoe_usd_mwh"], "o-", color=color, label=s)

    ax.set_xscale("log")
    viz.eje(ax, "LPSP [%]  (escala logarítmica)", "LCOE [USD/MWh]")
    ax.legend(loc="best")
    fig.suptitle("Cuánto cuesta cada punto de confiabilidad",
                 x=0.02, ha="left", fontsize=10)
    fig.tight_layout()
    viz.guardar(fig, cfg.rutas.figuras, "F7_pareto_costo_confiabilidad")


def main() -> None:
    cfg = preparar()
    viz.aplicar_estilo()
    salida = cfg.rutas.salida

    titulo("generación de figuras")

    comp = pd.read_excel(salida / "02_comparacion_metodos.xlsx").set_index("Serie")
    curvas = pd.read_excel(salida / "03_curvas.xlsx")
    optimos = pd.read_excel(salida / "04_optimos.xlsx").set_index("Serie")
    grilla = pd.read_excel(salida / "04_grilla.xlsx")
    pareto = pd.read_excel(salida / "04_pareto.xlsx")
    kappa = pd.read_excel(salida / "05_kappa.xlsx").set_index("Serie")
    diag = pd.read_excel(salida / "01_diagnostico_series.xlsx").set_index("Serie")

    from intermitencia.sustituto import ajustar_sustituto
    predictores = [p for p in cfg.sustituto["predictores"] if p in kappa.columns]
    res = ajustar_sustituto(kappa, predictores)

    for nombre, fn, args in [
        ("F1 comparación de métodos B y M", fig_comparacion_metodos, (comp,)),
        ("F2 curvas de confiabilidad", fig_curvas_confiabilidad, (curvas,)),
        ("F3 mapa LCOE(planta, batería)", fig_mapa_lcoe, (grilla, optimos, diag)),
        ("F4 kappa vs intermitencia", fig_ley_exponencial, (kappa,)),
        ("F5 validación LOO", fig_validacion_loo, (res,)),
        ("F6 óptimos por serie", fig_optimos, (optimos,)),
        ("F7 frente de Pareto", fig_pareto, (pareto,)),
    ]:
        try:
            fn(cfg, *args)
            print(f"  ok  {nombre}")
        except Exception as e:  # noqa: BLE001
            print(f"  FALLÓ  {nombre}: {type(e).__name__}: {e}")

    subtitulo("Figuras generadas")
    for f in sorted(cfg.rutas.figuras.glob("*.png")):
        print(f"  {f.relative_to(salida.parent)}")

    print("\nFiguras listas. Siguiente paso: pipeline/07_informe.py")


if __name__ == "__main__":
    main()
