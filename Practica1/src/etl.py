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
UNKNOWN_SK = -1     # el dato existe pero no se conoce
NO_APLICA_SK = -2   # el dato no existe para ese hecho

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
    # El ODBC Driver 18 cifra la conexion por defecto y rechaza los
    # certificados autofirmados. Poner DB_TRUST_CERT=yes permite trabajar
    # contra una instancia local o un contenedor sin certificado propio.
    trust_cert: bool = os.getenv("DB_TRUST_CERT", "").strip().lower() in {"1", "yes", "true", "si"}

    def connection_url(self) -> str:
        driver_q = self.driver.replace(" ", "+")
        extra = "&TrustServerCertificate=yes" if self.trust_cert else ""
        if self.user:
            return (
                f"mssql+pyodbc://{self.user}:{self.password}@{self.server}/"
                f"{self.database}?driver={driver_q}{extra}"
            )
        # Autenticacion de Windows (Trusted_Connection)
        return (
            f"mssql+pyodbc://@{self.server}/{self.database}"
            f"?driver={driver_q}&trusted_connection=yes{extra}"
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


def _es_vacio(value) -> bool:
    """Un valor se considera ausente si es None, si pandas lo marca como
    faltante (pd.NA en las columnas de texto, NaN en las numericas) o si
    es una cadena que queda vacia al quitarle los espacios, con lo que
    '' y ' ' reciben el mismo trato.

    Se comprueba pd.isna antes de convertir a texto porque str(pd.NA)
    devuelve la cadena '<NA>'. Deliberadamente NO se tratan como ausentes
    los textos que se parecen a un nulo, como 'NULL', 'N/A' o 'nan': eso
    es un dato presente con contenido cuestionable, y convertirlo en
    silencio ocultaria un problema de la fuente. El archivo de esta
    practica no trae ninguno."""
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    return str(value).strip() == ""


BARRAS_DDMM = "%d/%m/%Y %H:%M"
BARRAS_MMDD = "%m/%d/%Y %H:%M"
GUIONES     = "%m-%d-%Y %I:%M %p"

# Banda en la que se acepta que (llegada - salida) reproduce duration_min.
# Medida sobre las 5,718 filas cuyas dos fechas son inequivocas: el error
# va de -10 a +262 minutos con mediana de 12. Un dia y un mes
# intercambiados desplazan la fecha por dias o meses, ordenes de magnitud
# fuera de esta banda.
BANDA_LLEGADA = (-20, 300)


def _parse_datetime_flexible(value: str | float | None) -> pd.Timestamp | None:
    """Lectura por defecto: barras como dd/mm/yyyy y, si no encaja, el
    formato con guiones mm-dd-yyyy hh:MM AM/PM."""
    if _es_vacio(value):
        return pd.NaT
    text_val = str(value).strip()
    for fmt in (BARRAS_DDMM, GUIONES):
        try:
            return pd.to_datetime(text_val, format=fmt)
        except ValueError:
            continue
    log.warning("Fecha no reconocida en ningun formato: %r", text_val)
    return pd.NaT


def _candidatos_fecha(value) -> list:
    """Todas las lecturas posibles de una fecha, en orden de preferencia.

    El formato con guiones es inequivoco. El de barras es dd/mm/yyyy: lo
    confirman las 4,555 salidas, 4,339 llegadas y 4,549 reservas cuyo
    primer numero pasa de 12, contra cero filas del archivo que obliguen
    a leerlo como mm/dd. Pero cuando los dos numeros son 12 o menos la
    fecha es ambigua y hay que decidir con el resto de la fila."""
    if _es_vacio(value):
        return []
    text_val = str(value).strip()
    vistos, salida = set(), []
    for fmt in (BARRAS_DDMM, BARRAS_MMDD, GUIONES):
        try:
            ts = pd.to_datetime(text_val, format=fmt)
        except ValueError:
            continue
        if ts not in vistos:
            vistos.add(ts)
            salida.append(ts)
    return salida


def _cumple_reglas(salida, llegada, reserva, duracion) -> int:
    """Cuenta cuantas de las dos reglas de negocio satisface una
    combinacion de lecturas: que la llegada reproduzca duration_min y que
    la reserva no sea posterior a la salida. Una fecha ausente no
    incumple nada."""
    reglas = 0
    if llegada is None or duracion is None:
        reglas += 1
    else:
        lo, hi = BANDA_LLEGADA
        if lo <= (llegada - salida).total_seconds() / 60 - duracion <= hi:
            reglas += 1
    if reserva is None or reserva <= salida:
        reglas += 1
    return reglas


def _resolver_fechas(salida_raw, llegada_raw, reserva_raw, duracion):
    """Elige la combinacion de lecturas de las tres fechas que cumple mas
    reglas de negocio.

    Las tres columnas de fecha del archivo son ambiguas cuando el dia y el
    mes son ambos 12 o menos, y ninguna se puede resolver aisladamente:
    hay salidas que solo se aclaran con la reserva y llegadas que solo se
    aclaran con la duracion. Por eso se evaluan juntas.

    A igual cumplimiento gana la lectura dd/mm, que es la del resto del
    archivo; el desempate por el indice del candidato evita reinterpretar
    fechas que ya eran coherentes."""
    cand_sal = _candidatos_fecha(salida_raw) or [pd.NaT]
    cand_lle = _candidatos_fecha(llegada_raw) or [None]
    cand_res = _candidatos_fecha(reserva_raw) or [None]

    mejor, mejor_puntaje = None, None
    for i, sal in enumerate(cand_sal):
        for j, lle in enumerate(cand_lle):
            for k, res in enumerate(cand_res):
                puntaje = _cumple_reglas(sal, lle, res, duracion) * 10 - (i + j + k)
                if mejor_puntaje is None or puntaje > mejor_puntaje:
                    mejor_puntaje, mejor = puntaje, (sal, lle, res)

    sal, lle, res = mejor
    return sal, (pd.NaT if lle is None else lle), (pd.NaT if res is None else res)


def _date_key(ts: pd.Timestamp | None) -> int:
    if ts is None or pd.isna(ts):
        return UNKNOWN_SK
    return int(ts.strftime("%Y%m%d"))


def _clean_price(value: str | float | None) -> float | None:
    if _es_vacio(value):
        return None
    text_val = str(value).strip().replace(",", ".")
    try:
        return float(text_val)
    except ValueError:
        log.warning("Precio no numerico: %r", value)
        return None


def _clean_numeric(value: str | float | None) -> float | None:
    if _es_vacio(value):
        return None
    try:
        return float(str(value).strip())
    except ValueError:
        return None


def transform(df_raw: pd.DataFrame) -> pd.DataFrame:
    log.info("TRANSFORMACION: iniciando limpieza de %d registros", len(df_raw))
    df = df_raw.copy()

    for col in ["airline_code", "aircraft_type", "cabin_class", "status",
                "payment_method", "currency"]:
        df[col] = df[col].astype("string").str.strip()

    if "airline_name" in df.columns:
        df = df.drop(columns=["airline_name"])

    df["origin_airport"] = df["origin_airport"].astype("string").str.strip().str.upper()
    df["destination_airport"] = df["destination_airport"].astype("string").str.strip().str.upper()

    df["passenger_gender_clean"] = df["passenger_gender"].map(GENDER_MAP)
    faltantes_genero = df["passenger_gender_clean"].isna().sum()
    if faltantes_genero:
        log.warning("%d valores de genero no reconocidos por el mapeo", faltantes_genero)

    df["passenger_nationality_clean"] = (
        df["passenger_nationality"].astype("string").str.strip().str.upper()
    )
    df.loc[df["passenger_nationality_clean"] == "", "passenger_nationality_clean"] = pd.NA

    df["sales_channel_clean"] = df["sales_channel"].astype("string").str.strip()
    df.loc[df["sales_channel_clean"] == "", "sales_channel_clean"] = pd.NA

    df["ticket_price_clean"] = df["ticket_price"].apply(_clean_price)
    df["ticket_price_usd_clean"] = df["ticket_price_usd_est"].apply(_clean_price)

    df["duration_min_clean"] = df["duration_min"].apply(_clean_numeric)
    df["delay_min_clean"] = df["delay_min"].apply(_clean_numeric)
    df["passenger_age_clean"] = df["passenger_age"].apply(_clean_numeric)

    df["seat_clean"] = df["seat"].astype("string").str.strip()
    df.loc[df["seat_clean"] == "", "seat_clean"] = pd.NA

    ingenuas = [
        (
            _parse_datetime_flexible(sal),
            _parse_datetime_flexible(lle),
            _parse_datetime_flexible(res),
        )
        for sal, lle, res in zip(
            df["departure_datetime"], df["arrival_datetime"], df["booking_datetime"]
        )
    ]
    resueltas = [
        _resolver_fechas(sal, lle, res, dur)
        for sal, lle, res, dur in zip(
            df["departure_datetime"], df["arrival_datetime"],
            df["booking_datetime"], df["duration_min_clean"],
        )
    ]

    df["departure_ts"] = [t[0] for t in resueltas]
    df["arrival_ts"] = [t[1] for t in resueltas]
    df["booking_ts"] = [t[2] for t in resueltas]

    cambios = [0, 0, 0]
    incoherentes = 0
    for (ing, res) in zip(ingenuas, resueltas):
        for i in range(3):
            if pd.notna(res[i]) and res[i] != ing[i]:
                cambios[i] += 1
    for (sal, lle, res), dur in zip(resueltas, df["duration_min_clean"]):
        if _cumple_reglas(sal, None if pd.isna(lle) else lle,
                          None if pd.isna(res) else res, dur) < 2:
            incoherentes += 1

    log.info(
        "TRANSFORMACION: fechas releidas como mm/dd -> salidas=%d, llegadas=%d, reservas=%d",
        cambios[0], cambios[1], cambios[2],
    )
    if incoherentes:
        log.warning(
            "TRANSFORMACION: %d registros siguen incumpliendo alguna regla temporal",
            incoherentes,
        )
    else:
        log.info("TRANSFORMACION: las 3 fechas de los 10,000 registros quedan coherentes")

    df["sk_fecha_salida"] = df["departure_ts"].apply(_date_key)
    df["sk_fecha_llegada"] = df["arrival_ts"].apply(_date_key)
    df["sk_fecha_reserva"] = df["booking_ts"].apply(_date_key)


    log.info("TRANSFORMACION: limpieza completada")

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

    fact["record_id"] = df["record_id"]
    fact["numero_vuelo"] = df["flight_number"]
    fact["asiento"] = df["seat_clean"]
    fact["id_pasajero"] = df["passenger_id"]

    fact["sk_fecha_salida"] = df["sk_fecha_salida"]
    # Un vuelo cancelado no tiene hora de llegada porque nunca ocurrio, no
    # porque se desconozca. Su llave apunta al miembro NO APLICA y no al de
    # DESCONOCIDO, para no mezclar las dos ausencias en el mismo cubo.
    cancelado = df["status"].astype("string").str.strip().eq("CANCELLED")
    fact["sk_fecha_llegada"] = [
        NO_APLICA_SK if (sk == UNKNOWN_SK and canc) else sk
        for sk, canc in zip(df["sk_fecha_llegada"], cancelado)
    ]
    fact["sk_fecha_reserva"] = df["sk_fecha_reserva"]

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

    fact["fecha_hora_salida"] = df["departure_ts"]
    fact["fecha_hora_llegada"] = df["arrival_ts"]
    fact["fecha_hora_reserva"] = df["booking_ts"]
    fact["edad_pasajero"] = df["passenger_age_clean"]

    fact["duracion_min"] = df["duration_min_clean"]
    fact["retraso_min"] = df["delay_min_clean"]
    fact["precio_boleto"] = df["ticket_price_clean"]
    fact["precio_boleto_usd"] = df["ticket_price_usd_clean"]
    fact["equipaje_total"] = df["bags_total"]
    fact["equipaje_documentado"] = df["bags_checked"]

    log.info("CARGA: tabla de hechos construida con %d filas", len(fact))
    return fact


def load(fact: pd.DataFrame, engine: Engine, chunksize: int = 1000) -> None:
    with engine.begin() as conn:
        borradas = conn.execute(text("DELETE FROM dbo.Hecho_Boleto")).rowcount
    if borradas > 0:
        log.info("CARGA: se eliminaron %d filas de una corrida anterior", borradas)

    log.info("CARGA: insertando %d filas en Hecho_Boleto", len(fact))
    fact.to_sql(
        "Hecho_Boleto",
        con=engine,
        if_exists="append",
        index=False,
        chunksize=chunksize,
    )
    log.info("CARGA: insercion completada")


def validate_load(engine: Engine, expected_rows: int) -> None:
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