USE VuelosDW;
GO

-- Vistas de rol para Dim_Fecha y Dim_Aeropuerto.
-- El modelo dimensional referencia Dim_Fecha tres veces y Dim_Aeropuerto dos,
-- lo cual es correcto en SQL Server. Power BI, en cambio, solo admite una
-- relacion activa entre dos tablas, asi que cada papel se expone como una vista
-- independiente. No duplican datos: son consultas sobre la misma dimension.
-- La llave de cada vista se nombra igual que la columna del hecho a la que
-- corresponde, para que Power BI detecte la relacion automaticamente.

CREATE OR ALTER VIEW dbo.Dim_Fecha_Salida AS
SELECT
    sk_fecha AS sk_fecha_salida,
    fecha, anio, trimestre, mes, nombre_mes, dia, dia_semana, nombre_dia, es_fin_semana
FROM dbo.Dim_Fecha;
GO

CREATE OR ALTER VIEW dbo.Dim_Fecha_Llegada AS
SELECT
    sk_fecha AS sk_fecha_llegada,
    fecha, anio, trimestre, mes, nombre_mes, dia, dia_semana, nombre_dia, es_fin_semana
FROM dbo.Dim_Fecha;
GO

CREATE OR ALTER VIEW dbo.Dim_Fecha_Reserva AS
SELECT
    sk_fecha AS sk_fecha_reserva,
    fecha, anio, trimestre, mes, nombre_mes, dia, dia_semana, nombre_dia, es_fin_semana
FROM dbo.Dim_Fecha;
GO

CREATE OR ALTER VIEW dbo.Dim_Aeropuerto_Origen AS
SELECT
    sk_aeropuerto AS sk_aeropuerto_origen,
    codigo_iata, nombre, ciudad, pais
FROM dbo.Dim_Aeropuerto;
GO

CREATE OR ALTER VIEW dbo.Dim_Aeropuerto_Destino AS
SELECT
    sk_aeropuerto AS sk_aeropuerto_destino,
    codigo_iata, nombre, ciudad, pais
FROM dbo.Dim_Aeropuerto;
GO

SELECT name AS vista, create_date FROM sys.views WHERE schema_id = SCHEMA_ID('dbo') ORDER BY name;
GO
