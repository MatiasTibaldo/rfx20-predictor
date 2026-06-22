# CLAUDE.md — Proyecto RFX20 Predictor

Contexto de trabajo para Claude Code. Leer antes de generar cualquier código.

---

## Estado del proyecto — junio 2026

### Completado
- Nodo 1: Composición histórica (27 tickers, 2018→hoy) — raw/rfx20_composition.parquet
- Nodo 2: Series OHLCV 27 instrumentos (2018→hoy) — raw/{ticker}_ohlcv.parquet
- App Streamlit: visualización y validación de datos (app.py)
- Módulo de ajuste por splits: processing/adjustments.py + config/splits.yaml

### Próximo paso
- Nodo 3: Módulo processing/ completo
  - Filtro por participación en índice (Enfoque A y B)
  - Aplicación de ajustes de splits (COME obligatorio)
  - Cálculo de retornos logarítmicos y simples
  - Dataset wide y long format persistidos en processed/
  - Limpieza de dato sucio BBAR 11/06/2019
  - Variables dummy de rebalanceo y eventos macro
  - Reconstrucción del índice desde OHLCV para validar vs spot

### Decisiones clave documentadas
- Ver docs/decisions/ para decisiones metodológicas
- Variable objetivo: retornos logarítmicos
- Fuente del índice: spot + reconstruido (para validación cruzada)
- Splits: solo COME requiere ajuste para Enfoque A
- Eventos macro (PASO 2019, elecciones 2023): no ajustar, usar como dummy
- Gaps en datos: consultar caso a caso (no asumir estrategia fija)
- Tests sin prioridad en esta etapa (revisar al llegar a modelos)
- Formato procesado: wide + long persistidos, cada modelo elige

### Estructura de datos
- data/raw/v1/: Parquets crudos por ticker
- data/processed/: pendiente (Nodo 3)
- data/features/: pendiente (Nodo 4)
- results/: experimentos DuckDB + pipeline_state.json
- config/splits.yaml: splits confirmados y eventos macro
- docs/decisions/: registro de decisiones metodológicas

---

## Proyecto

Predicción del Índice ROFEX 20 (RFX20) mediante técnicas de ML y Deep Learning.
Tesis de Maestría — Universidad Austral. Alumno: Matías Humberto Tibaldo.

Doble objetivo:
1. Herramienta funcional para uso interno en Primary S.A.
2. Documentación académica a nivel de tesis de maestría

---

## Principio rector: modularidad

Cada módulo debe poder modificarse sin afectar a los subsiguientes.
Interfaces entre módulos: archivos Parquet en `data/` o vistas DuckDB.
**Nunca** acoplar lógica de un módulo con la implementación interna de otro.

---

## Estructura del proyecto

```
rfx20-predictor/
├── CLAUDE.md                  # Este archivo
├── README.md
├── pyproject.toml             # Gestionado con uv
├── .python-version
│
├── data/
│   ├── raw/                   # Datos crudos tal como llegan (solo lectura)
│   │   ├── ohlcv/             # Series RFX20 y acciones componentes
│   │   ├── macro/             # Variables macroeconómicas (BCRA, INDEC, etc.)
│   │   └── corporate/        # Eventos corporativos (dividendos, splits)
│   ├── processed/             # Parquet limpios, listos para features
│   └── rfx20.duckdb           # Base DuckDB con datos procesados y features
│
├── src/
│   └── rfx20/
│       ├── __init__.py
│       ├── ingestion/         # Módulo 1: carga y limpieza de datos crudos
│       ├── features/          # Módulo 2: ingeniería de features
│       ├── models/            # Módulo 3: implementación de modelos
│       │   ├── statistical/   # ARIMA, GARCH
│       │   ├── ml/            # XGBoost, LightGBM, RF, SVM
│       │   └── dl/            # LSTM, GRU, híbridos
│       ├── evaluation/        # Módulo 4: métricas y backtesting
│       └── pipeline/          # Módulo 5: orquestación end-to-end
│
├── notebooks/                 # Exploración y análisis (no producción)
│   ├── 01_eda/
│   ├── 02_features/
│   └── 03_experiments/
│
├── tests/                     # Tests unitarios por módulo
├── docs/                      # Documentación técnica y de tesis
└── outputs/                   # Resultados, gráficos, reportes generados
```

