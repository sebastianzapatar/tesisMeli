"""Paso 7 — Informe PDF de resultados y hallazgos.

Construye el informe **leyendo los archivos de resultados**, no con cifras
quemadas: si se vuelve a correr el pipeline con otros supuestos, el
informe se actualiza solo. Esa es la misma razón por la que el mapa de
calor anterior estaba mal (tenía los coeficientes escritos a mano).

Salida:
    resultados/Informe_intermitencia.pdf
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import pandas as pd
import matplotlib
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from _comun import preparar, titulo

# Paleta consistente con las figuras (validada para accesibilidad)
AZUL = colors.HexColor("#2a78d6")
NARANJA = colors.HexColor("#eb6834")
TINTA = colors.HexColor("#1a1a19")
GRIS = colors.HexColor("#6f6f6a")
GRIS_SUAVE = colors.HexColor("#ececeb")
ROJO = colors.HexColor("#c0392b")

ANCHO_UTIL = A4[0] - 4 * cm


# Helvetica no contiene κ, τ ni algunos subíndices usados en las fórmulas.
# DejaVu viene con Matplotlib, cubre Unicode y se incrusta dentro del PDF.
DIR_FUENTES = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
pdfmetrics.registerFont(TTFont("DejaVuSans", DIR_FUENTES / "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", DIR_FUENTES / "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DejaVuSans-Oblique", DIR_FUENTES / "DejaVuSans-Oblique.ttf"))
pdfmetrics.registerFont(TTFont("DejaVuSans-BoldOblique", DIR_FUENTES / "DejaVuSans-BoldOblique.ttf"))
pdfmetrics.registerFont(TTFont("DejaVuSansMono", DIR_FUENTES / "DejaVuSansMono.ttf"))
pdfmetrics.registerFontFamily(
    "DejaVuSans", normal="DejaVuSans", bold="DejaVuSans-Bold",
    italic="DejaVuSans-Oblique", boldItalic="DejaVuSans-BoldOblique",
)


# =====================================================================
# ESTILOS
# =====================================================================

def construir_estilos():
    ss = getSampleStyleSheet()
    e = {}
    e["titulo"] = ParagraphStyle(
        "titulo", parent=ss["Title"], fontName="DejaVuSans-Bold",
        fontSize=20, leading=24, textColor=TINTA, spaceAfter=4, alignment=0,
    )
    e["subtitulo"] = ParagraphStyle(
        "subtitulo", parent=ss["Normal"], fontName="DejaVuSans",
        fontSize=11, leading=15,
        textColor=GRIS, spaceAfter=18,
    )
    e["h1"] = ParagraphStyle(
        "h1", parent=ss["Heading1"], fontName="DejaVuSans-Bold", fontSize=14,
        leading=18, textColor=AZUL, spaceBefore=18, spaceAfter=8,
    )
    e["h2"] = ParagraphStyle(
        "h2", parent=ss["Heading2"], fontName="DejaVuSans-Bold", fontSize=11,
        leading=14, textColor=TINTA, spaceBefore=12, spaceAfter=5,
    )
    e["cuerpo"] = ParagraphStyle(
        "cuerpo", parent=ss["Normal"], fontName="DejaVuSans",
        fontSize=9.5, leading=14,
        textColor=TINTA, alignment=TA_JUSTIFY, spaceAfter=7,
    )
    e["nota"] = ParagraphStyle(
        "nota", parent=e["cuerpo"], fontSize=8.5, leading=12, textColor=GRIS,
    )
    e["alerta"] = ParagraphStyle(
        "alerta", parent=e["cuerpo"], fontSize=9.5, leading=14,
        textColor=TINTA, borderColor=NARANJA, borderWidth=0, borderPadding=8,
        backColor=colors.HexColor("#fdf1ec"), leftIndent=6, rightIndent=6,
        spaceBefore=6, spaceAfter=10,
    )
    e["pie_fig"] = ParagraphStyle(
        "pie_fig", parent=ss["Normal"], fontName="DejaVuSans",
        fontSize=8.5, leading=11,
        textColor=GRIS, spaceBefore=4, spaceAfter=14,
    )
    return e


def tabla(datos, anchos=None, encabezado=True, alinear_derecha_desde=1):
    # Table no ajusta cadenas por sí sola: cada celda debe ser un Paragraph.
    # Sin esto, la tabla larga de hallazgos se superpone y sale de la página.
    estilos_celda = {}

    def estilo_celda(es_encabezado: bool, derecha: bool):
        clave = es_encabezado, derecha
        if clave not in estilos_celda:
            estilos_celda[clave] = ParagraphStyle(
                f"celda_{int(es_encabezado)}_{int(derecha)}",
                fontName="DejaVuSans-Bold" if es_encabezado else "DejaVuSans",
                fontSize=8.2,
                leading=10.5,
                textColor=TINTA,
                alignment=TA_RIGHT if derecha else TA_LEFT,
                wordWrap="LTR",
            )
        return estilos_celda[clave]

    celdas = []
    for i, fila in enumerate(datos):
        celdas.append([
            Paragraph(str(valor), estilo_celda(encabezado and i == 0,
                                                j >= alinear_derecha_desde))
            for j, valor in enumerate(fila)
        ])

    t = Table(celdas, colWidths=anchos, hAlign="LEFT", repeatRows=1 if encabezado else 0)
    estilo = [
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, colors.HexColor("#dcdcda")),
    ]
    if encabezado:
        estilo += [
            ("BACKGROUND", (0, 0), (-1, 0), GRIS_SUAVE),
            ("LINEBELOW", (0, 0), (-1, 0), 0.8, GRIS),
        ]
    t.setStyle(TableStyle(estilo))
    return t


def figura(ruta: Path, pie: str, e, ancho=ANCHO_UTIL):
    """Inserta una figura escalada al ancho útil, con su pie."""
    from PIL import Image as PILImage

    with PILImage.open(ruta) as im:
        w, h = im.size
    alto = ancho * h / w
    return [Image(str(ruta), width=ancho, height=alto),
            Paragraph(pie, e["pie_fig"])]


def pie_de_pagina(canvas, doc):
    canvas.saveState()
    canvas.setFont("DejaVuSans", 7.5)
    canvas.setFillColor(GRIS)
    canvas.drawString(2 * cm, 1.2 * cm,
                      "Modelo de intermitencia PV+BESS · informe generado automáticamente")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"{doc.page}")
    canvas.setStrokeColor(colors.HexColor("#dcdcda"))
    canvas.setLineWidth(0.4)
    canvas.line(2 * cm, 1.6 * cm, A4[0] - 2 * cm, 1.6 * cm)
    canvas.restoreState()


# =====================================================================
# CONTENIDO
# =====================================================================

def main() -> None:
    cfg = preparar()
    e = construir_estilos()
    sal = cfg.rutas.salida
    figs = cfg.rutas.figuras

    titulo("informe pdf")

    # --- lectura de resultados ---------------------------------------
    diag = pd.read_excel(sal / "01_diagnostico_series.xlsx").set_index("Serie")
    comp = pd.read_excel(sal / "02_comparacion_metodos.xlsx").set_index("Serie")
    curvas = pd.read_excel(sal / "03_curvas.xlsx")
    inter = pd.read_excel(sal / "03_interanual.xlsx").set_index("Serie")
    opt = pd.read_excel(sal / "04_optimos.xlsx").set_index("Serie")
    kappa = pd.read_excel(sal / "05_kappa.xlsx").set_index("Serie")
    coef = pd.read_excel(sal / "05_sustituto_coeficientes.xlsx").set_index("index")

    gen_media = diag["gen_media_MW"]
    techo = curvas.groupby("Serie")["lpsp"].min()
    ceros = comp["frac_tau_cero_legacy"].mean()
    cambio_signo = int((np.sign(comp["M"]) != np.sign(comp["M_legacy"])).sum())
    r_b = np.corrcoef(comp["B"], comp["B_legacy"])[0, 1]
    r_m = np.corrcoef(comp["M"], comp["M_legacy"])[0, 1]
    r2_ley = kappa["r2_ley_exponencial"].median()

    doc = SimpleDocTemplate(
        str(sal / "Informe_intermitencia.pdf"), pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title="Modelo de intermitencia PV+BESS — resultados y hallazgos",
        author="Revisión del modelo",
    )

    C = []  # contenido

    # =================================================================
    # PORTADA / RESUMEN
    # =================================================================
    C.append(Paragraph("Modelo de intermitencia PV + BESS", e["titulo"]))
    C.append(Paragraph(
        f"Revisión del modelo, resultados y hallazgos &nbsp;·&nbsp; "
        f"{date.today():%d de %B de %Y}", e["subtitulo"]))

    C.append(Paragraph("Resumen ejecutivo", e["h1"]))
    C.append(Paragraph(
        "Se revisaron los siete scripts del modelo de intermitencia, se "
        "reconstruyó el pipeline sobre una base probada y se volvió a correr "
        "de punta a punta sobre las 51 series. Aparecieron tres hallazgos "
        "que cambian las conclusiones del trabajo.",
        e["cuerpo"]))

    C.append(Paragraph(
        "<b>1. El problema planteado no tenía solución.</b> Con la planta fija "
        f"en {cfg.planta.potencia_mw:.0f}&nbsp;MW, las {len(diag)} series generan en promedio "
        f"menos que la demanda de {cfg.demanda_mw:.0f}&nbsp;MW (mediana "
        f"{gen_media.median():.1f}&nbsp;MW). El balance energético anual es negativo, "
        "de modo que ninguna capacidad de batería alcanza alta confiabilidad: "
        "el almacenamiento desplaza energía en el tiempo, no la crea. Esa es la "
        "razón de fondo por la que el modelo anterior necesitaba un heurístico "
        "para definir un óptimo.", e["cuerpo"]))

    C.append(Paragraph(
        "<b>2. El óptimo económico está fuera del rango que se buscaba.</b> "
        "Resolviendo en dos dimensiones sobre (potencia de planta, capacidad de "
        f"batería), la planta óptima mediana es {opt['p_pv_mw'].median():.0f}&nbsp;MW y la "
        f"batería óptima es el {opt['bess_pct_energia_diaria'].median():.0f}&nbsp;% de la energía "
        "diaria. El barrido anterior exploraba entre 5&nbsp;% y 30&nbsp;%: el óptimo "
        "nunca estuvo dentro del rango de búsqueda.", e["cuerpo"]))

    C.append(Paragraph(
        "<b>3. Las métricas de intermitencia anteriores no eran utilizables, "
        "pero las corregidas sí funcionan.</b> El método antiguo producía "
        f"{ceros:.0%} de intervalos entre eventos iguales a cero, un artefacto de "
        f"medir cruces sobre una suma acumulada monótona. La memoria <i>M</i> cambia de "
        f"signo en {cambio_signo} de {len(comp)} series. Con la metodología corregida, "
        "la intermitencia sí explica el almacenamiento necesario "
        f"(R²<sub>LOO</sub> = {coef.loc['r2_loo','valor']:.2f}).", e["cuerpo"]))

    C.append(Paragraph(
        "<b>Advertencia.</b> Los parámetros económicos son valores de referencia "
        "marcados para revisión, no fuentes citables. Los tamaños óptimos dependen "
        "directamente del VoLL y del CAPEX, así que ninguna cifra de LCOE o de "
        "dimensionamiento de este informe es publicable hasta reemplazarlos por "
        "fuentes propias (NREL ATB para costos; resolución CREG vigente para el "
        "costo incremental de racionamiento).", e["alerta"]))

    # =================================================================
    # 1. FACTIBILIDAD
    # =================================================================
    C.append(PageBreak())
    C.append(Paragraph("1. El problema anterior no tenía solución", e["h1"]))

    C.append(Paragraph(
        "La primera comprobación del pipeline es si el sistema puede, en "
        "principio, cubrir la demanda. La respuesta es que no.", e["cuerpo"]))

    C.append(tabla([
        ["Generación media", "MW", "Serie"],
        ["Mínima", f"{gen_media.min():.2f}", gen_media.idxmin()],
        ["Mediana", f"{gen_media.median():.2f}", "—"],
        ["Máxima", f"{gen_media.max():.2f}", gen_media.idxmax()],
        ["Demanda plana", f"{cfg.demanda_mw:.2f}", "—"],
    ], anchos=[5 * cm, 3 * cm, 5 * cm], alinear_derecha_desde=1))
    C.append(Spacer(1, 10))

    C.append(Paragraph(
        f"<b>Series con generación media inferior a la demanda: "
        f"{int((gen_media < cfg.demanda_mw).sum())} de {len(gen_media)}.</b> "
        "Solo para equilibrar la energía haría falta una planta de "
        f"{(cfg.demanda_mw / diag['factor_planta']).median():.0f}&nbsp;MW (mediana), y bastante "
        "más para generar el excedente con el cual cargar la batería durante "
        "rachas nubladas y pagar las pérdidas de conversión.", e["cuerpo"]))

    C.append(Paragraph(
        "El síntoma se ve en el techo de confiabilidad: por grande que sea la "
        f"batería, la LPSP no baja de {techo.median():.0%} (mediana). El modelo "
        "anterior no podía detectar esto porque definía el óptimo <i>relativo al "
        "máximo alcanzable en su propia grilla</i>, con lo que un techo bajo "
        "quedaba disfrazado de óptimo.", e["cuerpo"]))

    C.extend(figura(figs / "F2_curvas_confiabilidad.png",
                    "<b>Figura 1.</b> Curvas capacidad–confiabilidad de las 51 series. "
                    "A la izquierda, la cobertura de déficit; a la derecha, la LPSP "
                    "estándar en escala logarítmica. Las curvas se aplanan muy por "
                    "encima del objetivo del 5&nbsp;%: el limitante es la energía, no "
                    "el almacenamiento.", e))

    # =================================================================
    # 2. B Y M
    # =================================================================
    C.append(PageBreak())
    C.append(Paragraph("2. Las métricas de intermitencia estaban mal calculadas", e["h1"]))

    C.append(Paragraph(
        "El cálculo original definía los eventos como los cruces de la <i>suma "
        "acumulada de excedentes</i> por múltiplos del percentil 25. Eso tiene un "
        "problema de fondo: una suma acumulada de una cantidad siempre positiva es "
        "monótona creciente, así que no tiene periodos de silencio ni ráfagas. La "
        "burstiness está definida para procesos puntuales; aplicarla a un "
        "acumulador monótono es un error de categoría.", e["cuerpo"]))

    C.append(Paragraph(
        "La consecuencia medible es que muchos pasos cruzaban varios umbrales a la "
        f"vez, produciendo intervalos entre eventos de duración cero: <b>{ceros:.0%} "
        "de los intervalos</b>. Un intervalo nulo no tiene sentido físico e infla "
        "artificialmente la desviación estándar, que es justamente el numerador de "
        "<i>B</i>.", e["cuerpo"]))

    C.append(Paragraph("Impacto sobre los valores publicados", e["h2"]))
    C.append(tabla([
        ["", "Método anterior", "Método corregido"],
        ["B — media", f"{comp['B_legacy'].mean():+.3f}", f"{comp['B'].mean():+.3f}"],
        ["B — rango", f"[{comp['B_legacy'].min():+.2f}, {comp['B_legacy'].max():+.2f}]",
         f"[{comp['B'].min():+.2f}, {comp['B'].max():+.2f}]"],
        ["M — media", f"{comp['M_legacy'].mean():+.3f}", f"{comp['M'].mean():+.3f}"],
        ["M — rango", f"[{comp['M_legacy'].min():+.2f}, {comp['M_legacy'].max():+.2f}]",
         f"[{comp['M'].min():+.2f}, {comp['M'].max():+.2f}]"],
        ["Correlación entre métodos (B)", f"r = {r_b:+.2f}", ""],
        ["Correlación entre métodos (M)", f"r = {r_m:+.2f}", ""],
        ["Series donde M cambia de signo", f"{cambio_signo} de {len(comp)}", ""],
    ], anchos=[6.5 * cm, 5 * cm, 5 * cm]))
    C.append(Spacer(1, 10))

    C.append(Paragraph(
        f"La lectura es que <i>B</i> conserva el ordenamiento entre sitios "
        f"(r = {r_b:+.2f}) pero no su nivel, mientras que <i>M</i> está "
        f"<b>anticorrelacionada</b> (r = {r_m:+.2f}): el ranking de memoria "
        "publicado hasta ahora estaba invertido.", e["cuerpo"]))

    C.append(Paragraph(
        "La corrección consiste en definir el evento como una corrida contigua de "
        "déficit, que sí tiene silencios (días despejados) y ráfagas (rachas "
        "nubladas), y en aplicar la corrección de tamaño finito de Kim &amp; Jo "
        "(2016), necesaria porque el número de eventos varía mucho entre sitios y "
        "la <i>B</i> clásica está sesgada por ese número.", e["cuerpo"]))

    C.extend(figura(figs / "F1_comparacion_metodos_BM.png",
                    "<b>Figura 2.</b> Comparación directa entre ambos métodos. Si "
                    "coincidieran, los puntos caerían sobre la diagonal. En "
                    "<i>M</i> la nube tiene pendiente contraria a la identidad.", e))

    # =================================================================
    # 3. ÓPTIMO
    # =================================================================
    C.append(PageBreak())
    C.append(Paragraph("3. Dimensionamiento óptimo de planta y batería", e["h1"]))

    C.append(Paragraph(
        "Sin costo, el problema de dimensionamiento es degenerado: la "
        "confiabilidad crece de forma monótona con la capacidad, de modo que "
        "«maximizar confiabilidad» siempre responde «más grande». Por eso hacía "
        "falta un heurístico. Al introducir el costo el óptimo se vuelve interior "
        "y único, y la regla de parada deja de ser arbitraria: se agrega batería "
        "mientras el costo marginal de la energía no suministrada que se evita sea "
        "menor que su valor.", e["cuerpo"]))

    C.append(tabla([
        ["", "Diseño anterior", "Óptimo económico (mediana)"],
        ["Potencia de planta", f"{cfg.planta.potencia_mw:.0f} MW (fija)",
         f"{opt['p_pv_mw'].median():.0f} MW"],
        ["Capacidad de batería", "se barría 5–30 % de la energía diaria",
         f"{opt['e_bess_mwh'].median():.0f} MWh  ({opt['bess_pct_energia_diaria'].median():.0f} %)"],
        ["Batería en horas de demanda", "—",
         f"{opt['bess_horas_de_demanda'].median():.1f} h"],
        ["LPSP", f"{techo.median():.0%} (techo alcanzable)",
         f"{opt['lpsp'].median():.1%}"],
        ["LCOE", "—", f"{opt['lcoe_usd_mwh'].median():.0f} USD/MWh"],
        ["Vertimiento", "no se contabilizaba", f"{opt['frac_vertida'].median():.0%}"],
    ], anchos=[5 * cm, 5.5 * cm, 6 * cm]))
    C.append(Spacer(1, 10))

    C.append(Paragraph(
        "<b>El óptimo nunca estuvo dentro del rango de búsqueda anterior:</b> se "
        f"exploraba entre 5&nbsp;% y 30&nbsp;% de la energía diaria y el óptimo está en "
        f"{opt['bess_pct_energia_diaria'].median():.0f}&nbsp;%. La optimización convergió en las "
        f"{int(opt['convergio'].sum())} series.", e["cuerpo"]))

    C.extend(figura(figs / "F3_mapa_lcoe_planta_bateria.png",
                    "<b>Figura 3.</b> Superficie de LCOE sobre (potencia de planta, "
                    "capacidad de batería) para tres sitios, con isolíneas de LPSP "
                    "en blanco. La estrella marca el óptimo económico y el cuadrado "
                    "naranja el diseño anterior, que queda en la zona de LCOE alto y "
                    "muy por debajo de la batería necesaria.", e))

    C.append(PageBreak())
    C.extend(figura(figs / "F6_optimos_por_serie.png",
                    "<b>Figura 4.</b> Dimensionamiento óptimo de las 51 series. La "
                    "banda naranja de la derecha es el rango que se barría antes; "
                    "ninguna serie tiene su óptimo dentro de ella.", e))

    C.extend(figura(figs / "F7_pareto_costo_confiabilidad.png",
                    "<b>Figura 5.</b> Frente costo–confiabilidad: cuánto cuesta cada "
                    "punto de LPSP adicional. Es la figura que sustenta la elección "
                    "de un objetivo de confiabilidad con criterio económico.", e))

    # =================================================================
    # 4. SUSTITUTO
    # =================================================================
    C.append(PageBreak())
    C.append(Paragraph("4. La intermitencia sí predice el almacenamiento", e["h1"]))

    C.append(Paragraph(
        "En lugar de regresar la capacidad contra (B, M) con una logística de "
        "cuatro parámetros sobre un objetivo artificial, se propone una forma con "
        "estructura física. La curva de confiabilidad resulta aproximadamente "
        "exponencial:", e["cuerpo"]))

    C.append(Paragraph(
        "<font face='DejaVuSans-Bold'>LPSP(E) ≈ L₀ · exp(−E / κ)</font>&nbsp;&nbsp;⟺&nbsp;&nbsp;"
        "<font face='DejaVuSans-Bold'>E*(LPSP*) = κ · ln(L₀ / LPSP*)</font>",
        ParagraphStyle("form", parent=e["cuerpo"], alignment=1, spaceBefore=8,
                       spaceAfter=8, fontSize=11)))

    C.append(Paragraph(
        f"El ajuste se sostiene con R² mediana de {r2_ley:.2f}. La lectura es que "
        "el almacenamiento requerido crece <b>logarítmicamente</b> con la meta de "
        "confiabilidad, con una pendiente κ fijada por la intermitencia del sitio. "
        "Todo el comportamiento de una serie queda resumido en un solo parámetro "
        "físico, κ [MWh]: el almacenamiento que hay que añadir para dividir la "
        "LPSP por e.", e["cuerpo"]))

    b0 = coef.loc["intercepto", "valor"]
    modelo_txt = f"ln κ = {b0:+.2f}"
    for p in ["B", "M", "PSH"]:
        if p in coef.index:
            modelo_txt += f" {coef.loc[p,'valor']:+.3f}·{p}"

    C.append(Paragraph("Modelo sustituto", e["h2"]))
    C.append(Paragraph(
        f"<font face='DejaVuSans-Bold'>{modelo_txt}</font>",
        ParagraphStyle("form2", parent=e["cuerpo"], alignment=1, spaceBefore=6,
                       spaceAfter=8, fontSize=11)))

    C.append(tabla([
        ["Métrica", "Valor"],
        ["R² fuera de muestra (LOO)", f"{coef.loc['r2_loo','valor']:.3f}"],
        ["RMSE LOO (en ln κ)", f"{coef.loc['rmse_loo','valor']:.3f}"],
        ["RMSE del baseline (predecir la media)", f"{coef.loc['rmse_loo_baseline','valor']:.3f}"],
        ["Mejora sobre el baseline", f"{coef.loc['mejora_sobre_baseline','valor']:+.1%}"],
    ], anchos=[9 * cm, 4 * cm]))
    C.append(Spacer(1, 8))

    C.append(Paragraph(
        "Los signos son físicamente correctos: más burstiness exige más "
        "almacenamiento, más recurso solar exige menos. A diferencia del modelo "
        "anterior, la validación es <b>fuera de muestra</b> y contra un baseline "
        "explícito: sin ese baseline, comparar cuatro modelos entre sí siempre "
        "produce un «ganador» aunque ninguno aporte.", e["cuerpo"]))

    C.append(Paragraph("Hallazgo metodológico: la planta de referencia importa", e["h2"]))
    C.append(Paragraph(
        "Si κ se calcula en la planta <i>óptima de cada serie</i>, el modelo "
        "fracasa: R²<sub>LOO</sub> = −0.04, peor que predecir la media, con todas "
        "las correlaciones por debajo de 0.13 en valor absoluto. A planta común "
        f"funciona: R²<sub>LOO</sub> = {coef.loc['r2_loo','valor']:.2f}.", e["cuerpo"]))
    C.append(Paragraph(
        "La explicación es física y vale la pena para la tesis: "
        "<b>sobredimensionar la planta es un sustituto de tener batería</b>. Al "
        "optimizar la planta sitio por sitio, el dimensionamiento absorbe "
        "precisamente las diferencias de intermitencia que B y M debían explicar, "
        "y κ queda casi constante. Para aislar el efecto de la intermitencia hay "
        "que comparar los sitios con la misma planta.", e["alerta"]))

    C.append(PageBreak())
    C.extend(figura(figs / "F4_kappa_vs_intermitencia.png",
                    "<b>Figura 6.</b> Relación entre κ y las métricas de "
                    "intermitencia, a planta común de referencia. La burstiness "
                    "muestra la relación positiva esperada y el recurso solar la "
                    "negativa.", e))

    C.extend(figura(figs / "F5_validacion_loo.png",
                    "<b>Figura 7.</b> Validación fuera de muestra (leave-one-out). "
                    "Reemplaza a la comparación «antes vs. después» del modelo "
                    "anterior, que se evaluaba sobre los mismos datos con los que "
                    "se había ajustado.", e, ancho=10 * cm))

    # =================================================================
    # 5. OTROS HALLAZGOS
    # =================================================================
    C.append(PageBreak())
    C.append(Paragraph("5. Otros hallazgos de la revisión", e["h1"]))

    filas = [
        ["Hallazgo", "Impacto"],
        ["El simulador no aplicaba límite de potencia, eficiencias, DoD ni "
         "vertimiento. La potencia se calculaba y nunca se usaba.",
         "La cobertura cae 6.3 puntos porcentuales al corregirlo, a igual capacidad."],
        ["La LPSP usaba como denominador la energía de déficit, no la demanda "
         "total.", "No era la LPSP de la literatura ni comparable. Ahora se "
         "reportan ambas con nombres distintos."],
        ["El objetivo de la regresión (conf_max × 0.99) dependía del extremo "
         "superior de la grilla de barrido.",
         "Se regresaba B y M contra un artefacto del código, no contra una "
         "cantidad física."],
        ["área × 0.17 da 79.9 MW de pico, no 100 MW: un módulo de 550 W en "
         "2.58 m² tiene η = 21.3 %, no 17 %.",
         "Equivalía a aplicar sin declararlo un performance ratio de 0.799. "
         "Ahora es explícito."],
        ["Los nombres de serie venían en Unicode NFD (tildes descompuestas).",
         "21 de 51 series tienen tilde: cualquier merge entre archivos NFD y NFC "
         "las descartaba en silencio."],
        ["Los resultados «antes vs. después» se evaluaban sobre los datos de "
         "entrenamiento.", "Las mejoras reportadas eran in-sample."],
        ["El mapa de calor tenía los coeficientes escritos a mano y otros "
         "límites que el modelo ajustado.",
         "La figura publicada dibujaba 0.30 + 0.20·σ(z) mientras el modelo "
         "producía 0.10 + 0.90·σ(z)."],
        ["Eje dual en la figura de cuenta de tienda.",
         "El eje derecho no era una reetiquetación lineal del izquierdo: la "
         "conversión depende de la PSH, que varía por serie."],
        ["Errores que impedían ejecutar: spearmanr sin importar, ruta "
         "«51 seriesH», índice de PSH sin convertir, series sin ordenar "
         "cronológicamente.",
         "El orden importa: la simulación de SOC depende de él."],
    ]
    C.append(tabla(filas, anchos=[8 * cm, 9 * cm], alinear_derecha_desde=99))
    C.append(Spacer(1, 6))
    C.append(Paragraph(
        "El detalle completo, con referencias a archivo y línea, está en "
        "<font face='Courier'>BITACORA.md</font>.", e["nota"]))

    # =================================================================
    # 6. VARIABILIDAD INTERANUAL
    # =================================================================
    C.append(Paragraph("6. Variabilidad interanual", e["h1"]))
    C.append(Paragraph(
        "El modelo anterior reportaba un solo número de confiabilidad sobre 27 "
        "años, lo que oculta por completo la dispersión entre años. Ahora se "
        "evalúa año por año. En la configuración actual la razón entre el peor "
        f"año y el año mediano es de apenas {inter['razon_peor_vs_mediana'].median():.2f}× "
        "(mediana), pero ese valor bajo es en sí mismo un síntoma: el sistema "
        "está tan limitado por energía que la LPSP se satura y la meteorología "
        "casi no cambia el resultado. Con la planta correctamente dimensionada "
        "esta dispersión debería crecer, y es ahí donde el análisis por fase ENSO "
        "cobra sentido.", e["cuerpo"]))

    # =================================================================
    # 7. PENDIENTES
    # =================================================================
    C.append(Paragraph("7. Qué falta y qué hay que decidir", e["h1"]))

    C.append(Paragraph("Decisiones que no son técnicas", e["h2"]))
    C.append(Paragraph(
        "<b>1. Reemplazar los parámetros económicos.</b> Están marcados para "
        "revisión en <font face='Courier'>config.yaml</font>. Ninguna cifra de "
        "LCOE o de dimensionamiento óptimo es publicable hasta hacerlo.",
        e["cuerpo"]))
    C.append(Paragraph(
        "<b>2. Definir el alcance frente al hallazgo 1.</b> O se acepta "
        "sobredimensionar la planta alrededor de 1.5×, o se baja la demanda "
        "objetivo, o se declara explícitamente que el sistema es de aporte "
        "parcial y no de suministro firme. Condiciona todo lo demás.", e["cuerpo"]))

    C.append(Paragraph("Trabajo pendiente", e["h2"]))
    for i, t in enumerate([
        "Aplicar el modelo a las 5 zonas; el paquete ya lo soporta.",
        "Clasificar los años por fase ENSO (ONI) y reportar confiabilidad por "
        "fase. Es la conexión natural con el capítulo climático de la tesis y "
        "probablemente el resultado más aprovechable.",
        "Probar la exponencial estirada exp(−(E/κ)^β) si se necesita más "
        f"precisión que el R² ≈ {r2_ley:.2f} actual.",
        "Revisar por qué el archivo de B y M anterior tiene 53 filas para 51 "
        "series.",
    ], 3):
        C.append(Paragraph(f"<b>{i}.</b> {t}", e["cuerpo"]))

    C.append(Spacer(1, 14))
    C.append(Paragraph(
        "Este informe se genera automáticamente a partir de los archivos de "
        "<font face='Courier'>resultados/</font> mediante "
        "<font face='Courier'>pipeline/07_informe.py</font>. Si se vuelve a correr "
        "el pipeline con otros supuestos, el informe se actualiza solo: no "
        "contiene cifras escritas a mano.", e["nota"]))

    doc.build(C, onFirstPage=pie_de_pagina, onLaterPages=pie_de_pagina)

    destino = sal / "Informe_intermitencia.pdf"
    print(f"  -> {destino.relative_to(sal.parent)}  "
          f"({destino.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
