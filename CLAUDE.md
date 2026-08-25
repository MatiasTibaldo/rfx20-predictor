# CLAUDE.md — Proyecto RFX20 Predictor

Contexto de trabajo para Claude Code. Leer antes de generar cualquier código.

---

## Estado del proyecto — junio 2026

### Completado

- Nodo 1: Composición histórica (27 tickers, 2018→hoy) — raw/rfx20_composition.parquet
- Nodo 2: Series OHLCV 27 instrumentos (2018→hoy) — raw/{ticker}\_ohlcv.parquet
- App Streamlit: visualización y validación de datos (app.py)
- Módulo de ajuste por splits: processing/adjustments.py + config/splits.yaml
- **Nodo 3: Módulo processing/ completo**
  - `processing/filter.py` — flag `in_index` por fecha (no se filtran filas, ver docs/decisions/index_membership_flag.md)
  - `processing/cleaner.py` — corrección datos sucios desde splits.yaml (BBAR 2019-06-11: open 260.0 → 145.25)
  - `processing/returns.py` — retornos log y simples, forward returns horizones [1, 3, 5]
  - `processing/dummies.py` — flags is_macro_event, macro_direction
  - `processing/wide_long.py` — datasets long y wide (ohlcv_long.parquet, ohlcv_wide.parquet)
  - `processing/reconstruction.py` — reconstrucción índice + corrección cambio de base oct-2023 (ver docs/decisions/base_change_oct2023.md)
  - `processing/pipeline.py` — orquestador ProcessingPipeline (8 pasos)
  - `processing/runner.py` — entry point para Streamlit pipeline
  - Validación: 14 días con error > 1% reducidos a 8 (máx 3.25%) post-corrección

### Próximo paso

**Nodo 4: Módulo features/ (ingeniería de features) — se construye por etapas**

- **Etapa 1 (completa, agosto 2026):** indicadores técnicos (MA 10/20/50,
  RSI 14, MACD, Bandas de Bollinger) y volatilidad realizada (rolling std de
  log_return, ventanas 10/20/50), calculados sobre los 27 componentes
  (`features/technical.py`, `features/volatility.py`) **y** sobre la propia
  serie del índice RFX20 (`rfx20_spot.parquet`). Incluye además la
  construcción del target del índice (`features/target.py`:
  `log_return_fwd_{1,3,5}` del RFX20, no existía antes). Ver
  `docs/decisions/technical_indicators_scope.md` para el razonamiento
  completo. Orquestado por `features/pipeline.py::FeaturesPipeline`, entry
  point `features/runner.py`. Output: `data/features/v1/technical_components_long.parquet`
  y `data/features/v1/technical_index.parquet` (intermedios — el
  `features_long.parquet` final del plan original se arma en una etapa
  posterior, al sumar macro).
- **Etapa 2 (completa, agosto 2026):** features macro — spreads cambiarios
  (oficial/informal/mep/ccl, sobre `venta`), riesgo país, tasa de plazo
  fijo, BADLAR, TAMAR, IPC con lag de publicación, y tasa implícita + term
  spread de futuros RFX20 (`ingestion/futures.py` + `features/macro.py`).
  Todo alineado por `join_asof(strategy="backward")` sobre el calendario
  del índice (1955 fechas). Ver `docs/decisions/macro_features_etapa2.md`
  (incluye un bug de `full join` + `join_asof` encontrado y corregido) y
  `docs/decisions/futures_implied_rate.md`. Output:
  `data/features/v1/macro.parquet`.
- **Pendiente:** diferenciación fraccional (exploración acotada),
  particionamiento temporal train/val/test (70/15/15) + consolidación en
  `features_long.parquet`.
- Variables dummy ya disponibles: is_macro_event, macro_direction

### Decisiones clave documentadas

- Ver docs/decisions/ para decisiones metodológicas
- Variable objetivo: retornos logarítmicos
- Fuente del índice: spot + reconstruido (para validación cruzada)
- Splits: solo COME requiere ajuste para Enfoque A
- Eventos macro (PASO 2019, elecciones 2023): no ajustar, usar como dummy
- Gaps en datos: consultar caso a caso (no asumir estrategia fija)
- Tests sin prioridad en esta etapa (revisar al llegar a modelos)
- Formato procesado: wide + long persistidos, cada modelo elige
- Flag in_index: conservar toda la serie histórica, marcar membresía con bool (ver docs/decisions/index_membership_flag.md)
- Cambio de base oct-2023: corrección ×10 en capa de procesamiento para 2023-09-29 a 2023-10-06 (ver docs/decisions/base_change_oct2023.md)
- 8 días con error residual (~2-3%) en reconstrucción: pendiente análisis manual (nov-2022, may-2024)