---

## Stack tecnológico

### Entorno
- **Python**: gestionado con `uv` (NO usar pip directamente, NO usar conda)
- Comando para agregar dependencias: `uv add <paquete>`
- Comando para ejecutar scripts: `uv run python src/...`

### Datos
- **Datos crudos**: archivos CSV o Parquet en `data/raw/` (inmutables, no modificar)
- **Procesamiento**: DuckDB como motor principal (`import duckdb`)
- **Formato intermedio**: Parquet (via `pyarrow` o `polars`)
- **NO usar pandas** salvo que una librería lo requiera como input obligatorio.
  En ese caso, convertir al final: `df.to_pandas()` desde polars/duckdb

### Procesamiento y features
- `polars` para transformaciones tabulares en Python
- `duckdb` para queries, joins y agregaciones sobre Parquet
- `ta-lib` o `pandas-ta` para indicadores técnicos (a confirmar)

### Modelos
- Estadísticos: `statsmodels` (ARIMA/SARIMA), `arch` (GARCH)
- ML: `scikit-learn`, `xgboost`, `lightgbm`
- DL: `pytorch` (preferido sobre TensorFlow)
- Optimización de hiperparámetros: `optuna`

### Evaluación y visualización
- Métricas: `scikit-learn` + funciones propias en `src/rfx20/evaluation/`
- Visualización: `plotly` (interactivo) o `matplotlib` (estático para tesis)

---

## Convenciones de código

- **Lenguaje**: Python 3.11+
- **Tipado**: type hints en todas las funciones públicas
- **Docstrings**: formato Google style
- **Linting**: `ruff` (NO flake8, NO black por separado)
- Cada módulo expone una interfaz clara; la lógica interna es privada
- Las funciones de transformación son **puras** cuando es posible (sin side effects)
- Los paths se manejan con `pathlib.Path`, nunca strings hardcodeados

---

## Contratos entre módulos (interfaces)

| Módulo origen | Módulo destino | Formato de salida |
|---|---|---|
| ingestion | features | Parquet en `data/processed/` |
| features | models | Vista DuckDB o Parquet en `data/processed/` |
| models | evaluation | Dict con predicciones + metadatos del modelo |
| evaluation | pipeline | Dict con métricas estandarizadas |

---

## Variable objetivo

Retornos logarítmicos: `R_t = ln(P_t / P_{t-1})`
Horizontes principales: t+1 a t+5 días hábiles
Secundario (a evaluar según resultados): t+30, t+45, t+60 días

---

## Decisiones a confirmar (pendientes)

- [ ] Librería definitiva para indicadores técnicos (`ta-lib` vs `pandas-ta` vs `ta`)
- [ ] Fuente concreta de datos macro (BCRA API, INDEC, scraping, otro)
- [ ] Fuente de datos de eventos corporativos
- [ ] ¿Se usa MLflow u otra herramienta para tracking de experimentos?
- [ ] ¿Git + GitHub/GitLab para control de versiones?

---

## Lo que Claude NO debe hacer sin consultar

- Cambiar el stack tecnológico definido arriba
- Agregar dependencias nuevas sin mencionarlo explícitamente
- Acoplar módulos entre sí fuera de los contratos definidos
- Modificar archivos en `data/raw/` (son inmutables)
- Tomar decisiones sobre el horizonte temporal o la variable objetivo


## Decisiones de desarrollo

### Testing
- Los módulos de ingestion y procesamiento de datos estáticos conocidos 
  NO requieren tests unitarios. Estos datos son normalizados, de procesamiento
  único y raramente se vuelven a ejecutar.
- Prioridad de recursos: producir código funcional y eficiente por sobre 
  cobertura de tests en etapas tempranas.
- EXCEPCIÓN FUTURA: los módulos de modelos, evaluación y pipeline de predicción
  SÍ requerirán tests para garantizar reproducibilidad académica.

### Performance y recursos
- Preferir Polars sobre pandas en todos los módulos nuevos.
- Usar DuckDB para queries sobre datos ya persistidos en Parquet.
- Evitar cargar datasets completos en memoria cuando se puede usar 
  lazy evaluation (pl.scan_csv, pl.lazy()).
