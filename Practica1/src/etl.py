"""
etl.py — Proceso ETL: dataset_vuelos_crudo.csv -> VuelosDW (SQL Server)

  1. EXTRACCION : lee el CSV crudo de 10,000 registros / 26 columnas.
  2. TRANSFORMACION : homologa aerolineas, aeropuertos, genero,
     nacionalidad, canal de venta, precios y fechas segun las reglas
     documentadas.
  3. CARGA : resuelve cada codigo natural contra las tablas de
     dimension ya pobladas por sql/poblar_dimensiones.sql (el ETL NO
     inserta dimensiones, solo las consulta) y carga Hecho_Boleto.

Requisitos previos (deben haberse ejecutado antes de correr este script):
  sql/crear_modelo.sql        -> crea la base VuelosDW y las 12 tablas
  sql/poblar_dimensiones.sql  -> carga catalogos y el calendario

Uso:
    python etl.py --csv dataset_vuelos_crudo.csv

Configuracion de conexion (variables de entorno, con valores por
defecto entre parentesis):
    DB_SERVER   (localhost)
    DB_NAME     (VuelosDW)
    DB_USER     (si se omite, se usa autenticacion de Windows)
    DB_PASSWORD
    DB_DRIVER   (ODBC Driver 17 for SQL Server)

Librerias: pandas, sqlalchemy, pyodbc
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# --------------------------------------------------------------------------
# Configuracion y logging
# --------------------------------------------------------------------------

LOG_FILE = "etl.log"
UNKNOWN_SK = -1

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("etl_vuelos")


@dataclass
class DBConfig:
    server: str = os.getenv("DB_SERVER", "localhost")
    database: str = os.getenv("DB_NAME", "VuelosDW")
    user: str | None = os.getenv("DB_USER")
    password: str | None = os.getenv("DB_PASSWORD")
    driver: str = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")

    def connection_url(self) -> str:
        driver_q = self.driver.replace(" ", "+")
        if self.user:
            return (
                f"mssql+pyodbc://{self.user}:{self.password}@{self.server}/"
                f"{self.database}?driver={driver_q}"
            )
        # Autenticacion de Windows (Trusted_Connection)
        return (
            f"mssql+pyodbc://@{self.server}/{self.database}"
            f"?driver={driver_q}&trusted_connection=yes"
        )


def get_engine(cfg: DBConfig) -> Engine:
    engine = create_engine(cfg.connection_url(), fast_executemany=True)
    return engine


# --------------------------------------------------------------------------
# 1. EXTRACCION
# --------------------------------------------------------------------------

RAW_DTYPES = {
    "record_id": "Int64",
    "airline_code": "string",
    "airline_name": "string",
    "flight_number": "string",
    "origin_airport": "string",
    "destination_airport": "string",
    "departure_datetime": "string",
    "arrival_datetime": "string",
    "duration_min": "string",
    "status": "string",
    "delay_min": "string",
    "aircraft_type": "string",
    "cabin_class": "string",
    "seat": "string",
    "passenger_id": "string",
    "passenger_gender": "string",
    "passenger_age": "string",
    "passenger_nationality": "string",
    "booking_datetime": "string",
    "sales_channel": "string",
    "payment_method": "string",
    "ticket_price": "string",
    "currency": "string",
    "ticket_price_usd_est": "string",
    "bags_total": "Int64",
    "bags_checked": "Int64",
}


def extract(csv_path: str) -> pd.DataFrame:
    """Lee el CSV crudo tal cual, sin interpretar tipos numericos ni
    fechas todavia (eso ocurre en transform), para no perder el control
    sobre como se homologa cada valor."""
    log.info("EXTRACCION: leyendo %s", csv_path)
    df = pd.read_csv(csv_path, dtype=RAW_DTYPES, keep_default_na=True)
    log.info("EXTRACCION: %d registros, %d columnas leidos", len(df), df.shape[1])
    return df


# --------------------------------------------------------------------------
# 2. TRANSFORMACION
# --------------------------------------------------------------------------

GENDER_MAP = {
    "M": "M", "m": "M", "Masculino": "M", "masculino": "M",
    "F": "F", "f": "F", "Femenino": "F", "femenino": "F",
    "X": "X", "x": "X", "NoBinario": "X", "nobinario": "X",
}


def _parse_datetime_flexible(value: str | float | None) -> pd.Timestamp | None:
    """Intenta dd/mm/yyyy HH:MM y cae a mm-dd-yyyy hh:MM AM/PM si falla,
    tal como describe el documento de modelado."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return pd.NaT
    text_val = str(value).strip()
    if text_val == "" or text_val.lower() == "nan":
        return pd.NaT
    try:
        return pd.to_datetime(text_val, format="%d/%m/%Y %H:%M")
    except ValueError:
        pass
    try:
        return pd.to_datetime(text_val, format="%m-%d-%Y %I:%M %p")
    except ValueError:
        log.warning("Fecha no reconocida en ningun formato: %r", text_val)
        return pd.NaT


