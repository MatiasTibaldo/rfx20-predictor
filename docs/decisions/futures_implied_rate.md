# Decisión: "volatilidad implícita" se reinterpreta como tasa implícita + term spread

**Fecha:** 24 de agosto de 2026 (decisión) — implementado 25 de agosto de 2026 (Etapa 2 de Nodo 4).
**Módulos afectados:** `ingestion/futures.py`, `features/macro.py`.
**Fuente de datos:** API pública de MatbaRofex (Circular Nro. 889, ver `Circular Nro. 889.pdf` en la raíz del proyecto).

## Contexto

El plan de trabajo original y `docs/plan_de_accion.md` listaban "volatilidad
implícita (futuros RFX20)" como feature macro pendiente, condicionada a
conseguir la URL de una API con histórico de contratos de futuros (no solo
el contrato vigente). El alumno compartió la URL:

```
https://apicem.matbarofex.com.ar/api/v2/closing-prices?product=RFX20&segment=Monedas&type=FUT&excludeEmptyVol=true&from=2020-08-21&to=2026-08-21&page=1&pageSize=50&sortDir=ASC&market=ROFX
```

## Hallazgo

La API devuelve precios de cierre diarios por contrato de futuro
(`symbol` con formato `RFX20{MM}{YYYY}`, ej. `RFX20092020`), paginada
(`totalEntries`/`page`/`pageSize`). Cada fila incluye, entre otros campos,
`impliedRate` — la **tasa de interés implícita** en el precio del futuro
respecto al spot (fórmula tipo F = S × (1+r)^(t/365), calculada por
MatbaRofex a partir del spot del RFX20 y el vencimiento del contrato).

No es una volatilidad implícita: RFX20 no tiene mercado de opciones con
volumen operable, por lo que no existe un instrumento del cual derivar una
IV real (la IV se calcula invirtiendo un modelo de pricing de opciones, no
de futuros). El alumno confirmó que el volumen de operaciones de opciones es
prácticamente nulo, descartando la posibilidad de calcularla igual con datos
ralos.

## Decisión

Se reinterpreta la feature "volatilidad implícita" del plan como:

1. **Tasa implícita** — `impliedRate` del contrato **front-month** (el
   vencimiento más próximo que todavía no expiró) en cada fecha, con rolado
   automático al siguiente contrato al vencer el actual. Proxy del costo de
   fondeo en pesos esperado por el mercado.
2. **Term spread de la curva de futuros** — diferencia entre el `impliedRate`
   (o el precio de cierre) del contrato front-month y el del siguiente
   vencimiento disponible el mismo día. Proxy de expectativas de
   devaluación/inflación a distintos plazos.

Esta reinterpretación se documenta ahora para no perder el contexto de la
decisión, aunque la implementación (script de ingesta paginado + feature de
selección de contrato front-month) se hace en la etapa de macro/futuros de
Nodo 4, no en la Etapa 1 (indicadores técnicos + volatilidad realizada).

## Implementación (Etapa 2 de Nodo 4, 25 ago 2026)

- `ingestion/futures.py::RfxFuturesConnector` — pagina la API completa
  (2608 filas / 39 contratos con el rango 2018-01-01 a 2026-08-21; la
  primera fecha real disponible es 2020-01-02, no hay datos anteriores en
  la API) y persiste en `data/raw/v1/rfx20_futures.parquet` vía
  `scripts/fetch_rfx20_futures.py` (script manual, no un nodo del pipeline).
- `features/macro.py::select_front_month` — selección de contrato
  front-month **sin calendario de vencimientos**: se determina de los
  datos mismos (menor `(año, mes)` entre los símbolos que cotizaron ese
  día), no por rolado basado en una fecha de vencimiento fija. Ver
  `docs/decisions/macro_features_etapa2.md` para el detalle y la
  validación contra el ejemplo 2020-08-21.
- Term spread = `implied_rate_front - implied_rate_next` (null cuando no
  hay un segundo contrato cotizando ese día).
- Output: columnas `implied_rate_front`, `implied_rate_next`,
  `term_spread_futures`, `futures_front_symbol` en
  `data/features/v1/macro.parquet`.

## Nota (5 sep 2026): el gap pre-2020 es de la API, no del mercado

Al preparar el feature set para los modelos de ML de Bloque 2 (Track A) se
precisó el alcance de este gap: el primer contrato disponible en la API es
`RFX20032020`, con primer dato el 2020-01-02. Según documentación adicional
consultada por el alumno (no la circular oficial todavía), los futuros de
RFX20 **empezaron a operarse en agosto de 2019** — la ausencia de datos
anteriores a enero de 2020 es una limitación de cobertura histórica de la
API de MatbaRofex, no evidencia de que el mercado no existiera antes. Esta
distinción debe quedar explícita en la tesis (no es lo mismo "no hay
mercado" que "no hay datos disponibles de un mercado que sí operaba").
Pendiente: anexar la circular que establece la fecha de inicio de
operatoria (agosto 2019) en cuanto el alumno la consiga.

Adicionalmente, dentro del rango sí cubierto por la API (2020-01-02 en
adelante) persisten nulos dispersos en `implied_rate_front`/`implied_rate_next`
en días puntuales sin tasa implícita o sin segundo contrato simultáneo (ver
sección "Front-month..." en `docs/decisions/macro_features_etapa2.md`) — no
es exclusivamente un problema de cobertura pre-2020.