- Los estados intermedios validados se persisten en Parquet y no se 
  reprocesan salvo cambio explícito de versión.

### Modularidad
- Cada módulo expone una interfaz clara de entrada/salida.
- Un cambio interno en un módulo no debe requerir cambios en otros módulos.
- Las decisiones de diseño no obvias se documentan con comentarios en el código.

### Flujo de trabajo con Claude
- Consultar antes de tomar decisiones cruciales de arquitectura o metodología.
- Documentar cada decisión importante en CLAUDE.md o en comentarios del código.
- Los commits se hacen por módulo completo y validado, no por archivo.

---

## Decisiones sobre datos

### Ajuste de series OHLCV por splits

**Fecha de decisión:** junio 2026  
**Contexto:** Las series OHLCV descargadas de la API de Primary S.A. 
(plataforma Matriz) presentan comportamiento inconsistente respecto 
al ajuste por splits (desdoblamientos de acciones):

**Hallazgo:** Mediante el script `validate_variation.py` se detectaron 
variaciones diarias mayores al 30% entre el close de un día y el open 
del siguiente. Se validaron manualmente contra fuentes externas 
(investing.com, digrin.com) y se clasificaron en tres categorías:

**Categoría 1 — Splits NO ajustados en la API:**
Confirmados y registrados en `config/splits.yaml`:
- COME: split 1.7:1 del 05/08/2019 (dentro del período en el índice)
- COME: split 2.2443:1 del 13/08/2025 (dentro del período en el índice)
- AGRO: split 12:1 del 03/11/2023 (fuera del período en el índice)
- MORI: split 1.8348:1 del 01/08/2018 (fuera del período en el índice)
- MORI: split 7.0947:1 del 05/09/2025 (fuera del período en el índice)

**Categoría 2 — Eventos macroeconómicos (falsos positivos):**
Movimientos reales del mercado, NO requieren ajuste:
- 12/08/2019: caída sistémica post-PASO (derrota Macri vs Fernández)
  Afectados: BYMA, EDN, GGAL, PAMP, SUPV, TGSU2
- 21/11/2023: suba sistémica post-elecciones presidenciales (victoria Milei)
  Afectados: AGRO, BMA, METR, YPFD
Estos eventos se marcarán como variables dummy en el módulo de features.

**Categoría 3 — Datos sucios:**
- BBAR 11/06/2019: precio de apertura anómalo (260.0 vs close anterior 142.6)
  A corregir en el módulo processing/.

**Decisión de ajuste:**
Se implementó ajuste backward (precio actual como referencia, 
factores aplicados retroactivamente) mediante `processing/adjustments.py`.
Los parámetros de ajuste se leen desde `config/splits.yaml` para 
permitir actualizaciones sin modificar código.

Se adoptaron dos enfoques según el uso posterior:
- **Enfoque A** (default): ajustar solo splits donde el ticker 
  participaba del índice RFX20 en la fecha del split.
  Parámetro: `enforce_index_only=True`
- **Enfoque B**: ajustar todos los splits de la serie completa.
  Parámetro: `enforce_index_only=False`

**Validación empírica:**
La hipótesis de que la API devuelve series ya ajustadas por dividendos 
fue verificada inspeccionando visualmente las series de TGSU2 en las 
fechas de eventos de dividendos registrados en `base.dividendos2.csv` 
(17/09/2018 y 16/04/2019). No se observaron discontinuidades abruptas, 
confirmando que los dividendos ya están incorporados en los precios.

**Implicancia para la tesis:**
El tipo de ajuste aplicado impacta directamente en la interpretación 
de los retornos logarítmicos definidos como variable objetivo. 
Esta decisión debe declararse explícitamente en la sección de 
metodología del trabajo final.

### Dividendos AC como splits encubiertos
- Regla validada con equipo de Primary S.A.: AC con monto >= 1 → tratar como split
- BYMA tiene dos eventos de este tipo: 06/07/2022 (10:1) y 10/05/2024 (5:1)
- Ver docs/decisions/dividends_and_splits.md para detalle completo
- Pendiente: Excel de dividendos en especie con splits manuales