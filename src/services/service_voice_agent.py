# src/services/voice_agent_service.py

from google import genai
from google.genai import types

from src.config import GEMINI_API_KEY

client = genai.Client(
    api_key=GEMINI_API_KEY
)

# =====================================================
# CLASIFICADOR
# =====================================================

def clasificar_gasto(descripcion: str) -> str:

    ejemplos = [
        ("Compra supermercado Carrefour", "Viveres"),
        ("Compra en verdulería", "Viveres"),
        ("Carnicería del barrio", "Viveres"),
        ("Agua", "Viveres"),

        ("Carga de nafta", "Transporte"),
        ("Viaje en Uber", "Transporte"),
        ("Pago de taxi", "Transporte"),

        ("Netflix", "Servicios"),
        ("Celular", "Servicios"),
        ("Luz", "Servicios"),
        ("Cable", "Servicios"),
        ("Gas", "Servicios"),
        ("Spotify", "Servicios"),

        ("Entrada al cine", "Entretenimiento"),
        ("Cine", "Entretenimiento"),
        ("Concierto", "Entretenimiento"),
        ("Teatro", "Entretenimiento"),
        ("Videojuegos", "Entretenimiento"),
        ("Pochoclos", "Entretenimiento"),

        ("Pago AWS", "Tecnologia"),
        ("Renovación dominio web", "Tecnologia"),
        ("Servidor VPS", "Tecnologia"),

        ("Consulta médica", "Salud"),
        ("Medicamentos farmacia", "Salud"),

        ("Curso de inglés", "Educacion"),
        ("Compra de libros", "Educacion")
    ]

    categorias = sorted(
        list(
            {
                categoria
                for _, categoria in ejemplos
            }
        )
    )

    prompt = f"""
Clasifica el siguiente gasto.

Descripción:
{descripcion}

Ejemplos:

{chr(10).join(
    f"- {texto} -> {categoria}"
    for texto, categoria in ejemplos
)}

Categorías disponibles:

{", ".join(categorias)}

Devuelve únicamente el nombre de la categoría.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=prompt
    )

    categoria = response.text.strip()

    if categoria not in categorias:
        return "Otros"

    return categoria


# =====================================================
# TOOLS GEOGRAFÍA
# =====================================================

def obtener_capital(pais: str) -> str:

    capitales = {
        "Francia": "París",
        "Japón": "Tokio",
        "Argentina": "Buenos Aires"
    }

    return capitales.get(
        pais,
        "Capital desconocida"
    )


def obtener_pais(capital: str) -> str:

    capitales = {
        "Francia": "París",
        "Japón": "Tokio",
        "Argentina": "Buenos Aires"
    }

    for pais, cap in capitales.items():

        if cap.lower() == capital.lower():
            return pais

    return "País desconocido"


# =====================================================
# TOOL REGISTRO DE GASTOS
# =====================================================

def registrar_gasto(
    description: str,
    amount: float
) -> str:

    categoria = clasificar_gasto(
        description
    )

    # Más adelante:
    # guardar_en_bd(
    #     description,
    #     amount,
    #     categoria
    # )

    return (
        f"Gasto registrado.\n"
        f"Descripción: {description}\n"
        f"Monto: ${amount:.2f}\n"
        f"Categoría: {categoria}"
    )


# =====================================================
# AGENTE DE VOZ
# =====================================================

def procesar_audio_con_tools(audio_bytes):

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(
                data=audio_bytes,
                mime_type="audio/ogg"
            )
        ],
        config=types.GenerateContentConfig(
            system_instruction="""
Eres un asistente de Telegram.

Escucha el audio.

Si preguntan por la capital de un país:
usa obtener_capital.

Si preguntan por el país de una capital:
usa obtener_pais.

Si desean registrar un gasto:

- Extrae descripción.
- Extrae monto.
- Usa registrar_gasto.

Si falta la descripción o el monto:

'Debes incluir tanto la descripción como el monto.'

Responde siempre en español.
""",
            tools=[
                obtener_capital,
                obtener_pais,
                registrar_gasto
            ]
        )
    )

    return response.text