# src/services/voice_agent_service.py

from google import genai
from google.genai import types

from src.config import GEMINI_API_KEY, LATITUDE, LONGITUDE
from src.logger import logger

from src.services.expense_service import (
    crear_gasto_pendiente,
    obtener_gasto_pendiente,
    confirmar_gasto,
    cancelar_gasto,
    actualizar_categoria
)

from src.services.geography_service import (
    obtener_capital,
    obtener_pais
)

from src.services.weather_service import (
    get_weather
)

from src.services.conversation_state_service import (
    obtener_estado,
    ESTADO_IDLE,
    ESTADO_ESPERANDO_CONFIRMACION_GASTO
)

client = genai.Client(
    api_key=GEMINI_API_KEY
)

def get_clima_local():
    return get_weather(
        latitud=LATITUDE,
        longitud=LONGITUDE
    )

def transcribir_audio(audio_bytes):

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=[
            """
            Transcribe exactamente el audio.
            Devuelve únicamente la transcripción.
            No expliques.
            No interpretes.
            """,
            types.Part.from_bytes(
                data=audio_bytes,
                mime_type="audio/ogg"
            )
        ]
    )

    return response.text.strip()

def procesar_estado_idle(
    texto: str,
    user_id: int
):

    prompt = f"""
Usuario dijo: {texto}

Analiza la intención.

Si desea registrar un gasto, devuelve exactamente:
GASTO|descripcion|monto

Ejemplo:
GASTO|Carrefour|15000

Para consultas de geografía utiliza las herramientas obtener_capital y obtener_pais, respondiendo de la siguiente manera:
La capital de Francia es Paris.

Para consultas sobre clima utiliza la herramienta get_clima_local

Para cualquier otra consulta responde que no conoces la respuesta.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[
                obtener_capital,
                obtener_pais,
                get_clima_local
            ]
        )
    )

    resultado = response.text.strip()

    # --------------------------------------------------
    # GASTOS
    # --------------------------------------------------

    if resultado.startswith("GASTO|"):

        partes = resultado.split("|")

        descripcion = partes[1]
        monto = float(partes[2])

        categoria = crear_gasto_pendiente(
            user_id,
            descripcion,
            monto
        )

        return (
            f"Detecté un gasto.\n\n"
            f"Descripción: {descripcion}\n"
            f"Monto: ${monto:.2f}\n"
            f"Categoría sugerida: {categoria}\n\n"
            f"¿Deseas registrarlo?"
        )
    
    return resultado


def procesar_confirmacion_gasto(
    texto: str,
    user_id: int
):

    prompt = f"""
Usuario respondió: {texto}

Clasifica únicamente como:

CONFIRMAR
CANCELAR
CAMBIAR_CATEGORIA
OTRO

Devuelve una sola palabra.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=prompt
    )

    accion = response.text.strip().upper()

    if accion == "CONFIRMAR":
        return confirmar_gasto(
            user_id
        )

    if accion == "CANCELAR":
        return cancelar_gasto(
            user_id
        )

    categorias = [
        "Viveres",
        "Transporte",
        "Servicios",
        "Entretenimiento",
        "Tecnologia",
        "Salud",
        "Educacion",
        "Otros"
    ]

    texto_lower = texto.lower()

    for categoria in categorias:

        if categoria.lower() in texto_lower:

            actualizar_categoria(
                user_id,
                categoria
            )

            return (
                f"Categoría actualizada a "
                f"{categoria}.\n\n"
                f"¿Deseas registrarlo?"
            )

    return (
        "No entendí la respuesta.\n\n"
        "Puedes decir:\n"
        "- confirmar\n"
        "- cancelar\n"
        "- una categoría"
    )


def procesar_audio_con_tools(
    audio_bytes: bytes,
    user_id: int
):
    
    estado = obtener_estado(user_id)
    estado_actual = estado["estado"]

    logger.info(f"El estado actual={estado_actual}")

    texto = transcribir_audio(audio_bytes)

    if estado_actual == ESTADO_IDLE:
        return procesar_estado_idle(texto, user_id)

    if estado_actual == ESTADO_ESPERANDO_CONFIRMACION_GASTO:
        return procesar_confirmacion_gasto(texto, user_id)

    return ("Estado desconocido, no se que responder.")