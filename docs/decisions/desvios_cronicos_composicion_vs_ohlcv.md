# Desvíos crónicos composición-vs-OHLCV por splits futuros (YPFD, BYMA, MIRG)

**Fecha:** 16 de septiembre de 2026
**Origen:** encontrado al investigar `docs/decisions/sept2019_composicion_corrupta.md`
(sección 5), extendido y consolidado acá. Suma formalmente el split de
MIRG y YPFD a `config/data_corrections.yaml::splits`, y documenta un
impacto concreto no corregido en `app.py`.

## El mecanismo

`data/raw/v1/*_ohlcv.parquet` viene de un feed en vivo (Matriz/Primary
S.A.) que, al refrescarse, **reajusta retroactivamente toda la serie
histórica** cada vez que un ticker hace un split — incluso para fechas muy
anteriores al evento. `rfx20_composition.parquet`, en cambio, se arma a
partir de snapshots congelados (`Cartera Historica/cartera_historica_*.csv`,
"la foto" del día), que nunca se retocan.

Consecuencia: para cualquier ticker con un split **posterior** a la fecha
que se esté mirando, `close` de composición (nominal, de la foto) queda
por encima de `close` de OHLCV (ya ajustado hacia adelante), por el factor
acumulado de todos los splits futuros documentados. No es un error de
ningún lado — son dos convenciones de ajuste distintas, consistentes cada
una consigo misma, pero no comparables directamente sin reescalar.

## Los tres tickers confirmados

| ticker | ratio | vigencia del desvío | causa |
|---|---|---|---|
| YPFD | ×10 constante | toda la historia pre-2026-08-03 (1.964 filas) | split 10:1, 2026-08-03 |
| MIRG | ×10 constante | 2020-01-02 → 2023-12-29 (972 filas — única ventana en que integró el índice) | split 10:1, 2026-08-03 (mismo día que YPFD, confirmado, no es coincidencia espuria) |
| BYMA | escalones: ×100 / ×10 / ×2 / ×1 | toda la historia, factor decrece en cada split | 3 splits acumulados: 10:1 (2022-07-06), 5:1 (2024-05-10), 2:1 (2025-05-25) |

Tabla completa de escalones de BYMA:

| período | ratio |
|---|---:|
| antes de 2022-07-06 | 100 |
| 2022-07-07 → 2024-05-09 | 10 |
| 2024-05-13 → 2025-05-23 | 2 |
| desde 2025-05-26 | 1 |

Ejemplos de filas (ver conversación de origen para el detalle completo):

| date | ticker | close (composición) | close_ohlcv (API) | ratio |
|---|---|---:|---:|---:|
| 2019-01-15 | YPFD | 532,35 | 53,20 | 10,01 |
| 2023-06-01 | YPFD | 5.609,30 | 560,93 | 10,00 |
| 2020-01-15 | BYMA | 290,00 | 2,91 | 99,66 |
| 2023-01-16 | BYMA | 276,00 | 27,60 | 10,00 |
| 2024-08-01 | BYMA | 310,00 | 155,00 | 2,00 |
| 2022-06-01 | MIRG | 3.444,00 | 344,40 | 10,00 |

MIRG: el split (2026-08-03) afecta retroactivamente toda su serie OHLCV
(2018-2026, sin salto visible alrededor del evento — mismo mecanismo de
feed ya ajustado), pero el desvío contra composición solo es **observable**
en la ventana 2020-2023, porque es la única donde existe el dato "de la
foto" para comparar. Fuera de esa ventana el efecto sigue existiendo, pero
no hay con qué contrastarlo.

Barrido completo de toda la historia (2018-2026, los 28 tickers): ningún
otro ticker muestra este patrón crónico. Los 105 días de desvío menor
restantes caen todos dentro de ventanas ya explicadas — el evento de
sep-2019 (corregido vía `dirty_data`/`composition_price_corrections`) y un
cluster menor de 2024-05-13→17 (ruido de timing coincidente con el split
de BYMA de esa semana, pendiente #4 de `sept2019_composicion_corrupta.md`,
magnitud mucho menor — no investigado a fondo).

## Corrección aplicada

Se agregaron entradas de split para BYMA (ya existían), YPFD y MIRG en
`config/data_corrections.yaml::composition_only_splits` — **no** en
`splits:`. Ver `docs/decisions/doble_ajuste_splits_cronicos.md` para por
qué: la primera versión de este fix puso las tres en `splits:`, que
también consume `processing/pipeline.py` (Nodo 3) para ajustar el OHLCV
crudo de cada ticker — eso duplicó el ajuste sobre BYMA, cuyo OHLCV crudo
ya viene retroajustado por el feed en vivo. `composition_only_splits` es
una sección separada que `SplitAdjuster` no toca; queda disponible para
cuando se implemente el reescalado genérico de composición (ver abajo).

```yaml
composition_only_splits:
  - ticker: MIRG
    date: "2026-08-03"
    ratio: 10.0
    in_index: false   # ya había salido del índice (dic-2023) para la fecha del split

  - ticker: YPFD
    date: "2026-08-03"
    ratio: 10.0
    in_index: true    # sigue en el índice
```

`docs/decisions/ypfd_split_2026.md` quedó con una nota de actualización —
su conclusión original ("no requiere entrada en `data_corrections.yaml`")
respondía si la *transición* generaba una discontinuidad artificial (no:
esa verificación sigue siendo válida), no si composición y OHLCV son
comparables en fechas lejanas al split (no lo son).

## Impacto encontrado, todavía sin corregir

**`app.py::fig_weight_history`** (gráfico "Peso histórico de componentes",
pestaña Índice RFX20 en Streamlit) usa `rfx20_composition.parquet` **sin**
aplicar ninguna corrección — a diferencia de
`compute_index_reconstruction()`, que sí aplica
`apply_composition_price_corrections()` (pero esa función solo cubre los
100 valores puntuales de sep-2019, no este patrón crónico). Resultado:
el gráfico muestra a BYMA con hasta **100x** su peso real antes de 2022,
YPFD con **10x** su peso real en casi toda su historia, y MIRG con **10x**
su peso real en 2020-2023.

**Pendiente:** generalizar la corrección. A diferencia de sep-2019 (donde
el precio de composición estaba objetivamente mal y la corrección fue una
lista de valores puntuales), acá el `close` de composición no está mal —
es nominal y consistente consigo mismo; el problema es compararlo con
OHLCV sin reescalar. La función apropiada no es una lista de overrides
sino un reescalado genérico: para un ticker/fecha dado, multiplicar
`close` de composición por el producto de `1/ratio` de todos los splits
de ese ticker con `date > fecha_de_la_fila` (ya documentados en
`composition_only_splits:`) — reutilizando la misma lógica de factor acumulado que
`SplitAdjuster.adjust_series`, pero en la dirección inversa (splits
futuros, no pasados). Falta decidir dónde vive esa función (¿nuevo método
en `SplitAdjuster`? ¿en `processing/cleaner.py` junto a
`apply_composition_price_corrections`?) y aplicarla en
`fig_weight_history` y cualquier otro consumidor directo de
`rfx20_composition.parquet`.
