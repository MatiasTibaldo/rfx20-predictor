# Registro consolidado de splits — los 28 componentes del RFX20

**Fecha:** 16 de septiembre de 2026 (actualizado 30 de octubre de 2026 — ver
`docs/decisions/validacion_manual_splits_oct2026.md` para la segunda ronda de
validación manual, Punto 1 del feedback de los directores: 2 splits nuevos
confirmados — COME 2020-08-24 y AGRO 2019-04-29 — y PAMP cerrado como "sin
split material")
**Reemplaza como referencia central a:** `docs/decisions/splits_adjustment.md`,
`docs/decisions/dividends_and_splits.md`, `docs/decisions/ypfd_split_2026.md`,
`docs/decisions/desvios_cronicos_composicion_vs_ohlcv.md` — esos documentos
quedan como registro histórico de cómo se fue encontrando cada cosa (no se
borran), pero para saber el estado actual de un ticker puntual, **esta es
la tabla a consultar**. La fuente de verdad ejecutable sigue siendo
`config/data_corrections.yaml`; esto es la vista legible + el historial de
investigación.

## Cómo leer la tabla

- **Ajustado en origen = Sí** → el feed OHLCV de Primary S.A. ya retroajustó
  retroactivamente toda la serie histórica para ese split (no hay salto
  visible en la fecha del evento). Va en
  `config/data_corrections.yaml::composition_only_splits` — **nunca** en
  `splits:` (aplicarlo ahí duplica el ajuste, ver
  `docs/decisions/doble_ajuste_splits_cronicos.md`).
- **Ajustado en origen = No** → el feed entrega el precio nominal, con un
  salto real y visible en la fecha del split. Va en
  `config/data_corrections.yaml::splits` (`SplitAdjuster` sí debe tocarlo).
- **Sin split conocido** → no se encontró evidencia de ningún split en la
  ventana de datos del proyecto (2018-04-03 → hoy). No requiere entrada en
  ninguna sección.
- **Fuera de ventana** → tuvo un split real, pero antes de que el proyecto
  tenga datos — irrelevante para el ajuste (no se agrega entrada).

## Tabla completa

| ticker | split(s) conocido(s) | ¿ajustado en origen? | fuente | notas |
|---|---|---|---|---|
| AGRO | 2023-11-03, 12:1; **2019-04-29, 1,3333:1 (4:3) — nuevo, 30-oct-2026** | No | validate_variation.py; validación manual (ambos) | fuera del índice en ambas fechas (ingresó 2024-05-02) — Enfoque A no aplica ninguno de los dos por default |
| ALUA | 2015-05-19, 1.12:1 | — | digrin.com | fuera de ventana |
| APBR | 2008, 2:1 | — | seekingalpha.com | fuera de ventana (CEDEAR/ADR de Petrobras) |
| BBAR | 2017-07-03, 1.021:1 | — | digrin.com | fuera de ventana (justo antes del inicio de datos) |
| BMA | — | — | — | **sin split real**: digrin.com reportó 6 eventos de 1.09 en 2023, verificados contra el OHLCV crudo y descartados — son tendencia normal de varios días, no un escalón limpio en una fecha puntual (ver "Falsos positivos" abajo) |
| BYMA | 2022-07-06 (10:1), 2024-05-10 (5:1), 2025-05-25 (2:1) | **Sí** | base.dividendos2.csv + Excel + alumno | `composition_only_splits` |
| CEPU | 2017-02-03, 8:1 | — | digrin.com | fuera de ventana |
| COME | 2019-08-05 (1.7:1), 2025-08-13 (2.2443:1), **2020-08-24 (1.238:1) — nuevo, 30-oct-2026** | No | investing.com + validate_variation.py; validación manual (el 3º) | `splits:`, salto real confirmado en los 3 |
| CRES | — | — | — | **sin split real**: digrin.com reportó 3 eventos chicos (2019-11-11, 2023-05-03, 2023-10-10), verificados y descartados — mismo patrón de falso positivo que BMA |
| CVH | ninguno | — | stockanalysis.com, Yahoo Finance | sin split conocido |
| ECOG | 2025-08-19, 10:1 | **No** | investing.com (tabla dedicada) | `splits:`, salto real confirmado (25.025,0 → 2.475,0); fuera del índice en la fecha |
| EDN | ninguno | — | investing.com (confianza media — macrotrends no se pudo leer directo) | sin split conocido |
| GGAL | ninguno | — | companiesmarketcap.com | sin split conocido |
| IRSA | posible ~1.036:1, 2024-11-29 (ligado a fusión IRSA/IRSA CP) | — | búsqueda combinada, confianza baja-media | **verificado y descartado** (16 sep 2026): ratio real en el OHLCV crudo es -0,78% esa fecha, no el -3,5% esperado — no hay evidencia de split real |
| LOMA | ninguno | — | companiesmarketcap.com | sin split conocido |
| METR | ninguno | — | consenso de fuentes | sin split conocido |
| MIRG | 2026-08-03, 10:1 | **Sí** | alumno (coincide con split YPFD) | `composition_only_splits` |
| MORI | 2018-08-01 (1.8348:1), 2025-09-05 (7.0947:1) | No | validate_variation.py | `splits:`, salto real confirmado |
| PAMP | posibles "4 splits" sin fecha/ratio confirmado (acción local); el ADR "PAM" en NYSE tiene 0 splits | — | búsqueda web, sin fuente confiable | **cerrado sin split material (30-oct-2026)** — sin ningún salto fuera de [0,78;1,28] en 8 años de OHLCV crudo; si los 4 rumoreados son reales, son todos demasiado chicos para requerir corrección |
| SUPV | "1471-por-1464" reportado por Alpha Spread | — | — | descartado como artefacto de parseo, ratio absurdo, no es un split real |
| TECO2 | ninguno | — | Alpha Spread (snippet) | sin split conocido |
| TGNO4 | ninguno | — | Yahoo Finance | sin split conocido |
| TGSU2 | — | — | — | **sin split real**: digrin.com reportó 1.038:1 el 2019-11-11, verificado y descartado — tendencia de varios días, no un escalón limpio |
| TRAN | ninguno | — | digrin.com | sin split conocido |
| TS | 2006-04-27, 5:1 | — | stocksplithistory.com / digrin.com | fuera de ventana |
| TXAR | 2012-03-07, 13:1 | — | digrin.com | fuera de ventana. Nota: se llamó "ERAR" (Siderar) antes de renombrarse — cambio de nombre, no split |
| VALO | ninguno (el "split" de digrin.com, 2017-08-08 ratio "4691000", es un artefacto de parseo) | — | — | ver "Fusión VALO→GFV" abajo — no es un split pero podría requerir tratamiento similar |
| YPFD | 2026-08-03, 10:1 | **Sí** | docs/decisions/ypfd_split_2026.md | `composition_only_splits` |

## Falsos positivos: por qué se descartaron BMA, CRES, TGSU2, IRSA, SUPV

El barrido externo (16 sep 2026) encontró "splits" chicos (ratio 1.01-1.09)
para estos cinco tickers en digrin.com/Alpha Spread. Al cruzarlos contra el
OHLCV crudo del proyecto en la fecha exacta reportada, **ninguno mostró un
escalón limpio aislado** — en cambio, el precio sigue una tendencia
continua de varios días en la misma dirección general, indistinguible del
movimiento normal de mercado (ver ejemplo TGSU2: 123,0 → 108,45 → 100,5 →
102,45 → 98,5 → 92,3 → 93,4 entre el 07 y el 15 de noviembre de 2019 — una
baja gradual, no un salto puntual). Un split real y aislado se ve como
ECOG: 25.025,0 el 18/08 → 2.475,0 el 19/08, sin graduación.

**Conclusión metodológica:** los detectores automáticos de splits chicos
(digrin.com, Alpha Spread) para acciones argentinas de este tamaño
producen falsos positivos con frecuencia — probablemente confunden
volatilidad normal con un "split" cuando el ratio detectado es cercano a
1. **Regla para validar cualquier hallazgo futuro de ratio < 1.15:**
nunca aceptar la fuente externa sola — siempre cruzar contra el OHLCV
crudo en una ventana de ±4 días hábiles alrededor de la fecha reportada;
si el movimiento es gradual (varios días en la misma dirección) y no un
escalón de un día para el otro, descartarlo.

## Pendientes

1. ~~**PAMP**~~ — cerrado 30-oct-2026, ver tabla arriba.
2. **Fusión VALO → GFV** (hallazgo colateral, no es un split): Banco de
   Valores absorbió a su controlante Grupo Financiero Valores S.A.
   (reorganización aprobada por CNV, efectiva 2025-01-01); el ticker
   pasaría de VALO a GFV. Verificado (16 sep 2026): el OHLCV crudo de VALO
   sigue continuo sin discontinuidad a través de esa fecha, y no existe
   ningún archivo `gfv_ohlcv.*` todavía — por ahora no requiere acción,
   pero si en el futuro el feed empieza a reportar bajo "GFV" habrá que
   tratarlo como un evento de continuidad de serie (similar a un cambio de
   nombre, no un split — ver nota de TXAR/ERAR arriba para el precedente).
3. **Salto sistémico sin documentar el 2025-10-27** (hallazgo colateral de
   la validación manual, 30-oct-2026, no es un split): visto en 8 de 28
   tickers (BBAR +31%, BMA +28,6%, CEPU +28,5%, METR +36,1%, SUPV +36,9%,
   TECO2 +28,7%, TGNO4 +35,3%, TRAN +29,5%) — candidato fuerte a nuevo
   `macro_event` (elecciones legislativas de octubre 2025), confirmado por
   el alumno como movimiento de mercado real. Pendiente: agregarlo
   formalmente a `config/data_corrections.yaml::macro_events`.
4. **SUPV 2018-08-24 (-30,8%)** — sin explicar, no visto en ningún otro
   ticker (no sistémico). Confirmado por el alumno como movimiento de
   mercado, no split. Queda sin investigar el motivo puntual.
5. **TXAR 2023-10-23 (-22,8%)** — candidato a reacción de la 1ª vuelta de
   las elecciones presidenciales (22/10/2023), distinta del balotaje de
   noviembre ya documentado. Confirmado por el alumno como movimiento de
   mercado. Pendiente: verificar si afecta a otros tickers esa fecha y
   documentar como `macro_event` si corresponde.
6. **COVID-19, marzo 2020** (YPFD 09 y 18-03, el 16-03 ya identificado
   antes) — pendiente menor ya señalado en `CLAUDE.md`, sigue sin sumarse
   formalmente a `macro_events`.
