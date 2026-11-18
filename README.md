# Búsqueda Semántica Multi-Tenant con PostgreSQL + pgvector

Implementación de un sistema de búsqueda semántica multi-inquilino (*multi-tenant*) sobre **PostgreSQL (Neon Serverless)** utilizando la extensión **`pgvector`** y embeddings locales gratuitos mediante **`sentence-transformers`**.

El sistema garantiza el **aislamiento real de datos entre empresas** (*tenants*: `academia` y `gimnasio`) a nivel de base de datos, asegurando que cada cliente acceda únicamente a sus propios documentos y recuperando siempre las **2 frases más similares** a una consulta.

---

## Arquitectura y Decisiones Técnicas

* **Modelo de Embeddings Gratuito:** Se utiliza `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 dimensiones) ejecutado en local mediante carga perezosa (*lazy loading* con `_modelo = None`) para ahorrar memoria y tiempo de arranque.
* **Aislamiento Real entre Tenants (Row-Level Security):** Se habilita `ENABLE ROW LEVEL SECURITY` junto con `FORCE ROW LEVEL SECURITY` en PostgreSQL. Cada consulta e inserción se ejecuta dentro de una transacción (`with conn.transaction():`) fijando `set_config('app.tenant_id', ..., true)` para mantener total compatibilidad con *Connection Pooling*.
* **Rendimiento y Escalabilidad:** Se combinan un índice vectorial aproximado **HNSW** (`vector_cosine_ops`) para búsquedas rápidas por distancia coseno (`<=>`) y un índice B-Tree sobre `tenant_id` (`idx_documentos_tenant`).
* **Separación de Responsabilidades:** El esquema SQL está desacoplado de la lógica en Python para evitar duplicidad de código.

---

## Estructura del Proyecto

```text
Databases_para_agentes/
├── .env.example        
├── esquema.sql         
├── conexion.py         
├── setup_db.py        
├── embeddings.py       
├── busqueda.py        
└── db/
    └── data.py        
```

---

## Requisitos e Instalación

1. **Clonar el proyecto y activar el entorno virtual:**
   ```bash
   python -m venv .venv
   # En Windows (PowerShell):
   .\.venv\Scripts\Activate.ps1
   ```

2. **Instalar dependencias:**
   ```bash
   pip install "psycopg[binary]" pgvector sentence-transformers python-dotenv
   ```

3. **Configurar variables de entorno:**
   Crea un archivo `.env` en la raíz del proyecto con tu cadena de conexión de Neon:
   ```env
   NEON_POSTGRE="postgresql://usuario:password@ep-ejemplo.pooler.aws.neon.tech/neondb?sslmode=require"
   ```

---

## Ejecución Paso a Paso

Ejecuta los tres scripts en orden desde la terminal:

```bash
# Paso 1: Crear extensión pgvector, tabla 'documentos', índices HNSW y seguridad RLS
python setup_db.py

# Paso 2: Generar embeddings (384 dims) y guardar las 5 frases de cada tenant bajo llave
python embeddings.py

# Paso 3: Ejecutar consulta semántica y recuperar las 2 frases más parecidas por empresa
python busqueda.py
```

*(Opcional)* También se puede pasar una consulta personalizada directamente desde la terminal:
```bash
python busqueda.py "¿Cómo cancelo una clase?"
```

---

## Ejemplo de Salida

### 1. Consulta sobre plazos de cancelación
**Pregunta:** `"¿Con cuánto tiempo tengo que avisar para cancelar?"`  
Recupera las políticas de cancelación específicas de cada negocio (`similitud 0.551` en `ACADEMIA` y `0.623` en `GIMNASIO`):

![Pregunta 1](img/pregunta1.png)

### 2. Consulta semántica por sinónimos (Descuentos y tarifas)
**Pregunta:** `"¿Tenéis algún descuento o tarifa especial?"`  
Demuestra comprensión semántica al relacionar *"descuentos especiales"* en `ACADEMIA` (`0.534`) con *"tarifas reducidas"* en `GIMNASIO` (`0.402`):

![Pregunta 2](img/pregunta2.png)

### 3. Consulta sobre clase o día de prueba gratuito
**Pregunta:** `"¿Puedo probar una clase gratis el primer día?"`  
Recupera la política de prueba inicial de `GIMNASIO` (`similitud 0.680`) manteniendo completamente aislados los registros de `ACADEMIA`:

![Pregunta 3](img/pregunta3.png)

### 4. Consulta específica de un solo tenant (Prueba máxima de aislamiento)
**Pregunta:** `"¿Se pueden descargar los apuntes en PDF y grabaciones desde el campus virtual?"`  
`ACADEMIA` alcanza una similitud casi exacta de **0.918** (`distancia 0.082`), mientras que `GIMNASIO` únicamente puede consultar sus propios registros devolviendo similitudes bajas (**0.193** y **0.157**), confirmando que **Row-Level Security (RLS)** impide cualquier fuga de información entre *tenants*:

![Pregunta 4](img/pregunta4.png)
