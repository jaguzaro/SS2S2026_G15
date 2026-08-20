IF DB_ID('VuelosDW') IS NULL
    CREATE DATABASE VuelosDW;
GO

USE VuelosDW;
GO

IF OBJECT_ID('dbo.Hecho_Boleto', 'U')      IS NOT NULL DROP TABLE dbo.Hecho_Boleto;
IF OBJECT_ID('dbo.Dim_Fecha', 'U')         IS NOT NULL DROP TABLE dbo.Dim_Fecha;
IF OBJECT_ID('dbo.Dim_Aerolinea', 'U')     IS NOT NULL DROP TABLE dbo.Dim_Aerolinea;
IF OBJECT_ID('dbo.Dim_Aeropuerto', 'U')    IS NOT NULL DROP TABLE dbo.Dim_Aeropuerto;
IF OBJECT_ID('dbo.Dim_Aeronave', 'U')      IS NOT NULL DROP TABLE dbo.Dim_Aeronave;
IF OBJECT_ID('dbo.Dim_ClaseCabina', 'U')   IS NOT NULL DROP TABLE dbo.Dim_ClaseCabina;
IF OBJECT_ID('dbo.Dim_EstadoVuelo', 'U')   IS NOT NULL DROP TABLE dbo.Dim_EstadoVuelo;
IF OBJECT_ID('dbo.Dim_CanalVenta', 'U')    IS NOT NULL DROP TABLE dbo.Dim_CanalVenta;
IF OBJECT_ID('dbo.Dim_MetodoPago', 'U')    IS NOT NULL DROP TABLE dbo.Dim_MetodoPago;
IF OBJECT_ID('dbo.Dim_Moneda', 'U')        IS NOT NULL DROP TABLE dbo.Dim_Moneda;
IF OBJECT_ID('dbo.Dim_Genero', 'U')        IS NOT NULL DROP TABLE dbo.Dim_Genero;
IF OBJECT_ID('dbo.Dim_Nacionalidad', 'U')  IS NOT NULL DROP TABLE dbo.Dim_Nacionalidad;
GO

CREATE TABLE dbo.Dim_Fecha (
    sk_fecha        INT          NOT NULL PRIMARY KEY,
    fecha           DATE         NULL,
    anio            SMALLINT     NULL,
    trimestre       TINYINT      NULL,
    mes             TINYINT      NULL,
    nombre_mes      VARCHAR(15)  NULL,
    dia             TINYINT      NULL,
    dia_semana      TINYINT      NULL,
    nombre_dia      VARCHAR(15)  NULL,
    es_fin_semana   BIT          NULL
);
GO

CREATE TABLE dbo.Dim_Aerolinea (
    sk_aerolinea    INT          NOT NULL PRIMARY KEY,
    codigo          VARCHAR(3)   NOT NULL,
    nombre          VARCHAR(50)  NOT NULL,
    pais_origen     VARCHAR(30)  NOT NULL,
    CONSTRAINT UQ_Dim_Aerolinea_codigo UNIQUE (codigo)
);
GO

CREATE TABLE dbo.Dim_Aeropuerto (
    sk_aeropuerto   INT          NOT NULL PRIMARY KEY,
    codigo_iata     VARCHAR(3)   NOT NULL,
    nombre          VARCHAR(60)  NOT NULL,
    ciudad          VARCHAR(40)  NOT NULL,
    pais            VARCHAR(30)  NOT NULL,
    CONSTRAINT UQ_Dim_Aeropuerto_codigo UNIQUE (codigo_iata)
);
GO

CREATE TABLE dbo.Dim_Aeronave (
    sk_aeronave     INT          NOT NULL PRIMARY KEY,
    codigo          VARCHAR(6)   NOT NULL,
    fabricante      VARCHAR(20)  NOT NULL,
    familia         VARCHAR(20)  NOT NULL,
    CONSTRAINT UQ_Dim_Aeronave_codigo UNIQUE (codigo)
);
GO

