USE VuelosDW;
GO

-- V1. Conteo total de boletos cargados contra los 10,000 registros del archivo
SELECT
    COUNT(*)                        AS boletos_cargados,
    10000                           AS registros_en_el_archivo,
    COUNT(DISTINCT record_id)       AS record_id_distintos,
    COUNT(DISTINCT id_pasajero)     AS pasajeros_distintos,
    CASE WHEN COUNT(*) = 10000 AND COUNT(DISTINCT record_id) = COUNT(*)
         THEN 'CARGA COMPLETA' ELSE 'REVISAR' END AS resultado
FROM dbo.Hecho_Boleto;
GO

-- V2. Ausencias por dimension, separando lo desconocido de lo que no aplica
SELECT 'Fecha de salida'  AS dimension,
       SUM(CASE WHEN sk_fecha_salida = -1 THEN 1 ELSE 0 END) AS desconocidos,
       SUM(CASE WHEN sk_fecha_salida = -2 THEN 1 ELSE 0 END) AS no_aplica
FROM dbo.Hecho_Boleto
UNION ALL SELECT 'Fecha de llegada',
       SUM(CASE WHEN sk_fecha_llegada = -1 THEN 1 ELSE 0 END),
       SUM(CASE WHEN sk_fecha_llegada = -2 THEN 1 ELSE 0 END) FROM dbo.Hecho_Boleto
UNION ALL SELECT 'Fecha de reserva',
       SUM(CASE WHEN sk_fecha_reserva = -1 THEN 1 ELSE 0 END),
       SUM(CASE WHEN sk_fecha_reserva = -2 THEN 1 ELSE 0 END) FROM dbo.Hecho_Boleto
UNION ALL SELECT 'Aerolinea',
       SUM(CASE WHEN sk_aerolinea = -1 THEN 1 ELSE 0 END),
       SUM(CASE WHEN sk_aerolinea = -2 THEN 1 ELSE 0 END) FROM dbo.Hecho_Boleto
UNION ALL SELECT 'Aeropuerto origen',
       SUM(CASE WHEN sk_aeropuerto_origen = -1 THEN 1 ELSE 0 END),
       SUM(CASE WHEN sk_aeropuerto_origen = -2 THEN 1 ELSE 0 END) FROM dbo.Hecho_Boleto
UNION ALL SELECT 'Aeropuerto destino',
       SUM(CASE WHEN sk_aeropuerto_destino = -1 THEN 1 ELSE 0 END),
       SUM(CASE WHEN sk_aeropuerto_destino = -2 THEN 1 ELSE 0 END) FROM dbo.Hecho_Boleto
UNION ALL SELECT 'Aeronave',
       SUM(CASE WHEN sk_aeronave = -1 THEN 1 ELSE 0 END),
       SUM(CASE WHEN sk_aeronave = -2 THEN 1 ELSE 0 END) FROM dbo.Hecho_Boleto
UNION ALL SELECT 'Clase de cabina',
       SUM(CASE WHEN sk_clase_cabina = -1 THEN 1 ELSE 0 END),
       SUM(CASE WHEN sk_clase_cabina = -2 THEN 1 ELSE 0 END) FROM dbo.Hecho_Boleto
UNION ALL SELECT 'Estado del vuelo',
       SUM(CASE WHEN sk_estado_vuelo = -1 THEN 1 ELSE 0 END),
       SUM(CASE WHEN sk_estado_vuelo = -2 THEN 1 ELSE 0 END) FROM dbo.Hecho_Boleto
UNION ALL SELECT 'Canal de venta',
       SUM(CASE WHEN sk_canal_venta = -1 THEN 1 ELSE 0 END),
       SUM(CASE WHEN sk_canal_venta = -2 THEN 1 ELSE 0 END) FROM dbo.Hecho_Boleto
UNION ALL SELECT 'Metodo de pago',
       SUM(CASE WHEN sk_metodo_pago = -1 THEN 1 ELSE 0 END),
       SUM(CASE WHEN sk_metodo_pago = -2 THEN 1 ELSE 0 END) FROM dbo.Hecho_Boleto