def _date_key(ts: pd.Timestamp | None) -> int:
    if ts is None or pd.isna(ts):
        return UNKNOWN_SK
    return int(ts.strftime("%Y%m%d"))


def _clean_price(value: str | float | None) -> float | None:
    """930 registros traen coma decimal (p.ej. '77,60'); hay que
    reemplazarla por punto antes de convertir a numero."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text_val = str(value).strip()
    if text_val == "" or text_val.lower() == "nan":
        return None
    text_val = text_val.replace(",", ".")
    try:
        return float(text_val)
    except ValueError:
        log.warning("Precio no numerico: %r", value)
        return None


def _clean_numeric(value: str | float | None) -> float | None:
    """duration_min, delay_min, passenger_age: se cargan como NULL,
    nunca como cero, cuando vienen vacios."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text_val = str(value).strip()
    if text_val == "" or text_val.lower() == "nan":
        return None
    try:
        return float(text_val)
    except ValueError:
        return None


def transform(df_raw: pd.DataFrame) -> pd.DataFrame:
    log.info("TRANSFORMACION: iniciando limpieza de %d registros", len(df_raw))
    df = df_raw.copy()

    # --- columnas que ya vienen limpias y se usan tal cual -------------
    # airline_code, aircraft_type, cabin_class, status, payment_method,
    # currency, ticket_price_usd_est, bags_total, bags_checked se dejan
    # como estan (solo se recortan espacios por seguridad).
    for col in ["airline_code", "aircraft_type", "cabin_class", "status",
                "payment_method", "currency"]:
        df[col] = df[col].astype("string").str.strip()

    # airline_name se ignora por completo (23 grafias para 12 aerolineas;
    # el codigo IATA ya identifica sin ambiguedad).
    if "airline_name" in df.columns:
        df = df.drop(columns=["airline_name"])

    # --- aeropuertos: mayuscula ----------------------------------------
    df["origin_airport"] = df["origin_airport"].astype("string").str.strip().str.upper()
    df["destination_airport"] = df["destination_airport"].astype("string").str.strip().str.upper()

    # --- genero: homologado a M/F/X -------------------------------------
    df["passenger_gender_clean"] = df["passenger_gender"].map(GENDER_MAP)
    faltantes_genero = df["passenger_gender_clean"].isna().sum()
    if faltantes_genero:
        log.warning("%d valores de genero no reconocidos por el mapeo", faltantes_genero)

    # --- nacionalidad: mayuscula, vacios -> desconocido -----------------
    df["passenger_nationality_clean"] = (
        df["passenger_nationality"].astype("string").str.strip().str.upper()
    )
    df.loc[df["passenger_nationality_clean"] == "", "passenger_nationality_clean"] = pd.NA

    # --- canal de venta: vacios -> desconocido ---------------------------
    df["sales_channel_clean"] = df["sales_channel"].astype("string").str.strip()
    df.loc[df["sales_channel_clean"] == "", "sales_channel_clean"] = pd.NA

    # --- precio: coma decimal -> punto -----------------------------------
    df["ticket_price_clean"] = df["ticket_price"].apply(_clean_price)
    df["ticket_price_usd_clean"] = df["ticket_price_usd_est"].apply(_clean_price)

    # --- numericos que deben quedar NULL, no cero -------------------------
    df["duration_min_clean"] = df["duration_min"].apply(_clean_numeric)
    df["delay_min_clean"] = df["delay_min"].apply(_clean_numeric)
    df["passenger_age_clean"] = df["passenger_age"].apply(_clean_numeric)

    # seat queda como esta (degenerada); solo se limpian vacios a NULL
    df["seat_clean"] = df["seat"].astype("string").str.strip()
    df.loc[df["seat_clean"] == "", "seat_clean"] = pd.NA

    # --- fechas: dos formatos, con caida del primero al segundo ----------
    df["departure_ts"] = df["departure_datetime"].apply(_parse_datetime_flexible)
    df["arrival_ts"] = df["arrival_datetime"].apply(_parse_datetime_flexible)
    df["booking_ts"] = df["booking_datetime"].apply(_parse_datetime_flexible)

    df["sk_fecha_salida"] = df["departure_ts"].apply(_date_key)
    df["sk_fecha_llegada"] = df["arrival_ts"].apply(_date_key)
    df["sk_fecha_reserva"] = df["booking_ts"].apply(_date_key)

    # bags_total / bags_checked ya vienen limpios, se usan tal cual.

    log.info("TRANSFORMACION: limpieza completada")

    # --- reporte rapido de calidad (no altera los datos) -------------------
    n_gender_unk = int((df["passenger_gender_clean"].isna()).sum())
    n_nat_unk = int(df["passenger_nationality_clean"].isna().sum())
    n_channel_unk = int(df["sales_channel_clean"].isna().sum())
    n_lower_origin = int((df["origin_airport"] != df_raw["origin_airport"].astype("string").str.strip()).sum())
    log.info(
        "TRANSFORMACION: genero no mapeado=%d, nacionalidad vacia=%d, "
        "canal vacio=%d, aeropuertos-origen normalizados=%d",
        n_gender_unk, n_nat_unk, n_channel_unk, n_lower_origin,
    )

    return df