CREATE TABLE dbo.Dim_ClaseCabina (
    sk_clase_cabina INT          NOT NULL PRIMARY KEY,
    codigo          VARCHAR(20)  NOT NULL,
    descripcion     VARCHAR(30)  NOT NULL,
    nivel_servicio  TINYINT      NOT NULL,
    CONSTRAINT UQ_Dim_ClaseCabina_codigo UNIQUE (codigo)
);
GO

CREATE TABLE dbo.Dim_EstadoVuelo (
    sk_estado_vuelo INT          NOT NULL PRIMARY KEY,
    codigo          VARCHAR(15)  NOT NULL,
    descripcion     VARCHAR(30)  NOT NULL,
    es_completado   BIT          NOT NULL,
    CONSTRAINT UQ_Dim_EstadoVuelo_codigo UNIQUE (codigo)
);
GO

CREATE TABLE dbo.Dim_CanalVenta (
    sk_canal_venta  INT          NOT NULL PRIMARY KEY,
    codigo          VARCHAR(15)  NOT NULL,
    descripcion     VARCHAR(30)  NOT NULL,
    es_digital      BIT          NOT NULL,
    CONSTRAINT UQ_Dim_CanalVenta_codigo UNIQUE (codigo)
);
GO

CREATE TABLE dbo.Dim_MetodoPago (
    sk_metodo_pago  INT          NOT NULL PRIMARY KEY,
    codigo          VARCHAR(15)  NOT NULL,
    descripcion     VARCHAR(30)  NOT NULL,
    CONSTRAINT UQ_Dim_MetodoPago_codigo UNIQUE (codigo)
);
GO

CREATE TABLE dbo.Dim_Moneda (
    sk_moneda       INT          NOT NULL PRIMARY KEY,
    codigo          VARCHAR(3)   NOT NULL,
    nombre          VARCHAR(30)  NOT NULL,
    CONSTRAINT UQ_Dim_Moneda_codigo UNIQUE (codigo)
);
GO

CREATE TABLE dbo.Dim_Genero (
    sk_genero       INT          NOT NULL PRIMARY KEY,
    codigo          VARCHAR(3)   NOT NULL,
    descripcion     VARCHAR(20)  NOT NULL,
    CONSTRAINT UQ_Dim_Genero_codigo UNIQUE (codigo)
);
GO

CREATE TABLE dbo.Dim_Nacionalidad (
    sk_nacionalidad INT          NOT NULL PRIMARY KEY,
    codigo          VARCHAR(3)   NOT NULL,
    pais            VARCHAR(30)  NOT NULL,
    CONSTRAINT UQ_Dim_Nacionalidad_codigo UNIQUE (codigo)
);
GO

