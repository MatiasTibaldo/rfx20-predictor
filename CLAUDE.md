# CLAUDE.md — Proyecto RFX20 Predictor

Contexto de trabajo para Claude Code. Leer antes de generar cualquier código.

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