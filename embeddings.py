# OBJETIVO: Generar embeddings con un modelo local y guardarlos en Neon
#           usando una función limpia y aislamiento real por empresa.
from conexion import MODELO, conectar, embedding
from db.data import academia, gimnasio

conn = conectar()

# Vaciamos la tabla antes de empezar y reiniciamos los IDs a 1
# así evitamos duplicar frases si ejecutamos el script varias veces
with conn.transaction():
    conn.execute("TRUNCATE documentos RESTART IDENTITY;")

# Definimos una única función reutilizable para cualquier empresa
def guardar_tenant(nombre_empresa: str, lista_frases: list[str]):
    """
    Convierte una lista de frases en vectores de 384 números y los guarda
    en Neon bajo el candado de seguridad (RLS) de 'nombre_empresa'.
    """
    # La IA traduce las 5 frases de esta empresa en 5 listas de 384 números
    vectores = embedding(lista_frases)
    print(f"Modelo {MODELO} [{nombre_empresa}]: {len(vectores)} embeddings generados")

    # Abrimos una transacción
    with conn.transaction():
        # Activamos el candado RLS: indicamos a Neon qué empresa entra ahora.
        # El 'true' borra esta credencial al terminar el bloque para no mezclar datos.
        conn.execute("SELECT set_config('app.tenant_id', %s, true);", (nombre_empresa,))

        # Guardamos cada frase original junto con su vector y su empresa
        for texto, emb in zip(lista_frases, vectores):
            conn.execute(
                "INSERT INTO documentos (texto, embedding, tenant_id) VALUES (%s, %s, %s);",
                (texto, emb, nombre_empresa)
            )

    print(f"Listo: {len(lista_frases)} frases guardadas para '{nombre_empresa}'.")


# Llamamos a la función para cada empresa
guardar_tenant("academia", academia)
guardar_tenant("gimnasio", gimnasio)

# Comprobación rápida de aislamiento:
# Verificamos cuántas filas puede ver cada empresa por separado.
print("\nComprobación de aislamiento tras guardado:")
for empresa in ("academia", "gimnasio"):
    with conn.transaction():
        conn.execute("SELECT set_config('app.tenant_id', %s, true);", (empresa,))
        total = conn.execute("SELECT count(*) FROM documentos;").fetchone()[0]
        print(f"  - Filas visibles para '{empresa}': {total}")

conn.close()
