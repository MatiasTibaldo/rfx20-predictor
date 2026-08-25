# Decisión: Lag de publicación real del IPC (evitar look-ahead bias)

**Fecha:** agosto 2026
**Módulos afectados:** `features/` (Nodo 4, a implementar)
**Archivo fuente:** `data/raw/macro/IPC.csv`

## Contexto

`IPC.csv` registra la variación mensual del IPC con la fecha de **cierre de mes**
(ej. `2024-03-31` para la inflación de marzo de 2024). El INDEC publica ese dato
recién unas dos semanas después del cierre del mes de referencia. Usar la fecha de
cierre como si el dato estuviera disponible ese mismo día introduce look-ahead bias:
el feature "vería" información que el mercado todavía no tenía.

## Fuente

INDEC no expone la fecha de publicación en la API de series de datos.gob.ar (se
verificó: el JSON solo trae fecha de período y metadata del dataset, sin fecha de
difusión por observación). La fuente autorizada es el **"Calendario de difusión"**
semestral que INDEC publica en PDF:

- [Calendario de difusión — 1er semestre 2024](https://www.indec.gob.ar/ftp/cuadros/publicaciones/calendario_1%20sem2024.pdf)
- [Calendario de difusión — 2do semestre 2024](https://www.indec.gob.ar/ftp/cuadros/publicaciones/calendario_2sem2024.pdf)
- [Calendario de difusión — 1er semestre 2025](https://www.indec.gob.ar/ftp/cuadros/publicaciones/calendario_1sem2025.pdf)
- [Calendario de difusión — 2do semestre 2025](https://www.indec.gob.ar/ftp/cuadros/publicaciones/calendario_2sem2025.pdf)
- [Calendario de difusión — 1er semestre 2026](https://www.indec.gob.ar/ftp/cuadros/publicaciones/calendario_1sem2026.pdf)

## Fechas exactas relevadas (mes de referencia → fecha real de publicación)

| Mes de referencia | Fecha de publicación | | Mes de referencia | Fecha de publicación |
|---|---|---|---|---|
| 2023-12 | 2024-01-11 | | 2025-03 | 2025-04-11 |
| 2024-01 | 2024-02-14 | | 2025-04 | 2025-05-14 |
| 2024-02 | 2024-03-12 | | 2025-05 | 2025-06-12 |
| 2024-03 | 2024-04-12 | | 2025-06 | 2025-07-14 |
| 2024-04 | 2024-05-14 | | 2025-07 | 2025-08-13 |
| 2024-05 | 2024-06-13 | | 2025-08 | 2025-09-10 |
| 2024-06 | 2024-07-12 | | 2025-09 | 2025-10-14 |
| 2024-07 | 2024-08-14 | | 2025-10 | 2025-11-12 |
| 2024-08 | 2024-09-11 | | 2025-11 | 2025-12-11 |
| 2024-09 | 2024-10-10 | | 2025-12 | 2026-01-13 |
| 2024-10 | 2024-11-12 | | 2026-01 | 2026-02-10 |
| 2024-11 | 2024-12-11 | | 2026-02 | 2026-03-12 |
| 2024-12 | 2025-01-14 | | 2026-03 | 2026-04-14 |
| 2025-01 | 2025-02-13 | | 2026-04 | 2026-05-14 |
| 2025-02 | 2025-03-14 | | 2026-05 | 2026-06-11 |

Cubre 30 meses consecutivos (diciembre 2023 a mayo 2026), es decir, la totalidad del
tramo de validación y test del particionamiento 70/15/15, y buena parte del tramo
final de entrenamiento.

## Regla para el resto de la serie (2018-01 a 2023-11)

Los calendarios semestrales de INDEC para 2018-2023 no están confirmados en la misma
ruta pública. Sobre los 30 meses relevados, el lag observado entre cierre de mes y
publicación es consistentemente de **10 a 14 días corridos** (promedio ≈ 12), sin un
día de semana fijo. Para el resto de la serie se aplica una **aproximación
documentada**: fecha de disponibilidad = cierre de mes + 12 días corridos, ajustado
al siguiente día hábil si cae en fin de semana. Si en el futuro se consiguen los
calendarios 2018-2023, se reemplaza la aproximación por fechas exactas en esa tabla.

## Implementación prevista (Nodo 4)

En el feature de IPC, la observación de un mes solo debe considerarse disponible
(`forward-fill`) a partir de la fecha de esta tabla (o de la aproximación), nunca
desde la fecha de cierre de mes registrada en `IPC.csv`.
