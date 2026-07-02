# Decisión: Flag in_index en lugar de filtro por membresía

**Fecha:** junio 2026  
**Módulos afectados:** `processing/filter.py`, `processing/pipeline.py`

## Contexto

Cada ticker en el dataset OHLCV tiene datos para toda la serie temporal
(2018 a la fecha), pero solo participó del índice RFX20 durante ciertos
períodos. La composición cambia cuatrimestralmente según criterios de
liquidez definidos en la Guía Metodológica.

## Alternativas consideradas

1. **Filtrar filas** — Mantener solo las filas donde el ticker era
   componente del índice. Dataset más chico y sin ambigüedad.

2. **Flag booleano `in_index`** ✅ — Conservar toda la serie y marcar
   cada fila con `in_index = True/False`.

## Decisión: Flag booleano

Se adoptó el enfoque de flag por las siguientes razones:

- **Información para modelos**: la dinámica de entrada y salida del índice
  refleja liquidez y capitalización de mercado. Un modelo puede aprender
  que un ticker que "vuelve" al índice tiene características distintas
  a uno que debuta.

- **Flexibilidad**: cada modelo puede decidir si usar toda la serie
  (`df`) o solo el período activo (`df.filter(pl.col("in_index"))`).
  La decisión de filtrar queda en manos del módulo de features/modelos,
  no del procesamiento.

- **Trazabilidad**: mantener toda la serie facilita el análisis exploratorio
  y la detección de anomalías en períodos fuera del índice.

## Implicancia para modelos

Los modelos que usen series individuales de tickers deben documentar
explícitamente si entrenan sobre la serie completa o solo sobre el
período `in_index = True`. Esta decisión impacta en la interpretación
de los resultados y debe declararse en la sección de metodología
de la tesis.
