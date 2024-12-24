# Ingeniero de Datos en NEQUI: Prueba Técnica

## Índice

1. [Introducción](#introducción)
2. [Objetivo del Proyecto](#objetivo-del-proyecto)
3. [Alcance y Elección del Dataset](#alcance-y-elección-del-dataset)
4. [Arquitectura Propuesta](#arquitectura-propuesta)
5. [Exploración y Evaluación de los Datos (EDA)](#exploración-y-evaluación-de-los-datos-eda)
6. [Modelo de Datos](#modelo-de-datos)
7. [Ejecución de la ETL](#ejecución-de-la-etl)
8. [Pruebas, Logs y Manejo de Excepciones](#pruebas-logs-y-manejo-de-excepciones)
9. [Resultados de Pruebas de Rendimiento](#resultados-de-pruebas-de-rendimiento)
10. [Análisis y Conclusiones](#análisis-y-conclusiones)
11. [Escenarios y Escalabilidad](#escenarios-y-escalabilidad)
12. [Cómo Ejecutar este Proyecto](#cómo-ejecutar-este-proyecto)
13. [Repositorio y Referencias](#repositorio-y-referencias)

------

## Introducción

Este proyecto surge como parte de la **Prueba Técnica** para un rol de **Ingeniero de Datos** en NEQUI. El objetivo es poner a prueba las habilidades de ingeniería de datos, desde la recopilación y análisis de grandes volúmenes de datos, hasta el diseño y la implementación de pipelines de ETL y la posterior verificación de la calidad de estos datos en distintas bases de datos (local y en la nube).

------

## Objetivo del Proyecto

1. **Validar habilidades** en ingeniería de datos: diseño de arquitecturas, selección de herramientas, manipulación de grandes volúmenes de datos (más de 1 millón de filas).
2. **Diseñar, desarrollar e implementar** un pipeline de datos (ETL) que abarque las fases de extracción, transformación y carga.
3. **Garantizar la calidad** del flujo de datos y la correcta modelación en una base de datos relacional tanto local como en AWS.
4. **Analizar** el desempeño de consultas concurrentes en distintas configuraciones y proponer optimizaciones o ajustes para una arquitectura escalable.

------

## Alcance y Elección del Dataset

- Se eligió un dataset público simulado de **transacciones bancarias** con más de 1 millón de registros (aprox. 1.004.480 filas).
- Uso Final:
  - Generación de reportes y tablas de análisis.
  - Posible alimentación de aplicaciones de backend.
  - Almacenamiento histórico en una base de datos central (fuente de verdad).

------

## Arquitectura Propuesta

La arquitectura seleccionada incluye los siguientes componentes:

1. **Fuente de Datos**: Archivo CSV grande con más de 1 millón de filas.
2. Procesamiento (ETL):
   - **Script Python** principal (`main.py`) que realiza la lectura del CSV, validaciones básicas y la carga a las bases de datos.
   - **EDA (Exploratory Data Analysis)** para evaluar la calidad de datos.
   - **Transformaciones** en caso de ser necesarias (parseo de fechas, valores nulos, etc.).
3. Bases de Datos:
   - **Local**: PostgreSQL en un contenedor Docker.
   - **AWS RDS**: PostgreSQL en la nube.
4. Herramientas y Tecnologías:
   - **Python** + librerías (psycopg2, pandas, concurrent.futures).
   - **Docker** + `docker-compose.yml` para levantar el contenedor de PostgreSQL local.
   - **AWS RDS** para la base de datos PostgreSQL en la nube.
   - **Logging** con la librería nativa de Python (`logging`).
5. Frecuencia de Actualización:
   - Para efectos de la prueba, se consideró una carga completa (carga inicial). En un ambiente productivo, se recomendaría un **cargue incremental** programado (por ejemplo, diariamente o semanalmente) en función de la criticidad de la información.

A alto nivel, el diagrama de arquitectura es el siguiente:

```
scssCopy code[CSV File] 
     |
     v
[Python ETL (main.py)] 
     |
     |----> Local PostgreSQL (Docker)
     |
     |----> AWS RDS (PostgreSQL)
```

------

## Exploración y Evaluación de los Datos (EDA)

En el **Paso 2** se realizó un proceso de EDA (Exploratory Data Analysis) para asegurar la calidad de los datos.

1. **Conteo de filas**: ~1.004.480.
2. **Columnas**: `Date`, `Domain`, `Location`, `Value`, `Transaction_count`.
3. **Valores nulos**: No se encontraron valores nulos en la muestra.
4. **Duplicados**: No se detectaron filas duplicadas.
5. **Tipos de datos**: Se detectó que las columnas `Value` y `Transaction_count` son numéricas (int64/float64). `Date`, `Domain`, `Location` son de tipo `object`.
6. Rango de valores:
   - `Value`: Mínimo 298,423 / Máximo 1,202,271
   - `Transaction_count`: Mínimo 400 / Máximo 2,548

Estos hallazgos indican que el dataset está bastante limpio y es válido para el proceso de ETL.

------

## Modelo de Datos

Para almacenar esta información, se eligió un **modelo relacional** simple con una sola tabla llamada `bank_transactions`:

```
sqlCopy codeCREATE TABLE IF NOT EXISTS bank_transactions (
    id SERIAL PRIMARY KEY,
    date DATE,
    domain VARCHAR(255),
    location VARCHAR(255),
    value NUMERIC,
    transaction_count INT
);
```

**Razones**:

- Se trata de transacciones bancarias con un esquema muy estructurado (fecha, dominio, localización, valor y conteo de transacciones).
- El esquema relacional facilita la integridad referencial y la realización de consultas analíticas rápidas y directas (por ejemplo, agregaciones por fecha, sumas de valores, etc.).

------

## Ejecución de la ETL

El **Paso 4** incluye la creación de tuberías de datos para cargar la información tanto en la base de datos local como en AWS RDS.

1. **Creación de Tabla**:
   - `create_table_if_not_exists(db_config)` se encarga de crear la tabla `bank_transactions` si no existe.
2. **Limpieza y Transformación**:
   - En este caso, se truncó la tabla antes de cada carga para asegurar un estado limpio.
   - Se hace un parseo básico de la columna `Date` y la conversión de los campos numéricos.
3. **Inserción en Lotes**:
   - Se recorre el CSV línea por línea y se insertan hasta 10.000 registros (límite de ejemplo) para la prueba.
4. **Validación**:
   - Al terminar la inserción, se hace un `SELECT COUNT(*)` para validar la cantidad de filas cargadas.
5. **Diccionario de Datos**:
   - **date** (DATE) – Fecha de la transacción
   - **domain** (VARCHAR) – Categoría/Tipo de la transacción (ej., Restaurante, Recarga, etc.)
   - **location** (VARCHAR) – Ubicación geográfica
   - **value** (NUMERIC) – Monto de la transacción
   - **transaction_count** (INT) – Cantidad de transacciones que tuvieron lugar

------

## Pruebas, Logs y Manejo de Excepciones

- **Pruebas de unidad**: Se realizan de forma implícita al invocar funciones como `create_table_if_not_exists` y `load_csv_to_db`.
- **Logs**: Se configuran en `logging.basicConfig` para capturar tanto la ejecución en consola como en el archivo `logs/data_pipeline.log`.
- **Excepciones**: Se capturan las excepciones más relevantes (e.g., errores de conexión a DB o de lectura de CSV) y se registran en el log.

La estructura de carpetas para este propósito (propuesta) es:

```
cCopy code.
├── main.py
├── logs/
│    └── data_pipeline.log
├── docker-compose.yml
├── bankdataset.csv
└── ...
```

------

## Resultados de Pruebas de Rendimiento

Se realizaron pruebas de consulta concurrente con diferentes cantidades de *threads* (1, 2, 3, 5, 8, 10, 15, 20, 30, 50). Se midió el **tiempo promedio de ejecución** de una consulta `SELECT COUNT(*) ...` sobre la tabla `bank_transactions`.

![output](C:\Users\Camilo Solano\Desktop\nt\output.png)

------

## Análisis y Conclusiones

1. **Tiempo de inserción**:
   - La carga en la DB local fue más rápida (decenas de segundos) comparada con la DB en la nube (varios minutos). Esto se debe a la latencia de red y a que el RDS de AWS está en un entorno remoto.
2. **Query de conteo**:
   - Tanto local como en AWS, la respuesta al `SELECT COUNT(*)` es adecuada. Sin embargo, la latencia en AWS para esta consulta fue consistentemente más alta (entre 0.15-0.17s).
3. **Concurrencia**:
   - En la DB local, el tiempo promedio con 50 threads aumentó (~0.08s), pero aún es competitivo.
   - En la DB AWS, se observa más latencia (~0.17s), predecible para un servicio en la nube con mayor RTT (round-trip time).
4. **Conclusión**:
   - La solución es escalable, se maneja la carga de datos en un volumen significativo (1 millón de filas), y se obtienen tiempos de respuesta aceptables para consultas simples.
   - Para un entorno productivo con mayores volúmenes y mayor concurrencia, se podrían optimizar índices, ajustar tamaños de batch, y explorar opciones de particionado o caching.

------

## Escenarios y Escalabilidad

1. **Si los datos se incrementaran en 100x**
   - Se recomienda escalar la arquitectura:
     - **Particionar tablas** en la base de datos.
     - **Optimizar índices** para permitir consultas rápidas.
     - **Usar procesamiento distribuido** (e.g., Spark, EMR).
     - Almacenar datos fríos en un data lake y datos calientes en la base relacional.
2. **Si las tuberías se ejecutaran diariamente en una ventana de tiempo específica**
   - Implementar un **scheduler** (Airflow, AWS Glue, cron en un contenedor Docker, etc.) para ejecutar la carga en horarios fijos.
   - Manejar cargas incrementales para no recargar la base de datos innecesariamente.
3. **Si la base de datos necesitara ser accedida por más de 100 usuarios funcionales**
   - Escalar la capa de base de datos (instancias más grandes, más CPU/RAM).
   - Configurar **pooling de conexiones** (p.ej., PgBouncer).
4. **Si se requiere hacer analítica en tiempo real**
   - Añadir componentes de **streaming** (Kafka, Kinesis) y bases de datos en tiempo real (Redis, Elasticsearch).
   - Mantener la base transaccional para la persistencia y usar un pipeline en streaming para la analítica en tiempo real.

------

## Cómo Ejecutar este Proyecto

1. Clonar el repositorio:

   ```
   bashCopy codegit clone https://github.com/tu-usuario/nequi_prueba_tecnica.git
   cd nequi_prueba_tecnica
   ```

2. Configurar variables (opcional):

   - Editar en el archivo `main.py` las credenciales de la DB local y de AWS.

3. Levantar la base de datos local:

   ```
   docker-compose up -d
   ```

4. Instalar dependencias:

   ```
   pip install -r requirements.txt
   ```

   (No olvides incluir tu `requirements.txt` con pandas, psycopg2, etc.)

5. Ejecutar el ETL:

   ```
   python main.py
   ```

6. Verificar Logs:

   - Consola: se imprimen logs básicos.
   - Archivo: `logs/data_pipeline.log`.