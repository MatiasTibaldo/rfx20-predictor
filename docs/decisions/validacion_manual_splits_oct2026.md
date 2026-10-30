# Validación manual de splits — los 28 componentes (Punto 1 del feedback)

**Fecha:** 30 de octubre de 2026
**Método:** el alumno investiga cada ticker manualmente contra fuentes externas
(no los detectores automáticos de digrin.com/Alpha Spread que ya mostraron
falsos positivos *y* falsos negativos — ver caso COME abajo). Cada hallazgo se
cruza de inmediato contra el OHLCV crudo del proyecto
(`data/raw/v1/{ticker}_ohlcv.parquet`) calculando `close_t/close_{t-1}` en una
ventana de ±7 días alrededor de la fecha reportada, antes de darlo por
confirmado.

Este documento es el registro de trabajo de esta ronda de validación. Una vez
completados los 28, las correcciones confirmadas se aplican a
`config/data_corrections.yaml` y se actualiza
`docs/decisions/registro_splits_componentes.md` (la tabla consolidada) en un
solo pase — no ticker por ticker, para no re-correr el Nodo 3 repetidas veces.

## Progreso

| Ticker | Splits según fuente externa (fecha, ratio) | Ratio observado en OHLCV crudo | Veredicto |
|---|---|---|---|
| **COME** | 2019-08-05 (1,700); 2020-08-24 (1,238); 2025-08-13 (2,000) | 2019-08-05: 0,6108 (esp. 0,588) ✓ · **2020-08-24: 0,8328 (esp. 0,808) ✓ — NUEVO** · 2025-08-13: 0,4570 | **Confirmado split nuevo el 2020-08-24.** El de 2025-08-13 ya estaba documentado con ratio 2,2443 (no 2,0) — el 2,2443 ajusta mejor al dato real (esperado 0,4456 vs. observado 0,4570) que el 2,0 de la fuente externa (esperado 0,50) → mantener 2,2443 salvo que el alumno traiga una fuente primaria más precisa |

| **AGRO** | 2023-11-02 (12:1); 2019-04-28 (1,3333:1 = 4:3) | 2023-11-03: 0,1157 (esp. 0,083) ✓ ya documentado · **2019-04-29: 0,8065 (esp. 0,75) ✓ — NUEVO** (no hay dato el 28, no habil) | **Confirmado split nuevo el 2019-04-28/29**, ratio 4:3. El de 2023-11-03 (12:1) ya estaba documentado, sin cambios. |

| **ALUA** | Sin splits conocidos (dentro de la ventana) | Sin saltos fuera de [0,78, 1,28] en toda la serie | **Confirmado limpio.** |

| **APBR** | Sin splits en la ventana (2008 2:1 fuera de ventana, ya sabido) | Sin saltos 2018-01-02→2019-11-11 (rango corto: deslistó en Argentina y salió del índice) | **Confirmado limpio.** |
| **BBAR** | Sin splits en el período de trabajo | Sin splits — pero 2 saltos no-split detectados: 2019-08-12 (PASO, ya conocido) y **2025-10-27 (+31%, SIN explicar, no es macro_event documentado)** | **Confirmado sin splits.** Anomalía de 2025-10-27 queda aparte como pendiente a investigar (no parece split — sube, no baja). |

| **BMA** | Sin splits en el período de trabajo | Sin splits — mismos 2 saltos no-split que BBAR: 2019-08-12 (PASO) y **2025-10-27 (+28,6%, mismo evento sistémico)** | **Confirmado sin splits.** 2025-10-27 ahora visto en 2 tickers — refuerza hipótesis de evento de mercado sistémico (post-elecciones), no específico de un ticker. |

| **BYMA** | 2022-07-06 (10:1); 2024-05-09 (5:1); 2025-05-25 (2:1) | Sin salto en ninguna de las 3 fechas (ya ajustado en origen) — solo PASO 2019; sin el salto de 2025-10-27 | **Confirmado, coincide con `composition_only_splits` ya documentado** (fecha 2024 desfasada 1 día, irrelevante). |

| **CEPU** | Sin splits en el período de trabajo | Sin splits — PASO 2019 y 2025-10-27 (+28,5%, 3º ticker con este salto) | **Confirmado sin splits.** |

| **CRES** | 2021-03-04 (1,02542:1); 2019-11-10/11 (1,02661:1); 2018-11-07 (1,043:1) | Ninguna muestra escalón limpio aislado — todas son movimiento gradual de varios días (mismo patrón ya documentado de falso positivo para CRES) | **Descartadas las 4** — ratios demasiado chicos (2,5%-4,3%), indistinguibles de volatilidad normal, no justifican corrección. |

