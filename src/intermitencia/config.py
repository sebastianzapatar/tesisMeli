"""Carga y validación de la configuración del proyecto.

Un único punto de verdad para rutas y parámetros. Los scripts del
pipeline nunca deben contener números mágicos: todo sale de aquí.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


def raiz_proyecto() -> Path:
    """Devuelve la raíz del proyecto (la carpeta que contiene config.yaml).

    Se resuelve subiendo desde este archivo, así que funciona sin importar
    desde qué directorio se lance el script. Esto elimina el problema de
    que cada script antiguo asumía un working directory distinto.
    """
    aqui = Path(__file__).resolve()
    for padre in aqui.parents:
        if (padre / "config.yaml").is_file():
            return padre
    raise FileNotFoundError(
        "No se encontró config.yaml subiendo desde " f"{aqui}. "
        "¿Se movió el paquete fuera del proyecto?"
    )


@dataclass(frozen=True)
class Rutas:
    series_51: Path
    series_5: Path
    series_ghi_psh: Path
    psh_51: Path
    tienda_5: Path
    salida: Path
    figuras: Path
    cache: Path

    def crear_directorios(self) -> None:
        for d in (self.salida, self.figuras, self.cache):
            d.mkdir(parents=True, exist_ok=True)

    def verificar_entradas(self) -> None:
        """Falla temprano y con un mensaje claro si falta un insumo."""
        faltantes = [
            str(p)
            for p in (self.series_51, self.series_5, self.psh_51, self.tienda_5)
            if not p.is_file()
        ]
        if faltantes:
            raise FileNotFoundError(
                "No se encontraron estos archivos de entrada:\n  - "
                + "\n  - ".join(faltantes)
                + "\n\nRevisa la sección 'rutas' de config.yaml."
            )


@dataclass(frozen=True)
class Planta:
    potencia_mw: float
    performance_ratio: float
    modelo_legacy: bool
    modulo_potencia_w: float
    modulo_ancho_m: float
    modulo_alto_m: float

    @property
    def area_modulo_m2(self) -> float:
        return self.modulo_ancho_m * self.modulo_alto_m

    @property
    def num_modulos(self) -> float:
        return self.potencia_mw * 1e6 / self.modulo_potencia_w

    @property
    def area_total_m2(self) -> float:
        return self.num_modulos * self.area_modulo_m2

    @property
    def eficiencia_modulo_real(self) -> float:
        """Eficiencia que realmente tiene el módulo declarado (W/m2 a STC)."""
        return self.modulo_potencia_w / (1000.0 * self.area_modulo_m2)

    @property
    def factor_legacy_mw_por_wm2(self) -> float:
        """El factor que usaba el código antiguo: area_total * 0.17 / 1e6."""
        return self.area_total_m2 * 0.17 / 1e6


@dataclass(frozen=True)
class Bess:
    duracion_h: float
    limitar_potencia: bool
    eff_carga: float
    eff_descarga: float
    soc_min_frac: float
    soc_max_frac: float
    soc_inicial_frac: float
    autodescarga_frac_h: float

    @property
    def eff_roundtrip(self) -> float:
        return self.eff_carga * self.eff_descarga

    @property
    def fraccion_utilizable(self) -> float:
        return self.soc_max_frac - self.soc_min_frac


@dataclass(frozen=True)
class Barrido:
    pct_min: float
    pct_max: float
    pct_paso: float


@dataclass(frozen=True)
class Intermitencia:
    base_evento: str
    resolucion: str
    umbral_mw: float
    min_eventos: int
    corregir_tamano_finito: bool
    metodo_memory: str


@dataclass(frozen=True)
class Economia:
    tasa_descuento: float
    vida_proyecto_anios: int
    capex_pv_usd_kw: float
    capex_bess_energia_usd_kwh: float
    capex_bess_potencia_usd_kw: float
    opex_pv_usd_kw_anio: float
    opex_bess_usd_kwh_anio: float
    vida_bess_anios: int
    ciclos_vida: int
    voll_usd_mwh: float
    costo_vertimiento_usd_mwh: float


@dataclass(frozen=True)
class Config:
    nombre: str
    semilla: int
    rutas: Rutas
    demanda_mw: float
    planta: Planta
    bess: Bess
    barrido: Barrido
    intermitencia: Intermitencia
    economia: Economia
    objetivos_lpsp: list[float]
    sustituto: dict[str, Any] = field(default_factory=dict)
    crudo: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def cargar(cls, ruta: Path | str | None = None) -> "Config":
        raiz = raiz_proyecto()
        ruta = Path(ruta) if ruta is not None else raiz / "config.yaml"
        with open(ruta, "r", encoding="utf-8") as fh:
            c = yaml.safe_load(fh)

        r = c["rutas"]
        rutas = Rutas(
            series_51=raiz / r["series_51"],
            series_5=raiz / r["series_5"],
            series_ghi_psh=raiz / r["series_ghi_psh"],
            psh_51=raiz / r["psh_51"],
            tienda_5=raiz / r["tienda_5"],
            salida=raiz / r["salida"],
            figuras=raiz / r["figuras"],
            cache=raiz / r["cache"],
        )

        cfg = cls(
            nombre=c["proyecto"]["nombre"],
            semilla=int(c["proyecto"]["semilla"]),
            rutas=rutas,
            demanda_mw=float(c["demanda"]["potencia_mw"]),
            planta=Planta(**c["planta"]),
            bess=Bess(**c["bess"]),
            barrido=Barrido(**c["barrido"]),
            intermitencia=Intermitencia(**c["intermitencia"]),
            economia=Economia(**c["economia"]),
            objetivos_lpsp=[float(x) for x in c["confiabilidad"]["objetivos_lpsp"]],
            sustituto=c.get("sustituto", {}),
            crudo=c,
        )
        cfg.validar()
        return cfg

    def validar(self) -> None:
        """Chequeos baratos que atrapan errores de dedo en el YAML."""
        b = self.bess
        if not 0 < b.eff_carga <= 1 or not 0 < b.eff_descarga <= 1:
            raise ValueError("Las eficiencias del BESS deben estar en (0, 1].")
        if not 0 <= b.soc_min_frac < b.soc_max_frac <= 1:
            raise ValueError(
                f"Ventana de SOC inválida: [{b.soc_min_frac}, {b.soc_max_frac}]."
            )
        if not b.soc_min_frac <= b.soc_inicial_frac <= b.soc_max_frac:
            raise ValueError(
                f"soc_inicial_frac={b.soc_inicial_frac} está fuera de la ventana "
                f"[{b.soc_min_frac}, {b.soc_max_frac}]."
            )
        if b.duracion_h <= 0:
            raise ValueError("bess.duracion_h debe ser > 0.")

        s = self.barrido
        if not 0 < s.pct_min < s.pct_max:
            raise ValueError("Se requiere 0 < barrido.pct_min < barrido.pct_max.")
        if s.pct_paso <= 0:
            raise ValueError("barrido.pct_paso debe ser > 0.")

        i = self.intermitencia
        if i.base_evento not in {"deficit", "excedente"}:
            raise ValueError(
                f"intermitencia.base_evento='{i.base_evento}' no es válido "
                "(usa 'deficit' o 'excedente')."
            )
        if i.resolucion not in {"horaria", "diaria"}:
            raise ValueError(
                f"intermitencia.resolucion='{i.resolucion}' no es válida "
                "(usa 'horaria' o 'diaria')."
            )
        if i.metodo_memory not in {"pearson", "spearman"}:
            raise ValueError(
                f"intermitencia.metodo_memory='{i.metodo_memory}' no es válido."
            )
        if i.min_eventos < 10:
            raise ValueError(
                "intermitencia.min_eventos < 10: la desviación estándar y la "
                "correlación de lag-1 no son estimables de forma confiable."
            )

        e = self.economia
        if not 0 < e.tasa_descuento < 1:
            raise ValueError("economia.tasa_descuento debe estar en (0, 1).")
        if e.vida_proyecto_anios <= 0:
            raise ValueError("economia.vida_proyecto_anios debe ser > 0.")

        if not self.objetivos_lpsp:
            raise ValueError("confiabilidad.objetivos_lpsp no puede estar vacío.")
        if any(not 0 < x < 1 for x in self.objetivos_lpsp):
            raise ValueError("Todos los objetivos_lpsp deben estar en (0, 1).")

    def resumen(self) -> str:
        p, b, e = self.planta, self.bess, self.economia
        return "\n".join(
            [
                f"Proyecto            : {self.nombre}",
                f"Demanda             : {self.demanda_mw:.1f} MW (plana)",
                f"Planta              : {p.potencia_mw:.1f} MW, PR = {p.performance_ratio:.3f}"
                + ("  [MODO LEGACY]" if p.modelo_legacy else ""),
                f"  eficiencia módulo  : {p.eficiencia_modulo_real*100:.1f} % real "
                f"(el código antiguo usaba 17 %)",
                f"BESS                : duración {b.duracion_h:.1f} h, "
                f"round-trip {b.eff_roundtrip*100:.1f} %, "
                f"DoD {b.fraccion_utilizable*100:.0f} %",
                f"  límite de potencia : {'SÍ' if b.limitar_potencia else 'NO'}",
                f"Economía            : WACC {e.tasa_descuento*100:.1f} %, "
                f"{e.vida_proyecto_anios} años, VoLL {e.voll_usd_mwh:.0f} USD/MWh",
            ]
        )
