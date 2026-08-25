# Decisión: exploración de diferenciación fraccional (Nodo 4, Etapa 3)

**Fecha:** 25 de agosto de 2026
**Módulo:** `scripts/fractional_diff_exploration.py` (exploratorio, no productivo)

## Contexto

Tarea 4 del plan de acción: "diferenciación fraccional — exploración
acotada, no bloqueante". El objetivo es evaluar si un `d` fraccionario
(entre 0 y 1) logra estacionariedad sobre el log-precio del índice RFX20
conservando más memoria que la diferenciación completa (d=1, equivalente
al log-return que ya se usa como target).

## Método

Fixed-Width Window Fracdiff (FFD), López de Prado — *Advances in Financial
Machine Learning*, cap. 5 — implementado a mano (sin agregar una
dependencia nueva; ver "Alcance" abajo). Pesos `w_0=1, w_k = -w_{k-1}
(d-k+1)/k`, truncados cuando `|w_k| < 1e-5` (ventana fija). Aplicado como
suma ponderada rodante sobre `log(close)` del índice
(`data/features/v1/technical_index.parquet`, 1955 ruedas, 2018-04-03 →
2026-04-17).

Para cada `d` en la grilla [0.00, 1.00] (paso 0.05):

1. Test ADF (`statsmodels`, `adfuller` con `autolag="AIC"`) sobre la serie
   fraccionalmente diferenciada → estacionariedad (p-value < 0.05).
2. Correlación de Pearson con la serie original → memoria conservada.

**Dependencia nueva:** se agregó `statsmodels` (`uv add statsmodels`) para
el test ADF — ya estaba prevista en el stack tecnológico (`CLAUDE.md`) para
los modelos ARIMA/SARIMA de Bloque 2, así que no es una dependencia fuera
de alcance, solo se adelantó su instalación.

## Resultado

| d | Ventana (ruedas) | ADF p-value | Estacionaria | Correlación con original |
|---|---|---|---|---|
| 0.00 | 1 | 0.5218 | No | 1.0000 (trivial) |
| 0.05 – 0.30 | 2275 – 4076 | — | No evaluable | Ventana requerida > 1955 ruedas disponibles |
| **0.35** | **1826** | **0.0165** | **Sí** | **0.5643** |
| 0.40 | 1458 | 0.0057 | Sí | 0.5169 |
| 0.45 | 1163 | 0.0002 | Sí | 0.6518 |
| 0.50 | 927 | 0.0000 | Sí | 0.4638 |
| 0.60 | 590 | 0.0000 | Sí | 0.2712 |
| 0.80 | 228 | ~0 | Sí | 0.1128 |
| 1.00 (= log-return) | 2 | ~0 | Sí | 0.0341 |

**d mínimo estacionario: d = 0.35** — ADF p=0.0165, correlación con la
serie original = 0.5643, ventana de 1826 ruedas (usa casi toda la historia
disponible).

## Lectura del resultado

- Entre d=0.05 y d=0.30 la ventana fija que exige el umbral de corte
  (1e-5) supera las 1955 ruedas disponibles — con este dataset no se puede
  evaluar esa franja baja de `d`. Un umbral más laxo (ej. 1e-4) permitiría
  testearla, pero no hace falta para esta exploración acotada: d=0.35 ya
  da una respuesta clara.
- La correlación **no es monótona** en el tramo 0.35–0.50 (sube de 0.56 a
  0.65 antes de empezar a bajar) — atribuible a cómo cambia la ventana de
  solapamiento válida con cada `d`, no a un error de cómputo (validado:
  `d=1.00` reproduce el comportamiento esperado del log-return puro, con
  correlación casi nula respecto al nivel de precio).
- El hallazgo concreto: fraccionar en d≈0.35 conserva **~16x más
  correlación** con la serie original que la diferenciación completa
  (0.56 vs 0.03) mientras logra estacionariedad. Es una diferencia real,
  pero la correlación absoluta (0.56) es moderada, no contundente — no es
  un resultado que grite "hay que usar esto sí o sí".

## Decisión de alcance

**No se productiviza como feature todavía.** Se mantiene como lo definía
el plan: exploración acotada, no bloqueante. Se retoma si el Track A de
Bloque 2 (ARIMA/SARIMA) lo necesita como input alternativo al log-return
estándar — recién ahí hay un consumidor concreto que justifica la decisión
de productivizarlo.

**Si se retoma:** evaluar en ese momento si conviene migrar de la
implementación manual (O(n·ventana) por `d`, ~1826 multiplicaciones por
punto en el caso ganador — suficientemente rápido para este dataset, pero
no vectorizado) al paquete `fracdiff` de PyPI, que implementa lo mismo con
FFT y es sustancialmente más rápido para barridos de `d` más finos o series
más largas.