UNION ALL SELECT 'Moneda',
       SUM(CASE WHEN sk_moneda = -1 THEN 1 ELSE 0 END),
       SUM(CASE WHEN sk_moneda = -2 THEN 1 ELSE 0 END) FROM dbo.Hecho_Boleto
UNION ALL SELECT 'Genero',
       SUM(CASE WHEN sk_genero = -1 THEN 1 ELSE 0 END),
       SUM(CASE WHEN sk_genero = -2 THEN 1 ELSE 0 END) FROM dbo.Hecho_Boleto
UNION ALL SELECT 'Nacionalidad',
       SUM(CASE WHEN sk_nacionalidad = -1 THEN 1 ELSE 0 END),
       SUM(CASE WHEN sk_nacionalidad = -2 THEN 1 ELSE 0 END) FROM dbo.Hecho_Boleto
ORDER BY desconocidos DESC, no_aplica DESC;
GO

-- V3. Coherencia entre el estado del vuelo y las medidas de duracion y retraso
SELECT
    ev.descripcion                  AS estado,
    COUNT(*)                        AS boletos,
    SUM(CASE WHEN h.fecha_hora_llegada IS NULL THEN 1 ELSE 0 END) AS sin_hora_llegada,
    SUM(CASE WHEN h.duracion_min       IS NULL THEN 1 ELSE 0 END) AS sin_duracion,
    SUM(CASE WHEN h.retraso_min        IS NULL THEN 1 ELSE 0 END) AS sin_retraso,
    CASE
        WHEN ev.es_completado = 0
             AND SUM(CASE WHEN h.fecha_hora_llegada IS NULL THEN 1 ELSE 0 END) = COUNT(*)
             THEN 'CORRECTO'
        WHEN ev.es_completado = 1
             AND SUM(CASE WHEN h.duracion_min IS NULL THEN 1 ELSE 0 END) = 0
             THEN 'CORRECTO'
        ELSE 'REVISAR'
    END AS resultado
FROM dbo.Hecho_Boleto h
JOIN dbo.Dim_EstadoVuelo ev ON ev.sk_estado_vuelo = h.sk_estado_vuelo
GROUP BY ev.descripcion, ev.es_completado
ORDER BY boletos DESC;
GO

-- V4. Rangos de fechas, duraciones, edades y precios despues de la carga
SELECT
    MIN(fecha_hora_salida)          AS primera_salida,
    MAX(fecha_hora_salida)          AS ultima_salida,
    MIN(duracion_min)               AS duracion_minima,
    MAX(duracion_min)               AS duracion_maxima,
    MIN(retraso_min)                AS retraso_minimo,
    MAX(retraso_min)                AS retraso_maximo,
    MIN(edad_pasajero)              AS edad_minima,
    MAX(edad_pasajero)              AS edad_maxima,
    MIN(precio_boleto_usd)          AS precio_usd_minimo,
    MAX(precio_boleto_usd)          AS precio_usd_maximo,
    CAST(SUM(precio_boleto_usd) AS DECIMAL(14,2)) AS ingreso_total_usd
FROM dbo.Hecho_Boleto;
GO

-- V5. Reglas de negocio que deben dar cero en todos los contadores
SELECT
    SUM(CASE WHEN h.fecha_hora_llegada IS NOT NULL
              AND h.fecha_hora_llegada <= h.fecha_hora_salida
             THEN 1 ELSE 0 END)                             AS llegada_antes_de_salida,
    SUM(CASE WHEN h.fecha_hora_reserva > h.fecha_hora_salida
             THEN 1 ELSE 0 END)                             AS reserva_despues_de_salida,
    SUM(CASE WHEN h.sk_aeropuerto_origen = h.sk_aeropuerto_destino
             THEN 1 ELSE 0 END)                             AS origen_igual_a_destino,
    SUM(CASE WHEN h.equipaje_documentado > h.equipaje_total
             THEN 1 ELSE 0 END)                             AS equipaje_inconsistente,
    SUM(CASE WHEN h.precio_boleto_usd <= 0 THEN 1 ELSE 0 END) AS precio_no_positivo
