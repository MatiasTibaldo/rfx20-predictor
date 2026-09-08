# Decisión: Split YPFD 10:1 (agosto 2026) — no requiere ajuste

**Fecha:** agosto 2026
**Módulos afectados:** ninguno (verificación, sin cambios de código)
**Archivo de configuración:** `config/splits.yaml` (sin nueva entrada)

## Contexto

YPFD realizó un split 10:1 con fecha efectiva 2026-08-03. A diferencia de
los splits de COME, AGRO, MORI y BYMA (ver `splits_adjustment.md`), este
evento no requirió agregar una entrada en `config/splits.yaml`.

## Verificación

### Paso 1 — Serie de precios (OHLCV)

`validate_variation.py --instrument YPFD --threshold 15` sobre
`data/raw/v1/ypfd_ohlcv.csv` (histórico hasta 2026-08-25) no detecta
ningún salto overnight atribuible al split. Los únicos dos candidatos
detectados corresponden a eventos macro ya documentados (PASO 2019-08-12,
elecciones 2023-11-21). La API de Primary S.A. (Matriz) entrega la serie
de YPFD ya ajustada por el split — mismo comportamiento confirmado
previamente para dividendos (TGSU2, ver `splits_adjustment.md`).

### Paso 2 — Composición del índice (cantidades vigentes)

Inspección de `data/raw/rfx20_composition/Cartera Historica/` alrededor
de la fecha del split:

| Fecha | cantidades_vigentes | close |
|---|---|---|
| 2026-07-31 | 1.250995 | 82.900,0 |
| 2026-08-03 | 12.51632 | 8.105,0 |

`cantidades_vigentes` sube ×10.006 el mismo día hábil en que el precio
cae ÷~10.2 — consistente con el split 10:1, y ambos ajustes ocurren el
mismo día en la fuente. El producto `cantidad × close` (participación en
`Σ(close_i × cantidad_i)`, ver `processing/reconstruction.py`) pasa de
~103.707 a ~101.445, una variación de -2,2% en línea con el movimiento
normal de mercado, sin discontinuidad artificial.

## Decisión

No se agrega entrada en `config/splits.yaml` ni se modifica
`processing/adjustments.py` para YPFD. Tanto el precio como la
composición del índice ya vienen resueltos en la fuente (PMY/Matriz),
de forma sincronizada, por lo que la reconstrucción del índice
(`processing/reconstruction.py`) no requiere corrección para este evento.

## Mantenimiento

Si se detecta en el futuro un split de un componente del RFX20 con
comportamiento similar (precio ajustado en origen), verificar igualmente
la serie de `cantidades_vigentes` en `Cartera Historica/` alrededor de la
fecha del evento antes de descartar la necesidad de ajuste — la
consistencia entre ambas series no está garantizada para todos los
instrumentos ni todos los proveedores de datos.
