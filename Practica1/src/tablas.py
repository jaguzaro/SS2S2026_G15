import pyodbc

conexion = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost;"
    "DATABASE=VuelosDW;"
    "Trusted_Connection=yes;"
)

cursor = conexion.cursor()

cursor.execute("""
    SELECT TABLE_SCHEMA, TABLE_NAME
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_TYPE = 'BASE TABLE'
    ORDER BY TABLE_SCHEMA, TABLE_NAME
""")

for tabla in cursor.fetchall():
    print(tabla[0], tabla[1])

conexion.close()