### Estructura de datos

- data/raw/v1/: Parquets crudos por ticker + rfx20_futures.parquet (futuros RFX20, MatbaRofex)
- data/processed/: ohlcv_long.parquet, ohlcv_wide.parquet (Nodo 3, completo)
- data/features/v1/: technical_components_long.parquet, technical_index.parquet
  (Nodo 4 Etapa 1 — indicadores técnicos, volatilidad, target del índice) +
  macro.parquet (Nodo 4 Etapa 2 — spreads, tasas, IPC con lag, futuros).
  Cada uno tiene un .csv hermano (mismo nombre, misma carpeta) para validación
  manual — `DuckDBStore.save_parquet(..., also_csv=True)`, activado en
  `features/pipeline.py`. Parquet sigue siendo la interfaz real entre
  módulos; el CSV es solo una copia de lectura para inspección humana.
- results/: experimentos DuckDB + pipeline_state.json
- config/splits.yaml: splits confirmados y eventos macro
- docs/decisions/: registro de decisiones metodológicas

#### data/raw/macro/ — Variables macroeconómicas disponibles

Todos los archivos tienen fechas en formato `YYYY-MM-DD`.

| Archivo | Columnas | Frecuencia | Rango | Notas |
|---------|----------|------------|-------|-------|
| `i_merval.csv` | date, open, high, low, close | diaria | 2018-01-02 → 2026-07-01 | Índice Merval en ARS |
| `IPC.csv` | date, ipc_pct | mensual | 2018-01-31 → 2026-05-31 | Variación mensual % (INDEC) |
| `riesgo_pais.csv` | date, riesgo_pais | diaria | 2018-01-02 → 2026-07-01 | Puntos básicos (347 → 4.362) |
| `tasa_plazo_fijo.csv` | date, tasa_pf | diaria | 2018-01-02 → 2026-06-30 | TNA % (18.66 → 130.42) |
| `dolar_oficial.csv` | date, compra, venta | diaria | 2018-01-02 → 2026-07-01 | Tipo de cambio oficial BNA |
| `dolar_bancos.csv` | date, compra, venta | diaria | 2018-01-02 → 2026-07-01 | Promedio bancos privados |
| `dolar_informal.csv` | date, compra, venta | diaria | 2018-01-02 → 2026-07-01 | Dólar blue |
| `dolar_mep.csv` | date, compra, venta | diaria | 2018-10-29 → 2026-07-01 | Dólar MEP (compra=venta) |
| `dolar_ccl.csv` | date, compra, venta | diaria | 2018-01-02 → 2026-07-01 | Contado con liquidación (compra=venta) |
| `badlar.csv` | Fecha, Valor BADLAR (%) | diaria | 2018-01-02 → 2026-08-21 | Tasa BADLAR bancos privados. Validada (sin nulls/duplicados, 2 gaps de feriados) |
| `tamar.csv` | Fecha, Valor TAMAR (%) | diaria | 2024-10-01 → 2026-08-21 | Tasa TAMAR (ex-LELIQ). Arranca ~10 meses después de la discontinuación de LELIQ (dic-2023) — gap real de la serie, no error |

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

Layout real (plano en la raíz, sin paquete `src/` — cada nodo del pipeline
es su propio paquete de nivel superior):

