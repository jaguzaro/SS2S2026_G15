# Entorno de trabajo

instalar Python 3
![instalacion de python](img/i_python.png)

En VS Code instala estas extensiones:

Python — Microsoft
Jupyter — Microsoft

En la terminal crear entorno virtual

$ python -m venv .venv
$ .venv\Scripts\activate

si todo esta bien se deberia ver algo asi

(.venv) PS C:\...\Tarea1>

actualizar pip

$ python -m pip install --upgrade pip

Instalar pandas

$ pip install pandas

comprobar la isntalacion

$ python -c "import pandas as pd; print(pd.__version__)"

![instalacion de pandas](img/i_pandas.png)

Instalar Matplotlib

$ pip install matplotlib

comprar la instalacion
$ python -c "import matplotlib; print(matplotlib.__version__)"

![instalacion de matplotlib](img/i_matplotlib.png)

Instalar Seaborn
$ pip install seaborn

comprabar su instalacion 
$ python -c "import seaborn as sns; print(sns.__version__)"

![instalacion de matplotlib](img/i_seaborn.png)
Instalar Jupyter

Para trabajar con el archivo .ipynb:

$ pip install jupyter







## 1. Información general



# Limpieza y Transformación de Datos









## 1. Información general

| Campo | Información |
|---|---|
| **Nombre del proyecto** | Limpieza y Transformación de Datos |
| **Nombre del estudiante** | [Tu nombre completo] |
| **Curso** | [Nombre del curso] |
| **Universidad** | [Nombre de la universidad] |
| **Dataset utilizado** | [Nombre del dataset] |
| **Fuente** | [Kaggle / CSV proporcionado] |
| **Archivo principal** | [nombre_archivo.ipynb / nombre_archivo.py] |

---

## 2. Dataset utilizado

### Nombre del dataset

**[Nombre completo del dataset]**

### Fuente

El dataset utilizado para esta práctica fue obtenido de:

- **Fuente:** [Kaggle / archivo CSV proporcionado]
- **Nombre del archivo:** `[nombre_dataset.csv]`
- **Cantidad de registros iniciales:** [cantidad]
- **Cantidad de columnas:** [cantidad]

### Descripción

[Escribir una breve descripción del dataset. Explicar qué tipo de información contiene y qué representa cada registro.]

Por ejemplo:

> El dataset contiene información relacionada con [tema del dataset]. Cada registro representa [explicar qué representa una fila] y contiene variables relacionadas con [mencionar las principales variables].

---

# 3. Objetivo

El objetivo de esta práctica es realizar un proceso de limpieza y transformación de datos utilizando Python y Pandas, aplicando técnicas para mejorar la calidad, consistencia y confiabilidad de la información.

Durante el proceso se realizaron las siguientes transformaciones:

- Eliminación de registros duplicados.
- Tratamiento de celdas vacías o valores faltantes.
- Estandarización de valores y formatos.
- Verificación de los resultados obtenidos.

---

# 4. Herramientas utilizadas

Las herramientas y tecnologías utilizadas fueron:

- **Python 3**
- **Pandas**
- **Matplotlib** [si aplica]
- **Seaborn** [si aplica]
- **Jupyter Notebook / Google Colab / VS Code**
- **Dataset en formato CSV**

---

# 5. Proceso de limpieza de datos

## 5.1 Carga del dataset

Primero se realizó la carga del archivo CSV utilizando Pandas.

```python
import pandas as pd

df = pd.read_csv("nombre_dataset.csv")

df.head()