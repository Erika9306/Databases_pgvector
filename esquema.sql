-- OBJETIVO: Definir la estructura de la base de datos en Neon
--  (pgvector, tabla 'documentos', índices HNSW y seguridad RLS).


-- ACTIVAR PGVECTOR:
-- Enciende el "superpoder" de PostgreSQL para guardar y comparar vectores.
CREATE EXTENSION IF NOT EXISTS vector;

--  CREAR TABLA 'documentos':
-- Borramos la tabla si existía de una prueba anterior para empezar limpios.
DROP TABLE IF EXISTS documentos;

-- Creamos nuestro "archivador" con 4 columnas:
-- - id: Número automático
-- - texto: La frase original en español
-- - embedding: Los 384 números que representan su significado
-- - tenant_id: El nombre de la empresa dueña de esa frase ('academia' o 'gimnasio')
CREATE TABLE documentos (
    id         SERIAL PRIMARY KEY,
    texto      TEXT NOT NULL,
    embedding  VECTOR(384) NOT NULL,
    tenant_id  TEXT NOT NULL
);

-- ÍNDICES PARA RENDIMIENTO (VELOCIDAD Y ESCALABILIDAD):
-- Aceleran tanto el filtro por empresa como la búsqueda de vectores cercanos (HNSW).
-- Evita leer fila por fila cuando haya miles o millones de documentos.
CREATE INDEX idx_documentos_tenant ON documentos (tenant_id);
CREATE INDEX documentos_embedding_hnsw ON documentos USING hnsw (embedding vector_cosine_ops);

-- AISLAMIENTO REAL ENTRE EMPRESAS (ROW-LEVEL SECURITY / RLS):
-- Activamos el guardia de seguridad interno de PostgreSQL para que cada empresa
-- vea y guarde ÚNICAMENTE sus propias filas.
ALTER TABLE documentos ENABLE ROW LEVEL SECURITY;

-- FORCE obliga a que el guardia vigile SIEMPRE..
ALTER TABLE documentos FORCE ROW LEVEL SECURITY;

-- Solo muestra (USING) o permite insertar (WITH CHECK) filas
-- cuyo 'tenant_id' coincida con la credencial activa 'app.tenant_id'.
CREATE POLICY aislamiento_tenant ON documentos
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
