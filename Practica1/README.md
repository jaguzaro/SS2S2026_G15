# Practica 1: ETL con Python y modelo dimensional en SQL Server

Curso: Seminario de Sistemas 2
Grupo: SS2S2026_G15
Entorno: Windows PowerShell, Python 3.10 o superior, Microsoft SQL Server

Este proyecto toma un archivo crudo de registros de aviacion comercial, lo limpia
y lo carga en un modelo dimensional en SQL Server desde el cual se responden
preguntas de operacion y de negocio mediante consultas analiticas.

## El problema

`dataset_vuelos_crudo.csv` trae 10,000 registros y 26 columnas donde cada fila es
el boleto de un pasajero en un vuelo. Los datos vienen sucios: los nombres de
aerolinea aparecen con veintitres grafias distintas para doce aerolineas, los
codigos de aeropuerto estan mezclados en mayuscula y minuscula, el genero del
pasajero tiene doce variantes para tres valores reales, los precios alternan coma
y punto decimal, y las fechas estan escritas en dos formatos incompatibles.

El proceso ETL absorbe todo eso sin perder un solo registro.

## Estructura del repositorio

```text
SS2S2026_G15/
└── Practica1/
    ├── docs/
    │   ├── modelo.md                    Documentacion tecnica del modelo
    │   └── 798_Practica_1_2S2026.pdf    Enunciado de la practica
    ├── sql/
    │   ├── crear_modelo.sql             DDL: base de datos y las doce tablas
    │   ├── poblar_dimensiones.sql       Catalogos de las once dimensiones
    │   └── consultas_analiticas.sql     Validaciones e indicadores
    ├── src/
    │   ├── etl.py                       Proceso ETL completo
    │   ├── dataset_vuelos_crudo.csv     Fuente, 10,000 registros
    │   ├── test_connection.py           Prueba de conexion con LocalDB
    │   └── test_sql.py                  Prueba de conexion con la instancia
    ├── README.md
    ├── requirements.txt
    └── .gitignore
```

## El modelo

Es un esquema estrella. `Hecho_Boleto` al centro, con grano de un boleto por
registro del archivo, rodeada de once dimensiones sin normalizar: fecha,
aerolinea, aeropuerto, aeronave, clase de cabina, estado del vuelo, canal de
venta, metodo de pago, moneda, genero y nacionalidad.

Dos dimensiones cumplen mas de un papel. `Dim_Aeropuerto` se referencia como
origen y como destino, y `Dim_Fecha` como salida, llegada y reserva. Cada una es
una sola tabla fisica y son las llaves foraneas las que definen el papel.

No existe una dimension de pasajero. El campo `passenger_id` tiene 10,000 valores
distintos en 10,000 registros, asi que esa tabla quedaria en relacion uno a uno
con el hecho sin aportar capacidad de analisis. En su lugar el genero y la
nacionalidad son dimensiones propias, la edad es un atributo del hecho y el
identificador del pasajero queda como dimension degenerada.

El diagrama completo y la justificacion de cada decision estan en
[docs/modelo.md](docs/modelo.md).

## El proceso ETL

La extraccion lee el archivo completo en memoria, que a 1.9 MB no necesita
particionarse, y lo hace con todas las columnas como texto. Dejar que pandas
infiera los tipos corrompe la columna de precio, donde 930 registros usan coma
decimal.

La transformacion homologa cada columna contra el catalogo que le corresponde.
Los nombres de aerolinea se descartan porque el codigo IATA ya identifica a cada
una sin ambiguedad. Los aeropuertos pasan a mayuscula. Las doce variantes de
genero se reducen a tres codigos. Los precios cambian la coma por punto.

El tratamiento de los datos que faltan merece parrafo aparte, porque no todos
faltan por la misma razon. Una nacionalidad vacia es un dato que existe y no se
conoce, y va al miembro DESCONOCIDO de su dimension junto con los 144 canales de
venta sin registrar. La hora de llegada de un vuelo cancelado es otra cosa: ese
vuelo nunca aterrizo, asi que no hay hora que conocer, y va al miembro NO APLICA.
La consulta V2 cuenta las dos ausencias en columnas separadas.