# --------------------------------------------------------------------------
# 3. CARGA
# --------------------------------------------------------------------------

# Convencion asumida para las tablas de dimension (creadas por
# crear_modelo.sql / poblar_dimensiones.sql): cada catalogo expone su
# llave subrogada sk_<dim> y un codigo natural sobre el que se hace la
# busqueda. Se documenta explicitamente aqui porque el ETL solo consulta,
# nunca inserta, estas tablas.
DIMENSION_LOOKUPS = {
    "airline_code": ("Dim_Aerolinea", "sk_aerolinea", "codigo"),
    "origin_airport": ("Dim_Aeropuerto", "sk_aeropuerto", "codigo_iata"),
    "destination_airport": ("Dim_Aeropuerto", "sk_aeropuerto", "codigo_iata"),
    "aircraft_type": ("Dim_Aeronave", "sk_aeronave", "codigo"),
    "cabin_class": ("Dim_ClaseCabina", "sk_clase_cabina", "codigo"),
    "status": ("Dim_EstadoVuelo", "sk_estado_vuelo", "codigo"),
    "sales_channel_clean": ("Dim_CanalVenta", "sk_canal_venta", "codigo"),
    "payment_method": ("Dim_MetodoPago", "sk_metodo_pago", "codigo"),
    "currency": ("Dim_Moneda", "sk_moneda", "codigo"),
    "passenger_gender_clean": ("Dim_Genero", "sk_genero", "codigo"),
    "passenger_nationality_clean": ("Dim_Nacionalidad", "sk_nacionalidad", "codigo"),
}


def _load_dimension_maps(engine: Engine) -> dict[str, dict[str, int]]:
    """Carga en memoria cada catalogo (son diminutos, 3-15 filas) como
    un diccionario codigo_normalizado -> llave subrogada, para resolver
    las llaves foraneas del hecho sin una consulta por fila."""
    maps: dict[str, dict[str, int]] = {}
    tables_seen: dict[str, dict[str, int]] = {}
    with engine.connect() as conn:
        for column, (table, sk_col, code_col) in DIMENSION_LOOKUPS.items():
            if table not in tables_seen:
                rows = conn.execute(
                    text(f"SELECT {code_col} AS codigo, {sk_col} AS sk FROM {table}")
                ).fetchall()
                tables_seen[table] = {
                    str(r.codigo).strip().upper(): int(r.sk)
                    for r in rows
                    if r.codigo is not None
                }
                log.info("CARGA: catalogo %s -> %d valores cacheados", table, len(tables_seen[table]))
            maps[column] = tables_seen[table]
    return maps


def _resolve(value, lookup: dict[str, int]) -> int:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return UNKNOWN_SK
    key = str(value).strip().upper()
    return lookup.get(key, UNKNOWN_SK)


