# Decisión: Corrección del cambio de base RFX20 — octubre 2023

**Fecha:** junio 2026  
**Fuente:** Análisis de desviaciones entre índice reconstruido y spot oficial  
**Módulos afectados:** `processing/reconstruction.py`, `app.py`

## Contexto

La Guía Metodológica del RFX20 (Anexo: registro de cambios metodológicos) documenta
un "Cambio de Base" con vigencia 9/10/2023:

> "Se fija el valor del divisor del Índice al valor de cierre del día 6/10/2023
> multiplicado por 10."

Este cambio redujo el valor nominal del índice en un factor de 10 (de ~860.000 a
~88.000 puntos). Para mantener la continuidad, las quantities teóricas (QI) de todos
los constituyentes fueron divididas por 10.

## Problema detectado

Al reconstruir el índice como `Σ(close_i × quantity_i)` y comparar contra el spot,
se detectó una desviación exacta del 90% en el período 2023-09-29 a 2023-10-06
(7 días hábiles). El error es exactamente 90.0000% en todos los días — no es
un error de redondeo sino un factor de escala exacto de 10x.

## Causa raíz

Las quantities en `rfx20_composition.parquet` cambian el 2023-09-29 (se adelantan
al cambio de base), pero el spot oficial cambia el 2023-10-09 (fecha efectiva de
la circular). Existe una brecha de 7 días hábiles donde las quantities ya usan
la nueva base (÷10) pero el spot todavía usa la base antigua.

Verificado con GGAL:
- 2023-09-28: quantity = 95.76  (base antigua)
- 2023-09-29: quantity =  9.577 (base nueva, factor ÷10 exacto)

## Alternativas consideradas

1. **Corregir en origen** — Modificar `rfx20_composition.parquet` multiplicando
   las quantities por 10 para ese período. **Descartado**: los archivos en
   `data/raw/` son inmutables por principio de diseño del proyecto.

2. **Corregir en procesamiento** ✅ — Aplicar factor ×10 a `reconstructed_index`
   para el rango 2023-09-29 a 2023-10-06 en la capa de reconstrucción.
   Los datos crudos quedan intactos.

3. **Excluir el período** — Descartar esas fechas del análisis. **Descartado**:
   son fechas válidas de mercado con datos reales.

## Decisión

Aplicar factor de corrección ×10 en la capa de procesamiento para el rango
`[2023-09-29, 2023-10-06]` inclusive. Implementado como constante
`BASE_CHANGE_CORRECTIONS` en `processing/reconstruction.py` y en
`compute_index_reconstruction()` de `app.py`.

## Resultado post-corrección

De 14 días con error > 1%, quedaron 8 días con error máximo de 3.25%.
Esos 8 casos (noviembre 2022 y mayo 2024) se analizarán manualmente
en una etapa posterior — pueden corresponder a dividendos no ajustados
u otras diferencias de fuente.

## Evento único

Según el anexo de cambios metodológicos de la Guía, este es el único cambio
de base registrado en la historia del RFX20. Si ocurriera uno nuevo, agregar
el rango correspondiente a `BASE_CHANGE_CORRECTIONS` en el código.
