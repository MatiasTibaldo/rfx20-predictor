# Principio: composición y OHLCV como fuentes independientes — cuándo se pueden mezclar

**Fecha:** 30 de octubre de 2026
**Origen:** Punto 1 del feedback de los directores, surgido al analizar las
variantes de dataset con datos de composición (A-F) y la reconciliación
reconstrucción-vs-spot de `processing/reconstruction.py`.

## El principio

`rfx20_composition.parquet` (quantity/close "de la foto") y
`data/processed/v1/ohlcv_long.parquet` (close ajustado por splits) son **dos
fuentes independientes, cada una internamente consistente dentro de sí
misma** — pero **no están necesariamente expresadas en la misma base entre
sí** para 3 tickers (BYMA, YPFD, MIRG), que tuvieron splits que el feed de
OHLCV retroajustó en vivo pero que `rfx20_composition.parquet` conserva
nominal.

**Esto no es un error de ninguna de las dos fuentes.** Verificado
empíricamente dos veces:

- **Composición es internamente consistente**: los splits puros de BYMA
  (2024-05-10 5:1, 2025-05-25 2:1) muestran `quantity` y `close` moviéndose
  sincronizados dentro de la propia composición — `quantity × close`
  (market value) queda continuo a través de la fecha del split, sin salto.
- **OHLCV es internamente consistente**: validado ticker por ticker contra
  fuentes externas en `docs/decisions/validacion_manual_splits_oct2026.md`
  (28/28 componentes), con 2 splits nuevos corregidos (COME, AGRO).

El desvío aparece **solo cuando se comparan o combinan niveles de precio
absolutos entre las dos fuentes directamente** — ejemplo concreto: el
`close` de YPFD el 2023-06-01 es 5.609,30 en composición pero 560,93 en
OHLCV (exactamente 10x, por el split YPFD 2026 retroajustado en origen por
OHLCV pero no por composición).

## Regla práctica para componer datasets

Antes de construir cualquier dataset que combine composición y OHLCV,
clasificar la operación:

**✅ Seguro — nunca compara niveles absolutos entre fuentes:**
- Calcular `weight` desde composición (`quantity × close / Σ`, todo
  composición contra sí misma).
- Calcular `return` desde OHLCV (`close_t / close_t-1`, todo OHLCV contra
  sí mismo).
- Combinar un ratio de una fuente con un ratio de la otra (ej.: variante A
  del prototipo de composición — `weight` de composición + `return` de
  OHLCV, nunca se tocan los niveles absolutos de ninguna de las dos).
- Usar `quantity` o `close` crudos **de una sola fuente**, sin cruzarlos
  contra la otra (ej.: variantes B/D — crudo, pero 100% composición).

**⚠️ Requiere reconciliar la base primero:**
- Reconstruir el índice como `composición.quantity × OHLCV.close`
  (`processing/reconstruction.py` lo hace así) — mezcla directa de niveles,
  por eso ~99% de los días quedan fuera de tolerancia cuando se valida
  contra el spot oficial.
- Cualquier dataset que combine `quantity` de composición con
  `open/high/low/close/volume` de OHLCV para el mismo ticker (variantes
  E/F del prototipo) — comprometido para BYMA/YPFD/MIRG específicamente.
- Resolución pendiente: implementar el consumidor de
  `config/data_corrections.yaml::composition_only_splits` (hoy documentado
  pero sin código que lo use) para reescalar el lado que corresponda antes
  de cualquier comparación entre fuentes.

## Cierre del cluster marzo-abril 2023

El cluster de ~25% de error encontrado en la re-corrida de la
reconciliación (varios días, marzo-abril 2023) **no es un problema de
datos** — corresponde a un período de alta volatilidad real del mercado
argentino. Cerrado, sin investigación adicional pendiente.
