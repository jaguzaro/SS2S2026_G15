# Linea base de validacion

Valores que el tablero debe reproducir, extraidos de VuelosDW despues de una
reconstruccion completa. Sirven para dos cosas: comprobar que cada medida DAX
quedo bien escrita, y detectar una relacion mal armada antes de construir
visuales encima de ella.

Un numero que no cuadre casi siempre significa una de tres cosas: la relacion
apunta a la columna equivocada, la medida suma `precio_boleto` en lugar de
`precio_boleto_usd`, o un filtro de contexto esta dejando fuera filas que
deberia contar.

## Medidas sin ningun filtro aplicado

Estos son los valores con el modelo completo, sin segmentadores activos.

| Medida | Valor esperado |
|---|---|
| Boletos Vendidos | 10,000 |
| Ingreso Total USD | 770,024.71 |
| Ticket Promedio USD | 77.00 |
| Boletos Puntuales | 7,278 |
| % Puntualidad | 72.78 % |
| % Cancelacion | 5.60 % |
| Retraso Promedio Min | 124.93 |
| Boletos sin Nacionalidad | 209 |

El conteo de boletos es la primera comprobacion y la mas importante. Si no da
exactamente 10,000, algo se perdio al importar o hay una relacion que esta
filtrando filas de mas.

## Por anio de salida

| Anio | Boletos | Ingreso USD | % Puntualidad |
|---|---|---|---|
| 2024 | 4,927 | 385,334.71 | 73.19 % |
| 2025 | 5,073 | 384,690.00 | 72.38 % |

Con esto se validan las medidas de anio contra anio. Puesta en 2025,
`Ingreso Anio Anterior` debe dar 385,334.71 y `% Crecimiento Ingreso` debe dar
-0.17 %. Es una caida leve pese a que 2025 vendio mas boletos, porque el ticket
promedio bajo.

En 2024 las dos medidas quedan en blanco, que es lo correcto: no hay datos de
2023 con que comparar.

## Puntualidad por aerolinea y semaforo

Es la tabla que sostiene el KPI. Con la meta en 73 % y la alerta en 72 %, el
semaforo reparte las doce aerolineas en tres grupos.

| Aerolinea | Boletos | % Puntualidad | Semaforo |
|---|---|---|---|
| JetBlue | 853 | 75.73 % | verde |
| Delta | 814 | 73.46 % | verde |
| Copa Airlines | 888 | 73.42 % | verde |
| LATAM | 803 | 73.35 % | verde |
| Ryanair | 850 | 73.18 % | verde |
| Aeromexico | 772 | 72.80 % | amarillo |
| British Airways | 829 | 72.62 % | amarillo |
| Iberia | 867 | 72.55 % | amarillo |
| United | 797 | 71.89 % | rojo |
| American Airlines | 824 | 71.84 % | rojo |
| Avianca | 835 | 71.38 % | rojo |
| Southwest | 868 | 71.08 % | rojo |

Los umbrales salen de la distribucion real y no de numeros redondos elegidos al
azar. La puntualidad va de 71.08 % a 75.73 %, un rango estrecho, asi que una meta
en 75 % dejaria once aerolineas en el mismo color y el semaforo no distinguiria
nada. Con 73 y 72 el reparto queda en cinco, tres y cuatro.

## Top cinco destinos

| Destino | Ciudad | Boletos |
|---|---|---|
| SAP | San Pedro Sula | 701 |
| CUN | Cancun | 699 |
| BCN | Barcelona | 696 |
| BOG | Bogota | 696 |
| HAV | La Habana | 693 |

Barcelona y Bogota empatan en 696, asi que el orden entre ambas puede variar
segun como desempate Power BI. No es un error.

Este visual usa `Dim_Aeropuerto_Destino`. Si los numeros salen distintos, lo mas
probable es que este conectado a `Dim_Aeropuerto_Origen` por error: son dos
vistas sobre la misma tabla y se confunden con facilidad.

## Ruta mas transitada

Miami a La Habana, con 76 boletos y 5,621.97 USD de ingreso. Necesita las dos
vistas de aeropuerto en el mismo visual, una como origen y otra como destino, asi
que es la comprobacion de que las dos relaciones quedaron bien.

## Clase de cabina

| Clase | Boletos | Ingreso USD |
|---|---|---|
| Economica | 7,866 | 499,766.74 |
| Economica Premium | 974 | 87,062.70 |
| Ejecutiva | 956 | 137,327.10 |
| Primera Clase | 204 | 45,868.17 |

Los cuatro ingresos suman 770,024.71, el total general. Si un desglose no suma el
total, hay filas que se estan quedando fuera de alguna categoria.

## Genero

| Genero | Boletos |
|---|---|
| Masculino | 4,912 |
| Femenino | 4,698 |
| No binario | 390 |

Suman 10,000 y ninguno cae en DESCONOCIDO, porque el ETL homologo las doce
variantes del archivo a estos tres codigos sin dejar ninguna sin mapear.

## Ausencias que deben aparecer en el tablero

Hay tres categorias que van a mostrarse en los visuales y no son errores.

Nacionalidad tiene 209 boletos en DESCONOCIDO y canal de venta tiene 144. Son
datos que el archivo original no registro.

Fecha de llegada tiene 560 boletos en NO APLICA. Son los vuelos cancelados, que
no tienen hora de llegada porque nunca aterrizaron. Es distinto de desconocer el
dato, y por eso el modelo usa un miembro aparte.

Lo que no se debe hacer es ocultarlos en un visual y mostrarlos en otro: los
porcentajes dejarian de cuadrar entre paginas del mismo tablero.

## Como reproducir esta linea base

Desde la carpeta `Practica1`, con SQL Server corriendo:

```
sqlcmd -S localhost -E -d VuelosDW -i sql\consultas_analiticas.sql
```

Las cinco primeras consultas validan la carga y las ocho siguientes producen los
indicadores. Si esos numeros cambian, esta linea base queda obsoleta y hay que
regenerarla antes de comparar nada contra el tablero.
