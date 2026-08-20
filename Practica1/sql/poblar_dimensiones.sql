USE VuelosDW;
GO

DELETE FROM dbo.Hecho_Boleto;
DELETE FROM dbo.Dim_Fecha;
DELETE FROM dbo.Dim_Aerolinea;
DELETE FROM dbo.Dim_Aeropuerto;
DELETE FROM dbo.Dim_Aeronave;
DELETE FROM dbo.Dim_ClaseCabina;
DELETE FROM dbo.Dim_EstadoVuelo;
DELETE FROM dbo.Dim_CanalVenta;
DELETE FROM dbo.Dim_MetodoPago;
DELETE FROM dbo.Dim_Moneda;
DELETE FROM dbo.Dim_Genero;
DELETE FROM dbo.Dim_Nacionalidad;
GO

INSERT INTO dbo.Dim_Fecha
    (sk_fecha, fecha, anio, trimestre, mes, nombre_mes, dia, dia_semana, nombre_dia, es_fin_semana)
VALUES
    (-1, NULL, NULL, NULL, NULL, 'DESCONOCIDO', NULL, NULL, 'DESCONOCIDO', NULL);
GO

WITH calendario AS (
    SELECT CAST('2023-01-01' AS DATE) AS fecha
    UNION ALL
    SELECT DATEADD(DAY, 1, fecha) FROM calendario WHERE fecha < '2026-12-31'
),
detalle AS (
    SELECT
        fecha,
        (DATEDIFF(DAY, '19000101', fecha) % 7) + 1 AS dia_semana
    FROM calendario
)
INSERT INTO dbo.Dim_Fecha
    (sk_fecha, fecha, anio, trimestre, mes, nombre_mes, dia, dia_semana, nombre_dia, es_fin_semana)
SELECT
    CONVERT(INT, FORMAT(fecha, 'yyyyMMdd')),
    fecha,
    YEAR(fecha),
    DATEPART(QUARTER, fecha),
    MONTH(fecha),
    CASE MONTH(fecha)
        WHEN 1 THEN 'Enero'      WHEN 2 THEN 'Febrero'   WHEN 3 THEN 'Marzo'
        WHEN 4 THEN 'Abril'      WHEN 5 THEN 'Mayo'      WHEN 6 THEN 'Junio'
        WHEN 7 THEN 'Julio'      WHEN 8 THEN 'Agosto'    WHEN 9 THEN 'Septiembre'
        WHEN 10 THEN 'Octubre'   WHEN 11 THEN 'Noviembre' ELSE 'Diciembre'
    END,
    DAY(fecha),
    dia_semana,
    CASE dia_semana
        WHEN 1 THEN 'Lunes'     WHEN 2 THEN 'Martes'  WHEN 3 THEN 'Miercoles'
        WHEN 4 THEN 'Jueves'    WHEN 5 THEN 'Viernes' WHEN 6 THEN 'Sabado'
        ELSE 'Domingo'
    END,
    CASE WHEN dia_semana >= 6 THEN 1 ELSE 0 END
FROM detalle
OPTION (MAXRECURSION 0);
GO

INSERT INTO dbo.Dim_Aerolinea (sk_aerolinea, codigo, nombre, pais_origen) VALUES
    (-1, 'ND', 'DESCONOCIDO',        'DESCONOCIDO'),
    ( 1, 'AA', 'American Airlines',  'Estados Unidos'),
    ( 2, 'AM', 'Aeromexico',         'Mexico'),
    ( 3, 'AV', 'Avianca',            'Colombia'),
    ( 4, 'B6', 'JetBlue',            'Estados Unidos'),
    ( 5, 'BA', 'British Airways',    'Reino Unido'),
    ( 6, 'CM', 'Copa Airlines',      'Panama'),
    ( 7, 'DL', 'Delta',              'Estados Unidos'),
    ( 8, 'FR', 'Ryanair',            'Irlanda'),
    ( 9, 'IB', 'Iberia',             'Espana'),
    (10, 'LA', 'LATAM',              'Chile'),
    (11, 'UA', 'United',             'Estados Unidos'),
    (12, 'WN', 'Southwest',          'Estados Unidos');
