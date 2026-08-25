# Informe de avance — Predicción del Índice ROFEX 20

**Alumno:** Matías Humberto Tibaldo
**Directora:** Fernanda Mendez — **Co-Director:** Rodrigo Del Rosso
**Fecha:** 20 de agosto de 2026

---

## 1. Objetivo del informe

Este documento resume el trabajo realizado hasta la fecha (Nodos 1 a 3 del pipeline)
y las decisiones metodológicas tomadas en el procesamiento de datos, previo a iniciar
la etapa de ingeniería de features (Nodo 4). El objetivo es recibir devolución sobre
estas decisiones antes de que el resto del pipeline (features, modelos, evaluación)
se construya sobre ellas.

## 2. Estado actual del pipeline

| Etapa | Estado | Descripción |
|---|---|---|
| Nodo 1 — Composición histórica | Completo | 27 tickers, 2018 → hoy, con series de divisor y spot oficial del índice |
| Nodo 2 — Series OHLCV | Completo | Ingesta de los 27 componentes desde la API de Primary S.A. |
| Ajuste por splits | Completo | Corrección backward de series OHLCV por splits no ajustados en la API |
| Nodo 3 — Procesamiento | Completo | Retornos, dummies, datasets wide/long, reconstrucción del índice |
| Nodo 4 — Ingeniería de features | **Próximo paso** | Arranca esta semana (ver plan de acción adjunto) |
| Nodos 5+ — Modelos, evaluación | Pendiente | — |

Todo el trabajo está versionado en git y respaldado por registros de decisión en
`docs/decisions/`, que son la fuente primaria para la sección de metodología de la tesis.

## 3. Decisiones metodológicas tomadas — pedido de validación

### 3.1 Ajuste de series OHLCV por splits

Se detectaron, mediante un script de validación (`validate_variation.py`, umbral 30%
de variación diaria close→open), tres categorías de anomalías en las series de Primary S.A.:

- **Splits no ajustados por la API** (confirmados contra investing.com y digrin.com):
  COME (1.7:1 en 2019, 2.2443:1 en 2025), AGRO, MORI.
- **Eventos macroeconómicos genuinos** (no requieren ajuste, se marcan como dummy):
  caída sistémica post-PASO 2019, suba sistémica post-elecciones 2023.
- **Dato sucio puntual**: BBAR 11/06/2019 (apertura anómala corregida manualmente).

Se implementó **ajuste backward** (precio actual como referencia) en
`processing/adjustments.py`, parametrizado desde `config/splits.yaml`. Se definieron
dos enfoques posibles: ajustar solo splits donde el ticker integraba el índice en la
fecha del evento (Enfoque A, adoptado como default) o ajustar toda la serie histórica
del ticker (Enfoque B). **Se usó el Enfoque A.**

Se validó además, inspeccionando visualmente TGSU2 en fechas de dividendos conocidas,
que las series de la API ya vienen ajustadas por dividendos en efectivo (no se
observan discontinuidades). Esta hipótesis quedó confirmada.

**Pedido de validación:** ¿el Enfoque A (ajuste solo dentro del período de membresía
en el índice) es el criterio correcto para los fines de la tesis, o preferirían que se
declare explícitamente como supuesto a discutir en la sección de limitaciones?

### 3.2 Dividendos en acciones (AC) como splits encubiertos

Validado directamente con el equipo que mantiene el índice en Primary S.A.: un
dividendo tipo AC con monto ≥ 1 se trata como split (se multiplican las cantidades
en el índice) en lugar de aplicar la fórmula estándar de ajuste por dividendo. Se
identificó un caso histórico (BYMA, 06/07/2022) donde este criterio no se había
aplicado correctamente en su momento. Un segundo caso (BYMA, split 5:1 del
10/05/2024) no figura en el dataset de dividendos y se resolvió manualmente.

**Pendiente:** solicitar a Primary S.A. el Excel de dividendos en especie que
contendría splits manuales adicionales no registrados en `base.dividendos2.csv`.

### 3.3 Corrección del cambio de base del índice (octubre 2023)

La Guía Metodológica documenta un cambio de base vigente desde el 09/10/2023
(divisor multiplicado por 10, cantidades teóricas divididas por 10). Se detectó que
las *quantities* en los datos de composición se actualizan el 2023-09-29, mientras que
el spot oficial recién refleja el cambio el 2023-10-09 — una brecha de 7 días hábiles
que generaba un error de reconstrucción exacto del 90%. Se corrigió aplicando un
factor ×10 en la capa de procesamiento (no en los datos crudos, que son inmutables
por diseño), acotado a ese rango de fechas.

Resultado: de 14 días con error de reconstrucción > 1%, quedaron 8 días con error
residual de hasta 3.25% (noviembre 2022 y mayo 2024), pendientes de análisis manual.

**Pedido de validación:** ¿corresponde profundizar el análisis de esos 8 días antes
de avanzar a features, o se documentan como limitación conocida y se continúa?

### 3.4 Flag `in_index` en lugar de filtrado por membresía

Se decidió conservar toda la serie histórica de cada ticker (2018→hoy) y marcar con
un flag booleano `in_index` los períodos en que efectivamente integró el RFX20, en
lugar de descartar filas fuera de esos períodos. Razones: preserva información sobre
dinámica de entrada/salida del índice (relevante para features de liquidez), da
flexibilidad a cada modelo para decidir si usa la serie completa o solo el período
activo, y facilita el análisis exploratorio.

## 4. Datos macroeconómicos disponibles

Consolidados en `data/raw/macro/`, con frecuencia diaria salvo IPC (mensual):
Merval, IPC (INDEC), riesgo país, tasa de plazo fijo, y cinco series de tipo
de cambio (oficial, bancos, informal, MEP, CCL).

## 5. Próximos pasos

Se adjunta el plan de acción (`docs/plan_de_accion.md`) con el detalle. En síntesis:
esta semana arranca el Nodo 4 (ingeniería de features), con el objetivo de llegar a
la comparación de modelos y presentación **antes de diciembre de 2026**. Dado el
volumen de trabajo restante, las Fases 3 (estadísticos/ML) y 4 (Deep Learning) del
plan original se ejecutarán en paralelo, y la redacción de la tesis se hace de forma
continua desde ahora — este informe es el primero de una serie de devoluciones
periódicas planificadas (ver sección de checkpoints en el plan de acción).

## 6. Preguntas abiertas para la reunión

1. Validación del Enfoque A de ajuste por splits (sección 3.1)
2. Prioridad del análisis de los 8 días con error residual de reconstrucción (sección 3.3)
3. Disponibilidad del spread de futuros RFX20/ABR26 para features de volatilidad
   implícita (mencionado en el Anexo Fase 3 del plan de trabajo)
4. Confirmación de que el cronograma comprimido (paralelizar Fases 3 y 4) es aceptable
   como enfoque, dado que el objetivo de presentar antes de diciembre se mantiene
