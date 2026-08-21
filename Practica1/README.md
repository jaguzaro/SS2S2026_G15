# Práctica 1: Proceso ETL con Python y Modelo Dimensional en SQL Server

* **Curso:** Seminario de Sistemas 2 
* **Grupo:** SS2S2026_G15
* **Entorno de Trabajo:** Windows PowerShell | Python 3.10+ | SQL Server (LocalDB)

                 PROYECTO PYTHON
                       │
             ┌─────────┴─────────┐
             │                   │
           pyodbc             SQLAlchemy
          5.3.0               2.0.52
             │                   │
             └─────────┬─────────┘
                       │
             ODBC Driver 17
                       │
                       ▼
            SQL Server 2025
             MSSQLSERVER
                       │
                       ▼
                  master

---

## 1. Resumen Ejecutivo y Marco Formativo

El presente proyecto implementa una solución de Inteligencia de Negocios de extremo a extremo (End-to-End). Se diseñó e implementó un proceso ETL (Extracción, Transformación y Carga) en **Python 3.10** que procesa información heterogénea de registros de aviación comercial (`dataset_vuelos_crudo.csv`) y la estructura en un **Modelo Dimensional (Esquema en Estrella)** alojado en **Microsoft SQL Server**.

### Objetivos Alcanzados:
* **Extracción Robusta:** Carga completa en memoria de 10,000 registros conservando los tipos de texto crudo (`dtype=str`) para evitar la corrupción de datos numéricos y de moneda.
* **Transformación y Limpieza:** Homologación de campos, estandarización de catálogos y tratamiento inteligente de inconsistencias de fechas sin pérdida de registros.
* **Carga Optimizada:** Integración por lotes (*bulk loading*) mediante **SQLAlchemy** vinculando llaves subrogadas (*Surrogate Keys*) previamente resueltas.
* **Verificación Analítica:** Soporte total para consultas analíticas de negocio (Conteos, Top 5, Distribuciones, Análisis de Retrasos).

---

## 2. Estructura del Repositorio

El proyecto cumple con la nomenclatura y jerarquía estandarizada exigida para el laboratorio:

```text
SS2S2026_G15/
└── Practica1/
    ├── docs/
    │   ├── diagrama_modelo.png       # Diagrama Entidad-Relación / Modelo Dimensional
    │   └── Documentacion_Tecnica.pdf # Copia oficial en PDF (opcional)
    ├── sql/
    │   ├── schema.sql                # DDL: Creación de BD y Tablas del Modelo
    │   └── analytics.sql             # DML: Consultas analíticas y validación de carga
    ├── src/
    │   ├── dataset_vuelos_crudo.csv  # Dataset fuente (10,000 registros, 1.9 MB)
    │   └── etl.py                    # Código fuente del pipeline ETL en Python
    ├── .gitignore                    # Reglas de exclusión (venv, temporales)
    ├── README.md                     # Documentación técnica principal del proyecto
    └── requirements.txt              # Dependencias del proyecto congeladas con pip