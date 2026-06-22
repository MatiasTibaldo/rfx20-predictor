# Decisión: Ajuste de series OHLCV por splits

**Fecha:** junio 2026  
**Módulos afectados:** `ingestion/`, `processing/adjustments.py`  
**Archivo de configuración:** `config/splits.yaml`

## Contexto

Las series OHLCV descargadas de Primary S.A. no tienen un comportamiento 
uniforme respecto al ajuste por splits. Se realizó un proceso de 
validación en tres pasos:

### Paso 1 — Detección automática
Script `validate_variation.py` detecta variaciones diarias entre 
close[t-1] y open[t] mayores al 30% (threshold configurable).
Compara días de negociación consecutivos (no días calendario) para 
evitar falsos negativos en fines de semana.

### Paso 2 — Clasificación manual
Cada alerta fue clasificada consultando:
- `base.dividendos2.csv` (datos internos de Primary S.A.)
- https://es.investing.com (splits históricos)
- https://www.digrin.com (splits históricos alternativos)

### Paso 3 — Decisión por caso
Ver tabla completa en `config/splits.yaml` y sección correspondiente 
en `CLAUDE.md`.

## Lógica de ajuste backward

Para un split de ratio R en fecha D:
- Precios con date >= D: sin cambio (factor = 1.0)
- Precios con date < D: multiplicar por (1/R)

Para múltiples splits, los factores se acumulan multiplicativamente
aplicados en orden descendente por fecha.

**Ejemplo COME:**
- Split 2025-08-13, ratio 2.2443: factor = 0.4456
- Split 2019-08-05, ratio 1.7: factor acumulado = 0.4456 × 0.5882 = 0.2621
- Precios anteriores al 05/08/2019 se multiplican por 0.2621

## Mantenimiento

Si se detectan nuevos splits en el futuro:
1. Ejecutar `validate_variation.py` con `--threshold 30`
2. Validar contra investing.com o digrin.com
3. Agregar entrada en `config/splits.yaml`
4. Re-ejecutar `processing/adjustments.py` con `force=True`

No se requiere modificar código.
