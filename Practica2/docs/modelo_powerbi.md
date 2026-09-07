# Vistas de rol para el modelo tabular

Documenta por que la base de la Practica 1 expone cinco vistas adicionales y como
se deben importar en Power BI.

## El problema

El modelo dimensional referencia `Dim_Fecha` tres veces desde la tabla de hechos,
como fecha de salida, de llegada y de reserva, y `Dim_Aeropuerto` dos veces, como
origen y destino. Es lo que se llama una dimension role-playing y es diseno
correcto: una sola tabla fisica y varias llaves foraneas que definen el papel.

Power BI no trabaja asi. Entre dos tablas admite varias relaciones pero solo una
puede estar activa; las demas quedan inactivas y no filtran nada. Importado tal
cual, el modelo tabular dejaria una sola fecha operativa y las otras dos mudas.

Lo peligroso no es que falle, sino que funcione a medias sin avisar. Un grafico
titulado "ingresos por mes de reserva" mostraria en realidad los ingresos por mes
de salida, y nada en la pantalla delataria el cambio.

## Por que no se resolvio con DAX

La funcion `USERELATIONSHIP` permite activar temporalmente una relacion inactiva,
pero solo dentro de una medida. Un segmentador o el eje de un grafico usan siempre
la relacion activa, sin excepcion. Es decir que con `USERELATIONSHIP` el usuario
del tablero nunca podria filtrar por mes de llegada, que es justo el tipo de
interaccion que se espera de un dashboard. Ademas obligaria a escribir una
variante de cada medida por cada papel, lo que multiplica las oportunidades de
equivocarse.

## Por que no se duplicaron las tablas

Copiar `Dim_Fecha` tres veces como tablas fisicas resolveria el problema de Power
BI a costa de romper el modelo dimensional: tres copias del mismo calendario que
hay que mantener sincronizadas, y un catalogo de aeropuertos por duplicado. El
diseno quedaria peor por acomodarse a una herramienta.

## La solucion

Cinco vistas, una por papel, en `sql/vistas_powerbi.sql`:

```
Dim_Fecha_Salida         Dim_Aeropuerto_Origen
Dim_Fecha_Llegada        Dim_Aeropuerto_Destino
Dim_Fecha_Reserva
```

Cada una es una consulta sobre la dimension original. No copian datos, no ocupan
espacio y cualquier correccion al calendario o al catalogo se refleja en las tres
al instante. Power BI las ve como tablas independientes, de modo que cada papel
obtiene su propia relacion activa y el modelo dimensional en SQL Server queda
intacto.

La llave de cada vista se renombro para que coincida con la columna del hecho a la
que corresponde: `Dim_Fecha_Salida` expone `sk_fecha_salida` y no `sk_fecha`. Con
eso Power BI detecta las cinco relaciones por si solo y no hay que crearlas a
mano.

Las vistas se crean despues de `crear_modelo.sql` y `poblar_dimensiones.sql`,
porque dependen de esas tablas. El script usa `CREATE OR ALTER`, asi que se puede
volver a ejecutar sin borrar nada.

## Que importar en Power BI

Del origen se traen la tabla de hechos, las cinco vistas y las nueve dimensiones
que no tienen papeles multiples:

```
Hecho_Boleto
Dim_Fecha_Salida, Dim_Fecha_Llegada, Dim_Fecha_Reserva
Dim_Aeropuerto_Origen, Dim_Aeropuerto_Destino
Dim_Aerolinea, Dim_Aeronave, Dim_ClaseCabina, Dim_EstadoVuelo,
Dim_CanalVenta, Dim_MetodoPago, Dim_Moneda, Dim_Genero, Dim_Nacionalidad
```

`Dim_Fecha` y `Dim_Aeropuerto` no se importan. Ya llegan a traves de sus vistas, y
traerlas ademas dejaria tablas sueltas sin relacion que solo confunden.

Las quince relaciones son de varios a uno desde `Hecho_Boleto` hacia cada
dimension, con filtro en direccion sencilla. No conviene activar el filtrado
bidireccional: en un esquema estrella no hace falta y puede producir totales
inconsistentes entre visuales.

## Dos detalles del lado de Power BI

Los meses se ordenan alfabeticamente salvo que se indique lo contrario. Hay que
seleccionar `nombre_mes` y usar Ordenar por columna apuntando a `mes`, en cada una
de las tres vistas de fecha.

Las vistas de fecha heredan los dos miembros especiales del calendario, el -1
DESCONOCIDO y el -2 NO APLICA, que tienen la columna `fecha` en blanco. Por eso
Power BI no permite marcarlas como tabla de fechas, cosa que solo hace falta para
funciones de inteligencia de tiempo. Los indicadores de esta practica se arman con
los atributos `anio`, `trimestre`, `mes` y `nombre_mes`, que estan en la vista y no
dependen de esa marca.

## Sobre la fecha de reserva

`Dim_Fecha_Reserva` existe para que el modelo quede completo, pero conviene
conocer su limitacion antes de construir un indicador encima. En 2,211 de los
10,000 registros la fecha de reserva del archivo original es ambigua: las dos
lecturas posibles cumplen la unica regla disponible, que la reserva no sea
posterior a la salida, y la brecha entre ellas tiene una mediana de 89 dias. El
proceso ETL resuelve el empate eligiendo `dd/mm`, que es el formato del resto del
archivo, pero no hay forma de confirmarlo con los datos.

La fecha de salida y la de llegada no tienen ese problema: la duracion del vuelo
las fija con precision de minutos. Las series de tiempo del tablero deberian
construirse sobre la fecha de salida.