GO

INSERT INTO dbo.Dim_Aeropuerto (sk_aeropuerto, codigo_iata, nombre, ciudad, pais) VALUES
    (-1, 'ND',  'DESCONOCIDO',                      'DESCONOCIDO',        'DESCONOCIDO'),
    ( 1, 'BCN', 'Josep Tarradellas Barcelona',      'Barcelona',          'Espana'),
    ( 2, 'BOG', 'El Dorado',                        'Bogota',             'Colombia'),
    ( 3, 'CUN', 'Cancun',                           'Cancun',             'Mexico'),
    ( 4, 'GUA', 'La Aurora',                        'Ciudad de Guatemala','Guatemala'),
    ( 5, 'HAV', 'Jose Marti',                       'La Habana',          'Cuba'),
    ( 6, 'JFK', 'John F. Kennedy',                  'Nueva York',         'Estados Unidos'),
    ( 7, 'LAX', 'Los Angeles',                      'Los Angeles',        'Estados Unidos'),
    ( 8, 'LIM', 'Jorge Chavez',                     'Lima',               'Peru'),
    ( 9, 'MAD', 'Adolfo Suarez Madrid-Barajas',     'Madrid',             'Espana'),
    (10, 'MEX', 'Benito Juarez',                    'Ciudad de Mexico',   'Mexico'),
    (11, 'MIA', 'Miami',                            'Miami',              'Estados Unidos'),
    (12, 'PTY', 'Tocumen',                          'Ciudad de Panama',   'Panama'),
    (13, 'SAL', 'Monsenor Oscar Arnulfo Romero',    'San Salvador',       'El Salvador'),
    (14, 'SAP', 'Ramon Villeda Morales',            'San Pedro Sula',     'Honduras'),
    (15, 'SJO', 'Juan Santamaria',                  'San Jose',           'Costa Rica');
GO

INSERT INTO dbo.Dim_Aeronave (sk_aeronave, codigo, fabricante, familia) VALUES
    (-1, 'ND',   'DESCONOCIDO', 'DESCONOCIDO'),
    ( 1, 'A319', 'Airbus',      'A320'),
    ( 2, 'A320', 'Airbus',      'A320'),
    ( 3, 'A321', 'Airbus',      'A320'),
    ( 4, 'B737', 'Boeing',      'B737'),
    ( 5, 'B738', 'Boeing',      'B737'),
    ( 6, 'B739', 'Boeing',      'B737'),
    ( 7, 'B757', 'Boeing',      'B757'),
    ( 8, 'B767', 'Boeing',      'B767'),
    ( 9, 'B777', 'Boeing',      'B777'),
    (10, 'B787', 'Boeing',      'B787'),
    (11, 'CRJ9', 'Bombardier',  'CRJ'),
    (12, 'E190', 'Embraer',     'E-Jet');
GO

INSERT INTO dbo.Dim_ClaseCabina (sk_clase_cabina, codigo, descripcion, nivel_servicio) VALUES
    (-1, 'ND',              'DESCONOCIDO',      0),
    ( 1, 'ECONOMY',         'Economica',        1),
    ( 2, 'PREMIUM_ECONOMY', 'Economica Premium',2),
    ( 3, 'BUSINESS',        'Ejecutiva',        3),
    ( 4, 'FIRST',           'Primera Clase',    4);
GO

INSERT INTO dbo.Dim_EstadoVuelo (sk_estado_vuelo, codigo, descripcion, es_completado) VALUES
    (-1, 'ND',        'DESCONOCIDO', 0),
    ( 1, 'ON_TIME',   'A tiempo',    1),
    ( 2, 'DELAYED',   'Retrasado',   1),
    ( 3, 'CANCELLED', 'Cancelado',   0),
    ( 4, 'DIVERTED',  'Desviado',    1);
