import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from sqlalchemy import create_engine, text

# -------------------------------------------------------------------------
# Configuración de Logging
# -------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

DB_CONNECTION_STRING = (
    "mssql+pyodbc:///?odbc_connect="
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=(localdb)\\mssqllocaldb;"
    "DATABASE=BD_Vuelos_Analytics;"
    "Trusted_Connection=yes;"
)

def parse_mixed_datetimes(series: pd.Series) -> pd.Series:
    """
    Parsea las fechas intentando el formato primario 'dd/mm/yyyy HH:MM'.
    Si falla, aplica el formato secundario 'mm-dd-yyyy hh:MM AM/PM'.
    """
    s = series.astype(str).str.strip()
    
    # Intento 1: Formato primario (dd/mm/yyyy HH:MM)
    parsed = pd.to_datetime(s, format='%d/%m/%Y %H:%M', errors='coerce')
    
    # Intento 2: Formato secundario para los NaT restantes (mm-dd-yyyy hh:MM AM/PM)
    missing = parsed.isna() & (s != 'nan') & (s != '')
    if missing.any():
        parsed.loc[missing] = pd.to_datetime(s[missing], format='%m-%d-%Y %I:%M %p', errors='coerce')
        
    return parsed

def fix_swapped_dates(departure: pd.Series, target: pd.Series, is_booking: bool = False) -> pd.Series:
    """
    Inverte el día y el mes cuando se detecta el patrón de error (inconsistencia lógica de fechas):
    - arrival <= departure
    - booking > departure
    """
    corrected = target.copy()
    
    if is_booking:
        mask = (corrected > departure) & corrected.notna() & departure.notna()
    else:
        mask = (corrected <= departure) & corrected.notna() & departure.notna()
        
    # Corregir intercambiando día y mes en los registros afectados
    for idx in corrected[mask].index:
        dt = corrected.loc[idx]
        try:
            # Re-formatear con día y mes invertidos
            corrected.loc[idx] = datetime(dt.year, dt.day, dt.month, dt.hour, dt.minute)
        except ValueError:
            # Si al intercambiar genera una fecha inválida (ej. mes 13), se conserva el valor original
            pass
            
    return corrected

def extract(file_path: str) -> pd.DataFrame:
    """Fase E: Extracción. Lee todo el CSV en memoria forzando dtype=str."""
    logging.info(f"Extrayendo dataset crudo desde: {file_path}")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
    
    df = pd.read_csv(file_path, dtype=str)
    logging.info(f"Extracción completada. Filas procesadas: {len(df)}")
    return df