| **CVH** | Sin splits en el período de trabajo | Sin splits — PASO 2019 y suba nov-2023 (elección Milei, macro_event ya documentado aunque CVH no estaba en esa lista) | **Confirmado sin splits.** |

| **ECOG** | 2025-08-18 (10:1) | 2025-08-19: ratio 0,0989 (esp. 0,100) ✓ (ya confirmado en la corrida inicial del script) | **Confirmado, coincide con `splits:` ya documentado** (fecha desfasada 1 día, irrelevante). |

| **EDN** | Sin splits en el período de trabajo | Sin splits — PASO 2019 y suba nov-2023 (elección Milei) | **Confirmado sin splits.** |

| **GGAL** | Sin splits registrados | Sin splits — solo PASO 2019 | **Confirmado sin splits.** |

| **IRSA** | Sin datos (el alumno no encontró fuente) | Sin splits — solo PASO 2019. Se mantiene el descarte previo del ~1,036:1 nov-2024 (fusión IRSA/IRSA CP) | **Confirmado sin splits.** |

| **LOMA** | Sin datos | Sin splits — solo PASO 2019 | **Confirmado sin splits.** |

| **METR** | Sin datos | Sin splits — PASO 2019 y 2025-10-27 (+36,1%, 4º ticker) | **Confirmado sin splits.** |

| **MIRG** | Sin datos en el rango de trabajo | Sin salto en 2026-08-03 (ya ajustado en origen) — solo PASO 2019 | **Confirmado, coincide con `composition_only_splits` ya documentado** (10:1, 2026-08-03). |

| **MORI** | 2020-10-22 (1,0476:1); 2018-07-31 (1,8348:1) | 2020-10-22: sube +4,1% (opuesto a lo esperado), días siguientes sin patrón limpio — ruido · 2018-07-31: confirmado antes en esta sesión (caída gradual real, ya documentado) | **Descartado el de 2020-10-22** (ruido, no split real). **Confirmado el de 2018-07-31**, sin cambios respecto a lo ya documentado. |

| **PAMP** | Sin datos (ya era el caso abierto — "4 splits" sin fecha/ratio verificable) | Sin saltos fuera de [0,78,1,28] en 8 años de datos — solo PASO 2019 | **Pendiente cerrado como "sin split material".** Si los 4 rumoreados son reales, son todos demasiado chicos para dejar un escalón visible — mismo tratamiento que las descartadas de CRES: no requieren corrección aunque existan. |

| **SUPV** | Sin datos | Sin split — PASO 2019, 2025-10-27 (5º ticker), y **2018-08-24 (-30,8%, SIN explicar, no visto en otros tickers)** | **Confirmado sin splits.** 2018-08-24 queda pendiente de investigar aparte (posible evento específico de SUPV, no sistémico). |

| **TECO2** | Sin datos | Sin splits — suba nov-2023 (elección Milei) y 2025-10-27 (6º ticker). Sin PASO 2019 | **Confirmado sin splits.** |

| **TGNO4** | Sin datos | Sin splits — PASO 2019, suba nov-2023, 2025-10-27 (7º ticker) | **Confirmado sin splits.** |

| **TGSU2** | 2019-11-10 (1,03849:1) | Mismo evento ya descartado (digrin.com, 2019-11-11, ratio 1,038) — tendencia gradual de varios días, no escalón | **Descartado**, sin cambios respecto a lo ya documentado. |

| **TRAN** | Sin datos | Sin splits — PASO 2019, suba nov-2023, 2025-10-27 (8º ticker) | **Confirmado sin splits.** |

| **TS** | Sin datos (2006 5:1 ya sabido fuera de ventana) | Sin saltos 2018-01-02→2019-10-10 (rango corto, salió del índice temprano) | **Confirmado limpio.** |

| **TXAR** | Sin datos | Sin splits — PASO 2019 y **2023-10-23 (-22,8%, SIN explicar — posible reacción a 1ª vuelta elecciones 22/10/2023, no documentada)** | **Confirmado sin splits.** 2023-10-23 queda pendiente de investigar aparte. |

| **VALO** | Sin datos (artefacto de parseo ya descartado en digrin.com) | Sin splits — solo PASO 2019 | **Confirmado sin splits.** |

| **YPFD** | 2026-08-03 (10:1, ya sabido) | Sin salto en 2026-08-03 (ya ajustado en origen, confirma `composition_only_splits`) — aparecen 2020-03-09 y 2020-03-18 (crash COVID, ya identificados, pendiente menor sumar a `macro_events` junto con 16-03) y suba nov-2023 | **Confirmado, coincide con lo ya documentado.** |