GO

INSERT INTO dbo.Dim_CanalVenta (sk_canal_venta, codigo, descripcion, es_digital) VALUES
    (-1, 'ND',          'DESCONOCIDO',       0),
    ( 1, 'WEB',         'Sitio web',         1),
    ( 2, 'APP',         'Aplicacion movil',  1),
    ( 3, 'AGENCIA',     'Agencia de viajes', 0),
    ( 4, 'AEROPUERTO',  'Mostrador',         0),
    ( 5, 'CALL_CENTER', 'Centro de llamadas',0);
GO

INSERT INTO dbo.Dim_MetodoPago (sk_metodo_pago, codigo, descripcion) VALUES
    (-1, 'ND',            'DESCONOCIDO'),
    ( 1, 'TARJETA',       'Tarjeta de credito'),
    ( 2, 'TRANSFERENCIA', 'Transferencia bancaria'),
    ( 3, 'PAYPAL',        'PayPal'),
    ( 4, 'EFECTIVO',      'Efectivo'),
    ( 5, 'PUNTOS',        'Puntos de lealtad');
GO

INSERT INTO dbo.Dim_Moneda (sk_moneda, codigo, nombre) VALUES
    (-1, 'ND',  'DESCONOCIDO'),
    ( 1, 'USD', 'Dolar estadounidense'),
    ( 2, 'GTQ', 'Quetzal guatemalteco'),
    ( 3, 'MXN', 'Peso mexicano'),
    ( 4, 'EUR', 'Euro');
GO

INSERT INTO dbo.Dim_Genero (sk_genero, codigo, descripcion) VALUES
    (-1, 'ND', 'DESCONOCIDO'),
    ( 1, 'M',  'Masculino'),
    ( 2, 'F',  'Femenino'),
    ( 3, 'X',  'No binario');
GO

INSERT INTO dbo.Dim_Nacionalidad (sk_nacionalidad, codigo, pais) VALUES
    (-1, 'ND', 'DESCONOCIDO'),
    ( 1, 'CO', 'Colombia'),
    ( 2, 'CR', 'Costa Rica'),
    ( 3, 'CU', 'Cuba'),
    ( 4, 'ES', 'Espana'),
    ( 5, 'GT', 'Guatemala'),
    ( 6, 'HN', 'Honduras'),
    ( 7, 'MX', 'Mexico'),
    ( 8, 'PA', 'Panama'),
    ( 9, 'PE', 'Peru'),
    (10, 'SV', 'El Salvador'),
    (11, 'US', 'Estados Unidos');
GO

SELECT 'Dim_Fecha' AS dimension, COUNT(*) AS filas FROM dbo.Dim_Fecha
UNION ALL SELECT 'Dim_Aerolinea',    COUNT(*) FROM dbo.Dim_Aerolinea
UNION ALL SELECT 'Dim_Aeropuerto',   COUNT(*) FROM dbo.Dim_Aeropuerto
UNION ALL SELECT 'Dim_Aeronave',     COUNT(*) FROM dbo.Dim_Aeronave
UNION ALL SELECT 'Dim_ClaseCabina',  COUNT(*) FROM dbo.Dim_ClaseCabina
UNION ALL SELECT 'Dim_EstadoVuelo',  COUNT(*) FROM dbo.Dim_EstadoVuelo
UNION ALL SELECT 'Dim_CanalVenta',   COUNT(*) FROM dbo.Dim_CanalVenta
UNION ALL SELECT 'Dim_MetodoPago',   COUNT(*) FROM dbo.Dim_MetodoPago
UNION ALL SELECT 'Dim_Moneda',       COUNT(*) FROM dbo.Dim_Moneda
UNION ALL SELECT 'Dim_Genero',       COUNT(*) FROM dbo.Dim_Genero
UNION ALL SELECT 'Dim_Nacionalidad', COUNT(*) FROM dbo.Dim_Nacionalidad;
GO