def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Fase T: Transformación y Limpieza siguiendo los requerimientos del negocio."""
    logging.info("Iniciando Fase de Transformación...")

    # 1. Ignorar airline_name (se utiliza únicamente airline_code)
    if 'airline_name' in df.columns:
        df = df.drop(columns=['airline_name'])

    # 2. Mayúsculas en aeropuertos (origin_airport, destination_airport)
    df['origin_airport'] = df['origin_airport'].str.strip().str.upper()
    df['destination_airport'] = df['destination_airport'].str.strip().str.upper()

    # 3. Homologación de género (12 variantes -> M, F, X)
    gender_map = {
        'M': 'M', 'm': 'M', 'Masculino': 'M', 'masculino': 'M',
        'F': 'F', 'f': 'F', 'Femenino': 'F', 'femenino': 'F',
        'X': 'X', 'x': 'X', 'NoBinario': 'X', 'nobinario': 'X'
    }
    df['passenger_gender'] = df['passenger_gender'].str.strip().map(gender_map).fillna('X')

    # 4. Homologación de Nacionalidad y Canal de Venta (Vacíos asignados a miembro no encontrado: -1)
    df['passenger_nationality'] = df['passenger_nationality'].str.strip().str.upper()
    df['passenger_nationality'] = df['passenger_nationality'].replace({'': '-1', np.nan: '-1'})

    df['sales_channel'] = df['sales_channel'].str.strip().str.upper()
    df['sales_channel'] = df['sales_channel'].replace({'': '-1', np.nan: '-1'})

    # 5. Reemplazo de coma decimal por punto en ticket_price y conversión a float
    df['ticket_price'] = df['ticket_price'].str.replace(',', '.', regex=False)
    df['ticket_price'] = pd.to_numeric(df['ticket_price'], errors='coerce')
    df['ticket_price_usd_est'] = pd.to_numeric(df['ticket_price_usd_est'], errors='coerce')

    # 6. Conversión a entero de passenger_age (Soporta nulos Int64)
    df['passenger_age'] = pd.to_numeric(df['passenger_age'], errors='coerce').astype('Int64')

    # 7. Vuelos cancelados: Cargar duration_min, delay_min y seat como NULL (no 0)
    df['duration_min'] = pd.to_numeric(df['duration_min'], errors='coerce').astype('Int64')
    df['delay_min'] = pd.to_numeric(df['delay_min'], errors='coerce').astype('Int64')
    
    df['seat'] = df['seat'].str.strip()
    df['seat'] = df['seat'].replace({'': None, 'nan': None, np.nan: None})

    # 8. Parseo de Fechas (Atendiendo los dos formatos)
    df['departure_datetime'] = parse_mixed_datetimes(df['departure_datetime'])
    df['arrival_datetime'] = parse_mixed_datetimes(df['arrival_datetime'])
    df['booking_datetime'] = parse_mixed_datetimes(df['booking_datetime'])

    # 9. Corrección de la Trampa de Fechas (Swap día/mes)
    logging.info("Corrigiendo inconsistencias de fechas (llegada anterior a salida y reserva posterior a salida)...")
    df['arrival_datetime'] = fix_swapped_dates(df['departure_datetime'], df['arrival_datetime'], is_booking=False)
    df['booking_datetime'] = fix_swapped_dates(df['departure_datetime'], df['booking_datetime'], is_booking=True)

    logging.info("Transformación completada con éxito.")
    return df

def fetch_dimension_catalog(engine, query: str, key_col: str, val_col: str) -> dict:
    """Consulta un catálogo de dimensión pre-cargado y retorna un diccionario mapeador."""
    with engine.connect() as conn:
        df_dim = pd.read_sql(text(query), conn)
        mapping = dict(zip(df_dim[val_col].astype(str), df_dim[key_col]))
        return mapping

def load(df: pd.DataFrame, engine):
    """Fase L: Carga masiva por lotes asociando Llaves Subrogadas desde los Catálogos pre-cargados."""
    logging.info("Iniciando Fase de Carga hacia la Fact Table (Hecho_Boleto)...")

    # Obtención de diccionarios de mapeo desde las dimensiones ya pre-cargadas
    map_aerolinea = fetch_dimension_catalog(engine, "SELECT aerolinea_key, codigo_aerolinea FROM Dim_Aerolinea", "aerolinea_key", "codigo_aerolinea")
    map_aeropuerto = fetch_dimension_catalog(engine, "SELECT aeropuerto_key, codigo_iata FROM Dim_Aeropuerto", "aeropuerto_key", "codigo_iata")
    map_pasajero = fetch_dimension_catalog(engine, "SELECT pasajero_key, passenger_id_origen FROM Dim_Pasajero", "pasajero_key", "passenger_id_origen")
    map_canal = fetch_dimension_catalog(engine, "SELECT canal_key, codigo_canal FROM Dim_Canal_Venta", "canal_key", "codigo_canal")
    map_metodo = fetch_dimension_catalog(engine, "SELECT metodo_pago_key, codigo_metodo FROM Dim_Metodo_Pago", "metodo_pago_key", "codigo_metodo")

    # Resolviendo Surrogate Keys (-1 si no hay correspondencia)
    df['aerolinea_key'] = df['airline_code'].map(map_aerolinea).fillna(-1).astype(int)
    df['origen_key'] = df['origin_airport'].map(map_aeropuerto).fillna(-1).astype(int)
    df['destino_key'] = df['destination_airport'].map(map_aeropuerto).fillna(-1).astype(int)
    df['pasajero_key'] = df['passenger_id'].map(map_pasajero).fillna(-1).astype(int)
    df['canal_key'] = df['sales_channel'].map(map_canal).fillna(-1).astype(int)
    df['metodo_pago_key'] = df['payment_method'].map(map_metodo).fillna(-1).astype(int)

    # Generación de Llaves de Tiempo (AAAAMMDD como entero; -1 para nulos)
    def date_to_key(dt_series):
        return dt_series.dt.strftime('%Y%m%d').fillna('-1').astype(int)

    df['fecha_salida_key'] = date_to_key(df['departure_datetime'])
    df['fecha_llegada_key'] = date_to_key(df['arrival_datetime'])
    df['fecha_reserva_key'] = date_to_key(df['booking_datetime'])

    # Mapeo final del DataFrame listo para insertar en Hecho_Boleto
    hecho_boleto = pd.DataFrame({
        'record_id': df['record_id'].astype(int),
        'flight_number': df['flight_number'],
        'aerolinea_key': df['aerolinea_key'],
        'origen_key': df['origen_key'],
        'destino_key': df['destino_key'],
        'pasajero_key': df['pasajero_key'],
        'canal_key': df['canal_key'],
        'metodo_pago_key': df['metodo_pago_key'],
        'fecha_salida_key': df['fecha_salida_key'],
        'fecha_llegada_key': df['fecha_llegada_key'],
        'fecha_reserva_key': df['fecha_reserva_key'],
        'status': df['status'],
        'aircraft_type': df['aircraft_type'],
        'cabin_class': df['cabin_class'],
        'seat': df['seat'],
        'departure_datetime': df['departure_datetime'],
        'arrival_datetime': df['arrival_datetime'],
        'booking_datetime': df['booking_datetime'],
        'duration_min': df['duration_min'],
        'delay_min': df['delay_min'],
        'ticket_price': df['ticket_price'],
        'currency': df['currency'],
        'ticket_price_usd_est': df['ticket_price_usd_est'],
        'bags_total': pd.to_numeric(df['bags_total'], errors='coerce').fillna(0).astype(int),
        'bags_checked': pd.to_numeric(df['bags_checked'], errors='coerce').fillna(0).astype(int)
    })

    # Carga por lotes (chunksize) para máxima velocidad
    with engine.begin() as conn:
        hecho_boleto.to_sql(
            name='Hecho_Boleto',
            con=conn,
            if_exists='append',
            index=False,
            chunksize=1000,
            method=None
        )
    
    logging.info(f"Carga por lotes completada. {len(hecho_boleto)} registros insertados en Hecho_Boleto.")

def run_pipeline():
    file_path = os.path.join('src', 'dataset_vuelos_crudo.csv')
    try:
        engine = create_engine(DB_CONNECTION_STRING)
        raw_df = extract(file_path)
        transformed_df = transform(raw_df)
        load(transformed_df, engine)
        logging.info("=== PROCESO ETL COMPLETADO EXITOSAMENTE ===")
    except Exception as e:
        logging.error(f"Error durante el proceso ETL: {str(e)}", exc_info=True)

if __name__ == '__main__':
    run_pipeline()