def build_fact_table(df: pd.DataFrame, dim_maps: dict[str, dict[str, int]]) -> pd.DataFrame:
    log.info("CARGA: resolviendo llaves foraneas contra las dimensiones")

    fact = pd.DataFrame()

    # --- dimensiones degeneradas -----------------------------------------
    fact["record_id"] = df["record_id"]
    fact["numero_vuelo"] = df["flight_number"]
    fact["asiento"] = df["seat_clean"]
    fact["id_pasajero"] = df["passenger_id"]

    # --- llaves de fecha ---------------------------------------------------
    fact["sk_fecha_salida"] = df["sk_fecha_salida"]
    fact["sk_fecha_llegada"] = df["sk_fecha_llegada"]
    fact["sk_fecha_reserva"] = df["sk_fecha_reserva"]

    # --- llaves resueltas contra catalogos ---------------------------------
    fact["sk_aerolinea"] = df["airline_code"].apply(lambda v: _resolve(v, dim_maps["airline_code"]))
    fact["sk_aeropuerto_origen"] = df["origin_airport"].apply(lambda v: _resolve(v, dim_maps["origin_airport"]))
    fact["sk_aeropuerto_destino"] = df["destination_airport"].apply(lambda v: _resolve(v, dim_maps["destination_airport"]))
    fact["sk_aeronave"] = df["aircraft_type"].apply(lambda v: _resolve(v, dim_maps["aircraft_type"]))
    fact["sk_clase_cabina"] = df["cabin_class"].apply(lambda v: _resolve(v, dim_maps["cabin_class"]))
    fact["sk_estado_vuelo"] = df["status"].apply(lambda v: _resolve(v, dim_maps["status"]))
    fact["sk_canal_venta"] = df["sales_channel_clean"].apply(lambda v: _resolve(v, dim_maps["sales_channel_clean"]))
    fact["sk_metodo_pago"] = df["payment_method"].apply(lambda v: _resolve(v, dim_maps["payment_method"]))
    fact["sk_moneda"] = df["currency"].apply(lambda v: _resolve(v, dim_maps["currency"]))
    fact["sk_genero"] = df["passenger_gender_clean"].apply(lambda v: _resolve(v, dim_maps["passenger_gender_clean"]))
    fact["sk_nacionalidad"] = df["passenger_nationality_clean"].apply(lambda v: _resolve(v, dim_maps["passenger_nationality_clean"]))

    # --- fechas y edad -------------------------------------------------------
    fact["fecha_hora_salida"] = df["departure_ts"]
    fact["fecha_hora_llegada"] = df["arrival_ts"]
    fact["fecha_hora_reserva"] = df["booking_ts"]
    fact["edad_pasajero"] = df["passenger_age_clean"]

    # --- medidas ---------------------------------------------------------
    fact["duracion_min"] = df["duration_min_clean"]
    fact["retraso_min"] = df["delay_min_clean"]
    fact["precio_boleto"] = df["ticket_price_clean"]
    fact["precio_boleto_usd"] = df["ticket_price_usd_clean"]
    fact["equipaje_total"] = df["bags_total"]
    fact["equipaje_documentado"] = df["bags_checked"]

    log.info("CARGA: tabla de hechos construida con %d filas", len(fact))
    return fact


def load(fact: pd.DataFrame, engine: Engine, chunksize: int = 1000) -> None:
    log.info("CARGA: insertando %d filas en Hecho_Boleto", len(fact))
    fact.to_sql(
        "Hecho_Boleto",
        con=engine,
        if_exists="append",
        index=False,
        chunksize=chunksize,
        method="multi",
    )
    log.info("CARGA: insercion completada")


def validate_load(engine: Engine, expected_rows: int) -> None:
    """V1: compara el conteo cargado contra los registros del archivo y
    verifica que no haya duplicados por record_id."""
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM Hecho_Boleto")).scalar()
        duplicados = conn.execute(
            text(
                "SELECT COUNT(*) FROM ("
                "  SELECT record_id FROM Hecho_Boleto"
                "  GROUP BY record_id HAVING COUNT(*) > 1"
                ") d"
            )
        ).scalar()
    log.info(
        "VALIDACION: filas cargadas=%d, esperadas=%d, duplicados=%d",
        total, expected_rows, duplicados,
    )
    if total != expected_rows:
        log.error("VALIDACION: el conteo cargado no coincide con el archivo fuente")
    if duplicados:
        log.error("VALIDACION: se encontraron record_id duplicados en Hecho_Boleto")


# --------------------------------------------------------------------------
# Orquestacion
# --------------------------------------------------------------------------

def run(csv_path: str, cfg: DBConfig) -> None:
    start = datetime.now()
    log.info("=== INICIO PROCESO ETL ===")

    try:
        df_raw = extract(csv_path)
    except FileNotFoundError:
        log.error("No se encontro el archivo fuente: %s", csv_path)
        raise
    except Exception:
        log.exception("Fallo la extraccion del CSV")
        raise

    try:
        df_clean = transform(df_raw)
    except Exception:
        log.exception("Fallo la transformacion de los datos")
        raise

    try:
        engine = get_engine(cfg)
        dim_maps = _load_dimension_maps(engine)
        fact = build_fact_table(df_clean, dim_maps)
        load(fact, engine)
        validate_load(engine, expected_rows=len(df_raw))
    except Exception:
        log.exception("Fallo la fase de carga hacia SQL Server")
        raise

    elapsed = (datetime.now() - start).total_seconds()
    log.info("=== PROCESO ETL FINALIZADO EN %.1f s ===", elapsed)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ETL dataset_vuelos_crudo.csv -> VuelosDW")
    parser.add_argument(
        "--csv",
        default="dataset_vuelos_crudo.csv",
        help="Ruta al archivo CSV fuente (default: dataset_vuelos_crudo.csv)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cfg = DBConfig()
    try:
        run(args.csv, cfg)
    except Exception:
        log.error("El proceso ETL termino con errores. Revise %s para el detalle.", LOG_FILE)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())