## ✅ Los 28 componentes revisados — resumen ejecutivo

### Correcciones nuevas confirmadas, a aplicar en `config/data_corrections.yaml::splits`

| Ticker | Fecha | Ratio | Evidencia |
|---|---|---|---|
| **COME** | 2020-08-24 | 1,238:1 | Ratio observado 0,8328 (esperado 0,808) |
| **AGRO** | 2019-04-28 | 1,3333:1 (4:3) | Ratio observado 0,8065 el 29/04 (esperado 0,75) |

### Candidatos descartados (ratio demasiado chico, movimiento gradual, no escalón limpio)

CRES ×4 (2021-03-04, 2019-11-10/11, 2018-11-07), MORI 2020-10-22, TGSU2 2019-11-10.

### Todo lo demás confirmado sin cambios

22 de 28 tickers quedaron exactamente como ya estaban documentados (incluye los 3 "ajustados en origen" — BYMA, MIRG, YPFD — re-confirmados desde el lado del OHLCV; AGRO 12:1, COME 1,7:1 y 2,2443:1, ECOG, MORI 1,8348:1 y 7,0947:1 re-confirmados; y 16 tickers sin ningún split real: ALUA, APBR, BBAR, BMA, CEPU, CVH, EDN, GGAL, IRSA, LOMA, METR, PAMP —ahora cerrado, no "abierto"—, SUPV, TECO2, TGNO4, TRAN, TS, TXAR, VALO).

### Hallazgos colaterales (no son splits — pendientes aparte, fuera del alcance de este documento)

1. **2025-10-27, salto sistémico sin documentar**: BBAR (+31%), BMA (+28,6%), CEPU (+28,5%), METR (+36,1%), SUPV (+36,9%), TECO2 (+28,7%), TGNO4 (+35,3%), TRAN (+29,5%) — 8 de 28 tickers. Candidato fuerte a nuevo `macro_event` (elecciones legislativas de octubre 2025). Recomendación: agregarlo a `config/data_corrections.yaml::macro_events` con estos 8 tickers (y verificar si hay más componentes no revisados aún que también muestren el salto).
2. **SUPV 2018-08-24 (-30,8%)**: sin explicar, no sistémico (no aparece en ningún otro ticker). Investigar aparte — posible evento corporativo específico.
3. **TXAR 2023-10-23 (-22,8%)**: candidato a 1ª vuelta de elecciones presidenciales (22/10/2023), no documentada (distinta del balotaje de noviembre). Verificar si afecta a otros tickers esa fecha.
4. **COVID-19 marzo 2020** (YPFD 09/18-03, ya con el 16-03 conocido): pendiente menor ya identificado en `CLAUDE.md`, sigue sin sumarse formalmente a `macro_events`.

## Próximo paso

Aplicar las 2 correcciones de splits confirmadas a `config/data_corrections.yaml::splits`,
re-correr Nodo 3 (`processing.runner`) para regenerar `ohlcv_long.parquet`/`ohlcv_wide.parquet`,
y actualizar `docs/decisions/registro_splits_componentes.md` (tabla consolidada) con todo
lo de este documento. Los 4 hallazgos colaterales quedan como pendientes separados,
a decidir con el alumno si se investigan ahora o más adelante.

## Pendientes menores detectados al pasar (no son splits, revisar después)

- **2025-10-27**: salto fuerte sin documentar en `macro_events`, visto en **BBAR (+31%), BMA (+28,6%), CEPU (+28,5%), METR (+36,1%), SUPV (+36,9%)** — ya con 5 tickers, prácticamente confirmado como evento sistémico (post-elecciones legislativas de octubre 2025).
- **SUPV 2018-08-24 (-30,8%)**: sin explicar, no visto en ningún otro ticker revisado hasta ahora — posible evento específico de SUPV, no sistémico. Investigar aparte.
- **TXAR 2023-10-23 (-22,8%)**: sin explicar, candidato a 1ª vuelta de las elecciones presidenciales (22/10/2023) — distinto del balotaje de noviembre ya documentado como macro_event. Investigar si afecta a más tickers esa fecha.

## Referencia — qué ya decía el barrido automático anterior (16-sep-2026)

Ver `docs/decisions/registro_splits_componentes.md` para no repetir trabajo a
ciegas, pero **no asumir que está completo** — el caso de COME mostró que el
barrido automático puede tener falsos negativos además de los falsos positivos
ya conocidos (BMA, CRES, TGSU2, IRSA, SUPV).