CREATE TABLE dbo.Hecho_Boleto (
    sk_boleto                INT           IDENTITY(1,1) NOT NULL,

    record_id                INT           NOT NULL,
    numero_vuelo             VARCHAR(10)   NOT NULL,
    asiento                  VARCHAR(5)    NULL,
    id_pasajero              CHAR(36)      NOT NULL,

    sk_fecha_salida          INT           NOT NULL,
    sk_fecha_llegada         INT           NOT NULL,
    sk_fecha_reserva         INT           NOT NULL,
    sk_aerolinea             INT           NOT NULL,
    sk_aeropuerto_origen     INT           NOT NULL,
    sk_aeropuerto_destino    INT           NOT NULL,
    sk_aeronave              INT           NOT NULL,
    sk_clase_cabina          INT           NOT NULL,
    sk_estado_vuelo          INT           NOT NULL,
    sk_canal_venta           INT           NOT NULL,
    sk_metodo_pago           INT           NOT NULL,
    sk_moneda                INT           NOT NULL,
    sk_genero                INT           NOT NULL,
    sk_nacionalidad          INT           NOT NULL,

    fecha_hora_salida        DATETIME2(0)  NOT NULL,
    fecha_hora_llegada       DATETIME2(0)  NULL,
    fecha_hora_reserva       DATETIME2(0)  NOT NULL,
    edad_pasajero            TINYINT       NULL,

    duracion_min             SMALLINT      NULL,
    retraso_min              SMALLINT      NULL,
    precio_boleto            DECIMAL(12,2) NOT NULL,
    precio_boleto_usd        DECIMAL(12,2) NOT NULL,
    equipaje_total           TINYINT       NOT NULL,
    equipaje_documentado     TINYINT       NOT NULL,

    CONSTRAINT PK_Hecho_Boleto PRIMARY KEY (sk_boleto),
    CONSTRAINT UQ_Hecho_Boleto_record_id UNIQUE (record_id),

    CONSTRAINT FK_Hecho_FechaSalida    FOREIGN KEY (sk_fecha_salida)       REFERENCES dbo.Dim_Fecha(sk_fecha),
    CONSTRAINT FK_Hecho_FechaLlegada   FOREIGN KEY (sk_fecha_llegada)      REFERENCES dbo.Dim_Fecha(sk_fecha),
    CONSTRAINT FK_Hecho_FechaReserva   FOREIGN KEY (sk_fecha_reserva)      REFERENCES dbo.Dim_Fecha(sk_fecha),
    CONSTRAINT FK_Hecho_Aerolinea      FOREIGN KEY (sk_aerolinea)          REFERENCES dbo.Dim_Aerolinea(sk_aerolinea),
    CONSTRAINT FK_Hecho_Origen         FOREIGN KEY (sk_aeropuerto_origen)  REFERENCES dbo.Dim_Aeropuerto(sk_aeropuerto),
    CONSTRAINT FK_Hecho_Destino        FOREIGN KEY (sk_aeropuerto_destino) REFERENCES dbo.Dim_Aeropuerto(sk_aeropuerto),
    CONSTRAINT FK_Hecho_Aeronave       FOREIGN KEY (sk_aeronave)           REFERENCES dbo.Dim_Aeronave(sk_aeronave),
    CONSTRAINT FK_Hecho_ClaseCabina    FOREIGN KEY (sk_clase_cabina)       REFERENCES dbo.Dim_ClaseCabina(sk_clase_cabina),
    CONSTRAINT FK_Hecho_EstadoVuelo    FOREIGN KEY (sk_estado_vuelo)       REFERENCES dbo.Dim_EstadoVuelo(sk_estado_vuelo),
    CONSTRAINT FK_Hecho_CanalVenta     FOREIGN KEY (sk_canal_venta)        REFERENCES dbo.Dim_CanalVenta(sk_canal_venta),
    CONSTRAINT FK_Hecho_MetodoPago     FOREIGN KEY (sk_metodo_pago)        REFERENCES dbo.Dim_MetodoPago(sk_metodo_pago),
    CONSTRAINT FK_Hecho_Moneda         FOREIGN KEY (sk_moneda)             REFERENCES dbo.Dim_Moneda(sk_moneda),
    CONSTRAINT FK_Hecho_Genero         FOREIGN KEY (sk_genero)             REFERENCES dbo.Dim_Genero(sk_genero),
    CONSTRAINT FK_Hecho_Nacionalidad   FOREIGN KEY (sk_nacionalidad)       REFERENCES dbo.Dim_Nacionalidad(sk_nacionalidad),

    CONSTRAINT CK_Hecho_Precio         CHECK (precio_boleto >= 0 AND precio_boleto_usd >= 0),
    CONSTRAINT CK_Hecho_Equipaje       CHECK (equipaje_documentado <= equipaje_total)
);
GO

CREATE INDEX IX_Hecho_Aerolinea    ON dbo.Hecho_Boleto (sk_aerolinea);
CREATE INDEX IX_Hecho_FechaSalida  ON dbo.Hecho_Boleto (sk_fecha_salida);
CREATE INDEX IX_Hecho_Ruta         ON dbo.Hecho_Boleto (sk_aeropuerto_origen, sk_aeropuerto_destino);
GO