```
rfx20-predictor/
├── CLAUDE.md                  # Este archivo
├── README.md
├── pyproject.toml             # Gestionado con uv
├── .python-version
├── app.py                     # Streamlit: monitor de pipeline + validación de datos
│
├── config/                    # Settings (Pydantic) + splits.yaml
├── storage/                   # DuckDBStore: persistencia Parquet + tracking de experimentos
├── ingestion/                 # Nodo 1-2: composición, OHLCV, futuros RFX20
├── processing/                # Nodo 3: limpieza, ajustes, retornos, reconstrucción — completo
├── features/                  # Nodo 4: indicadores técnicos, volatilidad, macro — por etapas
├── models/
│   ├── statistical/           # ARIMA, GARCH — pendiente (Bloque 2)
│   ├── ml/                    # XGBoost, LightGBM, RF, SVM — pendiente
│   └── deep_learning/         # LSTM, GRU, híbridos — pendiente (extra [cpu]/[colab])
├── evaluation/                # Métricas y backtesting — pendiente
│
├── data/
│   ├── raw/                   # Datos crudos, TRACKEADOS en git (irreproducibles)
│   │   ├── v1/                 # OHLCV por ticker + composición + spot + futuros (csv+parquet)
│   │   ├── macro/               # CSVs macroeconómicos (dólares, tasas, IPC, riesgo país)
│   │   └── rfx20_composition/  # Carteras históricas, divisores, dividendos
│   ├── processed/             # Output Nodo 3 (git-ignored, se regenera)
│   └── features/              # Output Nodo 4 (git-ignored, se regenera; parquet + csv hermano)
│
├── results/                   # experiments.duckdb + pipeline_state.json (git-ignored)
├── scripts/                   # Utilidades manuales (validate_variation.py, fetch_rfx20_futures.py)
├── notebooks/                 # Exploración — vacío por ahora, sin estructura fija todavía
├── tests/                     # Tests unitarios (hoy solo ingestion; ver "Decisiones de desarrollo")
└── docs/
    └── decisions/              # Registro de decisiones metodológicas — fuente para la tesis
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
- `ta` para indicadores técnicos (MA, RSI, MACD, Bollinger)

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

| Módulo origen | Módulo destino | Formato de salida                            |
| ------------- | -------------- | -------------------------------------------- |
| ingestion     | features       | Parquet en `data/processed/`                 |
| features      | models         | Vista DuckDB o Parquet en `data/processed/`  |
| models        | evaluation     | Dict con predicciones + metadatos del modelo |
| evaluation    | pipeline       | Dict con métricas estandarizadas             |

---

## Variable objetivo

Retornos logarítmicos: `R_t = ln(P_t / P_{t-1})`
Horizontes principales: t+1 a t+5 días hábiles
Secundario (a evaluar según resultados): t+30, t+45, t+60 días

---

## Decisiones a confirmar (pendientes)

- [x] Librería definitiva para indicadores técnicos → **`ta`** (agosto 2026). Se
  descartó `pandas-ta` porque requiere Python >=3.12 y el proyecto está fijado en
  3.11 (`.python-version`); no se cambia la versión de Python sin consultarlo antes.
  `ta-lib` descartado por requerir compilación de dependencias nativas. Instalado
  con `uv add ta` — ver `pyproject.toml`.
- [x] Fuente concreta de datos macro — archivos CSV en data/raw/macro/ (i_merval, IPC, riesgo_pais, tasa_plazo_fijo, badlar, tamar, dolar × 5)
- [x] Integración de datos macro al pipeline de features (Nodo 4) → **resuelto (Etapa 2, 25 agosto 2026)**,
  ver `features/macro.py` y `docs/decisions/macro_features_etapa2.md`.
- [x] Fuente de datos de eventos corporativos — `base.dividendos2.csv` + `Cartera Historica/`. El Excel de dividendos en especie
  no se persigue más (agosto 2026): impacto en precio inmaterial, ver `docs/decisions/dividends_and_splits.md` sección 4.
- [x] ¿Se usa MLflow u otra herramienta para tracking de experimentos? → **Sí, MLflow** (agosto 2026), instalado (`uv add mlflow`,
  backend local `mlruns/`, sin server). `results/experiments.duckdb` sigue para estado del pipeline y datos; MLflow es
  específicamente para tracking de runs de modelos a partir de Fase 3.
- [x] ¿Git + GitHub/GitLab para control de versiones? → Git ya en uso desde el inicio del repo.
- [x] BADLAR/TAMAR → **resuelto (25 agosto 2026): el alumno sumó `badlar.csv`/`tamar.csv` manualmente** a
  `data/raw/macro/`, sin pasar por `BCRAConnector.fetch()` (que sigue sin implementar). Validados y consumidos
  en Etapa 2 de Nodo 4 (`features/macro.py::load_rates_and_risk`). Ver `docs/decisions/macro_features_etapa2.md`.
- [x] URL de la API pública de futuros RFX20 → **provista por el alumno** (agosto 2026):
  `https://apicem.matbarofex.com.ar/api/v2/closing-prices?product=RFX20&...`. "Volatilidad implícita" se
  reinterpreta como **tasa implícita (`impliedRate`) + term spread de la curva de futuros**, ya que RFX20 no
  tiene mercado de opciones con volumen para calcular una IV real. Ver `docs/decisions/futures_implied_rate.md`.
  Implementación (ingesta + feature) pendiente para la etapa de macro/futuros de Nodo 4.
- [ ] **Nuevo (agosto 2026):** lag de publicación del IPC — resuelto con precisión para dic-2023 a may-2026, aproximado
  para 2018 a nov-2023. Ver `docs/decisions/ipc_publication_lag.md`.

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