En las medidas el criterio es el mismo aunque no haya dimension de por medio. La
edad queda en NULL cuando el archivo la trae vacia y nunca en cero, porque hay 57
pasajeros cuya edad si es cero. El retraso queda en NULL en los 560 cancelados y
nunca en cero, porque hay 7,470 vuelos con retraso cero de verdad y rellenar
convertiria a los cancelados en puntuales, falseando el indicador de puntualidad
por aerolinea.

Antes de decidir si un valor esta ausente se le quitan los espacios, de modo que
una cadena vacia y una de puros espacios reciben el mismo trato. Lo que el
proceso no hace es dar por ausente un texto que diga NULL o N/A: eso es un dato
presente con contenido cuestionable, y convertirlo en silencio ocultaria un
problema de la fuente. El archivo de esta practica no trae ninguno.

La carga resuelve las llaves subrogadas contra las dimensiones ya pobladas. Los
catalogos son diminutos, entre tres y quince filas, asi que se cachean en memoria
como diccionarios y se resuelven sin una consulta por fila. Lo que no encuentre
correspondencia cae en el miembro `-1`. El proceso nunca inserta en las
dimensiones, solo las consulta. Antes de insertar vacia la tabla de hechos, de
manera que se puede volver a ejecutar las veces que haga falta.

Toda la corrida queda registrada en `etl.log`, con las tres fases separadas y un
conteo de calidad al terminar la transformacion.

## Dos decisiones que conviene conocer

La duracion del vuelo es la que declara la fuente. La diferencia entre la hora de
llegada y la de salida no coincide con `duration_min` en 8,887 registros, con
desviaciones de hasta media hora en ambos sentidos. Se tomo `duration_min` como
valor autoritativo y las horas quedaron para el analisis temporal. Ninguna
consulta deriva la duracion restando.

Las fechas se desambiguan por fila. El archivo escribe la mayoria de las fechas
como `dd/mm/yyyy HH:MM`, unas mil quinientas de cada columna como
`mm-dd-yyyy hh:MM AM/PM`, y ademas intercala fechas con barras escritas en orden
`mm/dd`. Cuando el dia y el mes son ambos 12 o menos las dos lecturas son
validas y la fecha, por si sola, es indescifrable.

La salida no se puede resolver mirando solo la salida, ni la llegada mirando solo
la llegada. Lo que si funciona es evaluar las tres fechas de la fila en conjunto
contra dos reglas que el negocio impone: la llegada tiene que reproducir
`duration_min`, y la reserva no puede ser posterior a la salida. El proceso prueba
las lecturas posibles de las tres columnas y se queda con la combinacion que
cumple mas reglas, prefiriendo `dd/mm` en los empates para no reinterpretar
fechas que ya eran coherentes.

La banda de tolerancia para la primera regla se midio sobre los 5,718 registros
cuyas dos fechas son inequivocas, donde el error entre `llegada - salida` y
`duration_min` va de -10 a +262 minutos. Un dia y un mes intercambiados desplazan
la fecha por dias o meses, varios ordenes de magnitud fuera de esa banda, asi que
la separacion entre una lectura buena y una mala no es dudosa.

Con la lectura ingenua, 1,677 de los 10,000 registros violaban alguna de las dos
reglas. Con la desambiguacion conjunta no queda ninguno: se reinterpretan 407
salidas, 1,050 llegadas y 329 reservas, y la consulta V5 devuelve cero en los
cinco contadores.

## Requisitos

Python 3.10 o superior, Microsoft SQL Server y el ODBC Driver 17 for SQL Server.
Las dependencias de Python estan congeladas en `requirements.txt`; las que
importan son pandas, SQLAlchemy y pyodbc.

