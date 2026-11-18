#  Busqueda por similitud: devuelve los 2 textos mas parecidos en ambas
#  empresas garantizando que nunca se mezclen sus datos.

# Permite leer si una pregunta en la terminal al ejecutar.
import sys  
from conexion import conectar, embedding

# Lee una pregunta en la terminal (ej: python busqueda.py "¿Puedo probar gratis?"),
# la usa (sys.argv[1]). Si ejecutamos 'python busqueda.py' a secas, usa la pregunta por defecto.
pregunta = sys.argv[1] if len(sys.argv) > 1 else "¿Cuál es vuestro horario y puedo probar gratis?"

conn = conectar()

# Convertimos la pregunta en una lista de 384 números con el MISMO modelo
q = embedding(pregunta)


# FUNCIÓN PARA BUSCAR EN UNA EMPRESA CONCRETA CON  SEGURIDAD
def buscar_en_empresa(nombre_empresa: str, limite: int = 2):
    """
    Busca las 'limite' (2) frases más parecidas a 'q' viendo ÚNICAMENTE
    los documentos que pertenecen a 'nombre_empresa'.
    """
    # Abrimos transacción aislada
    with conn.transaction():
        # Enseñamos la credencial al guardia (RLS): Neon oculta las demás empresas
        conn.execute("SELECT set_config('app.tenant_id', %s, true);", (nombre_empresa,))

        # <=> calcula la distancia coseno (0 = mismo significado).
        # WHERE tenant_id = %s filtra por empresa y aprovecha el índice.
        # ORDER BY ordena de más parecida a menos parecida.       
        resultados = conn.execute("""
            SELECT texto, embedding <=> %s AS distancia
            FROM documentos
            WHERE tenant_id = %s
            ORDER BY embedding <=> %s
            LIMIT %s;
        """, (q, nombre_empresa, q, limite)).fetchall()

    # Mostramos los resultados de empresa en pantalla
    print(f"\n--- RESULTADOS PARA '{nombre_empresa.upper()}' ---")
    for i, (texto, distancia) in enumerate(resultados, 1):
        # '1 - distancia' convierte la distancia en nota de parecido (1.0 = 100% igual)
        print(f"{i}. distancia {distancia:.3f} · similitud {1 - distancia:.3f} | {texto}")


# EJECUTAMOS LA MISMA PREGUNTA EN AMBAS EMPRESAS PARA DEMOSTRAR EL AISLAMIENTO
print(f"Pregunta: {pregunta}")

buscar_en_empresa("academia", limite=2)
buscar_en_empresa("gimnasio", limite=2)

conn.close()
