# Decisión: Tratamiento de dividendos y splits en el índice RFX20

**Fecha:** junio 2026  
**Fuente:** Consulta directa con el equipo que mantiene el índice en Primary S.A.  
**Módulos afectados:** `processing/adjustments.py`, `config/splits.yaml`

## Tipos de eventos en base.dividendos2.csv

El archivo `base.dividendos2.csv` registra tres tipos de eventos corporativos:

| Tipo | Descripción | Efecto en precio |
|---|---|---|
| EF | Dividendo en efectivo | Reduce el precio ex-date |
| AC | Dividendo en acciones propias | Reduce el precio (dilución) |
| BONOS | Entrega de bono de la nación | Reduce el precio ex-date |

## Caso especial: dividendos AC (acciones) como splits encubiertos

### Regla aplicada por el equipo del índice
Si el monto del dividendo AC es **mayor o igual a 1**, se trata como 
**split**, no como dividendo. La lógica es:

- Un dividendo AC de monto < 1 significa que recibís menos de 1 acción 
  nueva por cada acción que tenés → efecto de dilución menor
- Un dividendo AC de monto >= 1 significa que recibís 1 o más acciones 
  nuevas por cada acción que tenés → efecto equivalente a un split

En ese caso, en lugar de aplicar la fórmula de ajuste de dividendo 
(que licúa la participación), se multiplica directamente la cantidad 
de acciones del componente en el índice.

### Caso BYMA — evento del 06/07/2022
- Registrado en base.dividendos2.csv como: `BYMA;9;6/7/2022;AC`
- Monto = 9, lo que implica que por cada acción se recibieron 9 nuevas
- Equivale a un split 10:1 (tenés 10 acciones donde antes tenías 1)
- El equipo del índice confirmó que en ese caso se aplicó la fórmula 
  de dividendo en vez de tratar como split, lo que licuó la participación
- A partir de ese evento se estableció la regla: monto AC >= 1 → tratar como split

### Caso BYMA — split del 10/05/2024
- Split de 5:1 **no registrado** en base.dividendos2.csv
- Los splits puros se hacen manualmente y no se registran en ese dataset
- El mismo día hubo dividendo EF de CRES, lo que generó un cambio en 
  la composición del índice ese día
- Tratamiento aplicado: multiplicar las cantidades de BYMA en el índice 
  por 5 para compensar la reducción de precio
- Registrado en un Excel separado de dividendos en especie (no en el CSV)

## Implicancias para el pipeline

### 1. base.dividendos2.csv no es la fuente completa de splits
Los splits puros (como BYMA 2024) no están en ese archivo.
Fuentes complementarias necesarias:
- Excel de dividendos en especie (a solicitar a Primary S.A.)
- Validación externa: investing.com, digrin.com
- Script validate_variation.py para detección empírica

### 2. Eventos AC con monto >= 1 requieren tratamiento especial
En el procesamiento, al leer base.dividendos2.csv:
- AC con monto < 1: tratar como dividendo en acciones (ajuste de precio)
- AC con monto >= 1: tratar como split (multiplicar cantidades en el índice,
  no ajustar precio con fórmula de dividendo)

### 3. La composición histórica ya refleja estos ajustes
Las cantidades en `rfx20_composition.parquet` (provenientes de 
Cartera Historica/) ya tienen las cantidades ajustadas por el equipo 
del índice. No es necesario recalcularlas — son la fuente de verdad 
para la reconstrucción del índice.

### 4. Pendiente: Excel de dividendos en especie
Se debe solicitar a Primary S.A. el Excel de dividendos en especie 
que contiene los splits manuales (como BYMA 2024) no registrados 
en base.dividendos2.csv. Hasta obtenerlo, validate_variation.py 
es la herramienta de detección empírica.

## Eventos AC con monto >= 1 en el dataset actual

| Ticker | Monto | Fecha | Interpretación |
|---|---|---|---|
| BYMA | 9 | 06/07/2022 | Split encubierto 10:1. Aplicado con fórmula incorrecta históricamente. |

Los 8 eventos AC restantes tienen monto < 1 y se tratan como 
dividendos en acciones normales.

## Decisión para el módulo processing/

1. Al procesar base.dividendos2.csv, clasificar AC >= 1 como split_encubierto
2. Agregar estos eventos a config/splits.yaml con tipo: "ac_split"
3. El ajuste de precio para estos casos sigue la misma lógica backward
   que los splits confirmados
4. Documentar en la tesis que la distinción entre split puro y 
   dividendo AC >= 1 es una decisión metodológica validada con 
   el equipo del índice