## Como ejecutarlo

Desde la carpeta `Practica1`, con el entorno virtual preparado:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Se crea el modelo y se cargan los catalogos:

```powershell
sqlcmd -S localhost -E -i sql\crear_modelo.sql
sqlcmd -S localhost -E -i sql\poblar_dimensiones.sql
```

Se corre el ETL:

```powershell
python src\etl.py --csv src\dataset_vuelos_crudo.csv
```

Y se valida la carga:

```powershell
sqlcmd -S localhost -E -d VuelosDW -i sql\consultas_analiticas.sql
```

La conexion se configura por variables de entorno, todas opcionales:
`DB_SERVER` (por defecto `localhost`), `DB_NAME` (`VuelosDW`), `DB_DRIVER`
(`ODBC Driver 17 for SQL Server`), `DB_USER` con `DB_PASSWORD` si se prefiere
autenticacion de SQL Server en lugar de la de Windows, y `DB_TRUST_CERT` para
aceptar un certificado autofirmado. Para una instancia LocalDB hay que apuntar el
servidor antes de correr el ETL:

```powershell
$env:DB_SERVER = "(localdb)\mssqllocaldb"
```

Los tres scripts SQL son idempotentes y el ETL tambien: antes de insertar vacia
la tabla de hechos, de modo que la secuencia completa se puede repetir sin dejar
residuos ni chocar contra la restriccion de unicidad.

### Sobre macOS y Linux

El proyecto tambien corre fuera de Windows levantando SQL Server en un
contenedor. Ahi cambian tres cosas. La primera es el driver: el que se instala
por Homebrew o apt es el 18, que cifra la conexion por defecto y rechaza el
certificado autofirmado del contenedor, asi que hay que declarar
`DB_DRIVER="ODBC Driver 18 for SQL Server"` y `DB_TRUST_CERT=yes`. La segunda es
la autenticacion, que pasa a ser la de SQL Server con `DB_USER` y `DB_PASSWORD`
porque no existe la de Windows. Y la tercera son las versiones congeladas en
`requirements.txt`, que corresponden al entorno de Windows con Python 3.10; en
versiones mas nuevas del interprete conviene instalar `pandas`, `sqlalchemy` y
`pyodbc` sin fijar version.

## Resultados

Las cinco primeras consultas de `consultas_analiticas.sql` validan la carga. V1
debe devolver 10,000 boletos sin duplicados de `record_id`. V2 debe reportar 209
desconocidos en nacionalidad y 144 en canal de venta, mas 560 no aplicables en la
fecha de llegada, que son los vuelos cancelados; cualquier otra dimension con
ausencias por encima de cero delataria un error de homologacion. V3 debe quedar en
CORRECTO en todas sus filas. V4 debe mostrar salidas entre el 1 de enero de 2024
y el 31 de diciembre de 2025, edades de 0 a 77 anios y duraciones de 45 a 420
minutos. V5 devuelve cero en sus cinco contadores.

Las ocho restantes producen los indicadores de negocio. Sobre los 10,000
registros del archivo, el trafico esta muy repartido: los cinco destinos
principales son San Pedro Sula, Cancun, Barcelona, Bogota y La Habana, y ninguno
pasa del 7.1% del total. La ruta mas transitada es Miami a La Habana con 76
boletos. Por estado del vuelo, 72.8% salieron a tiempo, 19.7% con retraso, 5.6%
se cancelaron y 1.9% fueron desviados. La distribucion por genero queda en 49.1%
masculino, 47.0% femenino y 3.9% no binario. El ingreso total, convertido a
dolares para poder sumar las cuatro monedas del archivo, es de 770,024.71.

## Reparto del trabajo

El modelo dimensional, los scripts SQL y las consultas analiticas corresponden a
la mitad de modelado. El proceso ETL en Python, esta documentacion y la
estructura del repositorio corresponden a la mitad de integracion.