FROM dbo.Hecho_Boleto h;
GO

-- I1. Top 5 de rutas mas transitadas con boletos e ingreso
SELECT TOP 5
    ori.codigo_iata + ' - ' + des.codigo_iata   AS ruta,
    ori.ciudad                                  AS ciudad_origen,
    des.ciudad                                  AS ciudad_destino,
    COUNT(*)                                    AS boletos,
    CAST(SUM(h.precio_boleto_usd) AS DECIMAL(14,2)) AS ingreso_usd
FROM dbo.Hecho_Boleto h
JOIN dbo.Dim_Aeropuerto ori ON ori.sk_aeropuerto = h.sk_aeropuerto_origen
JOIN dbo.Dim_Aeropuerto des ON des.sk_aeropuerto = h.sk_aeropuerto_destino
WHERE h.sk_aeropuerto_origen <> -1
  AND h.sk_aeropuerto_destino <> -1
GROUP BY ori.codigo_iata, des.codigo_iata, ori.ciudad, des.ciudad
ORDER BY boletos DESC;
GO

-- I2. Top 5 de destinos mas frecuentes con su porcentaje del total
SELECT TOP 5
    des.codigo_iata     AS destino,
    des.ciudad,
    des.pais,
    COUNT(*)            AS boletos,
    CAST(100.0 * COUNT(*) / SUM(COUNT(*)) OVER () AS DECIMAL(5,2)) AS porcentaje
FROM dbo.Hecho_Boleto h
JOIN dbo.Dim_Aeropuerto des ON des.sk_aeropuerto = h.sk_aeropuerto_destino
WHERE h.sk_aeropuerto_destino <> -1
GROUP BY des.codigo_iata, des.ciudad, des.pais
ORDER BY boletos DESC;
GO

-- I3. Distribucion de pasajeros por genero y clase de cabina
SELECT
    ge.descripcion      AS genero,
    cc.descripcion      AS clase_cabina,
    COUNT(*)            AS boletos,
    CAST(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY ge.descripcion) AS DECIMAL(5,2)) AS pct_dentro_del_genero,
    CAST(AVG(h.precio_boleto_usd) AS DECIMAL(10,2)) AS precio_promedio_usd
FROM dbo.Hecho_Boleto h
JOIN dbo.Dim_Genero      ge ON ge.sk_genero      = h.sk_genero
JOIN dbo.Dim_ClaseCabina cc ON cc.sk_clase_cabina = h.sk_clase_cabina
GROUP BY ge.descripcion, cc.descripcion, cc.nivel_servicio
ORDER BY ge.descripcion, cc.nivel_servicio;
GO

-- I4. Puntualidad, cancelaciones y retraso promedio por aerolinea
SELECT
    al.nombre                                   AS aerolinea,
    al.pais_origen,
    COUNT(*)                                    AS boletos,
    SUM(CASE WHEN ev.codigo = 'ON_TIME'   THEN 1 ELSE 0 END) AS a_tiempo,
    SUM(CASE WHEN ev.codigo = 'DELAYED'   THEN 1 ELSE 0 END) AS retrasados,
    SUM(CASE WHEN ev.codigo = 'CANCELLED' THEN 1 ELSE 0 END) AS cancelados,
    CAST(100.0 * SUM(CASE WHEN ev.codigo = 'ON_TIME' THEN 1 ELSE 0 END) / COUNT(*) AS DECIMAL(5,2)) AS pct_puntualidad,
    CAST(AVG(CASE WHEN ev.codigo = 'DELAYED' THEN CAST(h.retraso_min AS DECIMAL(10,2)) END) AS DECIMAL(10,2)) AS retraso_promedio_min
FROM dbo.Hecho_Boleto h
JOIN dbo.Dim_Aerolinea   al ON al.sk_aerolinea    = h.sk_aerolinea
JOIN dbo.Dim_EstadoVuelo ev ON ev.sk_estado_vuelo = h.sk_estado_vuelo
GROUP BY al.nombre, al.pais_origen
ORDER BY pct_puntualidad DESC;
GO

