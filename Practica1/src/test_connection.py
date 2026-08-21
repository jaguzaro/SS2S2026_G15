import pyodbc
from sqlalchemy import create_engine

# Cadena de conexión usando autenticación integrada de Windows
connection_string = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=(localdb)\\mssqllocaldb;"
    "DATABASE=master;"
    "Trusted_Connection=yes;"
)

try:
    # 1. Prueba con pyodbc
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    cursor.execute("SELECT @@VERSION;")
    row = cursor.fetchone()
    print(" Conexión pyodbc exitosa:")
    print(f"   {row[0][:60]}...\n")
    conn.close()

    # 2. Prueba con SQLAlchemy
    engine = create_engine(f"mssql+pyodbc:///?odbc_connect={connection_string}")
    with engine.connect() as engine_conn:
        print(" Conexión SQLAlchemy exitosa.")

except Exception as e:
    print(" Error de conexión:")
    print(e)