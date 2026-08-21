import pyodbc

conexion = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost;"
    "DATABASE=VuelosDW;"
    "Trusted_Connection=yes;"
)

print("¡Conexión exitosa con SQL Server!")

conexion.close()
