# Practica 2: Dashboard y KPIs con Power BI

Curso: Seminario de Sistemas 2
Grupo: SS2S2026_G15

Construye un dashboard en Power BI sobre `VuelosDW`, la base dimensional creada en
la Practica 1. El modelo, las medidas DAX y los indicadores se apoyan directamente
en ese esquema estrella, asi que la Practica 1 tiene que estar cargada y validada
antes de abrir Power BI.

## Estado

Lo que ya esta hecho y probado:

```
sql/vistas_powerbi.sql      las 5 vistas de rol, verificadas contra la base
dax/medidas.dax             las 12 medidas DAX listas para pegar
docs/modelo_powerbi.md      por que las vistas, que importar y como relacionar
docs/valores_esperados.md   linea base contra la que se valida el tablero
```

Falta el archivo `.pbix`, las capturas y el informe tecnico.

## Orden de trabajo

### 1. Reconstruir la base

Desde `Practica1`, con SQL Server corriendo. Los detalles de entorno y las
variables de conexion estan en `Practica1/README.md`.

```powershell
sqlcmd -S localhost -E -i sql\crear_modelo.sql
sqlcmd -S localhost -E -i sql\poblar_dimensiones.sql
python src\etl.py --csv src\dataset_vuelos_crudo.csv
```

### 2. Crear las vistas de rol

Desde `Practica2`:

```powershell
sqlcmd -S localhost -E -i sql\vistas_powerbi.sql
```

Deben quedar cinco vistas: `Dim_Fecha_Salida`, `Dim_Fecha_Llegada`,
`Dim_Fecha_Reserva`, `Dim_Aeropuerto_Origen` y `Dim_Aeropuerto_Destino`.

### 3. Comprobar que la base quedo bien

```powershell
sqlcmd -S localhost -E -d VuelosDW -i ..\Practica1\sql\consultas_analiticas.sql
```

Las senales de que todo esta correcto: V1 devuelve 10,000 boletos sin duplicados,
V5 devuelve cero en sus cinco contadores, y el ingreso total es 770,024.71 USD. Si
eso sale, la base coincide con la que produjo `docs/valores_esperados.md` y se
puede confiar en cada numero de ese documento.

### 4. Modelo tabular en Power BI

Seguir `docs/modelo_powerbi.md`, que explica que tablas importar y cuales no, como
quedan las quince relaciones y los dos ajustes que hay que hacer del lado de Power
BI. Despues crear las cuatro jerarquias: fecha, aeropuerto, aerolinea y aeronave.

### 5. Medidas

Pegar las de `dax/medidas.dax` una por una en Inicio, Nueva medida. Power BI no
importa medidas desde archivo. Crear primero las de la seccion Base, porque las
demas las referencian, y aplicar los formatos que el archivo indica al final.

Verificar contra `docs/valores_esperados.md` antes de construir un solo visual. Si
`Boletos Vendidos` no da 10,000 o `Ingreso Total USD` no da 770,024.71, hay una
relacion mal armada y conviene descubrirlo ahora.

### 6. Dashboard

Visuales, KPI con semaforo, segmentadores. La meta de puntualidad es 73 % y la
alerta 72 %; el reparto de aerolineas en verde, amarillo y rojo esta en la linea
base.

### 7. Informe y capturas

## Reparto

El archivo `.pbix` es binario y git no lo puede fusionar, asi que lo tiene una sola
persona a la vez y la posta se pasa de forma explicita.

Joel toma la primera fase: conexion, modelo tabular, jerarquias, medidas DAX y la
linea base de validacion. Cuando termina, commitea y avisa que el archivo cambio de
dueno.

Alvaro toma la segunda: visuales, KPI, segmentadores, formato, capturas,
exportacion a PDF, estructura del repositorio y el informe tecnico. Joel escribe la
seccion de modelo y medidas del informe y contrasta los numeros del tablero contra
la linea base.

Lo que hay que acordar antes de separarse son los nombres exactos de las medidas y
que va en cada pagina del tablero. Sin eso el informe termina describiendo cosas
que no coinciden con el archivo.