-- I5. Ingresos en dolares por canal de venta y metodo de pago
SELECT
    cv.descripcion      AS canal_venta,
    mp.descripcion      AS metodo_pago,
    COUNT(*)            AS boletos,
    CAST(SUM(h.precio_boleto_usd) AS DECIMAL(14,2)) AS ingreso_usd,
    CAST(AVG(h.precio_boleto_usd) AS DECIMAL(10,2)) AS ticket_promedio_usd
FROM dbo.Hecho_Boleto h
JOIN dbo.Dim_CanalVenta  cv ON cv.sk_canal_venta = h.sk_canal_venta
JOIN dbo.Dim_MetodoPago  mp ON mp.sk_metodo_pago = h.sk_metodo_pago
GROUP BY cv.descripcion, mp.descripcion
ORDER BY ingreso_usd DESC;
GO

-- I6. Estacionalidad mensual de boletos, ingresos y duracion promedio
SELECT
    f.anio,
    f.mes,
    f.nombre_mes,
    COUNT(*)                                        AS boletos,
    CAST(SUM(h.precio_boleto_usd) AS DECIMAL(14,2)) AS ingreso_usd,
    CAST(AVG(CAST(h.duracion_min AS DECIMAL(10,2))) AS DECIMAL(10,2)) AS duracion_promedio_min
FROM dbo.Hecho_Boleto h
JOIN dbo.Dim_Fecha f ON f.sk_fecha = h.sk_fecha_salida
WHERE h.sk_fecha_salida <> -1
GROUP BY f.anio, f.mes, f.nombre_mes
ORDER BY f.anio, f.mes;
GO

-- I7. Dias de anticipacion de la reserva por canal de venta
SELECT
    cv.descripcion      AS canal_venta,
    COUNT(*)            AS boletos,
    CAST(AVG(CAST(DATEDIFF(DAY, h.fecha_hora_reserva, h.fecha_hora_salida) AS DECIMAL(10,2))) AS DECIMAL(10,2)) AS dias_anticipacion_promedio,
    MIN(DATEDIFF(DAY, h.fecha_hora_reserva, h.fecha_hora_salida)) AS minimo,
    MAX(DATEDIFF(DAY, h.fecha_hora_reserva, h.fecha_hora_salida)) AS maximo,
    CAST(AVG(h.precio_boleto_usd) AS DECIMAL(10,2)) AS ticket_promedio_usd
FROM dbo.Hecho_Boleto h
JOIN dbo.Dim_CanalVenta cv ON cv.sk_canal_venta = h.sk_canal_venta
GROUP BY cv.descripcion
ORDER BY dias_anticipacion_promedio DESC;
GO

-- I8. Perfil de pasajeros por nacionalidad y rango de edad
SELECT
    na.pais             AS nacionalidad,
    r.rango_edad,
    COUNT(*)            AS boletos,
    CAST(AVG(h.precio_boleto_usd) AS DECIMAL(10,2)) AS ticket_promedio_usd,
    CAST(AVG(CAST(h.equipaje_total AS DECIMAL(10,2))) AS DECIMAL(10,2)) AS maletas_promedio
FROM dbo.Hecho_Boleto h
JOIN dbo.Dim_Nacionalidad na ON na.sk_nacionalidad = h.sk_nacionalidad
CROSS APPLY (VALUES (
    CASE
        WHEN h.edad_pasajero IS NULL THEN '0. Sin dato'
        WHEN h.edad_pasajero < 18    THEN '1. Menor de 18'
        WHEN h.edad_pasajero < 30    THEN '2. De 18 a 29'
        WHEN h.edad_pasajero < 45    THEN '3. De 30 a 44'
        WHEN h.edad_pasajero < 60    THEN '4. De 45 a 59'
        ELSE                              '5. 60 o mas'
    END
)) AS r(rango_edad)
GROUP BY na.pais, r.rango_edad
ORDER BY na.pais, r.rango_edad;
GO
